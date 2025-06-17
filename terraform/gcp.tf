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

# Create an Artifact Registry repository for Docker images
resource "google_artifact_registry_repository" "api_repo" {
  project       = var.project_id
  location      = var.region
  repository_id = "${var.project_id}-api-repo"
  description   = "Docker repository for the API backend"
  format        = "DOCKER"

  depends_on = [google_project_service.artifactregistry]
} 