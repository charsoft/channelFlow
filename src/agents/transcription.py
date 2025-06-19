import asyncio
import os
import tempfile
import uuid
import json
from datetime import datetime

import google.generativeai as genai
import yt_dlp
from google.cloud import storage
from google.oauth2.credentials import Credentials

from ..database import db
from ..event_bus import event_bus
from ..events import NewVideoDetected, TranscriptReady
from ..security import decrypt_data

class TranscriptionAgent:
    """
    ✍️ TranscriptionAgent
    Purpose: To convert spoken video content into written text.
    """
    def __init__(self, api_key: str, bucket_name: str, model_name: str, ffmpeg_path: str = None):
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel(model_name=model_name)
        self.storage_client = storage.Client()
        self.bucket_name = bucket_name
        self.bucket = self.storage_client.bucket(bucket_name)
        self.ffmpeg_path = ffmpeg_path
        self.cookies_file = os.getenv("YOUTUBE_COOKIES_FILE_PATH")
        event_bus.subscribe(NewVideoDetected, self.handle_new_video)

    async def update_video_status(self, video_id: str, status: str, data: dict = None):
        """Helper to update video status in Firestore."""
        doc_ref = db.collection("videos").document(video_id)
        update_data = {"status": status, "updated_at": datetime.utcnow()}
        if data:
            update_data.update(data)
        await doc_ref.update(update_data)

    def handle_new_video(self, event: NewVideoDetected):
        """Synchronous wrapper to schedule the async processing task."""
        asyncio.create_task(self.process_video(event))

    async def process_video(self, event: NewVideoDetected):
        """
        Main async method to handle the entire transcription process for a video.
        """
        print(f"✍️ TranscriptionAgent: Received new video: {event.video_title}")
        audio_gcs_uri = None
        try:
            doc_ref = db.collection("videos").document(event.video_id)
            doc = await doc_ref.get()
            
            if not doc.exists:
                await doc_ref.set({"video_title": event.video_title, "video_url": event.video_url, "created_at": datetime.utcnow()})
            else:
                video_data = doc.to_dict()
                if video_data.get("status") in ["transcribed", "analyzed", "copy_generated", "visuals_generated", "published"]:
                    print(f"   Transcript for '{event.video_title}' already exists. Skipping transcription.")
                    await self._republish_event(event, video_data)
                    return

            await self.update_video_status(event.video_id, "transcribing")
            
            audio_gcs_uri = await self._get_audio_from_youtube(event)

            print("   Passing GCS URI to Gemini for transcription...")
            audio_file = genai.Part.from_uri(mime_type="audio/mpeg", uri=audio_gcs_uri)
            prompt = "Please transcribe this audio."
            response = await self.model.generate_content_async([prompt, audio_file])
            print("   Transcription received.")

            transcript_json = self._parse_transcript_response(response)
            transcript_gcs_uri = await self._save_transcript_to_gcs(event.video_id, transcript_json)

            await self.update_video_status(
                event.video_id,
                "transcribed",
                {"transcript_gcs_uri": transcript_gcs_uri, "audio_gcs_uri": audio_gcs_uri}
            )

            await event_bus.publish(TranscriptReady(
                video_id=event.video_id,
                video_title=event.video_title,
                transcript_gcs_uri=transcript_gcs_uri
            ))

        except Exception as e:
            print(f"❌ TranscriptionAgent Error: {e}")
            await self.update_video_status(event.video_id, "transcription_failed", {"error": str(e)})
        
        finally:
            if audio_gcs_uri:
                await self._cleanup_gcs_file(audio_gcs_uri)
    
    async def _get_audio_from_youtube(self, event: NewVideoDetected) -> str:
        """Downloads audio from YouTube to a GCS bucket and returns the GCS URI."""
        audio_filename = f"{event.video_id}_{uuid.uuid4()}.mp3"
        audio_blob_gcs_path = f"temp_audio/{audio_filename}"
        audio_gcs_uri = f"gs://{self.bucket_name}/{audio_blob_gcs_path}"
        blob = self.bucket.blob(audio_blob_gcs_path)

        print(f"   Downloading audio for '{event.video_title}' to {audio_gcs_uri}")

        ydl_opts = {
            'format': 'bestaudio/best',
            'quiet': True,
            'outtmpl': '%(id)s.%(ext)s',
            'postprocessors': [{'key': 'FFmpegExtractAudio', 'preferredcodec': 'mp3'}],
            'ffmpeg_location': self.ffmpeg_path or None,
        }
        
        headers = await self._get_auth_headers(event)
        if headers:
            ydl_opts['add_header'] = [f'{key}: {value}' for key, value in headers.items()]
        elif self.cookies_file:
            ydl_opts['cookiefile'] = self.cookies_file
            print(f"   Using cookies from {self.cookies_file}")

        with tempfile.TemporaryDirectory() as tmpdir:
            ydl_opts['outtmpl'] = os.path.join(tmpdir, ydl_opts['outtmpl'])
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                error_code = await asyncio.to_thread(ydl.download, [event.video_url])
                if error_code != 0:
                    raise RuntimeError("yt-dlp failed to download the video.")
                
                downloaded_file = next(f for f in os.listdir(tmpdir) if f.startswith(event.video_id))
                downloaded_path = os.path.join(tmpdir, downloaded_file)
                await asyncio.to_thread(blob.upload_from_filename, downloaded_path)

        print(f"   Audio successfully uploaded to {audio_gcs_uri}")
        return audio_gcs_uri

    async def _get_auth_headers(self, event: NewVideoDetected) -> dict:
        """Returns authentication headers if user credentials are available."""
        if not event.user_id:
            return {}
            
        print(f"   Attempting to use credentials for user: {event.user_id}")
        cred_doc = await db.collection("user_credentials").document(event.user_id).get()
        if not cred_doc.exists:
            print(f"   Could not find credentials for user {event.user_id}. Falling back.")
            return {}
            
        try:
            encrypted_creds = cred_doc.to_dict().get("credentials")
            decrypted_creds_json = decrypt_data(encrypted_creds)
            creds = Credentials.from_authorized_user_info(json.loads(decrypted_creds_json))
            if creds.token:
                print("   Successfully created OAuth token for request header.")
                return {'Authorization': f'Bearer {creds.token}'}
        except Exception as e:
            print(f"   Failed to decrypt or load credentials for user {event.user_id}: {e}")
            
        return {}

    async def _save_transcript_to_gcs(self, video_id: str, transcript_json: dict) -> str:
        """Saves the final transcript JSON to GCS and returns the URI."""
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
        """Deletes a file from GCS given its URI."""
        try:
            blob_path = gcs_uri.replace(f"gs://{self.bucket_name}/", "")
            blob = self.bucket.blob(blob_path)
            await asyncio.to_thread(blob.delete)
            print(f"   Cleaned up GCS file: {gcs_uri}")
        except Exception as e:
            print(f"   ⚠️ Failed to clean up GCS file {gcs_uri}: {e}")
            
    async def _republish_event(self, event: NewVideoDetected, video_data: dict):
        """Republishes the TranscriptReady event if transcription is already done."""
        await event_bus.publish(TranscriptReady(
            video_id=event.video_id,
            video_title=event.video_title,
            transcript_gcs_uri=video_data.get("transcript_gcs_uri")
        ))

    def _parse_transcript_response(self, response) -> dict:
        """Parses the Gemini response into a structured JSON format."""
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