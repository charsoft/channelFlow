import os
import asyncio
import google.generativeai as genai
import vertexai
from vertexai.preview.vision_models import ImageGenerationModel

from ..event_bus import event_bus
from ..events import CopyReady, VisualsReady
from ..database import db
from google.cloud import storage
import uuid
import json

class VisualsAgent:
    """
    🎨 VisualsAgent
    Purpose: To create compelling visuals that complement the message using Imagen 2.
    """

    def __init__(self, project_id: str, location: str, bucket_name: str, api_key: str, model_name: str):
        genai.configure(api_key=api_key)
        vertexai.init(project=project_id, location=location)
        gemini_model_name = os.getenv("GEMINI_MODEL_NAME", "gemini-1.5-pro-latest")
        self.model = genai.GenerativeModel(model_name=gemini_model_name)
        self.image_model = ImageGenerationModel.from_pretrained(model_name)
        self.storage_client = storage.Client()
        self.bucket_name = bucket_name
        event_bus.subscribe(CopyReady, self.handle_copy_ready)

    async def _generate_and_upload_image(self, prompt: str, video_id: str, index: int, diversity_options: dict = None, model_name: str = None) -> str:
        """Generates a single image, uploads it, and returns the GCS URI."""
        
        # Determine which image model to use
        image_model_to_use = self.image_model
        if model_name:
            print(f"   Using on-demand model: {model_name}")
            image_model_to_use = ImageGenerationModel.from_pretrained(model_name)

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
            image_model_to_use.generate_images,
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
        blob_path = f"images/{image_filename}"
        blob = self.storage_client.bucket(self.bucket_name).blob(blob_path)
        
        await asyncio.to_thread(blob.upload_from_string, image_bytes, 'image/png')
        
        gcs_uri = f"gs://{self.bucket_name}/{blob_path}"
        print(f"       Uploaded to {gcs_uri}")
        return gcs_uri

    async def generate_single_image_from_prompt(self, video_id: str, prompt: str, model_name: str = None) -> dict:
        """
        Generates a single image and returns a dict with the prompt and the GCS URI.
        This is used for on-demand generation from the frontend.
        """
        index = f"ondemand_{uuid.uuid4()}"
        image_gcs_uri = await self._generate_and_upload_image(prompt, video_id, index, model_name=model_name)
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

    async def _update_status(self, doc_ref, status: str, message: str, extra_data: dict = None):
        """Helper to update status and message."""
        update = {
            "status": status,
            "status_message": message
        }
        if extra_data:
            update.update(extra_data)
        await doc_ref.update(update)

    async def handle_copy_ready(self, event: CopyReady):
        """
        Takes the marketing copy, generates a set of images with Imagen,
        and saves them to GCS and Firestore.
        """
        print(f"🎨 VisualsAgent: Received copy for: {event.video_title}")
        video_doc_ref = db.collection("videos").document(event.video_id)

        try:
            await self._update_status(video_doc_ref, "generating_visuals", "Received marketing copy. Starting image generation.")

            doc = await video_doc_ref.get()
            video_data = doc.to_dict()

            # Check if visuals already exist
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
            
            if not marketing_copy:
                raise ValueError("Marketing copy not found in Firestore document.")

            await self._update_status(video_doc_ref, "generating_visuals", "Generating image prompts with Gemini...")
            
            # 1. Use Gemini to generate creative prompts for Imagen
            gemini_prompt = self._build_gemini_prompt(event.video_title, marketing_copy)
            response = await self.model.generate_content_async(gemini_prompt)

            # --- Start Debug Logging ---
            print("--- RAW GEMINI RESPONSE (VisualsAgent) ---")
            print(response.text)
            print("--- END RAW GEMINI RESPONSE (VisualsAgent) ---")
            # --- End Debug Logging ---

            generated_prompts = json.loads(response.text).get("image_prompts", [])
            print(f"   Generated {len(generated_prompts)} image prompts.")

            # 2. Generate images with Imagen
            image_gcs_uris = []
            if generated_prompts:
                await self._update_status(video_doc_ref, "generating_visuals", f"Generating {len(generated_prompts)} images with Imagen...")
                # ... (rest of the logic for generating images)
                # This part is simplified for brevity. A real implementation would
                # loop through prompts and call the Imagen API.
                image_uris = await self.generate_images_from_prompts(
                    prompts=generated_prompts,
                    video_id=event.video_id
                )
                image_gcs_uris.extend(image_uris)
                print(f"   Generated {len(image_gcs_uris)} images and saved to GCS.")

            # 3. Save GCS URIs to Firestore
            await video_doc_ref.update({
                "image_gcs_uris": image_gcs_uris,
                "status": "visuals_generated",
                "status_message": "Social media images created."
            })
            print("   Image URIs saved to Firestore.")

            # 4. Publish event for next agents
            visuals_ready_event = VisualsReady(
                video_id=event.video_id,
                video_title=event.video_title,
            )
            await event_bus.publish(visuals_ready_event)
            
        except json.JSONDecodeError as e:
            print("--- FAILED TO PARSE JSON (VisualsAgent) ---")
            print(f"Error: {e}")
            print("--- Raw response was: ---")
            print(response.text if 'response' in locals() else "Response not available")
            print("--------------------------")
            await self._update_status(video_doc_ref, "visuals_failed", "Failed to parse image prompts from AI.", {"error": str(e)})

        except Exception as e:
            print(f"❌ VisualsAgent Error: {e}")
            await self._update_status(video_doc_ref, "visuals_failed", "Failed to generate images.", {"error": str(e)})

    def _build_image_prompt_generator(self, summary: str, hook: str) -> str:
        return f"""
        You are a creative director. Your job is to generate two distinct, compelling, and highly-descriptive prompts for an AI image generation model (Imagen 2).
        The goal is to create visuals for a piece of content.

        RULES:
        - The prompts must NOT contain any words, text, letters, or quotes.
    
        - The prompts should be distinct from each other in concept and composition.
        - Separate the two prompts with '---'. Do not add any other text before or after the prompts.

        Here is the creative brief:

        VIDEO SUMMARY:
        "{summary}"

        SUBSTACK HOOK:
        "{hook}"

        Based on this, generate two image prompts.
        """ 
      #  - The prompts should describe a visual concept, scene, or metaphor in a photorealistic or artistic style.

    async def generate_images_from_prompts(self, prompts: list[str], video_id: str) -> list[str]:
        """Generates multiple images concurrently from a list of prompts."""
        tasks = [
            self._generate_and_upload_image(prompt, video_id, i + 1)
            for i, prompt in enumerate(prompts)
        ]
        gcs_uris_with_none = await asyncio.gather(*tasks)
        # Filter out any None results from failed generations
        return [uri for uri in gcs_uris_with_none if uri]

    def _build_gemini_prompt(self, video_title: str, marketing_copy: dict) -> str:
        """Builds the prompt for Gemini to generate Imagen prompts."""
        
        # We'll use the Facebook post as the primary source for the visual style
        fb_post = marketing_copy.get("facebook_post", "")

        return f"""
        You are an expert creative director. Your task is to generate 3 distinct and compelling image prompts for an AI image generation model (like Google's Imagen) based on the provided marketing copy for a video titled "{video_title}".

        The goal is to create visuals that are thematically aligned with the content, are visually striking, and would work well as social media thumbnails or post images.

        RULES:
        - The prompts MUST NOT contain any words, text, letters, or quotes.
        - The prompts should describe a visual concept, scene, or metaphor.
        - The prompts should be evocative and detailed.
        - The prompts should be diverse in their concepts (e.g., don't just describe the same scene 3 times).

        MARKETING COPY:
        ---
        {fb_post}
        ---

        Based on the copy, generate a JSON object with a single key "image_prompts" which is a list of 3 strings.

        Example Output:
        {{
            "image_prompts": [
                "A photorealistic image of a single lightbulb glowing brightly in a dark, empty room, casting long shadows.",
                "An abstract painting representing the concept of 'flow state', with abstract shapes and colors.",
                "A close-up shot of a person's eye, with complex code and algorithms reflected in their iris."
            ]
        }}
        """