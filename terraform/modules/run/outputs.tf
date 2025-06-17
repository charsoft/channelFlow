output "service_name" {
  description = "The name of the Cloud Run service."
  value       = google_cloud_run_service.default.name
}

output "location" {
  description = "The location of the Cloud Run service."
  value       = google_cloud_run_service.default.location
}

output "service_account_email" {
  description = "The email of the service account used by the Cloud Run service."
  value       = google_service_account.run.email
} 