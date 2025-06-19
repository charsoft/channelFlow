import os
import requests
from google import genai
from google.genai.types import Part

# Step 1: Configure Gemini client
client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

# Step 2: Streaming download
video_url = "https://storage.googleapis.com/channel-flow-bfqk9g4k/youtube_cache/zTniZ9-MRuU.mp4"
resp = requests.get(video_url, stream=True)
resp.raise_for_status()
video_data = b''.join(resp.iter_content(chunk_size=8192))

# Step 3: Create Part from bytes
video_part = Part.from_bytes(
    data=video_data,
    mime_type="video/mp4"
)

# Step 4: Transcribe
response = client.models.generate_content(
    model="gemini-1.5-pro",
    contents=[
        video_part,
        "Transcribe this video fully, including pauses and speaker shifts."
    ]
)

print(response.text)
