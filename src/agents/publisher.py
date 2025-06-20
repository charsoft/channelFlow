import asyncio
from google.cloud import firestore
from ..event_bus import event_bus
from ..events import VisualsReady
from ..database import db

class PublisherAgent:
    """
    🚚 PublisherAgent
    Purpose: To flag content as ready for review once all assets are generated.
    """
    def __init__(self, bucket_name):
        self.bucket_name = bucket_name
        event_bus.subscribe(VisualsReady, self.handle_visuals_ready)

    async def _update_status(self, doc_ref, status: str, message: str, extra_data: dict = None):
        """Helper to update status and message."""
        update = {
            "status": status,
            "status_message": message
        }
        if extra_data:
            update.update(extra_data)
        await doc_ref.update(update)

    async def handle_visuals_ready(self, event: VisualsReady):
        """
        This is the final stage. For now, it just marks the video as "published".
        In a real-world scenario, this would interact with YouTube's API to
        upload shorts, update descriptions, etc.
        """
        print(f"🚀 PublisherAgent: Received visuals for: {event.video_title}")
        video_doc_ref = db.collection("videos").document(event.video_id)

        try:
            await self._update_status(video_doc_ref, "publishing", "All assets are ready. Preparing to publish.")

            # In a real implementation, this is where you would:
            # 1. Download the generated shorts clips from GCS.
            # 2. Use the marketing copy for titles/descriptions.
            # 3. Authenticate with the user's YouTube account.
            # 4. Upload the video using the YouTube Data API.
            # For this example, we'll just simulate the final step.
            
            print("   (Simulating final publishing step...)")
            await asyncio.sleep(2) # Simulate network activity

            await self._update_status(video_doc_ref, "published", "Content has been successfully published!")
            print(f"   ✅ Successfully 'published' video: {event.video_title}")

        except Exception as e:
            print(f"❌ PublisherAgent Error: {e}")
            await self._update_status(video_doc_ref, "publishing_failed", "Failed to publish content.", {"error": str(e)}) 