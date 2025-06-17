terraform {
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = ">= 5.45.0"
    }
    google-beta = {
      source  = "hashicorp/google-beta"
      version = ">= 5.45.0"
    }
    random = {
      source  = "hashicorp/random"
      version = ">= 3.0.0"
    }
  }

  backend "gcs" {
    bucket = "channel-flow-2-tf-storage-0617"
    prefix = "terraform/state"
  }
}

provider "google" {
  project               = var.project_id
  region                = var.region
  user_project_override = true
  billing_project       = var.project_id
}

provider "google-beta" {
  project               = var.project_id
  region                = var.region
  user_project_override = true
  billing_project       = var.project_id
}


resource "google_project_service" "iam" {
  project = var.project_id
  service = "iam.googleapis.com"
}

resource "google_project_service" "secretmanager" {
  project = var.project_id
  service = "secretmanager.googleapis.com"
}

resource "google_project_service" "apikeys" {
  service = "apikeys.googleapis.com"
}

resource "google_project_service" "youtube" {
  service = "youtube.googleapis.com"
}

resource "google_project_service" "generativelanguage" {
  project = var.project_id
  service = "generativelanguage.googleapis.com"
}

resource "google_service_account" "api_service_account" {
  account_id   = "channelflow-api-sa"
  display_name = "ChannelFlow API Service Account"
}



# --- API Keys ---

resource "google_apikeys_key" "youtube_api_key" {
  name         = "channel-flow-youtube-key"
  display_name = "API key for YouTube Data API"

  restrictions {
    api_targets {
      service = "youtube.googleapis.com"
    }
  }

  depends_on = [google_project_service.apikeys, google_project_service.youtube]
}

resource "google_apikeys_key" "gemini_api_key" {
  name         = "channel-flow-gemini-key"
  display_name = "API key for Generative Language API"

  restrictions {
    api_targets {
      service = "generativelanguage.googleapis.com"
    }
  }

  depends_on = [google_project_service.apikeys, google_project_service.generativelanguage]
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
  ingress  = "INGRESS_TRAFFIC_ALL"

  template {
    annotations = {
      "tf-secret-version-youtube" = google_secret_manager_secret_version.youtube_api_key_secret_version.version
      "tf-secret-version-channel" = google_secret_manager_secret_version.target_channel_id_secret_version.version
      "tf-secret-version-gemini"  = google_secret_manager_secret_version.gemini_api_key_secret_version.version
    }

    service_account = google_service_account.api_service_account.email

    volumes {
      name = "youtube-api-key-volume"
      secret {
        secret = google_secret_manager_secret.youtube_api_key_secret.secret_id
        items {
          path    = "YOUTUBE_API_KEY"
          version = "latest"
        }
      }
    }
    volumes {
      name = "target-channel-id-volume"
      secret {
        secret = google_secret_manager_secret.target_channel_id_secret.secret_id
        items {
          path    = "TARGET_CHANNEL_ID"
          version = "latest"
        }
      }
    }
    volumes {
      name = "gemini-api-key-volume"
      secret {
        secret = google_secret_manager_secret.gemini_api_key_secret.secret_id
        items {
          path    = "GEMINI_API_KEY"
          version = "latest"
        }
      }
    }

    containers {
      image = "us-central1-docker.pkg.dev/${var.project_id}/channelflow-api-repo/channelflow:latest"

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
      env {
        name  = "GOOGLE_CLOUD_PROJECT"
        value = var.project_id
      }
      env {
        name  = "GCS_BUCKET_NAME"
        value = google_storage_bucket.public_bucket.name
      }
      env {
        name  = "GCP_REGION"
        value = var.region
      }
      env {
        name  = "GEMINI_MODEL_NAME"
        value = "gemini-1.5-pro-latest"
      }
      env {
        name  = "IMAGEN_MODEL_NAME"
        value = var.imagen_model_name
      }
      env {
        name = "GEMINI_API_KEY"


        value_source {
          secret_key_ref {
            secret  = "gemini-api-key"
            version = "latest"
          }
        }
      }
      env {
        name = "YOUTUBE_API_KEY"


        value_source {
          secret_key_ref {
            secret  = "youtube-api-key"
            version = "latest"
          }
        }
      }
      env {
        name = "TARGET_CHANNEL_ID"


        value_source {
          secret_key_ref {
            secret  = "target-channel-id"
            version = "latest"
          }
        }
      }
      env {
        name = "SECRET_KEY"
        value_source {
          secret_key_ref {
            secret  = google_secret_manager_secret.app_secret_key.secret_id
            version = "latest"
          }
        }
      }
      env {
        name = "GOOGLE_CLIENT_ID"
        value_source {
          secret_key_ref {
            secret  = google_secret_manager_secret.google_client_id_secret.secret_id
            version = "latest"
          }
        }
      }
      env {
        name = "GOOGLE_CLIENT_SECRET"
        value_source {
          secret_key_ref {
            secret  = google_secret_manager_secret.google_client_secret_secret.secret_id
            version = "latest"
          }
        }
      }
      
      
     
    }
  }

  depends_on = [
    google_secret_manager_secret_iam_member.youtube_api_key_access,
    google_secret_manager_secret_iam_member.target_channel_id_access,
    google_secret_manager_secret_iam_member.gemini_api_key_access,
  ]
}

output "cloud_run_service_url" {
  description = "The URL of the deployed Cloud Run service."
  value       = google_cloud_run_v2_service.api_service.uri
} 