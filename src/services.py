from .sessions.firestore_session_service import FirestoreSessionService
from .artifacts.firestore_artifact_service import FirestoreArtifactService

# Initialize global services
# These are instantiated here to be used as singletons throughout the application.
session_service = FirestoreSessionService()
artifact_service = FirestoreArtifactService() 