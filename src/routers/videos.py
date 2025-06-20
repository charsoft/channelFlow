import asyncio
import json
import os
from datetime import datetime

from fastapi import APIRouter, Depends, Request, HTTPException, status
from fastapi.responses import JSONResponse
from sse_starlette.sse import EventSourceResponse
from pydantic import BaseModel
from google.cloud import storage, firestore
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

from ..database import db
from ..agents.ingestion import get_video_id
from ..events import NewVideoDetected, TranscriptReady, ContentAnalysisComplete, CopyReady
from ..event_bus import event_bus
from ..security import decrypt_data, encrypt_data
from .auth import get_current_user

router = APIRouter()

# This is a simplification. You'd likely have a shared storage client.
storage_client = storage.Client()
bucket_name = os.environ.get("GCS_BUCKET_NAME")

def _get_signed_url(gcs_uri: str) -> str:
    """Converts a GCS URI to a signed URL."""
    if not gcs_uri or not bucket_name:
        return None
    try:
        blob_name = gcs_uri.replace(f"gs://{bucket_name}/", "")
        bucket = storage_client.bucket(bucket_name)
        blob = bucket.blob(blob_name)
        
        signed_url = blob.generate_signed_url(
            version="v4",
            expiration=3600,  # 1 hour
            method="GET",
        )
        return signed_url
    except Exception as e:
        print(f"Error generating signed URL for {gcs_uri}: {e}")
        return None

class IngestUrlRequest(BaseModel):
    url: str
    force: bool = False

class RetriggerRequest(BaseModel):
    video_id: str
    stage: str # e.g., "transcription", "analysis", "copywriting", "visuals"

@router.post("/api/ingest-url")
async def ingest_url(request: IngestUrlRequest, current_user: dict = Depends(get_current_user)):
    """
    API endpoint to manually trigger ingestion. Uses the user's credentials.
    Requires our internal JWT authentication.
    """
    try:
        user_id = current_user.get("uid")
        print(f"Request received from authenticated user: {user_id}")

        # --- Get User's YouTube Credentials ---
        cred_doc_ref = db.collection("user_credentials").document(user_id)
        cred_doc = await cred_doc_ref.get()

        if not cred_doc.exists:
            return JSONResponse(status_code=403, content={"message": "User has not connected their YouTube account. Please authorize.", "code": "AUTH_REQUIRED"})

        encrypted_creds = cred_doc.to_dict().get("credentials")
        decrypted_creds_json = decrypt_data(encrypted_creds)
        creds = Credentials.from_authorized_user_info(json.loads(decrypted_creds_json))
        
        if creds.expired and creds.refresh_token:
            print(f"User {user_id} credentials expired. They will be refreshed on next API call.")

        youtube = build('youtube', 'v3', credentials=creds)
        
        video_id = get_video_id(request.url)
        if not video_id:
            return JSONResponse(status_code=400, content={"message": "Invalid YouTube URL"})

        video_doc_ref = db.collection("videos").document(video_id)
        doc = await video_doc_ref.get()

        if doc.exists and not request.force:
            print(f"Video {video_id} already exists. Returning existing video_id to trigger status stream.")
            # The frontend will immediately connect to the SSE stream, which will
            # send the latest status from the database. This avoids a separate
            # code path on the client.
            return JSONResponse(status_code=202, content={"message": "Video processing already in progress or complete.", "video_id": video_id})

        if doc.exists and request.force:
            print(f"Forcing reprocessing for video {video_id}. Deleting old data...")
            # ... (code for deleting old data)
            video_data = doc.to_dict()
            bucket_name = os.getenv("GCS_BUCKET_NAME")

            if bucket_name:
                storage_client = storage.Client()
                bucket = storage_client.bucket(bucket_name)

                gcs_uri_fields = ["transcript_gcs_uri", "analysis_gcs_uri", "substack_gcs_uri"]
                
                for field in gcs_uri_fields:
                    if gcs_uri := video_data.get(field):
                        try:
                            blob_path = gcs_uri.replace(f"gs://{bucket_name}/", "")
                            blob = bucket.blob(blob_path)
                            if await asyncio.to_thread(blob.exists):
                                await asyncio.to_thread(blob.delete)
                                print(f"   Deleted GCS file: {blob.name}")
                        except Exception as e:
                            print(f"   Could not delete GCS file from URI {gcs_uri}: {e}")

                if image_urls := video_data.get("image_urls"):
                    for url in image_urls:
                        try:
                            blob_path = url.replace(f"https://storage.googleapis.com/{bucket_name}/", "")
                            blob = bucket.blob(blob_path)
                            if await asyncio.to_thread(blob.exists):
                                await asyncio.to_thread(blob.delete)
                                print(f"   Deleted GCS image: {blob.name}")
                        except Exception as e:
                            print(f"   Could not delete GCS image from URL {url}: {e}")
            
            await video_doc_ref.delete()
            print(f"   Deleted Firestore document: {video_id}")

        try:
            video_response = await asyncio.to_thread(
                youtube.videos().list(part="snippet", id=video_id).execute
            )
            if not video_response.get("items"):
                return JSONResponse(status_code=400, content={"message": "Could not retrieve video title (video may be private or not exist)."})
            video_title = video_response["items"][0]["snippet"]["title"]
        except Exception as e:
            print(f"YouTube API Error for user {user_id}: {e}")
            return JSONResponse(status_code=403, content={"message": "Failed to access YouTube API. Your credentials may be invalid or revoked. Please try connecting your account again.", "code": "AUTH_REQUIRED"})

        # Save the refreshed credentials back to Firestore
        new_creds_json = creds.to_json()
        encrypted_new_creds = encrypt_data(new_creds_json.encode())
        await cred_doc_ref.set({"credentials": encrypted_new_creds})
        
        if not video_title:
             return JSONResponse(status_code=400, content={"message": "Could not retrieve video title."})

        # Create the initial video document in Firestore HERE
        await db.collection("videos").document(video_id).set({
            "video_id": video_id,
            "video_url": request.url,
            "video_title": video_title,
            "user_id": user_id,
            "status": "ingesting",
            "status_message": "Starting ingestion process...",
            "created_at": firestore.SERVER_TIMESTAMP,
            "updated_at": firestore.SERVER_TIMESTAMP,
        })
        print(f"   Saved initial data for {video_id} to Firestore.")

        event = NewVideoDetected(
            video_id=video_id,
            video_url=request.url,
            video_title=video_title,
            user_id=user_id
        )
        await event_bus.publish(event)

        return JSONResponse(status_code=202, content={"message": "Video ingestion started.", "video_id": video_id})

    except Exception as e:
        import traceback
        print(f"Error in /ingest-url: {e}\n{traceback.format_exc()}")
        return JSONResponse(status_code=500, content={"message": "An internal error occurred."})

@router.get("/api/status/{video_id}")
async def get_status(video_id: str):
    video_doc_ref = db.collection("videos").document(video_id)
    doc = await video_doc_ref.get()
    if not doc.exists:
        return JSONResponse(status_code=404, content={"message": "Video not found."})
    
    data = doc.to_dict()
    for key, value in data.items():
        if isinstance(value, datetime):
            data[key] = value.isoformat()
    
    return JSONResponse(status_code=200, content={"data": data})

@router.get("/api/stream-status/{video_id}")
async def stream_status(request: Request, video_id: str):
    async def event_generator():
        last_known_status = None
        try:
            while True:
                if await request.is_disconnected():
                    print(f"Client disconnected from {video_id} stream.")
                    break

                video_doc_ref = db.collection("videos").document(video_id)
                doc = await video_doc_ref.get()

                if not doc.exists:
                    yield { "event": "message", "data": json.dumps({"status": "not_found", "message": "Video not found."})}
                    break
                
                data = doc.to_dict()
                current_status = data.get("status")

                if current_status != last_known_status:
                    for key, value in data.items():
                        if isinstance(value, datetime):
                            data[key] = value.isoformat()
                    
                    yield { "event": "message", "data": json.dumps(data) }
                    last_known_status = current_status
                
                await asyncio.sleep(1)

        except Exception as e:
            print(f"Error in SSE stream for {video_id}: {e}")
        finally:
            print(f"Closing SSE stream for {video_id}.")

    return EventSourceResponse(event_generator())

@router.post("/api/re-trigger")
async def re_trigger(request: RetriggerRequest):
    video_doc_ref = db.collection("videos").document(request.video_id)
    doc = await video_doc_ref.get()

    if not doc.exists:
        return JSONResponse(status_code=404, content={"message": "Video not found."})

    video_data = doc.to_dict()
    video_title = video_data.get("video_title", "Unknown Title")
    user_id = video_data.get("user_id")
    
    event_to_publish = None
    if request.stage == "ingestion":
        if not user_id:
            return JSONResponse(status_code=400, content={"message": "Cannot re-trigger ingestion without a user_id."})
        # Note: This effectively restarts the entire process.
        # We need to clean up old data first, just like in the /ingest-url endpoint.
        print(f"Force re-ingesting for video {request.video_id} by user request.")
        # This part is complex, involving GCS file deletion. For now, we will just re-trigger the event.
        # A more robust solution would be to call a shared cleanup function.
        await video_doc_ref.update({"status": "re-triggering ingestion", "status_message": "Restarting process from the beginning."})
        event_to_publish = NewVideoDetected(
            video_id=request.video_id,
            video_url=video_data.get("video_url"),
            video_title=video_title,
            user_id=user_id
        )
    elif request.stage == "transcription":
        if not user_id:
            return JSONResponse(status_code=400, content={"message": "Cannot re-trigger transcription without a user_id."})
        await video_doc_ref.update({"status": "re-triggering transcription"})
        # This assumes the video is already downloaded and is just re-running the transcription model.
        # Currently, the `NewVideoDetected` event is the only way to trigger transcription.
        # This is a bit of a misnomer, but it's how the system is wired.
        event_to_publish = NewVideoDetected(
            video_id=request.video_id,
            video_url=video_data.get("video_url"),
            video_title=video_title,
            user_id=user_id
        )
    elif request.stage == "analysis":
        await video_doc_ref.update({"status": "re-triggering analysis"})
        event_to_publish = TranscriptReady(
            video_id=request.video_id,
            video_title=video_title,
            transcript_gcs_uri=video_data.get("transcript_gcs_uri"),
            user_id=user_id
        )
    elif request.stage == "copywriting":
        await video_doc_ref.update({"status": "re-triggering copywriting"})
        event_to_publish = ContentAnalysisComplete(
            video_id=request.video_id,
            video_title=video_title,
            structured_data=video_data.get("structured_data"),
            user_id=user_id
        )
    elif request.stage == "visuals":
        await video_doc_ref.update({"status": "re-triggering visuals"})
        event_to_publish = CopyReady(
            video_id=request.video_id,
            video_title=video_title,
            copy_gcs_uri=video_data.get("substack_gcs_uri"),
            user_id=user_id
        )
        
    if event_to_publish:
        await event_bus.publish(event_to_publish)
        return JSONResponse(status_code=200, content={"message": f"Stage '{request.stage}' re-triggered."})
    else:
        return JSONResponse(status_code=400, content={"message": f"Invalid stage '{request.stage}' provided."})

@router.get("/api/videos")
async def get_videos():
    try:
        # Fetch all documents without server-side sorting to ensure none are missed
        videos_ref = db.collection("videos")
        docs = videos_ref.stream()
        videos = []
        async for doc in docs:
            video_data = doc.to_dict()
            video_data["id"] = doc.id
            
            # Generate signed URLs for thumbnails to display on the dashboard
            thumbnail_urls = []
            image_gcs_uris = video_data.get("image_gcs_uris", [])
            on_demand_thumbnails = video_data.get("on_demand_thumbnails", [])

            # Get up to 4 URLs, prioritizing on-demand ones
            for item in reversed(on_demand_thumbnails): # newest first
                if len(thumbnail_urls) < 4 and "gcs_uri" in item:
                    thumbnail_urls.append(_get_signed_url(item["gcs_uri"]))
            
            for uri in image_gcs_uris:
                if len(thumbnail_urls) < 4:
                    thumbnail_urls.append(_get_signed_url(uri))
            
            video_data["thumbnails"] = [url for url in thumbnail_urls if url]

            for key, value in video_data.items():
                if isinstance(value, datetime):
                    video_data[key] = value.isoformat()
            videos.append(video_data)
        
        # Sort in the application to handle missing 'received_at' fields gracefully
        videos.sort(key=lambda v: v.get('received_at', '1970-01-01T00:00:00Z'), reverse=True)

        return {"videos": videos}
    except Exception as e:
        print(f"Error fetching all videos: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch videos.")

@router.get("/api/video/{video_id}")
async def get_video(video_id: str):
    try:
        doc_ref = db.collection("videos").document(video_id)
        video_doc = await doc_ref.get()
        if not video_doc.exists:
            raise HTTPException(status_code=404, detail="Video not found")
    
        video_data = video_doc.to_dict()

        # Convert image_gcs_uris to signed URLs
        if "image_gcs_uris" in video_data and video_data["image_gcs_uris"]:
            video_data["image_urls"] = [_get_signed_url(uri) for uri in video_data["image_gcs_uris"]]

        # Convert on_demand_thumbnails gcs_uris to signed URLs and datetimes
        if "on_demand_thumbnails" in video_data and video_data["on_demand_thumbnails"]:
            for item in video_data["on_demand_thumbnails"]:
                if "gcs_uri" in item:
                    item["image_url"] = _get_signed_url(item["gcs_uri"])
                if "created_at" in item and isinstance(item["created_at"], datetime):
                    item["created_at"] = item["created_at"].isoformat()

        # Convert top-level datetimes
        for key, value in video_data.items():
            if isinstance(value, datetime):
                video_data[key] = value.isoformat()

        return {"video": video_data}
    except Exception as e:
        print(f"Error fetching video {video_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch video.")

@router.delete("/api/videos/{video_id}")
async def delete_video(video_id: str):
    pass

# This is a duplicate and insecure endpoint. Removing it.
# @router.post("/api/ingest")
# async def ingest_video(request: IngestRequest, app_request: Request):
#     """
#     DEPRECATED: This endpoint is for automated ingestion and does not use
#     the user's credentials. It's less secure and should not be used
#     by the frontend.
#     """
#     # ... implementation ... 