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