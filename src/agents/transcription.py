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
        Checks if a transcript already exists. If not, it downloads the video,
        converts it to audio, and transcribes it using Gemini 1.5 Pro, and saves the result to Firestore.
        """
        print(f"✍️ TranscriptionAgent: Received new video: {event.video_title}")
        video_doc_ref = db.collection("videos").document(event.video_id)
        audio_file = None # Ensure audio_file is defined in the outer scope
        
        try:
            doc = await video_doc_ref.get()
            video_data = doc.to_dict()

            # Check if transcript already exists
            if video_data.get("status") in ["transcribed", "analyzed", "copy_generated", "visuals_generated", "published"]:
                print(f"   Transcript for '{event.video_title}' already exists. Skipping transcription.")
                transcript_ready_event = TranscriptReady(
                    video_id=event.video_id,
                    video_title=event.video_title,
                    transcript_gcs_uri=video_data.get("transcript_gcs_uri")
                )
                await event_bus.publish(transcript_ready_event)
                return

            # If not, proceed with transcription
            await video_doc_ref.update({"status": "transcribing"})

            with tempfile.TemporaryDirectory() as tmpdir:
                print(f"   Downloading and converting audio for: {event.video_title}")
                
                # Define the output path for yt-dlp
                audio_filename_template = f"{uuid.uuid4()}.%(ext)s"
                audio_path_template = os.path.join(tmpdir, audio_filename_template)

                ydl_opts = {
                    'format': 'bestaudio/best',
                    'quiet': True,
                    'outtmpl': audio_path_template,
                    'postprocessors': [{
                        'key': 'FFmpegExtractAudio',
                        'preferredcodec': 'mp3',
                        'preferredquality': '192',
                    }],
                    # Pass the ffmpeg path to yt-dlp if it's specified
                    'ffmpeg_location': self.ffmpeg_path or None,
                }

                # Run yt-dlp in a separate thread to avoid blocking the event loop
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    error_code = await asyncio.to_thread(ydl.download, [event.video_url])

                if error_code != 0:
                    raise RuntimeError("yt-dlp failed to download and convert the video.")

                # Find the downloaded file (yt-dlp adds the extension)
                downloaded_files = os.listdir(tmpdir)
                if not downloaded_files:
                    raise RuntimeError("Audio file not found after download.")
                
                audio_path = os.path.join(tmpdir, downloaded_files[0])
                print(f"   Audio downloaded to: {audio_path}")
                
                # The rest of the process remains the same
                print("   Uploading audio to Gemini for transcription...")
                
                audio_file = await asyncio.to_thread(genai.upload_file, path=audio_path)
                
                # Store the temporary Gemini file name in Firestore for cleanup
                await video_doc_ref.update({"temp_gemini_audio_file": audio_file.name})

                # The prompt is simplified. Asking for transcription of an audio file
                # is enough for Gemini 1.5 Pro to return a rich object with timestamps.
                # The previous prompt explicitly asking for "only text" was the problem.
                prompt = "Please transcribe this audio."
                
                response = await self.model.generate_content_async(
                    [prompt, audio_file]
                )

                print("   Transcription received.")
                
                # The response now contains more than just text.
                # We will save the full object as a structured JSON.
                transcript_json = self._parse_transcript_response(response)
                transcript_text = transcript_json["full_transcript"]


                # Save transcript to a .txt file in GCS
                transcript_filename = f"{event.video_id}_transcript.json"
                transcript_path_gcs = f"transcripts/{transcript_filename}"
                bucket = self.storage_client.bucket(self.bucket_name)
                blob = bucket.blob(transcript_path_gcs)
                await asyncio.to_thread(blob.upload_from_string, json.dumps(transcript_json, indent=2), 'application/json')
                await asyncio.to_thread(blob.make_public)
                
                print(f"   Transcript saved to GCS: gs://{self.bucket_name}/{transcript_path_gcs}")

                # Save GCS URI to Firestore
                transcript_gcs_uri = f"gs://{self.bucket_name}/{transcript_path_gcs}"
                await video_doc_ref.update({
                    "transcript_gcs_uri": transcript_gcs_uri,
                    "status": "transcribed",
                })

                # Publish event for analysis agent
                transcript_ready_event = TranscriptReady(
                    video_id=event.video_id,
                    video_title=event.video_title,
                    transcript_gcs_uri=transcript_gcs_uri
                )
                await event_bus.publish(transcript_ready_event)

                # Clean up the temp file on the local system
                print("   Cleaning up temporary local files.")

        except Exception as e:
            print(f"❌ TranscriptionAgent Error: {e}")
            await video_doc_ref.update({"status": "transcribing_failed", "error": str(e)})
        
        finally:
            # Clean up the file on Gemini's server
            if audio_file:
                await asyncio.to_thread(genai.delete_file, name=audio_file.name)
                print(f"   Cleaned up Gemini file: {audio_file.name}")
    
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