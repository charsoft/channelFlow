variable "project_id" {
  description = "The project ID to host the service."
  type        = string
}

variable "region" {
  description = "The region to host the service."
  type        = string
}

variable "run_service_name" {
  description = "The name of the Cloud Run service."
  type        = string
}

variable "labels" {
  description = "The labels to apply to the service."
  type        = map(string)
  default     = {}
} 