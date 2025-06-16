variable "project_id" {
  description = "The Google Cloud project ID."
  type        = string
}

variable "region" {
  description = "The Google Cloud region for resources."
  type        = string
  default     = "us-central1"
}

variable "target_channel_id" {
  description = "The YouTube channel ID to monitor. This will be stored in Secret Manager."
  type        = string
  sensitive   = true
}

variable "gemini_model_name" {
  description = "The name of the Gemini model to use."
  type        = string

}

variable "imagen_model_name" {
  description = "The name of the Imagen model to use."
  type        = string

}

variable "firebase_api_key" {
  description = "The API key for the Firebase web app."
  type        = string
  sensitive   = true
}

variable "firebase_auth_domain" {
  description = "The auth domain for the Firebase web app."
  type        = string
  sensitive   = true
}

variable "firebase_project_id" {
  description = "The project ID for the Firebase web app."
  type        = string
  sensitive   = true
} 