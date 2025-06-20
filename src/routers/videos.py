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
from ..events import NewVideoDetected, TranscriptReady, ContentAnalysisComplete, CopyReady
from ..event_bus import event_bus
from ..security import decrypt_data, encrypt_data
from .auth import get_current_user
from ..video_processing import create_vertical_clip

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
        blob = storage_client.bucket(bucket_name).blob(blob_name)
        
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
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Could not identify user from token.",
            )
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
        return JSONResponse(status_code=200, content={"message": f"Stage '{request.stage}' re-triggered successfully."})
    else:
        return JSONResponse(status_code=400, content={"message": f"Invalid stage '{request.stage}' provided."})

@router.get("/api/videos")
async def get_videos(
    current_user: dict = Depends(get_current_user),
    limit: int = 5,
    offset: int = 0
):
    """
    Retrieves videos processed by the currently authenticated user, with pagination.
    """
    user_id = current_user.get("uid")
    
    # Base query
    query = db.collection("videos").where("user_id", "==", user_id)
    
    # Order by 'created_at' if available, otherwise 'created_at'
    # Firestore requires the first orderBy field to be in the inequality filter if one exists
    # Since we don't have an inequality, we can order by any field.
    # However, to gracefully handle missing fields, it's often better to ensure 
    # the field exists or query separately. For this use case, we assume most will have it.
    # A more robust solution might involve a separate 'search' index or default values.
    query = query.order_by("created_at", direction=firestore.Query.DESCENDING)
    
    # Apply pagination
    query = query.limit(limit).offset(offset)
    
    docs = query.stream()

    videos = []
    async for doc in docs:
        video_data = doc.to_dict()
        video_data["video_id"] = doc.id
        
        if created_at := video_data.get("created_at"):
            if isinstance(created_at, datetime):
                 video_data["created_at"] = created_at.isoformat()
            else:
                # Handle potential timestamp strings if data format is inconsistent
                video_data["created_at"] = str(created_at)
        
        if processed_at := video_data.get("processed_at"):
            if isinstance(processed_at, datetime):
                 video_data["processed_at"] = processed_at.isoformat()
            else:
                video_data["processed_at"] = str(processed_at)

        # Generate signed URLs for thumbnails if they exist
        if image_urls := video_data.get("image_urls"):
            video_data["image_urls"] = [_get_signed_url(url) for url in image_urls if url]
        
        if on_demand_thumbs := video_data.get("on_demand_thumbnails"):
             video_data["on_demand_thumbnails"] = [
                {**thumb, "image_url": _get_signed_url(thumb["image_url"])}
                for thumb in on_demand_thumbs if thumb.get("image_url")
            ]

        videos.append(video_data)

    return {"videos": videos}

@router.get("/api/video/{video_id}")
async def get_video(video_id: str, current_user: dict = Depends(get_current_user)):
    """
    Retrieves details for a single video, ensuring it belongs to the authenticated user.
    """
    video_doc_ref = db.collection("videos").document(video_id)
    doc = await video_doc_ref.get()

    if not doc.exists:
        raise HTTPException(status_code=404, detail="Video not found.")

    video_data = doc.to_dict()
    
    # Security Check: Ensure the video belongs to the current user
    if video_data.get("user_id") != current_user.get("uid"):
        raise HTTPException(status_code=403, detail="Not authorized to view this video.")

    video_data["video_id"] = doc.id
    
    for key, value in video_data.items():
        if isinstance(value, datetime):
            video_data[key] = value.isoformat()

    # Generate signed URLs for any GCS URIs
    if image_urls := video_data.get("image_urls"):
        video_data["image_urls"] = [_get_signed_url(url) for url in image_urls if url]
        
    if on_demand_thumbs := video_data.get("on_demand_thumbnails"):
        video_data["on_demand_thumbnails"] = [
            {**thumb, "image_url": _get_signed_url(thumb["image_url"])}
            for thumb in on_demand_thumbs if thumb.get("image_url")
        ]

    return {"video": video_data}

@router.delete("/api/videos/{video_id}")
async def delete_video(video_id: str, current_user: dict = Depends(get_current_user)):
    """
    Deletes a video and its associated data, ensuring it belongs to the authenticated user.
    """
    video_doc_ref = db.collection("videos").document(video_id)
    doc = await video_doc_ref.get()

    if not doc.exists:
        raise HTTPException(status_code=404, detail="Video not found.")

    video_data = doc.to_dict()
    
    # Security Check
    if video_data.get("user_id") != current_user.get("uid"):
        raise HTTPException(status_code=403, detail="Not authorized to delete this video.")

    # --- Deletion from GCS ---
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
    print(f"   Deleted Firestore document for user {current_user.get('uid')}: {video_id}")

    return JSONResponse(status_code=200, content={"message": "Video and all associated data deleted successfully."})

@router.post("/api/video/{video_id}/generate-prompts")
async def generate_prompts(video_id: str, request: Request, current_user: dict = Depends(get_current_user)):
    """ Generate image prompts for a given video """
    body = await request.json()
    context = body.get("context")

    if not context:
        raise HTTPException(status_code=400, detail="Context (video summary) is required.")

    # Security Check
    video_doc_ref = db.collection("videos").document(video_id)
    doc = await video_doc_ref.get()
    if not doc.exists:
        raise HTTPException(status_code=404, detail="Video not found")
    if doc.to_dict().get("user_id") != current_user.get("uid"):
        raise HTTPException(status_code=403, detail="Not authorized to generate prompts for this video.")

    # This would call your LLM to generate prompts. For now, returning dummy data.
    # In a real app, this would be: `prompts = await llm_service.generate_prompts(context)`
    await asyncio.sleep(2) # Simulate network call
    prompts = [
        f"A cinematic shot of a computer screen showing code, reflecting the video's theme: '{context[:30]}...'",
        f"An abstract visual representation of '{context.split()[0]} {context.split()[1]}'.",
        "A minimalist graphic with a single, compelling icon related to the video's main topic.",
        f"Photo of a person looking thoughtfully at a whiteboard with diagrams about '{context[:20]}...'"
    ]
    return JSONResponse(status_code=200, content={"prompts": prompts})

class ImageGenerationRequest(BaseModel):
    prompt: str
    model_name: str

@router.post("/api/video/{video_id}/generate-image")
async def generate_image(video_id: str, request: ImageGenerationRequest, current_user: dict = Depends(get_current_user)):
    # Security Check
    user_id = current_user.get("uid")
    video_doc_ref = db.collection("videos").document(video_id)
    video_doc = await video_doc_ref.get()

    if not video_doc.exists or video_doc.to_dict().get("user_id") != user_id:
        raise HTTPException(status_code=403, detail="User does not have access to this video")

    # This is a placeholder for the actual image generation logic
    # In a real app, this would call a service like Vertex AI's Imagen
    print(f"Generating image for video {video_id} with prompt: '{request.prompt}' using model {request.model_name}")

    # Simulate generation and upload
    await asyncio.sleep(5) 
    
    # Create a unique filename
    unique_id = uuid.uuid4()
    file_name = f"on-demand-thumbnails/{video_id}/{unique_id}.png"
    
    # In a real scenario, you'd get the image bytes from the generation service
    # Here, we'll just create a placeholder file path for the GCS URI
    gcs_uri = f"gs://{bucket_name}/{file_name}"

    # Simulate uploading to GCS (we don't actually upload anything here)
    print(f"Simulated upload to {gcs_uri}")

    image_url = f"https://storage.googleapis.com/{bucket_name}/{file_name}"
    
    new_thumbnail_data = {
        "prompt": request.prompt,
        "model": request.model_name,
        "image_url": image_url, # Placeholder URL
        "gcs_uri": gcs_uri,
        "created_at": firestore.SERVER_TIMESTAMP
    }

    await video_doc_ref.update({
        "on_demand_thumbnails": firestore.ArrayUnion([new_thumbnail_data]),
        "updated_at": firestore.SERVER_TIMESTAMP
    })
    
    # The Firestore timestamp is an object that can't be directly serialized to JSON.
    # For the return value, we'll convert it to an ISO 8601 string.
    # The frontend already handles this correctly for display.
    response_data = new_thumbnail_data.copy()
    response_data["created_at"] = datetime.utcnow().isoformat()

    return JSONResponse(status_code=200, content=response_data)

@router.post("/api/video/{video_id}/generate-clip")
async def generate_clip(video_id: str, request: Request, current_user: dict = Depends(get_current_user)):
    """ Generate a short video clip from the original video. """
    body = await request.json()
    start_time = float(body.get("start_time"))
    end_time = float(body.get("end_time"))
    title = body.get("suggested_title", "Untitled Clip")

    # Security Check
    video_doc_ref = db.collection("videos").document(video_id)
    doc = await video_doc_ref.get()
    if not doc.exists:
        raise HTTPException(status_code=404, detail="Video not found")
    
    video_data = doc.to_dict()
    if video_data.get("user_id") != current_user.get("uid"):
        raise HTTPException(status_code=403, detail="Not authorized.")
    
    original_video_gcs_uri = video_data.get("original_video_gcs_uri")
    if not original_video_gcs_uri:
        raise HTTPException(status_code=400, detail="Original video not found in storage.")

    with tempfile.TemporaryDirectory() as tmpdir:
        try:
            # Download, process, and upload the clip
            source_blob_name = original_video_gcs_uri.replace(f"gs://{bucket_name}/", "")
            source_blob = storage_client.bucket(bucket_name).blob(source_blob_name)
            original_filename = os.path.basename(source_blob_name)
            local_input_path = os.path.join(tmpdir, original_filename)
            await asyncio.to_thread(source_blob.download_to_filename, local_input_path)

            clip_id = str(uuid.uuid4())
            local_output_path = os.path.join(tmpdir, f"{clip_id}.mp4")
            
            await asyncio.to_thread(
                create_vertical_clip,
                input_path=local_input_path,
                output_path=local_output_path,
                start_time=start_time,
                end_time=end_time
            )

            # Upload to a temporary location for preview
            dest_blob_name = f"generated_clips/tmp/{video_id}/{clip_id}.mp4"
            dest_blob = storage_client.bucket(bucket_name).blob(dest_blob_name)
            await asyncio.to_thread(dest_blob.upload_from_filename, local_output_path)
            
            preview_gcs_uri = f"gs://{bucket_name}/{dest_blob.name}"

            download_url = dest_blob.generate_signed_url(
                version="v4",
                expiration=timedelta(minutes=30), # Shorter expiration for previews
                method="GET",
            )
            
            # Return both the temporary URL and the permanent URI for the frontend to hold
            return JSONResponse(status_code=200, content={
                "clip_url": download_url,
                "clip_gcs_uri": preview_gcs_uri
            })

        except Exception as e:
            import traceback
            print(f"ERROR generating clip: {e}\n{traceback.format_exc()}")
            raise HTTPException(status_code=500, detail=f"Failed to generate clip: {e}")

@router.post("/api/video/{video_id}/generate-preview-clip")
async def generate_preview_clip(video_id: str, request: Request, current_user: dict = Depends(get_current_user)):
    """
    Generates a wider, editable preview clip for the user to select from.
    """
    body = await request.json()
    start_time = float(body.get("start_time"))
    end_time = float(body.get("end_time"))
    
    video_doc_ref = db.collection("videos").document(video_id)
    doc = await video_doc_ref.get()
    if not doc.exists or doc.to_dict().get("user_id") != current_user.get("uid"):
        raise HTTPException(status_code=403, detail="Not authorized.")

    video_data = doc.to_dict()
    original_video_gcs_uri = video_data.get("original_video_gcs_uri")
    if not original_video_gcs_uri:
        raise HTTPException(status_code=400, detail="Original video not found.")

    with tempfile.TemporaryDirectory() as tmpdir:
        try:
            source_blob_name = original_video_gcs_uri.replace(f"gs://{bucket_name}/", "")
            source_blob = storage_client.bucket(bucket_name).blob(source_blob_name)
            original_filename = os.path.basename(source_blob_name)
            local_input_path = os.path.join(tmpdir, original_filename)
            await asyncio.to_thread(source_blob.download_to_filename, local_input_path)

            # Create a wider time window for the preview
            preview_start = max(0, start_time - 30)
            preview_end = end_time + 30 # We don't know the video duration, but ffmpeg will handle it.
            
            clip_id = str(uuid.uuid4())
            local_output_path = os.path.join(tmpdir, f"preview-{clip_id}.mp4")
            
            # Create the vertical preview clip
            await asyncio.to_thread(
                create_vertical_clip,
                input_path=local_input_path,
                output_path=local_output_path,
                start_time=preview_start,
                end_time=preview_end
            )

            dest_blob_name = f"previews/{video_id}/{clip_id}.mp4"
            dest_blob = storage_client.bucket(bucket_name).blob(dest_blob_name)
            await asyncio.to_thread(dest_blob.upload_from_filename, local_output_path)
            
            download_url = dest_blob.generate_signed_url(
                version="v4",
                expiration=timedelta(minutes=60), # Previews can last a bit longer
                method="GET",
            )
            
            return JSONResponse(status_code=200, content={"preview_url": download_url})

        except Exception as e:
            import traceback
            print(f"ERROR generating preview clip: {e}\n{traceback.format_exc()}")
            raise HTTPException(status_code=500, detail=f"Failed to generate preview clip: {e}")

@router.post("/api/video/{video_id}/save-clip")
async def save_clip(video_id: str, request: Request, current_user: dict = Depends(get_current_user)):
    """ Saves a generated clip's metadata to Firestore. """
    body = await request.json()
    
    # Security Check
    video_doc_ref = db.collection("videos").document(video_id)
    doc = await video_doc_ref.get()
    if not doc.exists or doc.to_dict().get("user_id") != current_user.get("uid"):
        raise HTTPException(status_code=403, detail="Not authorized.")

    clip_data_to_save = {
        "start_time": body.get("start_time"),
        "end_time": body.get("end_time"),
        "title": body.get("title"),
        "clip_gcs_uri": body.get("clip_gcs_uri"),
        "generated_at": datetime.utcnow()
    }

    try:
        await video_doc_ref.update({
            "generated_clips": firestore.ArrayUnion([clip_data_to_save])
        })
        return JSONResponse(status_code=200, content={"message": "Clip saved successfully."})
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save clip: {e}")

@router.get("/api/clip/url")
async def get_clip_url(gcs_uri: str, current_user: dict = Depends(get_current_user)):
    """
    Generates a temporary signed URL for a clip from its GCS URI.
    A basic security check is performed to ensure the user is logged in,
    but it doesn't verify ownership of the clip itself. A more robust
    check would be needed in a production system.
    """
    if not gcs_uri or not gcs_uri.startswith(f"gs://{bucket_name}/"):
        raise HTTPException(status_code=400, detail="Invalid GCS URI.")
        
    try:
        blob_name = gcs_uri.replace(f"gs://{bucket_name}/", "")
        blob = storage_client.bucket(bucket_name).blob(blob_name)
        
        if not await asyncio.to_thread(blob.exists):
            raise HTTPException(status_code=404, detail="Clip not found.")

        url = blob.generate_signed_url(
            version="v4",
            expiration=timedelta(minutes=60),
            method="GET",
        )
        return {"url": url}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# This is a duplicate and insecure endpoint. Removing it.
# @router.post("/api/ingest")
# async def ingest_video(request: IngestRequest, app_request: Request):
#     """
#     DEPRECATED: This endpoint is for automated ingestion and does not use
#     the user's credentials. It's less secure and should not be used
#     by the frontend.
#     """
#     # ... implementation ... 