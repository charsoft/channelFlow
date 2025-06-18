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

resource "google_project_service" "firestore" {
  project = var.project_id
  service = "firestore.googleapis.com"
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