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

# The `random` provider is used to generate a secure secret key.
provider "random" {}

resource "random_password" "secret_key" {
  length  = 32
  special = false # Fernet keys are URL-safe base64, so no special chars needed
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
  secret_data = random_password.secret_key.result
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

resource "google_secret_manager_secret_iam_member" "youtube_api_key_access" {
  secret_id = google_secret_manager_secret.youtube_api_key_secret.id
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:${google_service_account.api_service_account.email}"
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

resource "google_secret_manager_secret_iam_member" "target_channel_id_access" {
  secret_id = google_secret_manager_secret.target_channel_id_secret.id
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:${google_service_account.api_service_account.email}"
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

resource "google_secret_manager_secret_iam_member" "gemini_api_key_access" {
  secret_id = google_secret_manager_secret.gemini_api_key_secret.id
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:${google_service_account.api_service_account.email}"
} 
