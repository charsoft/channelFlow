import asyncio
import os
import shutil

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from .routers import (
    auth as auth_router,
    videos as videos_router,
    clips as clips_router,
    generation as generation_router,
    admin as admin_router,
    db_upload as db_upload_router,
)
from .services import session_service, artifact_service
from google.cloud import storage, firestore
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build 
from .event_bus import EventBus
from .config import (
    GCP_PROJECT_ID,
    GCS_BUCKET_NAME,
    GEMINI_API_KEY,
    GCP_REGION,
    PROXY_URL,
    FFMPEG_PATH,
    IMAGEN_MODEL_NAME,
    GEMINI_MODEL_NAME,
    YOUTUBE_API_KEY,
    TARGET_CHANNEL_ID,
    ENABLE_AUTO_INGESTION
)

storage_client = storage.Client()
firestore_client = firestore.Client()

event_bus = EventBus()


bucket_name = storage_client.bucket(GCS_BUCKET_NAME) #not the bucket name, but the bucket object. this is not a string, it is an object.
gcp_project_id = GCP_PROJECT_ID
gcp_region = GCP_REGION
gemini_api_key = GEMINI_API_KEY
ffmpeg_path = FFMPEG_PATH
imagen_model_name = IMAGEN_MODEL_NAME
gemini_model_name = GEMINI_MODEL_NAME  
api_key = YOUTUBE_API_KEY
channel_id = TARGET_CHANNEL_ID
enable_auto_ingestion = ENABLE_AUTO_INGESTION



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
    # Import agents here to avoid circular dependencies on startup
    from src.agents.analysis import AnalysisAgent
    from src.agents.copywriter import CopywriterAgent
    from src.agents.ingestion import IngestionAgent
    from src.agents.publisher import PublisherAgent
    from src.agents.transcription import TranscriptionAgent
    from src.agents.visuals import VisualsAgent

    app.state.video_cache = video_cache
    app.state.bucket = bucket_name
    app.state.gcp_project_id = gcp_project_id
    app.state.gcp_region = gcp_region
    app.state.gemini_api_key = gemini_api_key
    app.state.ffmpeg_path = ffmpeg_path
    app.state.imagen_model_name = imagen_model_name
    app.state.gemini_model_name = gemini_model_name

    print("Application starting up...")
    
    gcs_bucket_name  = GCS_BUCKET_NAME
    if not gcs_bucket_name:
        print("🚨 GCS_BUCKET_NAME is not configured. File storage agents will fail.")
        return

   
    if not gemini_api_key or gemini_api_key == "YOUR_GEMINI_API_KEY_HERE":
        print("🚨 GEMINI_API_KEY is not configured. Transcription and other AI agents will fail.")
        return

   
    if not ffmpeg_path:
        print("⚪️ FFMPEG_PATH environment variable not set. Transcription will try to use 'ffmpeg' from the system's PATH.")

        

    if not gcp_project_id or not gcp_region:
        print("🚨 GOOGLE_CLOUD_PROJECT or GCP_REGION are not configured. The VisualsAgent will fail.")


    print(f"⚪️ Using Imagen model: {imagen_model_name}")

 
    print(f"⚪️ Using Gemini model: {gemini_model_name}")

 
    
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

   
    
    if enable_auto_ingestion and app.state.ingestion_agent:
        print("✅ Auto-ingestion monitoring is ENABLED.")
        asyncio.create_task(app.state.ingestion_agent.start_monitoring())
    else:
        print("⚪️ Auto-ingestion monitoring is DISABLED. Use the web UI for on-demand processing.")
    
    app.state.transcription_agent = TranscriptionAgent(
        api_key=gemini_api_key, 
        bucket_name=gcs_bucket_name,
        ffmpeg_path=ffmpeg_path,
        model_name=gemini_model_name
    )
    app.state.analysis_agent = AnalysisAgent(api_key=gemini_api_key, bucket_name=gcs_bucket_name, model_name=gemini_model_name)
    app.state.copywriter_agent = CopywriterAgent(api_key=gemini_api_key, bucket_name=gcs_bucket_name, model_name=gemini_model_name)
    
    app.state.visuals_agent = VisualsAgent(
        bucket=bucket_name,
        api_key=gemini_api_key,
        imagen_model_name=imagen_model_name,
        gemini_model_name=gemini_model_name
    )
    app.state.publisher_agent =    PublisherAgent(bucket_name=bucket_name)
    
    print("All agents have been initialized.")


    app.include_router(auth_router.router)
    app.include_router(videos_router.router)
    app.include_router(clips_router.router)
    app.include_router(generation_router.router)
    app.include_router(admin_router.router)
    app.include_router(db_upload_router.router)

    app.mount("/", StaticFiles(directory="frontend/dist", html=True), name="static-frontend") 