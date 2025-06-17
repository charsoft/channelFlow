variable "project_id" {
  type        = string
  description = "Google Cloud project ID to deploy resources to."
}

variable "run_service_name" {
  type        = string
  description = "The name of the Cloud Run service that this pipeline will deploy to."
}

variable "github_repository_url" {
  type        = string
  description = "URL of connected GitHub repository (https://github.com/repo_owner/repo_name)"
}

variable "region" {
  type        = string
  description = "Default region to use for Google Cloud resources."
  default     = "us-central1"
}

variable "labels" {
  type        = map(string)
  description = "A set of key/value label pairs to assign to the resources deployed by this solution."
  default     = {}
}