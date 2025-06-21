from typing import List, Optional
from google.cloud import firestore
from google.genai.types import Part

from .base_artifact_service import BaseArtifactService

class FirestoreArtifactService(BaseArtifactService):
    """
    An artifact service that stores artifact data in Google Cloud Firestore.
    """

    def __init__(self, db: firestore.AsyncClient = None):
        if db is None:
            self.db = firestore.AsyncClient()
        else:
            self.db = db

    def _get_collection(self, app_name: str, user_id: str, session_id: str) -> firestore.AsyncCollectionReference:
        return self.db.collection("users").document(user_id).collection(app_name).document(session_id).collection("artifacts")

    async def save_artifact(
        self,
        *,
        app_name: str,
        user_id: str,
        session_id: str,
        filename: str,
        artifact: Part,
    ) -> int:
        collection = self._get_collection(app_name, user_id, session_id)
        # For simplicity, we use the filename as the document ID. 
        # A real implementation might want a more robust versioning system.
        doc_ref = collection.document(filename)
        await doc_ref.set({
            "filename": filename,
            "blob": artifact.inline_data.blob,
            "mime_type": artifact.inline_data.mime_type,
            "timestamp": firestore.SERVER_TIMESTAMP
        })
        return 1 # Return a dummy version number

    async def load_artifact(
        self,
        *,
        app_name: str,
        user_id: str,
        session_id: str,
        filename: str,
        version: Optional[int] = None,
    ) -> Part:
        collection = self._get_collection(app_name, user_id, session_id)
        doc_ref = collection.document(filename)
        doc = await doc_ref.get()
        if not doc.exists:
            raise FileNotFoundError(f"Artifact '{filename}' not found.")
        
        data = doc.to_dict()
        return Part.from_blob(blob=data['blob'], mime_type=data['mime_type']) 