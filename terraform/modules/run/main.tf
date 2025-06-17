resource "google_service_account" "run" {
  project      = var.project_id
  account_id   = "${var.run_service_name}-sa"
  display_name = "Service Account for ${var.run_service_name}."
}

resource "google_cloud_run_service" "default" {
  name     = var.run_service_name
  project  = var.project_id
  location = var.region

  template {
    metadata {
      labels = var.labels
    }
    spec {
      service_account_name = google_service_account.run.email
      containers {
        image = "us-docker.pkg.dev/cloudrun/container/hello" # Placeholder image
      }
    }
  }

  traffic {
    percent         = 100
    latest_revision = true
  }
} 