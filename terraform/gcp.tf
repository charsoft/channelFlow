# Enable necessary APIs for the project

# Create an Artifact Registry repository for Docker images
resource "google_artifact_registry_repository" "api_repo" {
  project       = var.project_id
  location      = var.region
  repository_id = "${var.project_id}-api-repo"
  description   = "Docker repository for the API backend"
  format        = "DOCKER"
} 