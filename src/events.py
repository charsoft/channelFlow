from dataclasses import dataclass, field
from typing import Dict
from .event_base import Event

@dataclass
class NewVideoDetected(Event):
    """Fired when a new video is found."""
    video_id: str
    video_url: str
    video_title: str

@dataclass
class TranscriptReady(Event):
    """Fired when the transcript is ready."""
    video_id: str
    video_title: str
    transcript_gcs_uri: str

@dataclass
class ContentAnalysisComplete(Event):
    """Fired when the content analysis is complete."""
    video_id: str
    video_title: str
    structured_data: dict

@dataclass
class CopyReady(Event):
    """Fired when the marketing copy is ready."""
    video_id: str
    video_title: str

@dataclass
class VisualsReady(Event):
    """Fired when the visuals are ready."""
    video_id: str
    video_title: str
    # The PublisherAgent will fetch the URIs from Firestore.
    # No need to pass them in the event. 