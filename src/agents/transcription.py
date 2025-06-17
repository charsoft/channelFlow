import asyncio
import os
import tempfile
import uuid
import ffmpeg
import google.generativeai as genai
import yt_dlp
from google.cloud import storage
from ..event_bus import event_bus
from ..events import NewVideoDetected, TranscriptReady
from ..database import db
import json

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
        self.ffmpeg_path = ffmpeg_path
        event_bus.subscribe(NewVideoDetected, self.handle_new_video)

    async def handle_new_video(self, event: NewVideoDetected):
        """
        Downloads video audio to GCS, transcribes it using Gemini 1.5 Pro via the GCS URI,
        and saves the result to Firestore.
        """
        print(f"✍️ TranscriptionAgent: Received new video: {event.video_title}")
        video_doc_ref = db.collection("videos").document(event.video_id)
        audio_gcs_uri = None # Ensure audio_gcs_uri is defined for cleanup

        try:
            doc = await video_doc_ref.get()
            video_data = doc.to_dict()

            if video_data.get("status") in ["transcribed", "analyzed", "copy_generated", "visuals_generated", "published"]:
                print(f"   Transcript for '{event.video_title}' already exists. Skipping transcription.")
                transcript_ready_event = TranscriptReady(
                    video_id=event.video_id,
                    video_title=event.video_title,
                    transcript_gcs_uri=video_data.get("transcript_gcs_uri")
                )
                await event_bus.publish(transcript_ready_event)
                return

            await video_doc_ref.update({"status": "transcribing"})
            
            # --- New GCS-based workflow ---
            bucket = self.storage_client.bucket(self.bucket_name)
            audio_filename = f"{event.video_id}_{uuid.uuid4()}.mp3"
            audio_blob_gcs_path = f"temp_audio/{audio_filename}"
            audio_gcs_uri = f"gs://{self.bucket_name}/{audio_blob_gcs_path}"
            blob = bucket.blob(audio_blob_gcs_path)

            print(f"   Downloading and streaming audio for '{event.video_title}' to {audio_gcs_uri}")
            
            # Use a temporary local file *only* for the download buffer
            with tempfile.NamedTemporaryFile(suffix=".mp3") as tmp_audio_file:
                ydl_opts = {
                    'format': 'bestaudio/best',
                    'quiet': True,
                    'outtmpl': tmp_audio_file.name, # Download to this specific temp file
                    'postprocessors': [{
                        'key': 'FFmpegExtractAudio',
                        'preferredcodec': 'mp3',
                        'preferredquality': '192',
                    }],
                    'ffmpeg_location': self.ffmpeg_path or None,
                }

                # Download the audio locally first
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    error_code = await asyncio.to_thread(ydl.download, [event.video_url])

                if error_code != 0:
                    raise RuntimeError("yt-dlp failed to download and convert the video.")

                # Upload the downloaded file to GCS
                await asyncio.to_thread(blob.upload_from_filename, tmp_audio_file.name)
                print(f"   Audio successfully uploaded to GCS.")

            # Now, transcribe from the GCS URI
            print("   Passing GCS URI to Gemini for transcription...")
            audio_file = genai.Part.from_uri(
                mime_type="audio/mpeg",
                uri=audio_gcs_uri
            )
            
            prompt = "Please transcribe this audio."
            response = await self.model.generate_content_async([prompt, audio_file])
            print("   Transcription received.")

            transcript_json = self._parse_transcript_response(response)

            # Save transcript to a .json file in GCS
            transcript_filename_gcs = f"{event.video_id}_transcript.json"
            transcript_blob_gcs_path = f"transcripts/{transcript_filename_gcs}"
            transcript_blob = bucket.blob(transcript_blob_gcs_path)
            await asyncio.to_thread(
                transcript_blob.upload_from_string, 
                json.dumps(transcript_json, indent=2), 
                'application/json'
            )
            
            transcript_gcs_uri = f"gs://{self.bucket_name}/{transcript_blob_gcs_path}"
            print(f"   Transcript saved to GCS: {transcript_gcs_uri}")

            await video_doc_ref.update({
                "transcript_gcs_uri": transcript_gcs_uri,
                "audio_gcs_uri": audio_gcs_uri, # Save for potential future use or debugging
                "status": "transcribed",
            })

            transcript_ready_event = TranscriptReady(
                video_id=event.video_id,
                video_title=event.video_title,
                transcript_gcs_uri=transcript_gcs_uri
            )
            await event_bus.publish(transcript_ready_event)

        except Exception as e:
            print(f"❌ TranscriptionAgent Error: {e}")
            await video_doc_ref.update({"status": "transcribing_failed", "error": str(e)})
        
        finally:
            # Clean up the original audio file from GCS
            if audio_gcs_uri:
                try:
                    # We need to extract the blob path from the gs:// URI
                    blob_path = audio_gcs_uri.replace(f"gs://{self.bucket_name}/", "")
                    cleanup_blob = bucket.blob(blob_path)
                    await asyncio.to_thread(cleanup_blob.delete)
                    print(f"   Cleaned up GCS audio file: {audio_gcs_uri}")
                except Exception as cleanup_error:
                    print(f"   ⚠️ Failed to clean up GCS audio file {audio_gcs_uri}: {cleanup_error}")
    
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