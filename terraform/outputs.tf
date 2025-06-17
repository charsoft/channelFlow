output "gcs_bucket_name" {
  description = "The name of the GCS bucket for public assets."
  value       = google_storage_bucket.public_bucket.name
}

output "gemini_model_name" {
  description = "The name of the Gemini model to use."
  value       = var.gemini_model_name
}

output "imagen_model_name" {
  description = "The name of the Imagen model to use."
  value       = var.imagen_model_name
}

output "app_secret_id" {
  description = "The ID of the application's secret key."
  value       = google_secret_manager_secret.app_secret_key.secret_id
}

output "client_id_secret_id" {
  description = "The ID of the Google Client ID secret."
  value       = google_secret_manager_secret.google_client_id_secret.secret_id
}

output "client_secret_secret_id" {
  description = "The ID of the Google Client Secret secret."
  value       = google_secret_manager_secret.google_client_secret_secret.secret_id
} 