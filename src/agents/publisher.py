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
    def __init__(self):
        event_bus.subscribe(VisualsReady, self.handle_visuals_ready)

    async def handle_visuals_ready(self, event: VisualsReady):
        """
        This handler is triggered when visuals are ready.
        At this point, we know the copy is also ready due to the
        sequential nature of the event chain.
        """
        print(f"🚚 PublisherAgent: Received visuals ready for: {event.video_title}")
        video_doc_ref = db.collection("videos").document(event.video_id)

        try:
            # Set status to 'publishing' immediately.
            await video_doc_ref.update({"status": "publishing"})
            
            doc = await video_doc_ref.get()
            if not doc.exists:
                print(f"   Error: Document {event.video_id} not found.")
                return

            video_data = doc.to_dict()

            # Prevent re-processing
            if video_data.get("status") == "ready_for_review":
                print(f"   Content for '{event.video_title}' is already marked for review. Skipping.")
                return

            print(f"   All assets generated for {event.video_title}. Marking as 'ready_for_review'.")

            await video_doc_ref.update({
                "status": "ready_for_review",
                "ready_for_review_at": firestore.SERVER_TIMESTAMP,
            })
            
            print(f"   Successfully marked '{event.video_title}' as ready for review.")

        except Exception as e:
            print(f"❌ PublisherAgent Error: {e}")
            await video_doc_ref.update({"status": "publishing_failed", "error": str(e)}) 