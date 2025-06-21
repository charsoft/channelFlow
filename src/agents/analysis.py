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

    async def _update_status(self, doc_ref, status: str, message: str, extra_data: dict = None):
        """Helper to update status and message."""
        update = {
            "status": status,
            "status_message": message
        }
        if extra_data:
            update.update(extra_data)
        await doc_ref.update(update)

    async def handle_transcript_ready(self, event: TranscriptReady):
        """
        Downloads a transcript from GCS, analyzes it with Gemini, and saves the
        structured JSON analysis back to GCS and Firestore.
        """
        print(f"🧠 AnalysisAgent: Received transcript for: {event.video_title}")
        video_doc_ref = db.collection("videos").document(event.video_id)

        try:
            await self._update_status(video_doc_ref, "analyzing", "Starting content analysis.")
            
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
            
            await self._update_status(video_doc_ref, "analyzing", f"Downloading transcript from GCS...")
            
            print(f"   Downloading transcript from: {transcript_gcs_uri}")
            bucket = self.storage_client.bucket(self.bucket_name)
            blob = bucket.blob(transcript_gcs_uri.replace(f"gs://{self.bucket_name}/", ""))
            
            # The transcript is now a JSON object
            transcript_json_string = await asyncio.to_thread(blob.download_as_text)
            transcript_data = json.loads(transcript_json_string)

            # 2. Analyze with Gemini
            await self._update_status(video_doc_ref, "analyzing", "Generating insights with Gemini...")
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
                "status": "analyzed",
                "status_message": "Analysis complete. Content insights created."
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
            await self._update_status(video_doc_ref, "analyzing_failed", "Failed to analyze content.", {"error": str(e)})

    def _build_prompt(self, transcript_data: dict) -> str:
        # We now pass the full transcript text to the prompt
        full_transcript = transcript_data.get("full_transcript", "")

        return f"""
        You are an expert content strategist and creative director. Your goal is to analyze a video transcript and output a comprehensive JSON object that includes content analysis and creative assets.

        First, analyze the following video transcript to identify key themes, summaries, and compelling moments.
        Second, based on your analysis, create a set of 3-5 diverse and visually descriptive prompts for an AI image generation model like Imagen. These prompts should capture the essence of the video's main ideas.

        **CRITICAL INSTRUCTIONS FOR IMAGE PROMPTS:**
        - Prompts must be purely descriptive and should NOT contain any text, letters, or words meant to be rendered in the image.
        - Aim for a variety of styles (e.g., photorealistic, abstract, graphic design).
        - The prompts should be detailed enough to give the image model clear direction.

        Here is the full video transcript:
        ---
        {full_transcript}
        ---

        Based on the transcript, generate a single, valid JSON object with the exact following schema. Do not add any text or formatting outside of the JSON object.
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
            ],
            "image_prompts": [
                "A photorealistic image of a frustrated programmer staring at a complex web of glowing digital code that forms a tangled knot.",
                "An abstract, minimalist graphic representing the concept of 'imposter syndrome', using simple shapes and a muted color palette to convey a sense of doubt and isolation.",
                "Cinematic, dramatic shot of a single keyboard key being pressed, with a shockwave of light emanating from it, symbolizing a breakthrough moment in coding."
            ]
        }}
        """ 