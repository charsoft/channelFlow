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
from ..events import NewVideoDetected, IngestedVideo, TranscriptReady
from ..security import decrypt_data, encrypt_data

class TranscriptionAgent:
    """
    ✍️ TranscriptionAgent
    Purpose: To convert spoken video content into written text.
    """
    def __init__(self, api_key: str, bucket_name: str, model_name: str, ffmpeg_path: str = None):
        self.client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
        self.model_name = model_name
        self.storage_client = storage.Client()
        self.bucket_name = bucket_name
        self.bucket = self.storage_client.bucket(bucket_name)
        self.ffmpeg_path = ffmpeg_path
        # Listen for both the original event and our new manual upload event
        event_bus.subscribe(NewVideoDetected, self.handle_new_video)
        event_bus.subscribe(IngestedVideo, self.handle_video_ingested)

    async def update_video_status(self, video_id: str, status: str, data: dict = None):
        doc_ref = db.collection("videos").document(video_id)
        update_data = {"status": status, "updated_at": datetime.utcnow()}
        if data:
            update_data.update(data)
        
        # Add a default status message if one isn't provided
        if "status_message" not in update_data:
            update_data["status_message"] = f"Processing stage: {status}"
            
        await doc_ref.update(update_data)

    async def handle_new_video(self, event: "NewVideoDetected"):
        """Handles the original flow where the video needs to be downloaded."""
        print(f"✍️ TranscriptionAgent: Received new video: {event.video_title}")

        try:
            # Immediately update status to show we are starting the download/retrieval process
            await self.update_video_status(
                event.video_id,
                "downloading",
                {"status_message": "Locating video file..."}
            )

            video_gcs_uri, video_gcs_blob = await self._get_video_gcs_uri(event)
            if not video_gcs_uri:
                raise FileNotFoundError("Could not locate or download the video file.")
            
            # Now that we have a GCS URI, we can proceed with the common transcription logic
            await self._perform_transcription(event.video_id, event.video_title, video_gcs_uri)
        except Exception as e:
            print(f"❌ TranscriptionAgent Error during download: {e}")
            await self.update_video_status(
                event.video_id, 
                "ingestion_failed",
                {"error": str(e), "status_message": "Failed to download video from YouTube. Please use the Manual Video Upload tool on the Maintenance page."}
            )

    async def handle_video_ingested(self, event: "IngestedVideo"):
        """Handles the workaround flow where the video is already in GCS."""
        print(f"✍️ TranscriptionAgent: Received pre-ingested video: {event.video_title}")
        try:
            if not event.gcs_uri:
                raise ValueError("GCS URI not provided in IngestedVideo event.")
            
            # The GCS URI is already provided, so we can proceed directly
            await self._perform_transcription(event.video_id, event.video_title, event.gcs_uri)
        except Exception as e:
            # This error is for the transcription step itself
            print(f"❌ TranscriptionAgent Error during transcription: {e}")
            await self.update_video_status(
                event.video_id, 
                "transcription_failed",
                {"error": str(e), "status_message": "Failed to transcribe video."}
            )

    async def _perform_transcription(self, video_id: str, video_title: str, gcs_uri: str):
        """Core logic to transcribe a video file already located in GCS."""
        await self.update_video_status(
            video_id, 
            "transcribing", 
            {"status_message": "Starting transcription with Gemini..."}
        )
        print(f"   Transcribing from GCS URI: {gcs_uri}")

        blob_name = gcs_uri.replace(f"gs://{self.bucket_name}/", "")
        blob = self.bucket.blob(blob_name)
        if not await asyncio.to_thread(blob.exists):
            raise FileNotFoundError(f"File not found in GCS at {gcs_uri}")

        video_url = blob.generate_signed_url(
            expiration=timedelta(minutes=15),
            method="GET",
            version="v4"
        )
        response = requests.get(video_url, stream=True)
        response.raise_for_status()
        video_data = b''.join(response.iter_content(chunk_size=8192))
        mime_type = blob.content_type or "video/mp4"

        video_part = Part.from_bytes(data=video_data, mime_type=mime_type)
        prompt = "Please transcribe this video's audio."

        model_response = await asyncio.to_thread(
            self.client.models.generate_content,
            model=self.model_name,
            contents=[video_part, prompt]
        )
        print("   Transcription received.")

        transcript_json = self._parse_transcript_response(model_response)
        transcript_gcs_uri = await self._save_transcript_to_gcs(video_id, transcript_json)

        await self.update_video_status(
            video_id,
            "transcribed",
            {
                "transcript_gcs_uri": transcript_gcs_uri, 
                "original_video_gcs_uri": gcs_uri,
                "status_message": "Transcription complete. Saved to cloud."
            }
        )

        await event_bus.publish(TranscriptReady(
            video_id=video_id,
            video_title=video_title,
            transcript_gcs_uri=transcript_gcs_uri
        ))

    async def _download_video_to_gcs(self, event: NewVideoDetected) -> (str, storage.Blob):
        """Downloads a video from a URL using yt-dlp and saves it to GCS."""
        # First, check if the file already exists from a previous attempt
        possible_extensions = ['.mp4', '.mkv', '.webm', 'mov'] # Added mov
        for ext in possible_extensions:
            blob_path = f"videos/{event.video_id}{ext}" # Standardized path
            blob = self.bucket.blob(blob_path)
            if await asyncio.to_thread(blob.exists):
                print(f"   Found video in GCS cache: {blob.name}")
                return f"gs://{self.bucket_name}/{blob.name}", blob

        print(f"   Video not in cache. Downloading from YouTube: {event.video_url}")
        
        # Add a status update specifically for downloading from YouTube
        await self.update_video_status(
            event.video_id,
            "downloading",
            {"status_message": "Downloading video from YouTube..."}
        )

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

            cache_blob_path = f"videos/{downloaded_file_basename}" # Standardized path
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
        
        # New robust parsing logic
        try:
            # The entire response might be the text, or it might be in parts.
            # We prioritize getting the full text from the dedicated attribute first.
            if hasattr(response, 'text') and response.text:
                 full_text_parts.append(response.text)

            # Then, we look for detailed segments if they exist, to enrich the data.
            if hasattr(response, 'parts') and response.parts:
                for part in response.parts:
                    if hasattr(part, 'speech_to_text') and part.speech_to_text:
                        # If we find segments, we can build a more precise full transcript
                        # and clear out the one we got from .text
                        if full_text_parts:
                            full_text_parts = [] 
                        for segment in part.speech_to_text:
                            start_sec = segment.start_offset.total_seconds()
                            end_sec = segment.end_offset.total_seconds()
                            text = segment.transcript
                            transcript_data["segments"].append({"start": start_sec, "end": end_sec, "text": text})
                            full_text_parts.append(text)
        except Exception as e:
            print(f"   [Warning] An unexpected error occurred during transcript parsing: {e}")

        if not full_text_parts:
            print(f"   [Warning] Could not extract any transcript text from the response: {response}")
        
        if not transcript_data["segments"]:
            print("   [Notice] Detailed segments with timestamps were not available in the response.")

        transcript_data["full_transcript"] = " ".join(full_text_parts).strip()
        return transcript_data
