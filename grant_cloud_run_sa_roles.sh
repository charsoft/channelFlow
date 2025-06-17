#!/bin/bash

# This script grants the necessary IAM roles to a service account for running the Cloud Run service.
#
# Usage:
# ./grant_cloud_run_sa_roles.sh [PROJECT_ID] [SERVICE_ACCOUNT_EMAIL]
#
# Example:
# ./grant_cloud_run_sa_roles.sh my-gcp-project my-sa@my-gcp-project.iam.gserviceaccount.com

if [ "$#" -ne 2 ]; then
    echo "Usage: $0 [PROJECT_ID] [SERVICE_ACCOUNT_EMAIL]"
    exit 1
fi

PROJECT_ID=$1
SERVICE_ACCOUNT_EMAIL=$2

# An array of roles to be granted to the service account.
# Note: "roles/customStorageAdmin" is the custom role we created earlier.
ROLES=(
  "roles/datastore.owner"
  "roles/secretmanager.secretAccessor"
  "roles/storage.objectUser"
  "projects/$PROJECT_ID/roles/customStorageAdmin"
)

echo "Granting roles to '$SERVICE_ACCOUNT_EMAIL' on project '$PROJECT_ID'..."

for role in "${ROLES[@]}"; do
  echo "  - Granting role: $role"
  gcloud projects add-iam-policy-binding "$PROJECT_ID" \
    --member="serviceAccount:$SERVICE_ACCOUNT_EMAIL" \
    --role="$role" \
    --condition=None > /dev/null
done

echo "Successfully granted all required roles to '$SERVICE_ACCOUNT_EMAIL'." 