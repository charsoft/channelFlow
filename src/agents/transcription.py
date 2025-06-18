import asyncio
import os
import tempfile
import uuid
import ffmpeg
import google.generativeai as genai
import yt_dlp
from google.cloud import storage
from google.oauth2.credentials import Credentials
from ..event_bus import event_bus
from ..events import NewVideoDetected, TranscriptReady
from ..database import db
import json
from ..security import decrypt_data
from .base_agent import BaseAgent, handle_event

class TranscriptionAgent(BaseAgent):
    """
    ✍️ TranscriptionAgent
    Purpose: To convert spoken video content into written text.
    """

    def __init__(self, api_key: str, bucket_name: str, model_name: str, ffmpeg_path: str = None):
        super().__init__()
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel(model_name=model_name)
        self.storage_client = storage.Client()
        self.bucket_name = bucket_name
        self.bucket = self.storage_client.bucket(bucket_name)
        self.ffmpeg_path = ffmpeg_path
        self.cookies_file = os.getenv("YOUTUBE_COOKIES_FILE_PATH")
        event_bus.subscribe(NewVideoDetected, self.handle_new_video)

    @handle_event(NewVideoDetected)
    async def handle_new_video(self, event: NewVideoDetected):
        """
        Downloads video audio to GCS, transcribes it using Gemini 1.5 Pro via the GCS URI,
        and saves the result to Firestore.
        """
        print(f"✍️ TranscriptionAgent: Received new video: {event.video_title}")
        video_doc_ref = db.collection("videos").document(event.video_id)
        audio_gcs_uri = None

        try:
            doc = await video_doc_ref.get()
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

            transcript_ready_event = TranscriptReady(
                video_id=event.video_id,
                video_title=event.video_title,
                transcript_gcs_uri=transcript_gcs_uri
            )
            await event_bus.publish(transcript_ready_event)

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
                
                # Find the downloaded file
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
        transcript_ready_event = TranscriptReady(
            video_id=event.video_id,
            video_title=event.video_title,
            transcript_gcs_uri=video_data.get("transcript_gcs_uri")
        )
        await event_bus.publish(transcript_ready_event)

    def _parse_transcript_response(self, response) -> dict:
        """
        Parses the complex response object from Gemini into a structured
        JSON format containing the full text and timestamped segments.
        This version correctly handles a single GenerateContentResponse object.
        """
        transcript_data = {
            "full_transcript": "",
            "segments": []
        }
        
        full_text_parts = []
        
        # The response object from the SDK is not iterable. We access its .parts directly.
        try:
            for part in response.parts:
                # Check for the presence of speech-to-text data, which contains timestamps
                if hasattr(part, 'speech_to_text') and part.speech_to_text:
                    # If we find structured data, use it as the source of truth
                    for segment in part.speech_to_text:
                        start_sec = segment.start_offset.total_seconds()
                        end_sec = segment.end_offset.total_seconds()
                        text = segment.transcript
                        transcript_data["segments"].append({
                            "start": start_sec,
                            "end": end_sec,
                            "text": text
                        })
                        full_text_parts.append(text)
                # Fallback to plain text part if no structured data is found in a part
                elif part.text:
                    full_text_parts.append(part.text)

        except (AttributeError, TypeError) as e:
            # Log if the expected response structure isn't there, but don't crash
            print(f"   [Notice] Could not parse detailed segments from response part: {e}")
        
        # If no segments were extracted (e.g., audio was silent or API response was minimal),
        # rely on the response's top-level .text attribute as a final fallback.
        if not full_text_parts and response.text:
            transcript_data["full_transcript"] = response.text
        else:
            # Join all collected text parts to form the full transcript.
            transcript_data["full_transcript"] = " ".join(full_text_parts).strip()
            
        return transcript_data 