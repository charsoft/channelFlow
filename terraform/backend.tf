# This file defines the GCS bucket used to store the Terraform state itself.
# It is kept separate from the main infrastructure definition for clarity.

resource "google_storage_bucket" "terraform_state" {
  name          = "${var.project_id}-tfstate"
  location      = "US" # GCS bucket locations must be multi-regional or regional
  force_destroy = false # Protects state from accidental deletion

  # Enable versioning to keep a history of your state files, which allows for recovery.
  versioning {
    enabled = true
  }

  # Prevent accidental public exposure of the state files.
  public_access_prevention = "enforced"
} 