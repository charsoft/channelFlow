from fastapi import APIRouter, Depends, HTTPException, File, UploadFile, Form, BackgroundTasks
from google.cloud import storage, firestore
import os
import mimetypes
import json

from ..database import db
from ..agents.ingestion import get_video_id
from ..event_bus import event_bus
from .auth import get_current_user
from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials
from ..security import decrypt_data
import asyncio

router = APIRouter(
    prefix="/api/admin",
    tags=["admin"],
    dependencies=[Depends(get_current_user)]
)

# Initialize clients and constants
storage_client = storage.Client()
GCS_BUCKET_NAME = os.getenv("GCS_BUCKET_NAME")
ALLOWED_MIME_TYPES = ["video/mp4", "video/quicktime", "video/x-m4v", "video/mov"]

async def process_manual_upload(youtube_url: str, file_contents: bytes, content_type: str, user_id: str):
    """
    This function contains the actual logic and is run in the background.
    """
    video_id = get_video_id(youtube_url)
    
    # The logic from here is the same as the original endpoint
    video_doc_ref = db.collection("videos").document(video_id)
    doc = await video_doc_ref.get()
    video_title = ""
  
    if not doc.exists:
        try:
            cred_doc_ref = db.collection("user_credentials").document(user_id)
            cred_doc = await cred_doc_ref.get()
            if not cred_doc.exists:
                raise HTTPException(status_code=403, detail="User has not connected their YouTube account.")

            encrypted_creds = cred_doc.to_dict().get("credentials")
            decrypted_creds_json = decrypt_data(encrypted_creds)
            creds = Credentials.from_authorized_user_info(json.loads(decrypted_creds_json))
            
            youtube = build('youtube', 'v3', credentials=creds)
            video_response = youtube.videos().list(part="snippet", id=video_id).execute()
            
            if not video_response.get("items"):
                # Can't raise HTTPException in background, so we print and exit
                print(f"[BACKGROUND_ERROR] Could not find video on YouTube for video_id: {video_id}")
                return
            video_title = video_response["items"][0]["snippet"]["title"]
        except Exception as e:
            print(f"[BACKGROUND_ERROR] Failed to verify video with YouTube API: {e}")
            return
    else:
        video_title = doc.to_dict().get("video_title", "Title not found")

    gcs_blob_name = f"videos/{video_id}.mp4"
    bucket = storage_client.bucket(GCS_BUCKET_NAME)
    blob = bucket.blob(gcs_blob_name)
    gcs_uri = f"gs://{GCS_BUCKET_NAME}/{gcs_blob_name}"

    try:
        await asyncio.to_thread(blob.upload_from_string, file_contents, content_type=content_type)
        print(f"Successfully uploaded {gcs_blob_name} to GCS in background.")
    except Exception as e:
        print(f"[BACKGROUND_ERROR] Failed to upload file to GCS: {e}")
        return

    video_data = {
        "video_id": video_id,
        "user_id": user_id,
        "video_title": video_title,
        "video_url": youtube_url,
        "gcs_uri": gcs_uri,
        "status": "ingested",
        "status_message": "Video manually uploaded. Awaiting transcription.",
        "updated_at": firestore.SERVER_TIMESTAMP,
    }

    if not doc.exists:
        video_data["created_at"] = firestore.SERVER_TIMESTAMP
        await video_doc_ref.set(video_data)
    else:
        await video_doc_ref.update(video_data)
        
    from ..events import IngestedVideo
    event = IngestedVideo(video_id=video_id, gcs_uri=gcs_uri, user_id=user_id, video_title=video_title)
    await event_bus.publish(event)
    print(f"Published IngestedVideo event for {video_id} from background task.")


@router.post("/upload-video")
async def upload_video(
    background_tasks: BackgroundTasks,
    youtube_url: str = Form(...), 
    file: UploadFile = File(...),
    current_user: dict = Depends(get_current_user)
):
    """
    Accepts a video upload and immediately returns a response while processing
    the upload in the background.
    """
    if not GCS_BUCKET_NAME:
        raise HTTPException(status_code=500, detail="GCS_BUCKET_NAME is not configured.")

    try:
        get_video_id(youtube_url)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    if file.content_type not in ALLOWED_MIME_TYPES:
        raise HTTPException(status_code=400, detail=f"Invalid file type. Allowed types are: {', '.join(ALLOWED_MIME_TYPES)}")

    user_id = current_user.get("uid")
    
    # Read file contents into memory once.
    # This is necessary because the UploadFile object is not available in the background task.
    file_contents = await file.read()
    
    # Add the long-running task to the background
    background_tasks.add_task(
        process_manual_upload,
        youtube_url=youtube_url,
        file_contents=file_contents,
        content_type=file.content_type,
        user_id=user_id
    )

    return {"message": "Video upload started in the background. Processing will begin shortly."} 