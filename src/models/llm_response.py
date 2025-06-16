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

from typing import Optional

from google.genai import types
from pydantic import alias_generators
from pydantic import BaseModel
from pydantic import ConfigDict


class LlmResponse(BaseModel):
  """LLM response class that provides the first candidate response from the
  model if available. Otherwise, returns error code and message.
  """

  model_config = ConfigDict(
      extra='forbid',
      alias_generator=alias_generators.to_camel,
      populate_by_name=True,
  )
  """The pydantic model config."""

  content: Optional[types.Content] = None
  """The content of the response."""

  grounding_metadata: Optional[types.GroundingMetadata] = None
  """The grounding metadata of the response."""

  error_code: Optional[str] = None
  """Error code if the response is an error. Code varies by model."""

  error_message: Optional[str] = None
  """Error message if the response is an error.""" 