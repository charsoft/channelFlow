import os
from google.cloud import firestore
from dotenv import load_dotenv

# Load environment variables from .env file, including GOOGLE_CLOUD_PROJECT
load_dotenv()

# Get the project ID from the environment variable
project_id = os.getenv("GOOGLE_CLOUD_PROJECT")

# Initialize the async Firestore client, explicitly setting the project
# If project_id is None, the library will try to find it in the environment,
# but being explicit is better for clarity.
db = firestore.AsyncClient(project=project_id)

if not project_id:
    print("⚠️ WARNING: GOOGLE_CLOUD_PROJECT environment variable not set.")
    print("   The application may not connect to the correct Firestore database.")

# Initialize the async Firestore client
# This will be reused by all agents and services. 