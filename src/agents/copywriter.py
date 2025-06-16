import json
import asyncio
import google.generativeai as genai
from google.cloud import storage

from ..event_bus import event_bus
from ..events import ContentAnalysisComplete, CopyReady
from ..database import db

class CopywriterAgent:
    """
    ✍️ CopywriterAgent
    Purpose: To generate compelling marketing copy based on the analyzed content.
    """

    def __init__(self, api_key: str, bucket_name: str, model_name: str):
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel(model_name=model_name)
        self.storage_client = storage.Client()
        self.bucket_name = bucket_name
        event_bus.subscribe(ContentAnalysisComplete, self.handle_analysis_complete)

    async def handle_analysis_complete(self, event: ContentAnalysisComplete):
        """
        Takes structured data, generates various marketing copy with Gemini,
        and saves it to Firestore.
        """
        print(f"✍️ CopywriterAgent: Received analysis for: {event.video_title}")
        video_doc_ref = db.collection("videos").document(event.video_id)

        try:
            await video_doc_ref.update({"status": "generating_copy"})

            # 1. Check if copy already exists
            doc = await video_doc_ref.get()
            video_data = doc.to_dict()
            if video_data.get("status") in ["copy_generated", "visuals_generated", "published"]:
                print(f"   Copy for '{event.video_title}' already exists. Skipping copy generation.")
                copy_ready_event = CopyReady(
                    video_id=event.video_id,
                    video_title=event.video_title,
                )
                await event_bus.publish(copy_ready_event)
                return

            # 2. Fetch the full transcript from GCS
            transcript_gcs_uri = video_data.get("transcript_gcs_uri")
            if not transcript_gcs_uri:
                raise ValueError("Transcript GCS URI not found in Firestore document.")
            
            print(f"   Downloading transcript from: {transcript_gcs_uri}")
            bucket = self.storage_client.bucket(self.bucket_name)
            blob = bucket.blob(transcript_gcs_uri.replace(f"gs://{self.bucket_name}/", ""))
            transcript_text = await asyncio.to_thread(blob.download_as_text)

            # 3. Generate Copy with Gemini
            print("   Generating marketing copy with Gemini 1.5 Pro...")
            prompt = self._build_prompt(event.structured_data, transcript_text)
            response = await self.model.generate_content_async(
                prompt,
                generation_config=genai.types.GenerationConfig(response_mime_type="application/json")
            )
            copy_assets = json.loads(response.text)
            print("   Marketing copy generated.")

            # 4. Extract and save the Substack article BEFORE general cleanup
            # to preserve its Markdown formatting (e.g., newlines).
            substack_article_content = copy_assets.pop('substack_article', None)
            substack_gcs_uri = None
            substack_hook = None
            
            # --- Clean up the generated copy ---
            # The model may return strings with escaped newlines (\\n) or other artifacts.
            # We'll clean these up for better display on the frontend.
            for key, value in copy_assets.items():
                if isinstance(value, str):
                    # Replace escaped newlines with HTML line breaks and remove extra backslashes
                    copy_assets[key] = value.replace('\\n', '<br>').replace('\\', '')
            
            if substack_article_content:
                # Now, process the pristine Substack article
                article_filename = f"{event.video_id}_substack.md"
                article_path_gcs = f"substack_posts/{article_filename}"
                article_blob = bucket.blob(article_path_gcs)
                await asyncio.to_thread(
                    article_blob.upload_from_string, substack_article_content, 'text/markdown'
                )
                await asyncio.to_thread(article_blob.make_public)
                substack_gcs_uri = f"gs://{self.bucket_name}/{article_path_gcs}"
                # Extract the first line as the hook, splitting on the literal \n
                substack_hook = substack_article_content.split('\n')[0].strip()
                print(f"   Substack article saved to GCS: {substack_gcs_uri}")

            # 5. Save the rest of the copy and the new URI to Firestore
            update_data = {
                "marketing_copy": copy_assets, # Now without the Substack article
                "status": "copy_generated"
            }
            if substack_gcs_uri:
                update_data["substack_gcs_uri"] = substack_gcs_uri
            if substack_hook:
                update_data["substack_hook"] = substack_hook

            await video_doc_ref.update(update_data)
            print("   Marketing copy and artifacts saved to Firestore.")

            # 6. Publish event for next agents
            copy_ready_event = CopyReady(
                video_id=event.video_id,
                video_title=event.video_title,
            )
            await event_bus.publish(copy_ready_event)

        except Exception as e:
            print(f"❌ CopywriterAgent Error: {e}")
            await video_doc_ref.update({"status": "generating_copy_failed", "error": str(e)})

    def _build_prompt(self, structured_data: dict, transcript: str) -> str:
        # Pretty print the JSON for better readability in the prompt
        analysis_json = json.dumps(structured_data, indent=2)

        return f"""
        You are a world-class marketing copywriter and content strategist.
        Your task is to generate a set of marketing materials for a YouTube video based on the provided analysis and the full transcript.

        First, use the ANALYSIS JSON as a creative brief to understand the core concepts.
        Then, use the FULL TRANSCRIPT for deeper context, details, and to capture the speaker's authentic voice.

        ANALYSIS:
        ---
        {analysis_json}
        ---

        FULL TRANSCRIPT:
        ---
        {transcript}
        ---

        Generate a JSON object with the following schema. Ensure the tone is engaging, professional, and tailored to each platform.

        {{
            "facebook_post": "A post for Facebook or Instagram. Start with a strong hook, elaborate on the video's main themes, and encourage discussion. Use relevant hashtags.",
            "email_newsletter": "A complete email newsletter. It should summarize the video's value, provide key takeaways, and entice readers to click through and watch the original video.",
            "substack_article": "A complete Substack article of approximately 400 words, formatted as a single Markdown string. The article must start with a compelling hook to draw the reader in. It should then expand on the video's lessons in a thoughtful blog post. Conclude the article with 3-5 journal prompts that help the reader personalize and apply the content to their own life."
        }}
        """ 