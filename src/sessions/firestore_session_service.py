import uuid
from typing import Any, Optional
from google.cloud import firestore

from .base_session_service import BaseSessionService
from .session import Session
from ..event_bus import event_bus

class FirestoreSessionService(BaseSessionService):
    """
    A session service that stores session data in Google Cloud Firestore.
    """

    def __init__(self, db: firestore.AsyncClient = None):
        if db is None:
            # This will use the default credentials and project from the environment
            self.db = firestore.AsyncClient()
        else:
            self.db = db

    def _get_collection(self, app_name: str, user_id: str) -> firestore.AsyncCollectionReference:
        # Sessions are stored under a user's document
        return self.db.collection("users").document(user_id).collection(app_name)

    async def create_session(
        self,
        *,
        app_name: str,
        user_id: str,
        state: Optional[dict[str, Any]] = None,
        session_id: Optional[str] = None,
    ) -> Session:
        if not session_id:
            session_id = str(uuid.uuid4())
        
        session = Session(
            id=session_id,
            app_name=app_name,
            user_id=user_id,
            state=state or {},
        )
        
        collection = self._get_collection(app_name, user_id)
        await collection.document(session_id).set(session.model_dump(exclude_none=True))
        return session

    async def get_session(
        self,
        *,
        app_name: str,
        user_id: str,
        session_id: str,
    ) -> Optional[Session]:
        collection = self._get_collection(app_name, user_id)
        doc = await collection.document(session_id).get()
        if not doc.exists:
            return None
        return Session(**doc.to_dict())

    async def update_session(self, session: Session) -> None:
        collection = self._get_collection(session.app_name, session.user_id)
        await collection.document(session.id).update(session.model_dump(exclude={"id", "app_name", "user_id"}, exclude_none=True)) 