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
from enum import Enum
from typing import Any, Dict, Optional
from pydantic import BaseModel, ConfigDict, Field


class BaseModelWithConfig(BaseModel):
  """Base model with common configuration."""

  model_config = ConfigDict(
      extra='allow',
      arbitrary_types_allowed=True,
  )


class HttpCredentials(BaseModelWithConfig):
  """Represents the secret token value for HTTP authentication."""

  username: Optional[str] = None
  password: Optional[str] = None
  token: Optional[str] = None

  @classmethod
  def model_validate(cls, data: Dict[str, Any]) -> "HttpCredentials":
    return cls(
        username=data.get("username"),
        password=data.get("password"),
        token=data.get("token"),
    )


class HttpAuth(BaseModelWithConfig):
  """The credentials and metadata for HTTP authentication."""
  scheme: str
  credentials: HttpCredentials


class AuthCredentialTypes(str, Enum):
  """Represents the type of authentication credential."""
  API_KEY = "apiKey"
  HTTP = "http"


class AuthCredential(BaseModelWithConfig):
  """Data class representing an authentication credential."""
  auth_type: AuthCredentialTypes
  api_key: Optional[str] = None
  http: Optional[HttpAuth] = None 