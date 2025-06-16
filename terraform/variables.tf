variable "project_id" {
  description = "The ID of the Google Cloud project."
  type        = string
}

variable "region" {
  description = "The region for Google Cloud resources."
  type        = string
  default     = "us-central1"
} 