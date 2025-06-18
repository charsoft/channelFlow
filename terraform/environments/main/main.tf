terraform {
  required_providers {
    google = {
      source = "hashicorp/google"
    }
    google-beta = {
      source = "hashicorp/google-beta"
    }
  }
  backend "gcs" {
    bucket = "channel-flow-2-tf-storage-0617"
    prefix = "terraform/state/environments/main"
  }
}

resource "time_sleep" "project_services" {
  create_duration = "30s"
}

data "terraform_remote_state" "root" {
  backend = "gcs"
  config = {
    bucket = "channel-flow-2-tf-storage-0617"
    prefix = "terraform/state"
  }
  workspace = "default"
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
  gcs_bucket_name           = data.terraform_remote_state.root.outputs.gcs_bucket_name
  gemini_model_name         = data.terraform_remote_state.root.outputs.gemini_model_name
  imagen_model_name         = data.terraform_remote_state.root.outputs.imagen_model_name
}