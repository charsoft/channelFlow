import json
import asyncio
import google.generativeai as genai
from google.cloud import storage
from ..event_bus import event_bus
from ..events import TranscriptReady, ContentAnalysisComplete
from ..database import db

class AnalysisAgent:
    """
    🧠 AnalysisAgent
    Purpose: To understand and extract the core meaning, structure, and essence of the transcript.
    """

    def __init__(self, api_key: str, bucket_name: str, model_name: str):
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel(model_name=model_name)
        self.storage_client = storage.Client()
        self.bucket_name = bucket_name
        event_bus.subscribe(TranscriptReady, self.handle_transcript_ready)

    async def handle_transcript_ready(self, event: TranscriptReady):
        """
        Downloads a transcript from GCS, analyzes it with Gemini, and saves the
        structured JSON analysis back to GCS and Firestore.
        """
        print(f"🧠 AnalysisAgent: Received transcript for: {event.video_title}")
        video_doc_ref = db.collection("videos").document(event.video_id)

        try:
            await video_doc_ref.update({"status": "analyzing"})
            
            doc = await video_doc_ref.get()
            video_data = doc.to_dict()

            # Check if analysis already exists
            if video_data.get("status") in ["analyzed", "copy_generated", "visuals_generated", "published"]:
                print(f"   Analysis for '{event.video_title}' already exists. Skipping analysis.")
                analysis_complete_event = ContentAnalysisComplete(
                    video_id=event.video_id,
                    video_title=event.video_title,
                    structured_data=video_data.get("structured_data")
                )
                await event_bus.publish(analysis_complete_event)
                return

            # 1. Get transcript from GCS
            transcript_gcs_uri = video_data.get("transcript_gcs_uri")
            
            if not transcript_gcs_uri:
                raise ValueError("Transcript GCS URI not found in Firestore document.")
            
            print(f"   Downloading transcript from: {transcript_gcs_uri}")
            bucket = self.storage_client.bucket(self.bucket_name)
            blob = bucket.blob(transcript_gcs_uri.replace(f"gs://{self.bucket_name}/", ""))
            
            # The transcript is now a JSON object
            transcript_json_string = await asyncio.to_thread(blob.download_as_text)
            transcript_data = json.loads(transcript_json_string)

            # 2. Analyze with Gemini
            print("   Analyzing transcript with Gemini 1.5 Pro for shorts candidates...")
            prompt = self._build_prompt(transcript_data)
            response = await self.model.generate_content_async(
                prompt,
                generation_config=genai.types.GenerationConfig(response_mime_type="application/json")
            )
            analysis_results = json.loads(response.text)
            print("   Analysis complete.")

            # 3. Save analysis to GCS
            analysis_filename = f"{event.video_id}_analysis.json"
            analysis_path_gcs = f"analyses/{analysis_filename}"
            analysis_blob = bucket.blob(analysis_path_gcs)
            await asyncio.to_thread(analysis_blob.upload_from_string, json.dumps(analysis_results, indent=2), 'application/json')
            print(f"   Analysis saved to GCS: gs://{self.bucket_name}/{analysis_path_gcs}")

            # 4. Save GCS URI and structured data to Firestore
            # The entire analysis result, including shorts_candidates, is saved.
            await video_doc_ref.update({
                "analysis_gcs_uri": f"gs://{self.bucket_name}/{analysis_path_gcs}",
                "structured_data": analysis_results,
                "status": "analyzed"
            })
            print("   Analysis artifacts saved to Firestore.")

            # 5. Publish event for next agents
            analysis_complete_event = ContentAnalysisComplete(
                video_id=event.video_id,
                video_title=event.video_title,
                structured_data=analysis_results,
            )
            await event_bus.publish(analysis_complete_event)

        except Exception as e:
            print(f"❌ AnalysisAgent Error: {e}")
            await video_doc_ref.update({"status": "analyzing_failed", "error": str(e)})

    def _build_prompt(self, transcript_data: dict) -> str:
        # We now pass the full transcript text to the prompt
        full_transcript = transcript_data.get("full_transcript", "")

        return f"""
        You are an expert social media video editor and content strategist, specializing in identifying viral moments for YouTube Shorts.
        Analyze the following video transcript to identify 3-5 segments that would make compelling, self-contained YouTube Shorts (under 60 seconds).

        For each candidate, provide:
        - A catchy, SEO-friendly title.
        - The start and end time in seconds.
        - A brief (1-2 sentence) reason explaining why this segment is a strong candidate (e.g., "Strong emotional hook," "Clear, actionable advice," "Controversial but interesting take").
        - The transcript snippet for that segment.

        Your primary goal is to find "golden nuggets"—moments of high emotion, clear value, or strong hooks that can stand alone and capture attention.

        Here is the full video transcript:
        ---
        {full_transcript}
        ---

        Based on the transcript, generate a JSON object with the following schema:
        {{
            "key_themes": ["A list of 3-5 main topics or ideas discussed in the video."],
            "summary": "A concise, one-paragraph summary of the video's content.",
            "bullet_summary": ["A detailed summary of the video's content, presented as a list of strings (bullet points)."],
            "meaningful_quotes": ["A list of 2-4 impactful, shareable quotes from the transcript."],
            "call_to_action": "Identify the primary call to action or the main takeaway message for the audience.",
            "shorts_candidates": [
                {{
                    "suggested_title": "The Single Biggest Mistake Programmers Make",
                    "start_time": 45.3,
                    "end_time": 92.1,
                    "reason": "This segment has a very strong, controversial hook and presents a clear, common problem that will resonate with the target audience.",
                    "transcript_snippet": "The biggest mistake that I see programmers make is..."
                }}
            ]
        }}
        """ 