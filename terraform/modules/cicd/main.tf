variable "run_service_location" {
  description = "The location of the Cloud Run service."
  type        = string
}

variable "run_service_account_email" {
  description = "The email of the service account used by the Cloud Run service."
  type        = string
}

variable "time_sleep" {
  description = "The time_sleep resource."
  type        = any
  default     = null
}

locals {
  repository_name        = replace(split("/", replace(var.github_repository_url, "/(.*github.com/)/", ""))[1], ".git", "")
  repository_owner       = split("/", replace(var.github_repository_url, "/(.*github.com/)/", ""))[0]
  artifact_registry_repo = "${var.run_service_location}-docker.pkg.dev/${var.project_id}/${google_artifact_registry_repository.default.name}"
  github_repository_url  = replace(var.github_repository_url, "/(.*github.com)/", "https://github.com")
  new_release_config     = templatefile("${path.module}/cloudbuild/new-release.cloudbuild.yaml.tftpl", {})
  app_build_config       = templatefile("${path.module}/cloudbuild/app-build.cloudbuild.yaml.tftpl", {})
  skaffold_config        = templatefile("${path.module}/cloudbuild/skaffold.yaml.tftpl", { name = var.run_service_name })
  run_config = templatefile("${path.module}/cloudbuild/app-prod.yaml.tftpl",
    { run_service_name    = var.run_service_name
      project_id          = var.project_id
      run_service_account = var.run_service_account_email
    }
  )
}

# Retrieve existing resources
data "google_cloud_run_service" "default" {
  name     = var.run_service_name
  project  = var.project_id
  location = var.region
}

data "google_service_account" "cloud_run" {
  account_id = var.run_service_account_email
}

# Create Artifact Registry and the gcr Pub/Sub topic
resource "google_artifact_registry_repository" "default" {
  project       = var.project_id
  location      = var.region
  repository_id = "channel-flow-repo"
  description   = "Dev journey artifact registry repo."
  format        = "DOCKER"
  labels        = var.labels
  depends_on = [
    var.time_sleep
  ]
}

resource "google_pubsub_topic" "gcr" {
  project = var.project_id
  name    = "gcr"
}

# Cloud Build resources (triggers, service account, and IAM bindings)
resource "google_service_account" "cloud_build" {
  project      = var.project_id
  account_id   = "${substr(var.run_service_name, 0, 22)}-builder"
  display_name = "Service Account for Cloud Build deployment to Cloud Run."
}

resource "google_project_iam_member" "builder_logwriter" {
  project = var.project_id
  role    = "roles/logging.logWriter"
  member  = "serviceAccount:${google_service_account.cloud_build.email}"
}

resource "google_project_iam_member" "builder_deploy_admin" {
  project = var.project_id
  role    = "roles/clouddeploy.admin"
  member  = "serviceAccount:${google_service_account.cloud_build.email}"
}

resource "google_project_iam_member" "builder_builds_builder" {
  project = var.project_id
  role    = "roles/cloudbuild.builds.builder"
  member  = "serviceAccount:${google_service_account.cloud_build.email}"
}

resource "google_project_iam_member" "builder_sa_user" {
  project = var.project_id
  role    = "roles/iam.serviceAccountUser"
  member  = "serviceAccount:${google_service_account.cloud_build.email}"
}

resource "google_project_iam_member" "builder_run_developer" {
  project = var.project_id
  role    = "roles/run.developer"
  member  = "serviceAccount:${google_service_account.cloud_build.email}"
}

resource "google_cloudbuild_trigger" "app_new_build" {
  project         = var.project_id
  location        = var.region
  name            = "channel-flow-app-build"
  description     = "Initiates new build of ${var.run_service_name}. Triggers by changes to app on main branch of source repo."
  service_account = google_service_account.cloud_build.id
  included_files = [
    "src/**",
  ]
  github {
    name  = local.repository_name
    owner = local.repository_owner
    push {
      branch       = "^main$"
      invert_regex = false
    }
  }
  build {
    images = ["${local.artifact_registry_repo}/app:$${SHORT_SHA}"]
    substitutions = {
      _IMAGE = "${local.artifact_registry_repo}/app"
    }
    tags = []
    options {
      logging = "CLOUD_LOGGING_ONLY"
    }
    dynamic "step" {
      for_each = yamldecode(local.app_build_config).steps
      content {
        args       = step.value.args
        name       = step.value.name
        entrypoint = try(step.value.entrypoint, null)
        id         = try(step.value.id, null)
      }
    }
  }
}

resource "google_cloudbuild_trigger" "app_new_release" {
  project         = var.project_id
  name            = "channel-flow-new-release"
  description     = "Triggers on any new build pushed to Artifact Registry. Creates a new release in Cloud Deploy."
  service_account = google_service_account.cloud_build.id
  pubsub_config {
    topic = google_pubsub_topic.gcr.id
  }

  approval_config {
    approval_required = false
  }

  source_to_build {
    uri       = local.github_repository_url
    ref       = "refs/heads/main"
    repo_type = "GITHUB"
  }

  build {
    images = []
    substitutions = {
      _REGION           = var.region
      _RUN_SERVICE_NAME = var.run_service_name
      _PIPELINE_NAME    = google_clouddeploy_delivery_pipeline.default.name
      _IMAGE            = "${local.artifact_registry_repo}/app"
      _RUN_CONFIG       = local.run_config
      _SKAFFOLD_CONFIG  = local.skaffold_config
    }
    tags = []
    options {
      logging = "CLOUD_LOGGING_ONLY"
    }
    dynamic "step" {
      for_each = yamldecode(local.new_release_config).steps
      content {
        args       = step.value.args
        name       = step.value.name
        entrypoint = try(step.value.entrypoint, null)
        id         = try(step.value.id, null)
      }
    }
  }
}
# Cloud Deploy resources (pipeline, target service account, and IAM bindings)
resource "google_clouddeploy_delivery_pipeline" "default" {
  project     = var.project_id
  location    = var.region
  name        = "channel-flow-delivery"
  description = "Basic delivery pipeline for ${var.run_service_name} app."
  labels      = var.labels
  serial_pipeline {
    stages {
      profiles  = ["prod"]
      target_id = google_clouddeploy_target.prod.name
    }
  }
  depends_on = [
    var.time_sleep
  ]
}

resource "google_service_account" "cloud_deploy" {
  project      = var.project_id
  account_id   = "${substr(var.run_service_name, 0, 21)}-deployer"
  display_name = "Service Account for Cloud Deploy deployment to Cloud Run."
}

resource "google_project_iam_member" "deploy_job_runner" {
  project = var.project_id
  role    = "roles/clouddeploy.jobRunner"
  member  = "serviceAccount:${google_service_account.cloud_deploy.email}"
}

resource "google_project_iam_member" "deploy_run_admin" {
  project = var.project_id
  role    = "roles/run.admin"
  member  = "serviceAccount:${google_service_account.cloud_deploy.email}"
}

resource "google_service_account_iam_binding" "deploy_sa_user_run" {
  service_account_id = data.google_service_account.cloud_run.id
  role               = "roles/iam.serviceAccountUser"
  members = [
    "serviceAccount:${google_service_account.cloud_deploy.email}",
  ]
}

resource "google_clouddeploy_target" "prod" {
  project     = var.project_id
  provider    = google
  location    = var.run_service_location
  name        = "channel-flow-prod-target"
  description = "Prod target for ${var.run_service_name} app."

  execution_configs {
    usages          = ["RENDER", "DEPLOY", "VERIFY"]
    service_account = google_service_account.cloud_deploy.email
  }

  labels           = var.labels
  require_approval = true

  run {
    location = "projects/${var.project_id}/locations/${var.run_service_location}"
  }
  depends_on = [
    var.time_sleep
  ]
}