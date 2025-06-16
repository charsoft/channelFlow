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
import uuid
from typing import Optional, TYPE_CHECKING
from pydantic import BaseModel, ConfigDict
if TYPE_CHECKING:
  from google.genai import types
  from .base_agent import BaseAgent
  from ..artifacts.base_artifact_service import BaseArtifactService
  from ..sessions.base_session_service import BaseSessionService
  from ..sessions.session import Session


class InvocationContext(BaseModel):
  """An invocation context represents the data of a single invocation of an agent."""

  model_config = ConfigDict(
      arbitrary_types_allowed=True,
      extra="forbid",
  )
  """The pydantic model config."""

  artifact_service: Optional[BaseArtifactService] = None
  session_service: BaseSessionService

  invocation_id: str
  """The id of this invocation context. Readonly."""
  branch: Optional[str] = None
  """The branch of the invocation context."""
  agent: BaseAgent
  """The current agent of this invocation context. Readonly."""
  user_content: Optional[types.Content] = None
  """The user content that started this invocation. Readonly."""
  session: Session
  """The current session of this invocation context. Readonly."""

  end_invocation: bool = False
  """Whether to end this invocation."""

  @property
  def app_name(self) -> str:
    return self.session.app_name

  @property
  def user_id(self) -> str:
    return self.session.user_id


def new_invocation_context_id() -> str:
  return "e-" + str(uuid.uuid4()) 