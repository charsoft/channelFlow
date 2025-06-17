terraform {
  required_providers {
    google = {
      source = "hashicorp/google"
    }
    google-beta = {
      source = "hashicorp/google-beta"
    }
  }
}

resource "time_sleep" "project_services" {
  create_duration = "30s"
}

module "run_service" {
  source           = "../../modules/run"
  project_id       = var.project_id
  region           = var.region
  run_service_name = var.run_service_name
  labels           = var.labels
}

module "cicd_pipeline" {
  source                    = "../../modules/cicd"
  project_id                = var.project_id
  region                    = var.region
  run_service_name          = module.run_service.service_name
  run_service_location      = module.run_service.location
  run_service_account_email = module.run_service.service_account_email
  github_repository_url     = var.github_repository_url
  labels                    = var.labels
  time_sleep                = time_sleep.project_services
}