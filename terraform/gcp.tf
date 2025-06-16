# Enable necessary APIs for the project
resource "google_project_service" "cloudrun" {
  project            = var.project_id
  service            = "run.googleapis.com"
  disable_on_destroy = false
}

resource "google_project_service" "artifactregistry" {
  project            = var.project_id
  service            = "artifactregistry.googleapis.com"
  disable_on_destroy = false
}

resource "google_project_service" "cloudbuild" {
  project            = var.project_id
  service            = "cloudbuild.googleapis.com"
  disable_on_destroy = false
}

resource "google_project_service" "firebase" {
  project            = var.project_id
  service            = "firebase.googleapis.com"
  disable_on_destroy = false
}

resource "google_project_service" "firebasehosting" {
  project            = var.project_id
  service            = "firebasehosting.googleapis.com"
  disable_on_destroy = false
  depends_on         = [google_project_service.firebase]
}

# Create a Firebase Web App
resource "google_firebase_web_app" "default" {
  provider     = google-beta
  project      = var.project_id
  display_name = "ChannelFlow Web"
  depends_on   = [google_project_service.firebase]
}

# Get the config for the created Firebase Web App
data "google_firebase_web_app_config" "default" {
  provider   = google-beta
  project    = var.project_id
  web_app_id = google_firebase_web_app.default.app_id
}

# Create an Artifact Registry repository for Docker images
resource "google_artifact_registry_repository" "api_repo" {
  project       = var.project_id
  location      = var.region
  repository_id = "${var.project_id}-api-repo"
  description   = "Docker repository for the API backend"
  format        = "DOCKER"

  depends_on = [google_project_service.artifactregistry]
} 