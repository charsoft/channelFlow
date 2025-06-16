import asyncio
import os
from datetime import datetime
from fastapi import FastAPI, Request, Form, Depends, HTTPException, status
from fastapi.responses import HTMLResponse, JSONResponse, FileResponse
from sse_starlette.sse import EventSourceResponse
from pydantic import BaseModel
from dotenv import load_dotenv
from google.cloud import storage
from .database import db
from .agents.ingestion import IngestionAgent, get_video_id
from .agents.transcription import TranscriptionAgent
from .agents.analysis import AnalysisAgent
from .agents.copywriter import CopywriterAgent
from .agents.visuals import VisualsAgent
from .agents.publisher import PublisherAgent
from .event_bus import event_bus
from .events import NewVideoDetected, TranscriptReady, ContentAnalysisComplete, CopyReady
from .video_processing import create_vertical_clip
# import genai
import json
import yt_dlp
import tempfile
import uuid
import shutil
import firebase_admin
from firebase_admin import credentials, auth
#from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordBearer
from google_auth_oauthlib.flow import Flow
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from .security import encrypt_data, decrypt_data

# Load environment variables from .env file
load_dotenv()

app = FastAPI()

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, you should restrict this to your Firebase Hosting domain
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# A simple in-memory cache for downloaded video paths
# In a production multi-worker environment, a more robust cache like Redis or a shared filesystem would be better.
video_cache = {}

# db = firestore.Client(project=os.getenv("GOOGLE_CLOUD_PROJECT"))
#templates = Jinja2Templates(directory="src/static")

@app.on_event("shutdown")
def shutdown_event():
    """
    On shutdown, clean up any temporary video cache directories.
    """
    print("Application shutting down. Cleaning up video cache...")
    for video_id, path in video_cache.items():
        try:
            # The path is the video file; its directory is what we want to delete.
            dir_path = os.path.dirname(path)
            if os.path.isdir(dir_path):
                shutil.rmtree(dir_path)
                print(f"   Removed cache directory: {dir_path}")
        except Exception as e:
            print(f"   Error removing cache for {video_id}: {e}")
    print("Video cache cleanup complete.")

class IngestRequest(BaseModel):
    url: str

class IngestUrlRequest(BaseModel):
    url: str
    force: bool = False

class AuthCodeRequest(BaseModel):
    code: str

class ClientConfig(BaseModel):
    firebase_api_key: str
    firebase_auth_domain: str
    firebase_project_id: str
    google_client_id: str

@app.on_event("startup")
async def startup_event():
    """
    On startup, instantiate all the agents to register their event handlers
    and start any background tasks.
    """
    # Initialize Firebase Admin SDK
    try:
        # In a Cloud Run environment, the GOOGLE_APPLICATION_CREDENTIALS env var
        # is set automatically. For local dev, you'd set it to your service account key.
        firebase_admin.initialize_app()
        print("✅ Firebase Admin SDK initialized successfully.")
    except Exception as e:
        print(f"🚨 Failed to initialize Firebase Admin SDK: {e}")

    print("Application starting up...")
    
    # Get GCS Bucket Name
    gcs_bucket_name = os.getenv("GCS_BUCKET_NAME")
    if not gcs_bucket_name:
        print("🚨 GCS_BUCKET_NAME is not configured. File storage agents will fail.")
        return

    # Get Gemini API Key
    gemini_api_key = os.getenv("GEMINI_API_KEY")
    if not gemini_api_key or gemini_api_key == "YOUR_GEMINI_API_KEY_HERE":
        print("🚨 GEMINI_API_KEY is not configured. Transcription and other AI agents will fail.")
        return

    # Get optional FFMPEG Path
    ffmpeg_path = os.getenv("FFMPEG_PATH")
    if not ffmpeg_path:
        print("⚪️ FFMPEG_PATH environment variable not set. Transcription will try to use 'ffmpeg' from the system's PATH.")

    # Get Google Cloud config for Vertex AI
    gcp_project_id = os.getenv("GOOGLE_CLOUD_PROJECT")
    gcp_region = os.getenv("GCP_REGION")
    if not gcp_project_id or not gcp_region:
        print("🚨 GOOGLE_CLOUD_PROJECT or GCP_REGION are not configured. The VisualsAgent will fail.")
        # We can let it continue because other agents might work, but log a clear warning.

    # Get the Imagen model name from environment, with a default
    imagen_model_name = os.getenv("IMAGEN_MODEL_NAME", "imagegeneration@006")
    print(f"⚪️ Using Imagen model: {imagen_model_name}")

    # Get the Gemini model name from environment, with a default
    gemini_model_name = os.getenv("GEMINI_MODEL_NAME", "gemini-1.5-pro-latest")
    print(f"⚪️ Using Gemini model: {gemini_model_name}")

    # Get YouTube credentials from environment
    api_key = os.getenv("YOUTUBE_API_KEY")
    channel_id = os.getenv("TARGET_CHANNEL_ID")
    
    if not api_key or api_key == "YOUR_YOUTUBE_API_KEY":
        print("🚨 YOUTUBE_API_KEY is not set or is invalid. Please set it in your .env file.")
        # Store a dummy agent to prevent errors, but log that it's disabled
        app.state.ingestion_agent = None
        return
        
    # Create and store a single IngestionAgent instance
    app.state.ingestion_agent = IngestionAgent(api_key=api_key, channel_id=channel_id)

    # Check if auto-ingestion is enabled via environment variable
    enable_auto_ingestion = os.getenv("ENABLE_AUTO_INGESTION", "false").lower() == "true"
    
    if enable_auto_ingestion:
        print("✅ Auto-ingestion monitoring is ENABLED.")
        # Start the monitoring loop
        asyncio.create_task(app.state.ingestion_agent.start_monitoring())
    else:
        print("⚪️ Auto-ingestion monitoring is DISABLED. Use the web UI for on-demand processing.")
    
    # Instantiate other agents to register their handlers
    TranscriptionAgent(
        api_key=gemini_api_key, 
        bucket_name=gcs_bucket_name,
        ffmpeg_path=ffmpeg_path,
        model_name="gemini-1.5-pro-latest"
    )
    AnalysisAgent(api_key=gemini_api_key, bucket_name=gcs_bucket_name, model_name=gemini_model_name)
    CopywriterAgent(api_key=gemini_api_key, bucket_name=gcs_bucket_name, model_name=gemini_model_name)
    
    # Store the visuals agent on the app state to make it accessible to endpoints
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

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

async def verify_token(token: str = Depends(oauth2_scheme)):
    """
    FastAPI dependency to verify Firebase ID token.
    """
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing authentication token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    try:
        # Verify the token against the Firebase Auth API.
        decoded_token = auth.verify_id_token(token)
        return decoded_token
    except auth.InvalidIdTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except Exception as e:
        print(f"Error verifying token: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error while verifying token",
        )

@app.get("/api/config", response_model=ClientConfig)
async def get_client_config():
    """
    Provides the client-side configuration needed for Firebase and Google OAuth.
    """
    config = {
        "firebase_api_key": os.getenv("FIREBASE_API_KEY"),
        "firebase_auth_domain": os.getenv("FIREBASE_AUTH_DOMAIN"),
        "firebase_project_id": os.getenv("FIREBASE_PROJECT_ID"),
        "google_client_id": os.getenv("GOOGLE_CLIENT_ID"),
    }
    if not all(config.values()):
        raise HTTPException(
            status_code=500,
            detail="Server is missing required client-side configuration environment variables."
        )
    return config

@app.post("/api/oauth/exchange-code")
async def exchange_code(request: AuthCodeRequest, decoded_token: dict = Depends(verify_token)):
    """
    Exchanges a Google OAuth authorization code for credentials and stores them securely.
    """
    user_id = decoded_token.get("uid")
    
    try:
        client_id = os.getenv("GOOGLE_CLIENT_ID")
        client_secret = os.getenv("GOOGLE_CLIENT_SECRET")
        if not client_id or not client_secret:
            raise ValueError("Google Client ID or Secret is not configured on the server.")

        # IMPORTANT: The redirect_uri must EXACTLY match one of the authorized redirect URIs
        # for the OAuth 2.0 client, which you configured in the Google Cloud console.
        # For a pure client-side flow like this, 'postmessage' is a common and secure choice.
        flow = Flow.from_client_config(
            client_config={
                "web": {
                    "client_id": client_id,
                    "client_secret": client_secret,
                    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                    "token_uri": "https://oauth2.googleapis.com/token",
                }
            },
            scopes=['https://www.googleapis.com/auth/youtube.readonly'],
            redirect_uri='postmessage'
        )

        # Exchange the authorization code for credentials
        flow.fetch_token(code=request.code)
        creds = flow.credentials

        # Convert credentials to a dict and encrypt them
        creds_json = creds.to_json()
        encrypted_creds = encrypt_data(creds_json.encode())

        # Save encrypted credentials to Firestore
        cred_doc_ref = db.collection("user_credentials").document(user_id)
        await cred_doc_ref.set({"credentials": encrypted_creds})

        return JSONResponse(content={"message": "Successfully connected YouTube account."})

    except Exception as e:
        import traceback
        print(f"Error exchanging code for user {user_id}: {e}\n{traceback.format_exc()}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to exchange authorization code."
        )

@app.post("/api/ingest-url")
async def ingest_url(request: IngestUrlRequest, decoded_token: dict = Depends(verify_token)):
    """
    API endpoint to manually trigger ingestion. Uses the user's credentials.
    Requires authentication.
    """
    try:
        user_id = decoded_token.get("uid")
        print(f"Request received from authenticated user: {user_id}")

        # --- Get User's YouTube Credentials ---
        cred_doc_ref = db.collection("user_credentials").document(user_id)
        cred_doc = await cred_doc_ref.get()

        if not cred_doc.exists:
            return JSONResponse(status_code=403, content={"message": "User has not connected their YouTube account. Please authorize.", "code": "AUTH_REQUIRED"})

        encrypted_creds = cred_doc.to_dict().get("credentials")
        decrypted_creds_json = decrypt_data(encrypted_creds)
        creds = Credentials.from_authorized_user_info(json.loads(decrypted_creds_json))
        
        # Auto-refresh logic: If the token is expired, google-auth will try to refresh it
        # if a refresh token is present. We should save the potentially refreshed credentials.
        if creds.expired and creds.refresh_token:
            # The library handles the refresh call implicitly when you use the client
            print(f"User {user_id} credentials expired. They will be refreshed on next API call.")

        youtube = build('youtube', 'v3', credentials=creds)
        # --- End Get User's YouTube Credentials ---
        
        video_id = get_video_id(request.url)
        if not video_id:
            return JSONResponse(status_code=400, content={"message": "Invalid YouTube URL"})

        video_doc_ref = db.collection("videos").document(video_id)
        doc = await video_doc_ref.get()

        if doc.exists and not request.force:
            # Video exists and we are NOT forcing a reprocess
            print(f"Video {video_id} already processed. Returning cached data.")
            
            # Manually convert Firestore timestamp to a serializable format
            data = doc.to_dict()
            for key, value in data.items():
                if isinstance(value, datetime):
                    data[key] = value.isoformat()

            # Add the current status to the response
            response_data = {
                "status": "exists",
                "current_stage": data.get("status", "unknown"),
                "data": data
            }
            return JSONResponse(status_code=200, content=response_data)

        if doc.exists and request.force:
            # Video exists and we ARE forcing a reprocess
            print(f"Forcing reprocessing for video {video_id}. Deleting old data...")
            
            video_data = doc.to_dict()
            bucket_name = os.getenv("GCS_BUCKET_NAME")

            if bucket_name:
                storage_client = storage.Client()
                bucket = storage_client.bucket(bucket_name)

                # List of fields in Firestore that contain a single GCS URI
                gcs_uri_fields = ["transcript_gcs_uri", "analysis_gcs_uri", "substack_gcs_uri"]
                
                for field in gcs_uri_fields:
                    if gcs_uri := video_data.get(field):
                        try:
                            # Assumes format gs://<bucket_name>/<blob_path>
                            blob_path = gcs_uri.replace(f"gs://{bucket_name}/", "")
                            blob = bucket.blob(blob_path)
                            if await asyncio.to_thread(blob.exists):
                                await asyncio.to_thread(blob.delete)
                                print(f"   Deleted GCS file: {blob.name}")
                        except Exception as e:
                            print(f"   Could not delete GCS file from URI {gcs_uri}: {e}")

                # Handle image_urls (which is a list of public URLs)
                if image_urls := video_data.get("image_urls"):
                    for url in image_urls:
                        try:
                            # Assumes format https://storage.googleapis.com/<bucket_name>/<blob_path>
                            blob_path = url.replace(f"https://storage.googleapis.com/{bucket_name}/", "")
                            blob = bucket.blob(blob_path)
                            if await asyncio.to_thread(blob.exists):
                                await asyncio.to_thread(blob.delete)
                                print(f"   Deleted GCS image: {blob.name}")
                        except Exception as e:
                            print(f"   Could not delete GCS image from URL {url}: {e}")
            
            # 3. Delete Firestore document
            await video_doc_ref.delete()
            print(f"   Deleted Firestore document: {video_id}")
            
        # Proceed with ingestion for a new video or a forced reprocessing, using user's credentials
        try:
            video_response = await asyncio.to_thread(
                youtube.videos().list(part="snippet", id=video_id).execute
            )
            if not video_response.get("items"):
                return JSONResponse(status_code=400, content={"message": "Could not retrieve video title (video may be private or not exist)."})
            video_title = video_response["items"][0]["snippet"]["title"]
        except Exception as e:
            # This can happen if the user's token is invalid, revoked, or doesn't have permission.
            print(f"YouTube API Error for user {user_id}: {e}")
            return JSONResponse(status_code=403, content={"message": "Failed to access YouTube API. Your credentials may be invalid or revoked. Please try connecting your account again.", "code": "AUTH_REQUIRED"})

        # After getting the credentials, save them back to Firestore.
        # This is because a refresh token might have been used, and a new access token issued.
        # The google-auth library updates the credentials object in place.
        new_creds_json = creds.to_json()
        encrypted_new_creds = encrypt_data(new_creds_json.encode())
        await cred_doc_ref.set({"credentials": encrypted_new_creds})
        
        if not video_title:
             return JSONResponse(status_code=400, content={"message": "Could not retrieve video title."})

        event = NewVideoDetected(
            video_id=video_id,
            video_url=request.url,
            video_title=video_title
        )
        await event_bus.publish(event)

        return JSONResponse(status_code=202, content={"message": "Video ingestion started.", "video_id": video_id})

    except Exception as e:
        import traceback
        print(f"Error in /ingest-url: {e}\n{traceback.format_exc()}")
        return JSONResponse(status_code=500, content={"message": "An internal error occurred."})

@app.get("/status/{video_id}")
async def get_status(video_id: str):
    """
    API endpoint to poll for the status of a video processing job.
    """
    video_doc_ref = db.collection("videos").document(video_id)
    doc = await video_doc_ref.get()
    if not doc.exists:
        return JSONResponse(status_code=404, content={"message": "Video not found."})
    
    data = doc.to_dict()
    # Sanitize datetime objects for JSON serialization
    for key, value in data.items():
        if isinstance(value, datetime):
            data[key] = value.isoformat()
    
    return JSONResponse(status_code=200, content={"data": data})

@app.get("/stream-status/{video_id}")
async def stream_status(request: Request, video_id: str):
    """
    Streams status updates for a given video_id using Server-Sent Events (SSE).
    This implementation polls the Firestore document on the server-side.
    """
    async def event_generator():
        last_known_status = None
        try:
            while True:
                if await request.is_disconnected():
                    print(f"Client disconnected from {video_id} stream.")
                    break

                video_doc_ref = db.collection("videos").document(video_id)
                doc = await video_doc_ref.get()

                if not doc.exists:
                    # If document doesn't exist, stop streaming.
                    yield { "event": "message", "data": json.dumps({"status": "not_found", "message": "Video not found."})}
                    break
                
                data = doc.to_dict()
                current_status = data.get("status")

                # If the status has changed since the last time we checked, send an update.
                if current_status != last_known_status:
                    # Sanitize datetime objects for JSON serialization
                    for key, value in data.items():
                        if isinstance(value, datetime):
                            data[key] = value.isoformat()
                    
                    yield { "event": "message", "data": json.dumps(data) }
                    last_known_status = current_status
                
                # Wait for a short period before polling again
                await asyncio.sleep(1)

        except Exception as e:
            print(f"Error in SSE stream for {video_id}: {e}")
        finally:
            print(f"Closing SSE stream for {video_id}.")

    return EventSourceResponse(event_generator())

class RetriggerRequest(BaseModel):
    video_id: str
    stage: str # e.g., "transcription", "analysis", "copywriting", "visuals"

@app.post("/api/re-trigger")
async def re_trigger(request: RetriggerRequest):
    """
    Manually re-triggers a specific stage of the pipeline for a video.
    """
    video_doc_ref = db.collection("videos").document(request.video_id)
    doc = await video_doc_ref.get()

    if not doc.exists:
        return JSONResponse(status_code=404, content={"message": "Video not found."})

    video_data = doc.to_dict()
    video_title = video_data.get("video_title", "Unknown Title")
    
    # Map the stage name from the request to the corresponding event and data
    event_to_publish = None
    if request.stage == "transcription":
        await video_doc_ref.update({"status": "re-triggering transcription"})
        event_to_publish = NewVideoDetected(
            video_id=request.video_id,
            video_url=video_data.get("video_url"),
            video_title=video_title
        )
    elif request.stage == "analysis":
        await video_doc_ref.update({"status": "re-triggering analysis"})
        event_to_publish = TranscriptReady(
            video_id=request.video_id,
            video_title=video_title,
            transcript_gcs_uri=video_data.get("transcript_gcs_uri")
        )
    elif request.stage == "copywriting":
        await video_doc_ref.update({"status": "re-triggering copywriting"})
        event_to_publish = ContentAnalysisComplete(
            video_id=request.video_id,
            video_title=video_title,
            structured_data=video_data.get("structured_data")
        )
    elif request.stage == "visuals":
        await video_doc_ref.update({"status": "re-triggering visuals"})
        event_to_publish = CopyReady(
            video_id=request.video_id,
            video_title=video_title
        )
        
    if event_to_publish:
        await event_bus.publish(event_to_publish)
        return JSONResponse(status_code=200, content={"message": f"Stage '{request.stage}' re-triggered."})
    else:
        return JSONResponse(status_code=400, content={"message": f"Invalid stage '{request.stage}' provided."})

class RegenerateImageRequest(BaseModel):
    video_id: str
    prompt: str
    diversity_gender: bool = False
    diversity_ethnicity: bool = False
    diversity_ability: bool = False

@app.post("/regenerate-image")
async def regenerate_image(request: RegenerateImageRequest):
    """
    Generates a new image from a prompt and adds it to the video's record.
    """
    print(f" regenerating image for video {request.video_id} with prompt: {request.prompt[:30]}...")
    video_doc_ref = db.collection("videos").document(request.video_id)

    try:
        # We need a VisualsAgent instance to call its method.
        # This requires getting all the necessary config from env vars again.
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

        # Call the refactored method to generate a single image
        # We don't have a great index here, so we'll use a random number
        new_image_url = await visuals_agent._generate_and_upload_image(
            prompt=request.prompt,
            video_id=request.video_id,
            index=99,  # Using a placeholder index
            diversity_options={
                "gender": request.diversity_gender,
                "ethnicity": request.diversity_ethnicity,
                "ability": request.diversity_ability,
            }
        )

        # Atomically add the new URL to the image_urls array in Firestore
        await video_doc_ref.update({
            "image_urls": firestore.ArrayUnion([new_image_url])
        })

        print(f"   Successfully generated and saved new image: {new_image_url}")
        return JSONResponse(status_code=200, content={"new_image_url": new_image_url})

    except Exception as e:
        print(f"❌ Image Regeneration Error: {e}")
        await video_doc_ref.update({"status": "visuals_failed", "error": f"Regeneration failed: {e}"})
        return JSONResponse(status_code=500, content={"message": "An internal error occurred during image regeneration."})

class RegeneratePromptsRequest(BaseModel):
    video_id: str

@app.post("/regenerate-prompts")
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

    # Re-instantiate the agent to call its method.
    # In a larger app, you might use a dependency injection system.
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

        # Atomically add the new prompts to the image_prompts array
        await video_doc_ref.update({
            "image_prompts": firestore.ArrayUnion(new_prompts)
        })

        print(f"   ✅ Successfully generated and saved {len(new_prompts)} new prompts.")
        return JSONResponse(status_code=200, content={"new_prompts": new_prompts})

    except Exception as e:
        print(f"❌ Prompt Regeneration Error: {e}")
        return JSONResponse(status_code=500, content={"message": "An internal error occurred during prompt regeneration."})

@app.get("/api/videos")
async def get_all_videos():
    """
    API endpoint to fetch all video documents from Firestore.
    """
    videos = []
    try:
        videos_ref = db.collection("videos").stream()
        async for video in videos_ref:
            video_data = video.to_dict()
            # Ensure all data is JSON serializable
            for key, value in video_data.items():
                if isinstance(value, datetime):
                    video_data[key] = value.isoformat()
            videos.append(video_data)
        
        # Sort videos by last update time, newest first
        videos.sort(key=lambda v: v.get('updated_at', '1970-01-01T00:00:00'), reverse=True)
        
        return JSONResponse(content={"videos": videos})
    except Exception as e:
        print(f"Error fetching all videos: {e}")
        return JSONResponse(status_code=500, content={"message": "Failed to fetch videos."})

@app.get("/api/video/{video_id}")
async def get_video(video_id: str):
    """API endpoint to fetch a single video's complete data."""
    try:
        video_doc_ref = db.collection("videos").document(video_id)
        doc = await video_doc_ref.get()
        if not doc.exists:
            return JSONResponse(status_code=404, content={"message": "Video not found"})
        
        video_data = doc.to_dict()
        # Ensure all data is JSON serializable
        for key, value in video_data.items():
            if isinstance(value, datetime):
                video_data[key] = value.isoformat()
        
        return JSONResponse(content={"video": video_data})
    except Exception as e:
        print(f"Error fetching video {video_id}: {e}")
        return JSONResponse(status_code=500, content={"message": "Failed to fetch video."})

@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    return "API is running"

@app.get("/management", response_class=HTMLResponse)
async def management(request: Request):
    return "API is running"

@app.get("/video/{video_id}", response_class=HTMLResponse)
async def video_detail_page(request: Request, video_id: str):
    return "API is running"

@app.get("/health")
async def health_check():
    return {"status": "ok"}

class PromptRequest(BaseModel):
    prompt: str

@app.post("/api/video/{video_id}/generate-thumbnail")
async def generate_thumbnail_on_demand(video_id: str, request: PromptRequest):
    """API endpoint to generate a single thumbnail on-demand."""
    visuals_agent = app.state.visuals_agent
    if not visuals_agent:
        return JSONResponse(status_code=500, content={"message": "Visuals agent not initialized."})
    
    try:
        new_thumbnail = await visuals_agent.generate_single_image_from_prompt(video_id, request.prompt)
        if not new_thumbnail:
            raise Exception("Image generation failed.")

        # Atomically add the new thumbnail to the array in Firestore
        video_doc_ref = db.collection("videos").document(video_id)
        await video_doc_ref.update({
            "generated_thumbnails": firestore.ArrayUnion([new_thumbnail])
        })
        
        return JSONResponse(content={"thumbnail": new_thumbnail}, status_code=201)

    except Exception as e:
        print(f"On-demand thumbnail generation failed: {e}")
        return JSONResponse(status_code=500, content={"message": str(e)})

@app.post("/api/video/{video_id}/generate-prompts")
async def generate_prompts_on_demand(video_id: str):
    """API endpoint to generate a new set of image prompts on-demand."""
    visuals_agent = app.state.visuals_agent
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

class ClipRequest(BaseModel):
    start_time: float
    end_time: float
    short_index: int

@app.post("/api/video/{video_id}/create-clip")
async def create_clip_endpoint(video_id: str, request: ClipRequest):
    """
    Creates, crops, and uploads a short video clip from the original video.
    Caches the downloaded source video in memory to avoid redundant downloads.
    """
    try:
        input_path = video_cache.get(video_id)

        if not input_path:
            video_doc_ref = db.collection("videos").document(video_id)
            doc = await video_doc_ref.get()
            if not doc.exists:
                return JSONResponse(status_code=404, content={"message": "Video not found"})
            
            video_data = doc.to_dict()
            video_url = video_data.get("video_url")

            if not video_url:
                return JSONResponse(status_code=404, content={"message": "Video URL not found in document."})

            tmpdir = tempfile.mkdtemp(prefix="channel_video_cache_")
            print(f"Downloading video: {video_url} to cache directory {tmpdir}")
            ydl_opts = {
                # Request a standard format that is guaranteed to have both video and audio.
                'format': 'best[ext=mp4][vcodec^=avc1][acodec^=mp4a]/best[ext=mp4]/best',
                'outtmpl': os.path.join(tmpdir, f'{video_id}.%(ext)s'),
                'quiet': True,
            }
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                await asyncio.to_thread(ydl.download, [video_url])
            
            input_path = os.path.join(tmpdir, f'{video_id}.mp4')
            video_cache[video_id] = input_path
        else:
            print(f"Using cached video for {video_id} from path: {input_path}")

        # Create a unique output path for this specific clip
        output_dir = os.path.dirname(input_path)
        output_filename = f"clip_{video_id}_{uuid.uuid4()}.mp4"
        output_path = os.path.join(output_dir, output_filename)
        
        await asyncio.to_thread(
            create_vertical_clip,
            input_path=input_path,
            output_path=output_path,
            start_time=request.start_time,
            end_time=request.end_time
        )

        # 3. Upload to GCS
        gcs_bucket_name = os.getenv("GCS_BUCKET_NAME")
        storage_client = storage.Client()
        bucket = storage_client.bucket(gcs_bucket_name)
        blob_path = f"shorts/{output_filename}"
        blob = bucket.blob(blob_path)
        
        await asyncio.to_thread(blob.upload_from_filename, output_path)
        await asyncio.to_thread(blob.make_public)

        print(f"Uploaded clip to: {blob.public_url}")

        # Update the Firestore document with the new clip URL
        doc = await db.collection("videos").document(video_id).get()
        if doc.exists:
            video_data = doc.to_dict()
            if 'structured_data' in video_data and 'shorts_candidates' in video_data['structured_data']:
                if request.short_index < len(video_data['structured_data']['shorts_candidates']):
                    video_data['structured_data']['shorts_candidates'][request.short_index]['generated_clip_url'] = blob.public_url
                    await db.collection("videos").document(video_id).set(video_data)
                    print(f"Saved clip URL to Firestore for short index {request.short_index}")

        # Clean up the specific clip file, but not the source video
        os.remove(output_path)

        return JSONResponse(status_code=200, content={"clip_url": blob.public_url})

    except Exception as e:
        print(f"Error creating clip for {video_id}: {e}")
        return JSONResponse(status_code=500, content={"message": "Internal server error"})

class DeleteClipRequest(BaseModel):
    short_index: int
    clip_url: str

@app.post("/api/video/{video_id}/delete-clip")
async def delete_clip_endpoint(video_id: str, request: DeleteClipRequest):
    """
    Deletes a generated clip from GCS and its reference in Firestore.
    """
    try:
        # 1. Delete from GCS
        gcs_bucket_name = os.getenv("GCS_BUCKET_NAME")
        if gcs_bucket_name and request.clip_url:
            storage_client = storage.Client()
            bucket = storage_client.bucket(gcs_bucket_name)
            # Assumes URL is in format https://storage.googleapis.com/<bucket>/<path>
            blob_path = request.clip_url.replace(f"https://storage.googleapis.com/{gcs_bucket_name}/", "")
            blob = bucket.blob(blob_path)
            if await asyncio.to_thread(blob.exists):
                await asyncio.to_thread(blob.delete)
                print(f"Deleted GCS file: {blob_path}")

        # 2. Delete from Firestore
        video_doc_ref = db.collection("videos").document(video_id)
        doc = await video_doc_ref.get()
        if doc.exists:
            video_data = doc.to_dict()
            if 'structured_data' in video_data and 'shorts_candidates' in video_data['structured_data']:
                if request.short_index < len(video_data['structured_data']['shorts_candidates']):
                    # Use pop to remove the key, fallback to None if it doesn't exist
                    video_data['structured_data']['shorts_candidates'][request.short_index].pop('generated_clip_url', None)
                    await video_doc_ref.set(video_data)
                    print(f"Removed clip URL from Firestore for short index {request.short_index}")

        return JSONResponse(status_code=200, content={"message": "Clip deleted successfully"})

    except Exception as e:
        print(f"Error deleting clip for {video_id}: {e}")
        return JSONResponse(status_code=500, content={"message": "Internal server error"})

@app.post("/api/cleanup-cache")
async def cleanup_cache():
    """
    Manually triggers the cleanup of the video cache.
    """
    global video_cache
    cleaned_count = 0
    errors = []
    
    # Create a copy of the keys to avoid issues with modifying the dict while iterating
    cache_items = list(video_cache.items())

    for video_id, path in cache_items:
        try:
            dir_path = os.path.dirname(path)
            if os.path.isdir(dir_path):
                shutil.rmtree(dir_path)
                # Remove from the active cache
                del video_cache[video_id]
                cleaned_count += 1
                print(f"   Manually removed cache directory: {dir_path}")
        except Exception as e:
            error_message = f"Error removing cache for {video_id}: {e}"
            print(error_message)
            errors.append(error_message)

    if errors:
        return JSONResponse(status_code=500, content={"message": f"Cleanup completed with {len(errors)} errors.", "errors": errors})
    
    if cleaned_count == 0:
        return JSONResponse(content={"message": "Video cache is already empty. No files to clean up."})

    return JSONResponse(content={"message": f"Successfully cleaned up {cleaned_count} cached video(s)."})

@app.post("/api/ingest")
async def ingest_video(request: IngestRequest):
    """
    API endpoint to manually trigger ingestion. Uses the shared IngestionAgent.
    """
    try:
        video_id = get_video_id(request.url)
        if not video_id:
            return JSONResponse(status_code=400, content={"message": "Invalid YouTube URL"})

        video_doc_ref = db.collection("videos").document(video_id)
        doc = await video_doc_ref.get()

        if doc.exists:
            # Video exists and we are NOT forcing a reprocess
            print(f"Video {video_id} already processed. Returning cached data.")
            
            # Manually convert Firestore timestamp to a serializable format
            data = doc.to_dict()
            for key, value in data.items():
                if isinstance(value, datetime):
                    data[key] = value.isoformat()

            # Add the current status to the response
            response_data = {
                "status": "exists",
                "current_stage": data.get("status", "unknown"),
                "data": data
            }
            return JSONResponse(status_code=200, content=response_data)

        # Proceed with ingestion for a new video
        ingestion_agent = app.state.ingestion_agent
        if not ingestion_agent:
            return JSONResponse(status_code=500, content={"message": "IngestionAgent is not available."})

        video_title = await ingestion_agent.get_video_title(video_id)
        
        if not video_title:
             return JSONResponse(status_code=400, content={"message": "Could not retrieve video title."})

        event = NewVideoDetected(
            video_id=video_id,
            video_url=request.url,
            video_title=video_title
        )
        await event_bus.publish(event)

        return JSONResponse(status_code=202, content={"message": "Video ingestion started.", "video_id": video_id})

    except Exception as e:
        import traceback
        print(f"Error in /ingest: {e}\n{traceback.format_exc()}")
        return JSONResponse(status_code=500, content={"message": "An internal error occurred."}) 