# Copyright 2025 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
from __future__ import annotations

from datetime import datetime
import random
import string
from typing import Optional

from google.genai import types
from pydantic import alias_generators
from pydantic import ConfigDict
from pydantic import Field

from ..models.llm_response import LlmResponse
from .event_actions import EventActions


class Event(LlmResponse):
  """Represents an event in a conversation between agents and users."""

  model_config = ConfigDict(
      extra='forbid',
      ser_json_bytes='base64',
      val_json_bytes='base64',
      alias_generator=alias_generators.to_camel,
      populate_by_name=True,
  )
  """The pydantic model config."""
  invocation_id: str = ''
  """The invocation ID of the event."""
  author: str
  """'user' or the name of the agent, indicating who appended the event to the
  session."""
  actions: EventActions = Field(default_factory=EventActions)
  """The actions taken by the agent."""

  branch: Optional[str] = None
  """The branch of the event."""

  id: str = ''
  """The unique identifier of the event."""
  timestamp: float = Field(default_factory=lambda: datetime.now().timestamp())
  """The timestamp of the event."""

  def model_post_init(self, __context):
    """Post initialization logic for the event."""
    # Generates a random ID for the event.
    if not self.id:
      self.id = Event.new_id()

  @staticmethod
  def new_id():
    characters = string.ascii_letters + string.digits
    return ''.join(random.choice(characters) for _ in range(8)) 