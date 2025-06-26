import asyncio
import google.generativeai as genai
import vertexai
from vertexai.preview.vision_models import ImageGenerationModel

from ..event_bus import event_bus
from ..events import CopyReady, VisualsReady
from ..database import db
from google.cloud import storage
import uuid

class VisualsAgent:
    """  
    🎨 VisualsAgent
    Purpose: To create compelling visuals that complement the message using Imagen 2.
    """

    def __init__(self, *, bucket, api_key: str, imagen_model_name: str, gemini_model_name: str):
        #✅ Use * to enforce keyword arguments — this makes it harder to mix up params when initializing.
        genai.configure(api_key=api_key)
        vertexai.init(project=bucket.client.project, location=bucket.location)
        
        self.model = genai.GenerativeModel(model_name=gemini_model_name)
        self.image_model = ImageGenerationModel.from_pretrained(imagen_model_name)

        self.bucket = bucket  # already initialized in startup_event()
        self.storage_client = bucket.client  # optional
        event_bus.subscribe(CopyReady, self.handle_copy_ready)

    async def _generate_and_upload_image(self, prompt: str, video_id: str, index: int, diversity_options: dict = None) -> str:
        """Generates a single image, uploads it, and returns the public URL."""
        
        # Modify prompt based on diversity options
        if diversity_options:
            modifiers = []
            if diversity_options.get("gender"):
                modifiers.append("diverse genders")
            if diversity_options.get("ethnicity"):
                modifiers.append("diverse ethnicities and skin tones")
            if diversity_options.get("ability"):
                modifiers.append("people with varying physical abilities")
            
            if modifiers:
                diversity_string = " The image should include " + ", and ".join(modifiers) + "."
                prompt += diversity_string

        print(f"     - Generating image {index}: {prompt[:80]}...")
        response = await asyncio.to_thread(
            self.image_model.generate_images,
            prompt=prompt,
            number_of_images=1
        )
        
        # Add a check to ensure the model returned an image
        if not response.images:
            print(f"       ⚠️ Image generation failed for prompt: {prompt[:80]}...")
            return None

        image_bytes = response.images[0]._image_bytes
        
        # Upload to GCS
        image_filename = f"{video_id}_visual_{index}_{uuid.uuid4()}.png"
        blob = self.storage_client.bucket(self.bucket_name).blob(f"images/{image_filename}")
        
        await asyncio.to_thread(blob.upload_from_string, image_bytes, 'image/png')
        
        gcs_uri = f"gs://{self.bucket_name}/{blob.name}"
        print(f"       Uploaded to {gcs_uri}")
        return gcs_uri

    async def generate_single_image_from_prompt(self, video_id: str, prompt: str) -> dict:
        """
        Generates a single image and returns a dict with the prompt and URL.
        This is used for on-demand generation from the frontend.
        """
        index = f"ondemand_{uuid.uuid4()}"
        image_gcs_uri = await self._generate_and_upload_image(prompt, video_id, index)
        if image_gcs_uri:
            return {"prompt": prompt, "gcs_uri": image_gcs_uri}
        return None

    async def _generate_quote_image(self, quote: str, video_id: str, index: int, key_themes: list) -> dict:
        """Generates a background image for a specific quote."""
        theme_str = ", ".join(key_themes)
        prompt = (
            "Create a visually stunning, abstract, and subtle background image suitable for a quote. "
            f"The image should be inspired by themes of: {theme_str}. "
            "It should evoke a feeling of inspiration and insight. Do NOT include any text, letters, or words in the image. "
            "The style should be elegant and minimalist, with a soft focus and a gentle color palette."
        )
        
        print(f"   - Generating background for quote {index}...")
        image_gcs_uri = await self._generate_and_upload_image(prompt, video_id, f"quote_{index}")
        
        if image_gcs_uri:
            return {"quote": quote, "gcs_uri": image_gcs_uri}
        return None

    async def _generate_image_prompts(self, structured_data: dict, substack_gcs_uri: str) -> list[str]:
        """Generates a list of image prompts using Gemini."""
        # Download the substack article from GCS to get the hook
        hook = ""
        if substack_gcs_uri:
            try:
                bucket = self.storage_client.bucket(self.bucket_name)
                blob_name = substack_gcs_uri.replace(f"gs://{self.bucket_name}/", "")
                blob = bucket.blob(blob_name)
                substack_article_content = await asyncio.to_thread(blob.download_as_text)
                hook = substack_article_content.split('\n')[0]
            except Exception as e:
                print(f"   Could not download Substack article to get hook: {e}")
                hook = structured_data.get("summary", "") # Fallback
        else:
            hook = structured_data.get("summary", "")

        # Generate image prompts with Gemini
        print("   Generating descriptive prompts for image generation...")
        summary = structured_data.get("summary", "")
        prompt_generation_prompt = self._build_image_prompt_generator(summary, hook)
        response = await self.model.generate_content_async(prompt_generation_prompt)
        return [p.strip() for p in response.text.split('---') if p.strip()]

    async def handle_copy_ready(self, event: CopyReady):
        """
        Generates image prompts and then uses Imagen 2 to generate images,
        which are then uploaded to GCS.
        """
        print(f"🎨 VisualsAgent: Received copy ready for: {event.video_title}")
        video_doc_ref = db.collection("videos").document(event.video_id)

        try:
            await video_doc_ref.update({"status": "generating_visuals"})

            # Check if visuals already exist
            doc = await video_doc_ref.get()
            video_data = doc.to_dict()
            if video_data.get("status") in ["visuals_generated", "published"]:
                print(f"   Visuals for '{event.video_title}' already exist. Skipping visuals generation.")
                visuals_ready_event = VisualsReady(
                    video_id=event.video_id,
                    video_title=event.video_title,
                )
                await event_bus.publish(visuals_ready_event)
                return

            # Get the analysis and copy from the document
            structured_data = video_data.get("structured_data")
            if not structured_data:
                raise ValueError("Could not find 'structured_data' in the video document.")

            marketing_copy = video_data.get("marketing_copy", {})
            substack_article_gcs_uri = video_data.get("substack_gcs_uri")
            
            # --- Thumbnail Image Generation ---
            print("   Starting thumbnail generation...")
            image_prompts_task = self._generate_image_prompts(structured_data, substack_article_gcs_uri)
            
            # --- Quote Visual Generation ---
            quotes = structured_data.get("meaningful_quotes", [])
            key_themes = structured_data.get("key_themes", [])
            quote_visuals_task = None
            if quotes:
                print(f"   Starting visual generation for {len(quotes)} quotes...")
                quote_tasks = [
                    self._generate_quote_image(quote, event.video_id, i, key_themes)
                    for i, quote in enumerate(quotes)
                ]
                quote_visuals_task = asyncio.gather(*quote_tasks)

            # Await the prompt generation first
            image_prompts = await image_prompts_task
            
            # Now, create and gather the tasks for generating the main thumbnail images
            print(f"   Generating and uploading {len(image_prompts)} thumbnail images...")
            thumbnail_tasks = [
                self._generate_and_upload_image(prompt, event.video_id, i + 1)
                for i, prompt in enumerate(image_prompts)
            ]
            thumbnails_gathertask = asyncio.gather(*thumbnail_tasks)

            # Await all image generation tasks concurrently
            all_results = await asyncio.gather(
                thumbnails_gathertask,
                quote_visuals_task if quote_visuals_task else asyncio.sleep(0) # gather needs an awaitable
            )
            
            image_urls_with_none = all_results[0]
            quote_visuals_with_none = all_results[1] if len(all_results) > 1 and quote_visuals_task else []

            # --- New Data Structure ---
            # Combine prompts and URLs into a list of objects
            generated_thumbnails = [
                {"prompt": prompt, "gcs_uri": url}
                for prompt, url in zip(image_prompts, image_urls_with_none) if url is not None
            ]

            quote_visuals = [qv for qv in quote_visuals_with_none if qv is not None]

            # Update Firestore with all generated URLs at once
            update_data = {
                # Storing the combined list of objects now
                "generated_thumbnails": generated_thumbnails,
                "status": "visuals_generated"
            }
            if quote_visuals:
                update_data["quote_visuals"] = quote_visuals
            
            await video_doc_ref.update(update_data)

            print("   Visuals generated and saved to Firestore.")

            # Publish event
            visuals_ready_event = VisualsReady(
                video_id=event.video_id,
                video_title=event.video_title,
            )
            await event_bus.publish(visuals_ready_event)

        except Exception as e:
            print(f"❌ VisualsAgent Error: {e}")
            await video_doc_ref.update({"status": "generating_visuals_failed", "error": str(e)})

    def _build_image_prompt_generator(self, summary: str, hook: str) -> str:
        return f"""
        You are a creative director. Your job is to generate two distinct, compelling, and highly-descriptive prompts for an AI image generation model (Imagen 2).
        The goal is to create visuals for a piece of content.

        RULES:
        - The prompts must NOT contain any words, text, letters, or quotes.
        - The prompts should describe a visual concept, scene, or metaphor in a photorealistic or artistic style.
        - The prompts should be distinct from each other in concept and composition.
        - Separate the two prompts with '---'. Do not add any other text before or after the prompts.

        Here is the creative brief:

        VIDEO SUMMARY:
        "{summary}"

        SUBSTACK HOOK:
        "{hook}"

        Based on this, generate two image prompts.
        """