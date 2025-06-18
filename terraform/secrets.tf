# This file manages the secrets required by the application.

# You must manually create the OAuth Client ID and Secret in the
# Google Cloud Console and provide them as variables.
variable "google_client_id" {
  type        = string
  description = "The Google OAuth 2.0 Client ID."
  sensitive   = true
}

variable "google_client_secret" {
  type        = string
  description = "The Google OAuth 2.0 Client Secret."
  sensitive   = true
}

variable "secret_key" {
  type        = string
  description = "A URL-safe, base64-encoded 32-byte key for Fernet encryption."
  sensitive   = true
}

variable "target_channel_id" {
  type        = string
  description = "The YouTube channel ID to monitor."
  sensitive   = true
}

variable "jwt_secret_key" {
  type        = string
  description = "A secret key for encoding and decoding JWTs."
  sensitive   = true
}

resource "google_secret_manager_secret" "app_secret_key" {
  secret_id = "channelflow-secret-key"
  project   = var.project_id

  replication {
    auto {}
  }
}

resource "google_secret_manager_secret_version" "app_secret_key_version" {
  secret      = google_secret_manager_secret.app_secret_key.id
  secret_data = var.secret_key
}

resource "google_secret_manager_secret" "google_client_id_secret" {
  secret_id = "channelflow-google-client-id"
  project   = var.project_id

  replication {
    auto {}
  }
}

resource "google_secret_manager_secret_version" "google_client_id_secret_version" {
  secret      = google_secret_manager_secret.google_client_id_secret.id
  secret_data = var.google_client_id
}

resource "google_secret_manager_secret" "google_client_secret_secret" {
  secret_id = "channelflow-google-client-secret"
  project   = var.project_id

  replication {
    auto {}
  }
}

resource "google_secret_manager_secret_version" "google_client_secret_secret_version" {
  secret      = google_secret_manager_secret.google_client_secret_secret.id
  secret_data = var.google_client_secret
}

resource "google_secret_manager_secret" "jwt_secret" {
  secret_id = "jwt-secret-key"
  project   = var.project_id

  replication {
    auto {}
  }
}

resource "google_secret_manager_secret_version" "jwt_secret_version" {
  secret      = google_secret_manager_secret.jwt_secret.id
  secret_data = var.jwt_secret_key
}

# --- Secrets from main.tf ---

# YouTube API Key Secret
resource "google_secret_manager_secret" "youtube_api_key_secret" {
  secret_id = "youtube-api-key"
  replication {
    auto {}
  }
  depends_on = [google_project_service.secretmanager]
}

resource "google_secret_manager_secret_version" "youtube_api_key_secret_version" {
  secret      = google_secret_manager_secret.youtube_api_key_secret.id
  secret_data = google_apikeys_key.youtube_api_key.key_string
}

# Target Channel ID Secret
resource "google_secret_manager_secret" "target_channel_id_secret" {
  secret_id = "target-channel-id"
  replication {
    auto {}
  }
  depends_on = [google_project_service.secretmanager]
}

resource "google_secret_manager_secret_version" "target_channel_id_secret_version" {
  secret      = google_secret_manager_secret.target_channel_id_secret.id
  secret_data = var.target_channel_id
}

# Gemini API Key Secret
resource "google_secret_manager_secret" "gemini_api_key_secret" {
  secret_id = "gemini-api-key"
  replication {
    auto {}
  }
  depends_on = [google_project_service.secretmanager]
}

resource "google_secret_manager_secret_version" "gemini_api_key_secret_version" {
  secret      = google_secret_manager_secret.gemini_api_key_secret.id
  secret_data = google_apikeys_key.gemini_api_key.key_string
}
