import os
from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from google.cloud import firestore

from ..database import db
from ..agents.visuals import VisualsAgent

router = APIRouter(
    tags=["generation"],
)

class RegenerateImageRequest(BaseModel):
    video_id: str
    prompt: str
    diversity_gender: bool = False
    diversity_ethnicity: bool = False
    diversity_ability: bool = False

class RegeneratePromptsRequest(BaseModel):
    video_id: str

class PromptRequest(BaseModel):
    prompt: str

@router.post("/regenerate-image")
async def regenerate_image(request: RegenerateImageRequest):
    """
    Generates a new image from a prompt and adds it to the video's record.
    """
    print(f" regenerating image for video {request.video_id} with prompt: {request.prompt[:30]}...")
    video_doc_ref = db.collection("videos").document(request.video_id)

    try:
        gcp_project_id = os.getenv("GOOGLE_CLOUD_PROJECT")
        gcp_region = os.getenv("GCP_REGION")
        gcs_bucket_name = os.getenv("GCS_BUCKET_NAME")
        gemini_api_key = os.getenv("GEMINI_API_KEY")
        imagen_model_name = os.getenv("IMAGEN_MODEL_NAME", "imagen-3.0-generate-002")

        if not all([gcp_project_id, gcp_region, gcs_bucket_name, gemini_api_key]):
            raise ValueError("Missing necessary configuration for VisualsAgent on the server.")

        visuals_agent = VisualsAgent(
            project_id=gcp_project_id,
            location=gcp_region,
            bucket_name=gcs_bucket_name,
            api_key=gemini_api_key,
            model_name=imagen_model_name
        )

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

    gcp_project_id = os.getenv("GOOGLE_CLOUD_PROJECT")
    gcp_region = os.getenv("GCP_REGION")
    gcs_bucket_name = os.getenv("GCS_BUCKET_NAME")
    gemini_api_key = os.getenv("GEMINI_API_KEY")
    imagen_model_name = os.getenv("IMAGEN_MODEL_NAME", "imagegeneration@006")
    gemini_model_name = os.getenv("GEMINI_MODEL_NAME", "gemini-1.5-pro-latest")

    visuals_agent = VisualsAgent(
        project_id=gcp_project_id, 
        location=gcp_region, 
        bucket_name=gcs_bucket_name, 
        api_key=gemini_api_key, 
        model_name=imagen_model_name,
        gemini_model_name=gemini_model_name
    )
    
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
        new_thumbnail = await visuals_agent.generate_single_image_from_prompt(video_id, prompt_request.prompt)
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

@router.post("/api/video/{video_id}/generate-prompts")
async def generate_prompts_on_demand(video_id: str, request: Request):
    """API endpoint to generate a new set of image prompts on-demand."""
    visuals_agent = request.app.state.visuals_agent
    if not visuals_agent:
        return JSONResponse(status_code=500, content={"message": "Visuals agent not initialized."})

    try:
        video_doc_ref = db.collection("videos").document(video_id)
        doc = await video_doc_ref.get()
        if not doc.exists:
            return JSONResponse(status_code=404, content={"message": "Video not found"})
        
        video_data = doc.to_dict()
        structured_data = video_data.get("structured_data")
        substack_gcs_uri = video_data.get("substack_gcs_uri")

        if not structured_data:
             raise ValueError("Structured data not found, cannot generate prompts.")

        new_prompts = await visuals_agent._generate_image_prompts(structured_data, substack_gcs_uri)
        return JSONResponse(content={"prompts": new_prompts})

    except Exception as e:
        print(f"On-demand prompt generation failed: {e}")
        return JSONResponse(status_code=500, content={"message": str(e)}) 