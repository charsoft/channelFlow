variable "project_id" {
  description = "The Google Cloud project ID."
  type        = string
}

variable "region" {
  description = "The Google Cloud region for resources."
  type        = string
  default     = "us-central1"
}

variable "github_repository_url" {
  description = "The URL of the GitHub repository."
  type        = string
}

variable "run_service_name" {
  description = "The name of the Cloud Run service."
  type        = string
  default     = "channel-flow-svc"
}

variable "gemini_model_name" {
  description = "The name of the Gemini model to use."
  type        = string
}

variable "imagen_model_name" {
  description = "The name of the Imagen model to use."
  type        = string
}

variable "labels" {
  description = "A map of labels to apply to resources."
  type        = map(string)
  default = {
    "app"       = "channel-flow"
    "terraform" = "true"
  }
} 