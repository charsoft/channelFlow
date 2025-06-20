import asyncio
import os
import tempfile
import uuid
import json
from datetime import datetime, timedelta
from google import genai
from google.genai.types import Part

import yt_dlp
from google.cloud import storage
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from google.auth.exceptions import RefreshError
import requests
from google.oauth2 import service_account

from ..database import db
from ..event_bus import event_bus
from ..events import NewVideoDetected, TranscriptReady
from ..security import decrypt_data, encrypt_data

class TranscriptionAgent:
    """
    ✍️ TranscriptionAgent
    Purpose: To convert spoken video content into written text.
    """
    def __init__(self, api_key: str, bucket_name: str, model_name: str, ffmpeg_path: str = None):
        self.client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
        self.model_name = model_name

        creds = None
        creds_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
        if creds_path and os.path.exists(creds_path):
            creds = service_account.Credentials.from_service_account_file(creds_path)
            print("✍️ TranscriptionAgent: Authenticating with service account credentials.")

        self.storage_client = storage.Client(credentials=creds)
        self.bucket_name = bucket_name
        self.bucket = self.storage_client.bucket(bucket_name)
        self.ffmpeg_path = ffmpeg_path
        event_bus.subscribe(NewVideoDetected, self.handle_new_video)

    async def update_video_status(self, video_id: str, status: str, data: dict = None):
        doc_ref = db.collection("videos").document(video_id)
        update_data = {"status": status, "updated_at": datetime.utcnow()}
        if data:
            update_data.update(data)
        
        # Add a default status message if one isn't provided
        if "status_message" not in update_data:
            update_data["status_message"] = f"Processing stage: {status}"
            
        await doc_ref.update(update_data)

    async def handle_new_video(self, event: NewVideoDetected):
        asyncio.create_task(self.process_video(event))

    async def process_video(self, event: NewVideoDetected):
        print(f"✍️ TranscriptionAgent: Received new video: {event.video_title}")

        try:
            video_gcs_uri, video_gcs_blob = await self._get_video_gcs_uri(event)
            if not video_gcs_uri:
                raise FileNotFoundError("Could not locate or download the video file.")

            await self.update_video_status(
                event.video_id, 
                "transcribing", 
                {"status_message": "Starting transcription with Gemini..."}
            )

            print(f"   Passing GCS URI '{video_gcs_uri}' to Gemini for transcription...")

            # grab the signed URL on the Blob (as before)
            blob = self.bucket.blob(video_gcs_blob.name)
            video_url = blob.generate_signed_url(
                expiration=timedelta(minutes=15),
                method="GET",
                version="v4"
            )

            # download the bytes
            response = requests.get(video_url, stream=True)
            response.raise_for_status()
            video_data = b''.join(response.iter_content(chunk_size=8192))
            
            mime_type = video_gcs_blob.content_type or "video/mp4"
            
            # prepare the multimodal Part
            video_part = Part.from_bytes(
                data=video_data,
                mime_type=mime_type
            )
            prompt = "Please transcribe this video's audio."

            # ←— HERE: use the supported sync generate_content, wrapped in to_thread
            response = await asyncio.to_thread(
                self.client.models.generate_content,
                model=self.model_name,
                contents=[video_part, prompt]
            )  # :contentReference[oaicite:0]{index=0}

            print("   Transcription received.")

            transcript_json = self._parse_transcript_response(response)
            transcript_gcs_uri = await self._save_transcript_to_gcs(event.video_id, transcript_json)

            await self.update_video_status(
                event.video_id,
                "transcribed",
                {
                    "transcript_gcs_uri": transcript_gcs_uri, 
                    "original_video_gcs_uri": video_gcs_uri,
                    "status_message": "Transcription complete. Saved to cloud."
                }
            )

            await event_bus.publish(TranscriptReady(
                video_id=event.video_id,
                video_title=event.video_title,
                transcript_gcs_uri=transcript_gcs_uri
            ))

        except Exception as e:
            print(f"❌ TranscriptionAgent Error: {e}")
            await self.update_video_status(
                event.video_id, 
                "transcription_failed", 
                {"error": str(e), "status_message": "Failed to transcribe video."}
            )


    async def _get_video_gcs_uri(self, event: NewVideoDetected) -> (str, storage.Blob):
        possible_extensions = ['.mp4', '.mkv', '.webm', '.mov']
        for ext in possible_extensions:
            blob_path = f"youtube_cache/{event.video_id}{ext}"
            blob = self.bucket.blob(blob_path)
            if await asyncio.to_thread(blob.exists):
                print(f"   Found video in GCS cache: {blob.name}")
                return f"gs://{self.bucket_name}/{blob.name}", blob

        print(f"   Video not in cache. Downloading from YouTube: {event.video_url}")
        with tempfile.TemporaryDirectory() as tmpdir:
            ydl_opts = {
                'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best',
                'outtmpl': os.path.join(tmpdir, f"{event.video_id}.%(ext)s"),
                'quiet': True,
                'ffmpeg_location': self.ffmpeg_path or None,
            }
            proxy = os.getenv("PROXY_URL")
            if proxy:
                ydl_opts['proxy'] = proxy

            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                error_code = await asyncio.to_thread(ydl.download, [event.video_url])
                if error_code != 0:
                    raise RuntimeError("yt-dlp failed to download the video.")

            downloaded_file_basename = next(f for f in os.listdir(tmpdir) if f.startswith(event.video_id))
            downloaded_file_fullpath = os.path.join(tmpdir, downloaded_file_basename)

            cache_blob_path = f"youtube_cache/{downloaded_file_basename}"
            cache_blob = self.bucket.blob(cache_blob_path)
            await asyncio.to_thread(cache_blob.upload_from_filename, downloaded_file_fullpath)
            print(f"   Saved downloaded video to GCS cache: {cache_blob.name}")

            return f"gs://{self.bucket_name}/{cache_blob.name}", cache_blob

    async def _get_auth_headers(self, event: NewVideoDetected) -> dict:
        if not event.user_id:
            return {}

        print(f"   Attempting to use credentials for user: {event.user_id}")
        cred_doc_ref = db.collection("user_credentials").document(event.user_id)
        cred_doc = await cred_doc_ref.get()

        if not cred_doc.exists:
            print(f"   Could not find credentials for user {event.user_id}. Falling back.")
            return {}

        try:
            encrypted_creds = cred_doc.to_dict().get("credentials")
            decrypted_creds_json = decrypt_data(encrypted_creds)
            creds = Credentials.from_authorized_user_info(json.loads(decrypted_creds_json))

            if creds.expired and creds.refresh_token:
                print("   Credentials expired. Attempting to refresh...")
                try:
                    await asyncio.to_thread(creds.refresh, Request())
                    new_creds_json = creds.to_json()
                    encrypted_new_creds = encrypt_data(new_creds_json.encode())
                    await cred_doc_ref.set({"credentials": encrypted_new_creds})
                    print("   Credentials successfully refreshed and stored.")

                except RefreshError as e:
                    print(f"   ❌ Could not refresh token for user {event.user_id}: {e}")
                    await self.update_video_status(
                        event.video_id,
                        "auth_failed",
                        {
                            "error": "Failed to refresh YouTube authentication token. Please reconnect your account.",
                            "status_message": "Authentication with YouTube failed."
                        }
                    )
                    return {}

            if creds.token:
                print("   Successfully created OAuth token for request header.")
                return {'Authorization': f'Bearer {creds.token}'}

        except Exception as e:
            print(f"   Failed to decrypt or load credentials for user {event.user_id}: {e}")

        return {}

    async def _save_transcript_to_gcs(self, video_id: str, transcript_json: dict) -> str:
        transcript_filename_gcs = f"{video_id}_transcript.json"
        transcript_blob_gcs_path = f"transcripts/{transcript_filename_gcs}"
        transcript_blob = self.bucket.blob(transcript_blob_gcs_path)

        await asyncio.to_thread(
            transcript_blob.upload_from_string,
            json.dumps(transcript_json, indent=2),
            'application/json'
        )

        transcript_gcs_uri = f"gs://{self.bucket_name}/{transcript_blob_gcs_path}"
        print(f"   Transcript saved to GCS: {transcript_gcs_uri}")
        return transcript_gcs_uri

    async def _cleanup_gcs_file(self, gcs_uri: str):
        try:
            blob_path = gcs_uri.replace(f"gs://{self.bucket_name}/", "")
            blob = self.bucket.blob(blob_path)
            await asyncio.to_thread(blob.delete)
            print(f"   Cleaned up GCS file: {gcs_uri}")
        except Exception as e:
            print(f"   ⚠️ Failed to clean up GCS file {gcs_uri}: {e}")

    async def _republish_event(self, event: NewVideoDetected, video_data: dict):
        await event_bus.publish(TranscriptReady(
            video_id=event.video_id,
            video_title=event.video_title,
            transcript_gcs_uri=video_data.get("transcript_gcs_uri")
        ))

    def _parse_transcript_response(self, response) -> dict:
        transcript_data = {"full_transcript": "", "segments": []}
        full_text_parts = []
        try:
            for part in response.parts:
                if hasattr(part, 'speech_to_text') and part.speech_to_text:
                    for segment in part.speech_to_text:
                        start_sec = segment.start_offset.total_seconds()
                        end_sec = segment.end_offset.total_seconds()
                        text = segment.transcript
                        transcript_data["segments"].append({"start": start_sec, "end": end_sec, "text": text})
                        full_text_parts.append(text)
                elif part.text:
                    full_text_parts.append(part.text)
        except (AttributeError, TypeError) as e:
            print(f"   [Notice] Could not parse detailed segments from response part: {e}")

        if not full_text_parts and response.text:
            transcript_data["full_transcript"] = response.text
        else:
            transcript_data["full_transcript"] = " ".join(full_text_parts).strip()

        return transcript_data
