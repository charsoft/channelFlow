# src/config.py
import os
from dotenv import load_dotenv

load_dotenv()

GCP_PROJECT_ID = os.getenv("GOOGLE_CLOUD_PROJECT")
GCS_BUCKET_NAME = os.getenv("GCS_BUCKET_NAME")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GCP_REGION = os.getenv("GCP_REGION")
PROXY_URL = os.getenv("PROXY_URL")
FFMPEG_PATH = os.getenv("FFMPEG_PATH")
IMAGEN_MODEL_NAME = os.getenv("IMAGEN_MODEL_NAME", "")
GEMINI_MODEL_NAME = os.getenv("GEMINI_MODEL_NAME", "")  
YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY")
TARGET_CHANNEL_ID = os.getenv("TARGET_CHANNEL_ID")
ENABLE_AUTO_INGESTION = os.getenv("ENABLE_AUTO_INGESTION", "false").lower() == "true"   