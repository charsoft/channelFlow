import asyncio
import json
import os
from datetime import datetime, timedelta
import tempfile
import uuid

from fastapi import APIRouter, Depends, Request, HTTPException, status, Query
from fastapi.responses import JSONResponse
from sse_starlette.sse import EventSourceResponse
from pydantic import BaseModel
from google.cloud import storage, firestore
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

from ..database import db
from ..agents.ingestion import get_video_id
from ..events import NewVideoDetected, TranscriptReady, ContentAnalysisComplete, CopyReady, IngestedVideo
from ..event_bus import event_bus
from ..security import decrypt_data, encrypt_data
from .auth import get_current_user, get_current_user_from_query
from ..video_processing import create_vertical_clip
from ..agents.visuals import VisualsAgent

router = APIRouter()

# This is a simplification. You'd likely have a shared storage client.
storage_client = storage.Client()
bucket_name = os.environ.get("GCS_BUCKET_NAME")

def serialize_firestore_doc(doc):
    """
    Recursively converts Firestore-specific types in a document to JSON-serializable formats.
    This version uses duck-typing to avoid brittle internal imports.
    """
    if doc is None:
        return None

    def convert(value):
        # Check for Firestore's DatetimeWithNanoseconds by checking for a unique method
        if hasattr(value, 'to_datetime'):
            return value.to_datetime().isoformat()
        # Handle standard Python datetime objects
        if isinstance(value, datetime):
            return value.isoformat()
        # Recurse into dicts and lists
        if isinstance(value, dict):
            return {k: convert(v) for k, v in value.items()}
        if isinstance(value, list):
            return [convert(item) for item in value]
        # Return all other types as-is
        return value

    return convert(doc)

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
            print(f"Video {video_id} already exists. Returning full video data.")
            video_data = serialize_firestore_doc(doc.to_dict())
            video_data["video_id"] = doc.id
            
            if image_urls := video_data.get("image_urls"):
                video_data["image_urls"] = [_get_signed_url(url) for url in image_urls if url]
            
            if on_demand_thumbs := video_data.get("on_demand_thumbnails"):
                video_data["on_demand_thumbnails"] = [
                    {**thumb, "image_url": _get_signed_url(thumb["image_url"])}
                    for thumb in on_demand_thumbs if thumb.get("image_url")
                ]
            
            print(json.dumps(video_data, indent=2))

            return JSONResponse(status_code=200, content={"message": "Video already exists.", "video_id": video_id, "data": video_data, "status": "exists"})

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
    
    data = serialize_firestore_doc(doc.to_dict())
    return JSONResponse(status_code=200, content={"data": data})

@router.get("/api/stream-status/{video_id}")
async def stream_status(request: Request, video_id: str, token: str):
    async def event_generator():
        try:
            # First, authenticate the user from the token.
            current_user = await get_current_user_from_query(token)

            # Then, perform the authorization check.
            video_doc_ref = db.collection("videos").document(video_id)
            doc = await video_doc_ref.get()

            if not doc.exists:
                yield { "event": "message", "data": json.dumps({"status": "not_found", "message": "Video not found."})}
                return
            
            video_data = doc.to_dict()
            if video_data.get("user_id") != current_user.get("uid"):
                yield { "event": "error", "data": json.dumps({"status": "error", "message": "Unauthorized."})}
                return

            # If we've gotten this far, user is auth'd and auth'z. Start the stream.
            while True:
                if await request.is_disconnected():
                    print(f"Client disconnected from {video_id} stream.")
                    break

                # We can re-fetch the document in the loop to get live updates
                doc_snapshot = await video_doc_ref.get()

                if not doc_snapshot.exists:
                    yield { "event": "message", "data": json.dumps({"status": "not_found", "message": "Video not found."})}
                    break
                
                # FIX: Always send the latest data. The frontend can decide what to do with it.
                # This ensures that when a client connects, it immediately gets the
                # current state, and it prevents the connection from closing due to inactivity.
                data = serialize_firestore_doc(doc_snapshot.to_dict())
                
                yield { "event": "message", "data": json.dumps(data) }
                
                # We can increase the sleep time slightly to reduce the frequency of reads
                await asyncio.sleep(2)

        except HTTPException as e:
            # Catch auth exceptions and send a proper SSE error
            yield { "event": "error", "data": json.dumps({"status": "error", "message": e.detail or "Authentication failed" }) }
        except Exception as e:
            print(f"Error in SSE stream for {video_id}: {e}")
            import traceback
            traceback.print_exc()
            yield { "event": "error", "data": json.dumps({"status": "error", "message": "An internal error occurred on the stream."}) }
        finally:
            print(f"Closing SSE stream for {video_id}.")

    return EventSourceResponse(event_generator())

@router.post("/api/re-trigger")
async def re_trigger(request: RetriggerRequest, current_user: dict = Depends(get_current_user)):
    video_doc_ref = db.collection("videos").document(request.video_id)
    doc = await video_doc_ref.get()

    if not doc.exists:
        return JSONResponse(status_code=404, content={"message": "Video not found."})

    video_data = doc.to_dict()
    video_title = video_data.get("video_title", "Unknown Title")
    user_id = video_data.get("user_id")
    
    event_to_publish = None
    if request.stage == "ingestion":
        # Note: This is a destructive action and should be used with care.
        # It's simplified here for brevity. A real implementation would have more safeguards.
        await video_doc_ref.update({"status": "re-triggering ingestion", "status_message": "Re-starting process from the beginning."})
        event_to_publish = NewVideoDetected(
            video_id=request.video_id,
            video_url=video_data.get("video_url"),
            video_title=video_title,
            user_id=user_id
        )
    elif request.stage == "transcription":
        # Re-running transcription starts from the very beginning of that phase.
        await video_doc_ref.update({"status": "pending_transcription_rerun", "status_message": "Re-running transcription..."})
        event_to_publish = IngestedVideo(
            video_id=request.video_id,
            gcs_uri=video_data.get("original_video_gcs_uri"), # The Ingestion agent needs the location of the video file
            video_title=video_title,
            user_id=user_id
        )
    elif request.stage == "analysis":
        transcript_gcs_uri = video_data.get("transcript_gcs_uri")
        await video_doc_ref.update({"status": "re-triggering analysis"})
        event_to_publish = TranscriptReady(
            video_id=request.video_id,
            video_title=video_title,
            transcript_gcs_uri=transcript_gcs_uri
        )
    elif request.stage == "copywriting":
        structured_data = video_data.get("structured_data")
        if not structured_data:
            raise HTTPException(status_code=400, detail="Cannot re-trigger copywriting without analysis data.")
        
        await video_doc_ref.update({"status": "pending_copywriting_rerun", "status_message": "Re-running copywriting..."})
        event_to_publish = ContentAnalysisComplete(
            video_id=request.video_id,
            video_title=video_title,
            structured_data=structured_data
        )
    elif request.stage == "visuals":
        structured_data = video_data.get("structured_data")
        # The new architecture requires prompts to be in the structured data.
        if not structured_data or not structured_data.get("image_prompts"):
            raise HTTPException(status_code=400, detail="Cannot re-trigger visuals without image prompts from the analysis stage.")

        await video_doc_ref.update({"status": "pending_visuals_rerun", "status_message": "Re-running visuals..."})
        # The VisualsAgent is a "dumb" executor, so we fire the same event that the AnalysisAgent does.
        event_to_publish = ContentAnalysisComplete(
            video_id=request.video_id,
            video_title=video_title,
            structured_data=structured_data # This now correctly contains the prompts
        )

    if event_to_publish:
        await event_bus.publish(event_to_publish)
        return JSONResponse(status_code=200, content={"message": f"Stage '{request.stage}' re-triggered."})
    else:
        return JSONResponse(status_code=400, content={"message": f"Invalid stage '{request.stage}' provided."})

@router.get("/api/videos")
async def get_videos(current_user: dict = Depends(get_current_user)):
    try:
        user_id = current_user.get("uid")
        if not user_id:
            raise HTTPException(status_code=403, detail="Could not verify user.")

        # Fetch documents for the specific user
        videos_ref = db.collection("videos").where("user_id", "==", user_id)
        docs = videos_ref.stream()
        videos = []
        async for doc in docs:
            video_data = serialize_firestore_doc(doc.to_dict())
            video_data["video_id"] = doc.id
            
            # Generate signed URLs for thumbnails if they exist
            if image_urls := video_data.get("image_urls"):
                video_data["image_urls"] = [_get_signed_url(url) for url in image_urls if url]
            
            if on_demand_thumbs := video_data.get("on_demand_thumbnails"):
                video_data["on_demand_thumbnails"] = [
                    {**thumb, "image_url": _get_signed_url(thumb["image_url"])}
                    for thumb in on_demand_thumbs if thumb.get("image_url")
                ]

            videos.append(video_data)
        
        # Sort in the application to handle missing 'created_at' fields gracefully
        videos.sort(key=lambda v: v.get('created_at', '1970-01-01T00:00:00Z'), reverse=True)

        return {"videos": videos}
    except Exception as e:
        print(f"Error fetching user videos: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch videos.")

@router.get("/api/video/{video_id}")
async def get_video(video_id: str):
    """
    Retrieves details for a single video.
    """
    video_doc_ref = db.collection("videos").document(video_id)
    doc = await video_doc_ref.get()

    if not doc.exists:
        raise HTTPException(status_code=404, detail="Video not found.")

    video_data = serialize_firestore_doc(doc.to_dict())
    video_data["video_id"] = doc.id
    
    # Generate signed URLs for any GCS URIs
    if image_urls := video_data.get("image_urls"):
        video_data["image_urls"] = [_get_signed_url(url) for url in image_urls if url]
        
    # Convert on_demand_thumbnails gcs_uris to signed URLs and datetimes
    if "on_demand_thumbnails" in video_data and video_data["on_demand_thumbnails"]:
        for item in video_data["on_demand_thumbnails"]:
            if "gcs_uri" in item:
                item["image_url"] = _get_signed_url(item["gcs_uri"])
            if "created_at" in item and isinstance(item["created_at"], datetime):
                item["created_at"] = item["created_at"].isoformat()

    return {"video": video_data}

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