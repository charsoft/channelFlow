import asyncio
import os
import shutil

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import firebase_admin

from src.agents.analysis import AnalysisAgent
from src.agents.copywriter import CopywriterAgent
from src.agents.ingestion import IngestionAgent
from src.agents.publisher import PublisherAgent
from src.agents.transcription import TranscriptionAgent
from src.agents.visuals import VisualsAgent
from src.routers import admin, auth, clips, generation, videos

# Load environment variables from .env file
load_dotenv()

app = FastAPI()

# Get the frontend URL from environment variables, with a default for local dev
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:5173")

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=[FRONTEND_URL, "https://accounts.google.com"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# A simple in-memory cache for downloaded video paths
video_cache = {}


@app.on_event("shutdown")
def shutdown_event():
    """
    On shutdown, clean up any temporary video cache directories.
    """
    print("Application shutting down. Cleaning up video cache...")
    for video_id, path in video_cache.items():
        try:
            dir_path = os.path.dirname(path)
            if os.path.isdir(dir_path):
                shutil.rmtree(dir_path)
                print(f"   Removed cache directory: {dir_path}")
        except Exception as e:
            print(f"   Error removing cache for {video_id}: {e}")
    print("Video cache cleanup complete.")


@app.on_event("startup")
async def startup_event():
    """
    On startup, instantiate all the agents to register their event handlers
    and start any background tasks.
    """
    app.state.video_cache = video_cache
    try:
        firebase_admin.initialize_app()
        print("✅ Firebase Admin SDK initialized successfully.")
    except Exception as e:
        print(f"🚨 Failed to initialize Firebase Admin SDK: {e}")

    print("Application starting up...")

    gcs_bucket_name = os.getenv("GCS_BUCKET_NAME")
    if not gcs_bucket_name:
        print("🚨 GCS_BUCKET_NAME is not configured. File storage agents will fail.")
        return

    gemini_api_key = os.getenv("GEMINI_API_KEY")
    if not gemini_api_key or gemini_api_key == "YOUR_GEMINI_API_KEY_HERE":
        print("🚨 GEMINI_API_KEY is not configured. Transcription and other AI agents will fail.")
        return

    ffmpeg_path = os.getenv("FFMPEG_PATH")
    if not ffmpeg_path:
        print("⚪️ FFMPEG_PATH environment variable not set. Transcription will try to use 'ffmpeg' from the system's PATH.")

    gcp_project_id = os.getenv("GOOGLE_CLOUD_PROJECT")
    gcp_region = os.getenv("GCP_REGION")
    if not gcp_project_id or not gcp_region:
        print("🚨 GOOGLE_CLOUD_PROJECT or GCP_REGION are not configured. The VisualsAgent will fail.")

    imagen_model_name = os.getenv("IMAGEN_MODEL_NAME", "imagegeneration@006")
    print(f"⚪️ Using Imagen model: {imagen_model_name}")

    gemini_model_name = os.getenv("GEMINI_MODEL_NAME", "gemini-1.5-pro-latest")
    print(f"⚪️ Using Gemini model: {gemini_model_name}")

    api_key = os.getenv("YOUTUBE_API_KEY")
    channel_id = os.getenv("TARGET_CHANNEL_ID")

    if not api_key or api_key == "YOUR_YOUTUBE_API_KEY":
        print("🚨 YOUTUBE_API_KEY is not set or is invalid. Please set it in your .env file.")
        app.state.ingestion_agent = None
        return

    try:
        print("Attempting to initialize IngestionAgent...")
        app.state.ingestion_agent = IngestionAgent(api_key=api_key, channel_id=channel_id)
        print("✅ IngestionAgent initialized successfully.")
    except Exception as e:
        print("🚨🚨🚨 FAILED TO INITIALIZE INGESTION AGENT 🚨🚨🚨")
        print(f"The error was: {e}")
        import traceback
        traceback.print_exc()
        app.state.ingestion_agent = None

    enable_auto_ingestion = os.getenv("ENABLE_AUTO_INGESTION", "false").lower() == "true"

    if enable_auto_ingestion and app.state.ingestion_agent:
        print("✅ Auto-ingestion monitoring is ENABLED.")
        asyncio.create_task(app.state.ingestion_agent.start_monitoring())
    else:
        print("⚪️ Auto-ingestion monitoring is DISABLED. Use the web UI for on-demand processing.")

    TranscriptionAgent(
        api_key=gemini_api_key,
        bucket_name=gcs_bucket_name,
        ffmpeg_path=ffmpeg_path,
        model_name="gemini-1.5-pro-latest"
    )
    AnalysisAgent(api_key=gemini_api_key, bucket_name=gcs_bucket_name, model_name=gemini_model_name)
    CopywriterAgent(api_key=gemini_api_key, bucket_name=gcs_bucket_name, model_name=gemini_model_name)

    app.state.visuals_agent = VisualsAgent(
        api_key=gemini_api_key,
        project_id=gcp_project_id,
        location=gcp_region,
        bucket_name=gcs_bucket_name,
        model_name=imagen_model_name,
        gemini_model_name=gemini_model_name
    )
    PublisherAgent()

    print("All agents have been initialized.")


app.include_router(auth.router)
app.include_router(videos.router)
app.include_router(generation.router)
app.include_router(clips.router)
app.include_router(admin.router)

app.mount("/", StaticFiles(directory="frontend/dist", html=True), name="static-frontend") 