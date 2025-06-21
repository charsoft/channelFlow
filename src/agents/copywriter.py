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

    async def _update_status(self, doc_ref, status: str, message: str, extra_data: dict = None):
        """Helper to update status and message."""
        update = {
            "status": status,
            "status_message": message
        }
        if extra_data:
            update.update(extra_data)
        await doc_ref.update(update)

    async def handle_analysis_complete(self, event: ContentAnalysisComplete):
        """
        Takes structured data, generates various marketing copy with Gemini,
        and saves it to Firestore.
        """
        print(f"✍️ CopywriterAgent: Received analysis for: {event.video_title}")
        video_doc_ref = db.collection("videos").document(event.video_id)

        try:
            await self._update_status(video_doc_ref, "generating_copy", "Received content analysis. Starting copy generation.")

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
            
            await self._update_status(video_doc_ref, "generating_copy", "Downloading full transcript for context...")
            
            print(f"   Downloading transcript from: {transcript_gcs_uri}")
            bucket = self.storage_client.bucket(self.bucket_name)
            blob = bucket.blob(transcript_gcs_uri.replace(f"gs://{self.bucket_name}/", ""))
            transcript_text = await asyncio.to_thread(blob.download_as_text)

            # 3. Generate Copy with Gemini
            await self._update_status(video_doc_ref, "generating_copy", "Writing copy with Gemini...")
            print(f"   Generating marketing copy with {self.model.model_name}...")
            prompt = self._build_prompt(event.structured_data, transcript_text)
            response = await self.model.generate_content_async(
                prompt,
                generation_config=genai.types.GenerationConfig(response_mime_type="application/json")
            )
            
            # --- Start Debug Logging ---
            print("--- RAW GEMINI RESPONSE ---")
            print(response.text)
            print("--- END RAW GEMINI RESPONSE ---")
            # --- End Debug Logging ---

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
                substack_gcs_uri = f"gs://{self.bucket_name}/{article_path_gcs}"
                # Extract the first line as the hook, splitting on the literal \n
                substack_hook = substack_article_content.split('\n')[0].strip()
                print(f"   Substack article saved to GCS: {substack_gcs_uri}")

            # 5. Save the rest of the copy and the new URI to Firestore
            update_data = {
                "marketing_copy": copy_assets, # Now without the Substack article
                "status": "copy_generated",
                "status_message": "Marketing copy created and saved."
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

        except json.JSONDecodeError as e:
            print("--- FAILED TO PARSE JSON ---")
            print(f"Error: {e}")
            print("--- Raw response was: ---")
            # It's already been printed above, but we can print it again in the error context
            print(response.text if 'response' in locals() else "Response not available")
            print("--------------------------")
            # Re-raise or handle as a failed status
            await self._update_status(video_doc_ref, "generating_copy_failed", "Failed to parse marketing copy from AI.", {"error": str(e)})

        except Exception as e:
            print(f"❌ CopywriterAgent Error: {e}")
            await self._update_status(video_doc_ref, "generating_copy_failed", "Failed to generate marketing copy.", {"error": str(e)})

    def _build_prompt(self, structured_data: dict, transcript: str) -> str:
        # Pretty print the JSON for better readability in the prompt
        analysis_json = json.dumps(structured_data, indent=2)

        return f"""
        You are a world-class marketing copywriter and content strategist specializing in content for spiritual and personal growth brands.
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

        Generate a JSON object with the following schema. Ensure the tone is engaging, insightful, and tailored to each platform.
        IMPORTANT: The entire output must be a single, valid JSON object. All strings within the JSON must be properly escaped, with any newline characters represented as \\n.

        {{
            "facebook_post": "A post for Facebook or Instagram. Start with a strong hook, elaborate on the video's main themes, and encourage discussion. Use relevant hashtags. Use \\n for all newlines.",
            "email_newsletter": "A complete email newsletter. CRITICAL: ALL newlines, paragraphs, and line breaks MUST be represented as literal \\n characters. It must follow this exact structure: A short title, followed by '## Do you ever find yourself...' and an opening question. Then a brief reflection. A horizontal rule (---). '### ✨ In our latest video, we dive into a powerful idea:'. A blockquote with the core teaching. A sentence explaining what the video is NOT about, and then a sentence explaining what it IS about. A sentence describing the video's central metaphor. Another horizontal rule. A section titled '### 🔍 Here's a glimpse of what you'll explore:'. A list of the key takeaways from the ANALYSIS, each bolded and followed by its description on a new line. A final horizontal rule. A concluding sentence starting with 'If you're ready to...'. And finally, a link formatted as '👉 [**Watch Now**](#)'.",
            "substack_article": "A complete Substack article of approximately 400 words. CRITICAL: ALL newlines, paragraphs, and line breaks MUST be represented as literal \\n characters. The article must start with a compelling hook to draw the reader in. It should then expand on the video's lessons in a thoughtful blog post. Conclude the article with 3-5 journal prompts that help the reader personalize and apply the content to their own life."
        }}
        """ 