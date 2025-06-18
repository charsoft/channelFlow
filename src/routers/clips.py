import asyncio
import os
import shutil
import tempfile
import uuid
import yt_dlp
from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from google.cloud import storage

from ..database import db
from ..video_processing import create_vertical_clip

router = APIRouter(
    prefix="/api/video/{video_id}",
    tags=["clips"],
)

class ClipRequest(BaseModel):
    start_time: float
    end_time: float
    short_index: int

class DeleteClipRequest(BaseModel):
    short_index: int
    clip_url: str

@router.post("/create-clip")
async def create_clip_endpoint(video_id: str, clip_request: ClipRequest, request: Request):
    """
    Creates, crops, and uploads a short video clip from the original video.
    Caches the downloaded source video in memory to avoid redundant downloads.
    """
    try:
        video_cache = request.app.state.video_cache
        input_path = video_cache.get(video_id)

        if not input_path:
            video_doc_ref = db.collection("videos").document(video_id)
            doc = await video_doc_ref.get()
            if not doc.exists:
                return JSONResponse(status_code=404, content={"message": "Video not found"})
            
            video_data = doc.to_dict()
            video_url = video_data.get("video_url")

            if not video_url:
                return JSONResponse(status_code=404, content={"message": "Video URL not found in document."})

            tmpdir = tempfile.mkdtemp(prefix="channel_video_cache_")
            print(f"Downloading video: {video_url} to cache directory {tmpdir}")
            ydl_opts = {
                'format': 'best[ext=mp4][vcodec^=avc1][acodec^=mp4a]/best[ext=mp4]/best',
                'outtmpl': os.path.join(tmpdir, f'{video_id}.%(ext)s'),
                'quiet': True,
            }
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                await asyncio.to_thread(ydl.download, [video_url])
            
            input_path = os.path.join(tmpdir, f'{video_id}.mp4')
            video_cache[video_id] = input_path
        else:
            print(f"Using cached video for {video_id} from path: {input_path}")

        output_dir = os.path.dirname(input_path)
        output_filename = f"clip_{video_id}_{uuid.uuid4()}.mp4"
        output_path = os.path.join(output_dir, output_filename)
        
        await asyncio.to_thread(
            create_vertical_clip,
            input_path=input_path,
            output_path=output_path,
            start_time=clip_request.start_time,
            end_time=clip_request.end_time
        )

        gcs_bucket_name = os.getenv("GCS_BUCKET_NAME")
        storage_client = storage.Client()
        bucket = storage_client.bucket(gcs_bucket_name)
        blob_path = f"shorts/{output_filename}"
        blob = bucket.blob(blob_path)
        
        await asyncio.to_thread(blob.upload_from_filename, output_path)
        await asyncio.to_thread(blob.make_public)

        print(f"Uploaded clip to: {blob.public_url}")

        doc = await db.collection("videos").document(video_id).get()
        if doc.exists:
            video_data = doc.to_dict()
            if 'structured_data' in video_data and 'shorts_candidates' in video_data['structured_data']:
                if clip_request.short_index < len(video_data['structured_data']['shorts_candidates']):
                    video_data['structured_data']['shorts_candidates'][clip_request.short_index]['generated_clip_url'] = blob.public_url
                    await db.collection("videos").document(video_id).set(video_data)
                    print(f"Saved clip URL to Firestore for short index {clip_request.short_index}")

        os.remove(output_path)

        return JSONResponse(status_code=200, content={"clip_url": blob.public_url})

    except Exception as e:
        print(f"Error creating clip for {video_id}: {e}")
        return JSONResponse(status_code=500, content={"message": "Internal server error"})

@router.post("/delete-clip")
async def delete_clip_endpoint(video_id: str, delete_request: DeleteClipRequest):
    """
    Deletes a generated clip from GCS and its reference in Firestore.
    """
    try:
        gcs_bucket_name = os.getenv("GCS_BUCKET_NAME")
        if gcs_bucket_name and delete_request.clip_url:
            storage_client = storage.Client()
            bucket = storage_client.bucket(gcs_bucket_name)
            blob_path = delete_request.clip_url.replace(f"https://storage.googleapis.com/{gcs_bucket_name}/", "")
            blob = bucket.blob(blob_path)
            if await asyncio.to_thread(blob.exists):
                await asyncio.to_thread(blob.delete)
                print(f"Deleted GCS file: {blob_path}")

        video_doc_ref = db.collection("videos").document(video_id)
        doc = await video_doc_ref.get()
        if doc.exists:
            video_data = doc.to_dict()
            if 'structured_data' in video_data and 'shorts_candidates' in video_data['structured_data']:
                if delete_request.short_index < len(video_data['structured_data']['shorts_candidates']):
                    video_data['structured_data']['shorts_candidates'][delete_request.short_index].pop('generated_clip_url', None)
                    await video_doc_ref.set(video_data)
                    print(f"Removed clip URL from Firestore for short index {delete_request.short_index}")

        return JSONResponse(status_code=200, content={"message": "Clip deleted successfully"})

    except Exception as e:
        print(f"Error deleting clip for {video_id}: {e}")
        return JSONResponse(status_code=500, content={"message": "Internal server error"}) 