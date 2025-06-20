import asyncio
import os
import pickle
from urllib.parse import urlparse, parse_qs
from datetime import datetime
from ..event_bus import event_bus
from ..events import NewVideoDetected
from ..database import db
from googleapiclient.discovery import build
import re
from google.cloud import firestore

def get_video_id(url: str) -> str | None:
    """Extracts the YouTube video ID from a URL."""
    # Examples:
    # - http://youtu.be/SA2iWivDJiE
    # - http://www.youtube.com/watch?v=_oPAwA_Udwc&feature=feedu
    # - http://www.youtube.com/embed/SA2iWivDJiE
    # - http://www.youtube.com/v/SA2iWivDJiE?version=3&amp;hl=en_US
    query = urlparse(url)
    if query.hostname == 'youtu.be':
        return query.path[1:]
    if query.hostname in ('www.youtube.com', 'youtube.com'):
        if query.path == '/watch':
            p = parse_qs(query.query)
            return p.get('v', [None])[0]
        if query.path[:7] == '/embed/':
            return query.path.split('/')[2]
        if query.path[:3] == '/v/':
            return query.path.split('/')[2]
    return None

class IngestionAgent:
    """
    🕵️ IngestionAgent
    Monitors a YouTube channel for new videos and can also process on-demand URLs.
    """

    def __init__(self, api_key: str, channel_id: str = None):
        self.api_key = api_key
        self.channel_id = channel_id
        self.youtube = build('youtube', 'v3', developerKey=self.api_key)
        # This agent should not be a listener. It is called directly.
        # event_bus.subscribe(NewVideoDetected, self.handle_new_video)

    async def process_single_video(self, video_url: str):
        """Processes a single video URL provided on demand."""
        print(f"🕵️ IngestionAgent: Received on-demand request for URL: {video_url}")
        video_id = get_video_id(video_url)

        if not video_id:
            print(f"🕵️ IngestionAgent: ❌ Could not extract video ID from URL: {video_url}")
            return
            
        video_doc_ref = db.collection("videos").document(video_id)
        doc = await video_doc_ref.get()
        if doc.exists:
            print(f"🕵️ IngestionAgent: ⚪️ Video ID '{video_id}' already exists in Firestore. Skipping.")
            return

        try:
            loop = asyncio.get_running_loop()
            request = self.youtube.videos().list(
                part="snippet",
                id=video_id
            )
            response = await loop.run_in_executor(None, request.execute)
            
            if not response.get("items"):
                print(f"🕵️ IngestionAgent: ❌ Video with ID '{video_id}' not found on YouTube.")
                return

            video_title = response["items"][0]["snippet"]["title"]
            print(f"🕵️ IngestionAgent: ✅ Found video: '{video_title}'")

            # Create the initial document in Firestore
            await video_doc_ref.set({
                "video_id": video_id,
                "video_title": video_title,
                "video_url": video_url,
                "status": "ingested",
                "status_message": f"Successfully ingested video: {video_title}",
                "created_at": datetime.utcnow(),
            })

            new_video_event = NewVideoDetected(
                video_id=video_id,
                video_url=video_url,
                video_title=video_title
            )
            await event_bus.publish(new_video_event)
            
        except Exception as e:
            print(f"🕵️ IngestionAgent: ❌ An error occurred while fetching video details: {e}")

    async def check_for_new_videos(self):
        """The main method for the agent to perform its action."""
        print(f"🕵️ IngestionAgent: Checking for new videos on channel {self.channel_id}...")
        
        try:
            loop = asyncio.get_running_loop()
            request = self.youtube.search().list(
                part="snippet",
                channelId=self.channel_id,
                order="date",
                maxResults=10
            )
            response = await loop.run_in_executor(None, request.execute)

            for item in response.get("items", []):
                if item.get("id", {}).get("kind") == "youtube#video":
                    video_id = item["id"]["videoId"]
                    video_title = item["snippet"]["title"]
                    
                    video_doc_ref = db.collection("videos").document(video_id)
                    doc = await video_doc_ref.get()
                    if not doc.exists:
                        print(f"🕵️ IngestionAgent: ✅ New video found: '{video_title}'")
                        print("   (Processing only the single most recent new video for this cycle)")
                        
                        video_url = f"https://www.youtube.com/watch?v={video_id}"
                        
                        # Create the initial document in Firestore
                        await video_doc_ref.set({
                            "video_id": video_id,
                            "video_title": video_title,
                            "video_url": video_url,
                            "status": "ingested",
                            "status_message": f"New video found on channel: {video_title}",
                            "created_at": datetime.utcnow(),
                        })

                        new_video_event = NewVideoDetected(
                            video_id=video_id,
                            video_url=video_url,
                            video_title=video_title
                        )
                        await event_bus.publish(new_video_event)
                        
                        # Stop after processing the first new video to avoid flooding.
                        break
                    else:
                        # Videos are ordered by date, so if we've seen this one, we've seen all subsequent ones.
                        print(f"🕵️ IngestionAgent: ⚪️ Video '{video_title}' already processed. No newer videos to process in this cycle.")
                        break
            
            print("🕵️ IngestionAgent: Check complete.")

        except Exception as e:
            print(f"🕵️ IngestionAgent: ❌ An error occurred: {e}")

    async def start_monitoring(self):
        """This method runs on a schedule to check for new videos."""
        while True:
            await self.check_for_new_videos()
            await asyncio.sleep(900) # Check every 15 minutes 

    async def monitor_new_videos(self, interval_seconds=900):
        """Monitors the channel for new videos, checking against Firestore."""
        if not self.channel_id:
            print("⚠️ IngestionAgent: No YOUTUBE_CHANNEL_ID. Automatic monitoring is disabled.")
            return

        print(f"🕵️ IngestionAgent: Starting to monitor channel {self.channel_id}...")
        while True:
            try:
                print("   Checking for new videos...")
                request = self.youtube.search().list(
                    part="snippet",
                    channelId=self.channel_id,
                    order="date",
                    type="video",
                    maxResults=5 # Check the 5 most recent videos
                )
                response = await asyncio.to_thread(request.execute)
                
                for item in response.get("items", []):
                    video_id = item["id"]["videoId"]
                    video_doc_ref = db.collection("videos").document(video_id)
                    doc = await video_doc_ref.get()

                    if not doc.exists:
                        # Found a new one
                        video_title = item["snippet"]["title"]
                        video_url = f"https://youtu.be/{video_id}"
                        print(f"   ✨ Found new video: {video_title}")
                        event = NewVideoDetected(
                            video_id=video_id,
                            video_title=video_title,
                            video_url=video_url
                        )
                        await event_bus.publish(event)
                        # Process only the single most recent new video per cycle
                        break 
                
            except Exception as e:
                print(f"❌ IngestionAgent Error during monitoring: {e}")
            
            await asyncio.sleep(interval_seconds)

    async def handle_new_video(self, event: NewVideoDetected):
        """Saves the initial video data to Firestore upon detection."""
        print(f"🕵️ IngestionAgent: Handling new video event for: {event.video_title}")
        video_doc_ref = db.collection("videos").document(event.video_id)
        doc = await video_doc_ref.get()
        if not doc.exists:
            # Prepare the data, including the user_id if it exists
            initial_data = {
                "video_id": event.video_id,
                "video_url": event.video_url,
                "video_title": event.video_title,
                "status": "new",
                "status_message": "Received new video request.",
                "received_at": firestore.SERVER_TIMESTAMP,
                "user_id": event.user_id
            }
            # Remove user_id if it's None to keep the document clean
            if initial_data["user_id"] is None:
                del initial_data["user_id"]

            await video_doc_ref.set(initial_data)
            print(f"   Saved initial data for {event.video_id} to Firestore.")
        else:
            print(f"   Document for {event.video_id} already exists. Skipping initial save.")

    async def get_video_title(self, video_id: str) -> str | None:
        """Gets the video title for a given video ID."""
        try:
            request = self.youtube.videos().list(part="snippet", id=video_id)
            response = await asyncio.to_thread(request.execute)
            if response.get("items"):
                return response["items"][0]["snippet"]["title"]
            return None
        except Exception as e:
            print(f"Error fetching video title for {video_id}: {e}")
            return None 