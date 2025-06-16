terraform {
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = ">= 5.45.0"
    }
    random = {
      source  = "hashicorp/random"
      version = ">= 3.0.0"
    }
  }
}


variable "target_channel_id" {
  description = "The YouTube channel ID to monitor."
  type        = string
}

variable "youtube_api_key" {
  description = "The YouTube API key. This will be stored in Secret Manager."
  type        = string
  sensitive   = true
}

variable "gemini_api_key" {
  description = "The Gemini API key. This will be stored in Secret Manager."
  type        = string
  sensitive   = true
}

provider "google" {
  project = var.project_id
  region  = var.region
}

resource "google_project_service" "secretmanager" {
  service = "secretmanager.googleapis.com"
}

resource "google_service_account" "api_service_account" {
  account_id   = "channelflow-api-sa"
  display_name = "ChannelFlow API Service Account"
}

# --- Secrets ---

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
  secret_data = var.youtube_api_key
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
  secret_data = var.gemini_api_key
}

resource "google_secret_manager_secret_iam_member" "gemini_api_key_access" {
  secret_id = google_secret_manager_secret.gemini_api_key_secret.id
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:${google_service_account.api_service_account.email}"
}

resource "random_string" "bucket_suffix" {
  length  = 8
  special = false
  upper   = false
}

resource "google_storage_bucket" "public_bucket" {
  name          = "channel-flow-${random_string.bucket_suffix.result}"
  location      = var.region
  force_destroy = true

  uniform_bucket_level_access = true
}

resource "google_storage_bucket_iam_member" "public_access" {
  bucket = google_storage_bucket.public_bucket.name
  role   = "roles/storage.objectViewer"
  member = "allUsers"
}

resource "google_cloud_run_v2_service" "api_service" {
  name     = "channelflow-api-service"
  location = var.region

  template {
    service_account = google_service_account.api_service_account.email

    volumes {
      name = "youtube-api-key-volume"
      secret {
        secret  = google_secret_manager_secret.youtube_api_key_secret.secret_id
        items {
          path    = "YOUTUBE_API_KEY"
          version = "latest"
        }
      }
    }
    volumes {
      name = "target-channel-id-volume"
      secret {
        secret  = google_secret_manager_secret.target_channel_id_secret.secret_id
        items {
          path    = "TARGET_CHANNEL_ID"
          version = "latest"
        }
      }
    }
    volumes {
      name = "gemini-api-key-volume"
      secret {
        secret  = google_secret_manager_secret.gemini_api_key_secret.secret_id
        items {
          path    = "GEMINI_API_KEY"
          version = "latest"
        }
      }
    }

    containers {
      image = "us-central1-docker.pkg.dev/${var.project_id}/channelflow-test-deploy-api-repo/channelflow:latest"

      volume_mounts {
        name       = "youtube-api-key-volume"
        mount_path = "/etc/secrets/youtube"
      }
      volume_mounts {
        name       = "target-channel-id-volume"
        mount_path = "/etc/secrets/channel"
      }
      volume_mounts {
        name       = "gemini-api-key-volume"
        mount_path = "/etc/secrets/gemini"
      }

      ports {
        container_port = 8080
      }
    }
  }

  depends_on = [
    google_secret_manager_secret_iam_member.youtube_api_key_access,
    google_secret_manager_secret_iam_member.target_channel_id_access,
    google_secret_manager_secret_iam_member.gemini_api_key_access,
  ]
}

resource "google_cloud_run_service_iam_member" "api_public_access" {
  location = google_cloud_run_v2_service.api_service.location
  service     = google_cloud_run_v2_service.api_service.name
  role     = "roles/run.invoker"
  member   = "allUsers"
}

output "cloud_run_service_url" {
  description = "The URL of the deployed Cloud Run service."
  value       = google_cloud_run_v2_service.api_service.uri
} 