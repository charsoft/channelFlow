import os
import asyncio
import google.generativeai as genai
import vertexai
from vertexai.preview.vision_models import ImageGenerationModel

from ..event_bus import event_bus
from ..events import CopyReady, VisualsReady
from ..database import db
from google.cloud import storage
from google.cloud.firestore import ArrayUnion
from datetime import datetime, timezone
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
        # Subscribe to CopyReady
        event_bus.subscribe(CopyReady, self.handle_copy_ready)

    async def _generate_and_upload_image(self, prompt: str, video_id: str, index: int) -> dict:
        """Generates a single image, uploads it, and returns a dictionary with image metadata."""
        
        print(f"     - Generating image {index}: {prompt[:80]}...")
        try:
            response = await asyncio.to_thread(
                self.image_model.generate_images,
                prompt=prompt,
                number_of_images=1,
                # Common negative prompt to improve quality
                negative_prompt="text, letters, words, numbers, blurry, low-quality, watermark"
            )
            
            if not response.images:
                print(f"       ⚠️ Image generation failed for prompt: {prompt[:80]}...")
                return None

            image_bytes = response.images[0]._image_bytes
            
            # Upload to GCS
            image_filename = f"{video_id}_visual_{index}_{uuid.uuid4()}.png"
            blob_path = f"images/{image_filename}"
            blob = self.storage_client.bucket(self.bucket_name).blob(blob_path)
            
            # Use a non-blocking upload
            await asyncio.to_thread(blob.upload_from_string, image_bytes, 'image/png')
            
            gcs_uri = f"gs://{self.bucket_name}/{blob_path}"
            print(f"       Uploaded to {gcs_uri}")
            
            return {
                "gcs_uri": gcs_uri,
                "prompt": prompt,
                "created_at": datetime.now(timezone.utc)
            }
        except Exception as e:
            # If there's an error with a specific image generation, log it and continue
            print(f"       ❌ Error generating image for prompt '{prompt[:80]}...': {e}")
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
            if not doc.exists:
                raise FileNotFoundError(f"Video document {event.video_id} not found.")
            video_data = doc.to_dict()

            # The new re-trigger logic might leave old images. Clear them out.
            if video_data.get("status") == "pending_visuals_rerun":
                print("   Re-running visuals. Clearing previous on-demand thumbnails.")
                await video_doc_ref.update({"on_demand_thumbnails": []})

            marketing_copy = video_data.get("marketing_copy", {})
            if not marketing_copy:
                raise ValueError("Marketing copy not found in Firestore document.")

            await self._update_status(video_doc_ref, "generating_visuals", "Generating image prompts with Gemini...")
            
            # 1. Use Gemini to generate creative prompts for Imagen
            gemini_prompt = self._build_gemini_prompt(event.video_title, marketing_copy)
            response = await self.model.generate_content_async(
                gemini_prompt,
                generation_config=genai.types.GenerationConfig(response_mime_type="application/json")
                )
            generated_prompts = json.loads(response.text).get("image_prompts", [])
            print(f"   Generated {len(generated_prompts)} image prompts.")

            # 2. Generate images with Imagen
            image_data_list = []
            if generated_prompts:
                await self._update_status(video_doc_ref, "generating_visuals", f"Generating {len(generated_prompts)} images with Imagen...")
                image_data_list = await self.generate_images_from_prompts(
                    prompts=generated_prompts,
                    video_id=event.video_id
                )
                print(f"   Generated {len(image_data_list)} images and saved to GCS.")

            # 3. Save a structured list of image data to Firestore
            if image_data_list:
                await video_doc_ref.update({
                    # Use ArrayUnion to add to the list without overwriting
                    "on_demand_thumbnails": ArrayUnion(image_data_list),
                    "status": "visuals_generated",
                    "status_message": "Social media images created."
                })
                print("   Image data saved to Firestore in 'on_demand_thumbnails'.")
            else:
                 await video_doc_ref.update({
                    "status": "visuals_generated",
                    "status_message": "Completed visual stage, but no images were generated."
                })

            # 4. Publish event for next agents
            visuals_ready_event = VisualsReady(
                video_id=event.video_id,
                video_title=event.video_title,
            )
            await event_bus.publish(visuals_ready_event)

        except Exception as e:
            import traceback
            print(f"❌ VisualsAgent Error: {e}\n{traceback.format_exc()}")
            await self._update_status(video_doc_ref, "visuals_failed", f"Failed to generate images: {e}", {"error": str(e)})

    async def generate_images_from_prompts(self, prompts: list[str], video_id: str) -> list[dict]:
        """Generates multiple images concurrently from a list of prompts."""
        tasks = [
            self._generate_and_upload_image(prompt, video_id, i + 1)
            for i, prompt in enumerate(prompts)
        ]
        image_data_results = await asyncio.gather(*tasks)
        # Filter out any None results from failed generations
        return [data for data in image_data_results if data]

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