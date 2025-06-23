import os
from fastapi import APIRouter, Request, HTTPException, Body
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from google.cloud import firestore
from google.cloud import storage
from fastapi import Depends
from datetime import datetime, timezone

from ..database import db
from ..agents.visuals import VisualsAgent

router = APIRouter(
    tags=["generation"],
    prefix="/api"
)

class RegenerateImageRequest(BaseModel):
    video_id: str = Field(..., description="The ID of the video to regenerate an image for.")
    prompt: str = Field(..., description="The prompt to use for generating the image.")
    diversity_gender: bool = False
    diversity_ethnicity: bool = False
    diversity_ability: bool = False

class RegeneratePromptsRequest(BaseModel):
    video_id: str

class PromptRequest(BaseModel):
    prompt: str
    model_name: str | None = None

class OnDemandImageRequest(BaseModel):
    prompt: str
    model_name: str | None = None

class GeneratePromptsRequest(BaseModel):
    context: str

# This is a simplification. You'd likely have a shared storage client.
storage_client = storage.Client()
bucket_name = os.environ.get("GCS_BUCKET_NAME")

def get_visuals_agent():
    gcp_project_id = os.getenv("GOOGLE_CLOUD_PROJECT")
    gcp_region = os.getenv("GCP_REGION")
    gcs_bucket_name = os.getenv("GCS_BUCKET_NAME")
    gemini_api_key = os.getenv("GEMINI_API_KEY")
    imagen_model_name = os.getenv("IMAGEN_MODEL_NAME", "imagegeneration@006")
    gemini_model_name = os.getenv("GEMINI_MODEL_NAME")

    if not all([gcp_project_id, gcp_region, gcs_bucket_name, gemini_api_key, gemini_model_name]):
        raise HTTPException(status_code=500, detail="Missing critical environment variables for VisualsAgent.")

    visuals_agent = VisualsAgent(
        project_id=gcp_project_id, 
        location=gcp_region, 
        bucket_name=gcs_bucket_name, 
        api_key=gemini_api_key, 
        model_name=imagen_model_name,
        gemini_model_name=gemini_model_name
    )
    return visuals_agent

@router.post("/regenerate-image")
async def regenerate_image(request: RegenerateImageRequest):
    """
    Generates a new image from a prompt and adds it to the video's record.
    """
    print(f" regenerating image for video {request.video_id} with prompt: {request.prompt[:30]}...")
    video_doc_ref = db.collection("videos").document(request.video_id)

    try:
        visuals_agent = get_visuals_agent()

        new_image_url = await visuals_agent._generate_and_upload_image(
            prompt=request.prompt,
            video_id=request.video_id,
            index=99,
            diversity_options={
                "gender": request.diversity_gender,
                "ethnicity": request.diversity_ethnicity,
                "ability": request.diversity_ability,
            }
        )

        await video_doc_ref.update({
            "image_urls": firestore.ArrayUnion([new_image_url])
        })

        print(f"   Successfully generated and saved new image: {new_image_url}")
        return JSONResponse(status_code=200, content={"new_image_url": new_image_url})

    except Exception as e:
        print(f"❌ Image Regeneration Error: {e}")
        await video_doc_ref.update({"status": "visuals_failed", "error": f"Regeneration failed: {e}"})
        return JSONResponse(status_code=500, content={"message": "An internal error occurred during image regeneration."})

@router.post("/regenerate-prompts")
async def regenerate_prompts(request: RegeneratePromptsRequest):
    """
    API endpoint to regenerate image prompts for a video.
    """
    video_doc_ref = db.collection("videos").document(request.video_id)
    doc = await video_doc_ref.get()

    if not doc.exists:
        return JSONResponse(status_code=404, content={"message": "Video not found"})

    video_data = doc.to_dict()
    structured_data = video_data.get("structured_data")
    substack_gcs_uri = video_data.get("substack_gcs_uri")
    if not structured_data:
        return JSONResponse(status_code=400, content={"message": "Analysis data (structured_data) not found."})

    visuals_agent = get_visuals_agent()
    
    try:
        new_prompts = await visuals_agent._generate_image_prompts(structured_data, substack_gcs_uri)

        await video_doc_ref.update({
            "image_prompts": firestore.ArrayUnion(new_prompts)
        })

        print(f"   ✅ Successfully generated and saved {len(new_prompts)} new prompts.")
        return JSONResponse(status_code=200, content={"new_prompts": new_prompts})

    except Exception as e:
        print(f"❌ Prompt Regeneration Error: {e}")
        return JSONResponse(status_code=500, content={"message": "An internal error occurred during prompt regeneration."})

@router.post("/api/video/{video_id}/generate-thumbnail")
async def generate_thumbnail_on_demand(video_id: str, prompt_request: PromptRequest, request: Request):
    """API endpoint to generate a single thumbnail on-demand."""
    visuals_agent = request.app.state.visuals_agent
    if not visuals_agent:
        return JSONResponse(status_code=500, content={"message": "Visuals agent not initialized."})
    
    try:
        new_thumbnail = await visuals_agent.generate_single_image_from_prompt(
            video_id, 
            prompt_request.prompt,
            model_name=prompt_request.model_name
        )
        if not new_thumbnail:
            raise Exception("Image generation failed.")

        video_doc_ref = db.collection("videos").document(video_id)
        await video_doc_ref.update({
            "generated_thumbnails": firestore.ArrayUnion([new_thumbnail])
        })
        
        return JSONResponse(content={"thumbnail": new_thumbnail}, status_code=201)

    except Exception as e:
        print(f"On-demand thumbnail generation failed: {e}")
        return JSONResponse(status_code=500, content={"message": str(e)})

@router.post("/video/{video_id}/generate-prompts")
async def generate_prompts_for_video(video_id: str, request: GeneratePromptsRequest, agent: VisualsAgent = Depends(get_visuals_agent)):
    """API endpoint to generate a new set of image prompts on-demand."""
    doc_ref = db.collection("videos").document(video_id)
    try:
        doc = await doc_ref.get()
        if not doc.exists:
            return JSONResponse(status_code=404, content={"message": "Video not found"})
        
        video_data = doc.to_dict()
        structured_data = video_data.get("structured_data")
        substack_gcs_uri = video_data.get("substack_gcs_uri")
        
        if not structured_data:
            raise ValueError("Structured data not found, cannot generate prompts.")

        prompts = await agent._generate_image_prompts(structured_data, substack_gcs_uri)
        return {"prompts": prompts}
    except Exception as e:
        print(f"On-demand prompt generation failed: {e}")
        return JSONResponse(status_code=500, content={"message": str(e)})

@router.post("/video/{video_id}/generate-image")
async def generate_on_demand_image(video_id: str, request: OnDemandImageRequest, agent: VisualsAgent = Depends(get_visuals_agent)):
    """
    On-demand, generates a single image for a video based on a user-provided prompt.
    """
    if not request.prompt:
        raise HTTPException(status_code=400, detail="Prompt cannot be empty.")
    
    try:
        print(f"   Using on-demand model: {request.model_name}")
        image_data = await agent.generate_single_image_from_prompt(
            video_id,
            request.prompt,
            model_name=request.model_name
        )
        if image_data and "gcs_uri" in image_data:
            gcs_uri = image_data["gcs_uri"]
            
            # Convert the GCS URI to a signed URL for the frontend
            blob_name = gcs_uri.replace(f"gs://{bucket_name}/", "")
            bucket = storage_client.bucket(bucket_name)
            blob = bucket.blob(blob_name)

            signed_url = blob.generate_signed_url(
                version="v4",
                expiration=3600, # 1 hour
                method="GET",
            )
            
            # Save the permanent GCS URI to Firestore for later use
            video_doc_ref = db.collection("videos").document(video_id)
            await video_doc_ref.update({
                "on_demand_thumbnails": firestore.ArrayUnion([
                    {"prompt": request.prompt, "gcs_uri": gcs_uri, "model": request.model_name, "created_at": datetime.now(timezone.utc)}
                ])
            })

            # Prepare data to return to frontend
            response_data = {
                "prompt": request.prompt,
                "gcs_uri": gcs_uri,
                "model": request.model_name,
                "created_at": datetime.now(timezone.utc).isoformat(),
                "image_url": signed_url
            }

            # Return the data with the signed URL for immediate display
            return response_data

        raise HTTPException(status_code=500, detail="Image generation failed.")
    except Exception as e:
        print(f"On-demand thumbnail generation failed: {e}")
        raise HTTPException(status_code=500, detail=f"An error occurred: {e}") 