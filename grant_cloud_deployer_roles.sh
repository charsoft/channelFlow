#!/bin/bash

# This script grants the necessary IAM roles to a service account for deploying to Cloud Run.
#
# Usage:
# ./grant_cloud_deployer_roles.sh [PROJECT_ID] [SERVICE_ACCOUNT_EMAIL]
#
# Example:
# ./grant_cloud_deployer_roles.sh my-gcp-project my-deployer-sa@my-gcp-project.iam.gserviceaccount.com

if [ "$#" -ne 2 ]; then
    echo "Usage: $0 [PROJECT_ID] [SERVICE_ACCOUNT_EMAIL]"
    exit 1
fi

PROJECT_ID=$1
SERVICE_ACCOUNT_EMAIL=$2

# An array of roles to be granted to the deployer service account.
ROLES=(
  "roles/artifactregistry.reader"
  "roles/cloudbuild.workerPoolUser"
  "roles/clouddeploy.jobRunner"
  "roles/clouddeploy.operator"
  "roles/clouddeploy.releaser"
  "roles/clouddeploy.viewer"
  "roles/iam.serviceAccountUser"
  "roles/run.admin"
  "roles/secretmanager.secretAccessor"
  "roles/storage.admin"
  "roles/storage.objectViewer"
)

echo "Granting deployer roles to '$SERVICE_ACCOUNT_EMAIL' on project '$PROJECT_ID'..."

for role in "${ROLES[@]}"; do
  echo "  - Granting role: $role"
  gcloud projects add-iam-policy-binding "$PROJECT_ID" \
    --member="serviceAccount:$SERVICE_ACCOUNT_EMAIL" \
    --role="$role" \
    --condition=None > /dev/null
done

echo "Successfully granted all required deployer roles to '$SERVICE_ACCOUNT_EMAIL'." 