import os
import asyncio
import google.generativeai as genai
import vertexai
from vertexai.preview.vision_models import ImageGenerationModel

from ..event_bus import event_bus
from ..events import ContentAnalysisComplete, VisualsReady
from ..database import db
from google.cloud import storage
import uuid
import json
import traceback

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
        event_bus.subscribe(ContentAnalysisComplete, self.handle_analysis_complete)

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
        try:
            response = await asyncio.to_thread(
                image_model_to_use.generate_images,
                prompt=prompt,
                number_of_images=1
            )
        except Exception as e:
            print(f"       ⚠️ Imagen API Error for prompt: {prompt[:80]}... Error: {e}")
            return None
        
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
        Takes the structured data from the AnalysisAgent, extracts the image prompts,
        generates a set of images with Imagen, and saves them to GCS and Firestore.
        """
        print(f"🎨 VisualsAgent: Received analysis for: {event.video_title}")
        video_doc_ref = db.collection("videos").document(event.video_id)

        try:
            await self._update_status(video_doc_ref, "generating_visuals", "Received content analysis. Starting image generation.")

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

            # Get the analysis from the event
            structured_data = event.structured_data
            if not structured_data:
                raise ValueError("Could not find 'structured_data' in the event payload.")

            # 1. Get pre-made prompts from the AnalysisAgent
            generated_prompts = structured_data.get("image_prompts", [])
            if not generated_prompts:
                print("   No image prompts found in the analysis. Skipping image generation.")
                # Update status to reflect that we are skipping this step, but not failing
                await self._update_status(video_doc_ref, "visuals_skipped", "No image prompts provided by Analysis agent.")
                return 

            print(f"   Found {len(generated_prompts)} image prompts.")

            # 2. Generate images with Imagen
            image_gcs_uris = []
            if generated_prompts:
                await self._update_status(video_doc_ref, "generating_visuals", f"Generating {len(generated_prompts)} images with Imagen...")
                
                image_uris = await self.generate_images_from_prompts(
                    prompts=generated_prompts,
                    video_id=event.video_id
                )
                image_gcs_uris.extend(image_uris)
                print(f"   Generated {len(image_gcs_uris)} images and saved to GCS.")

            # 3. Save GCS URIs to Firestore
            await video_doc_ref.update({
                "image_gcs_uris": firestore.ArrayUnion(image_gcs_uris),
                "image_prompts": firestore.ArrayUnion(generated_prompts), # Save prompts for reference
                "status": "visuals_generated",
                "status_message": "Social media images created."
            })
            print("   Image URIs and prompts saved to Firestore.")

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
            import traceback
            print(f"❌ VisualsAgent Error: {e}\n{traceback.format_exc()}")
            await self._update_status(video_doc_ref, "visuals_failed", "Failed to generate images.", {"error": str(e)})

    async def generate_images_from_prompts(self, prompts: list[str], video_id: str) -> list[str]:
        """
        Takes a list of prompts and generates an image for each one.
        Returns a list of the GCS URIs for the generated images.
        """
        tasks = [self._generate_and_upload_image(prompt, video_id, i) for i, prompt in enumerate(prompts)]
        results = await asyncio.gather(*tasks)
        # Filter out any None results from failed generations
        return [uri for uri in results if uri]