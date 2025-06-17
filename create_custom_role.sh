#!/bin/bash

# This script creates or updates a custom IAM role in a Google Cloud project.
# The role is defined with specific permissions for managing Cloud Storage objects.
#
# Usage:
# ./create_custom_role.sh [PROJECT_ID]
#
# Example:
# ./create_custom_role.sh my-gcp-project

if [ "$#" -ne 1 ]; then
    echo "Usage: $0 [PROJECT_ID]"
    exit 1
fi

PROJECT_ID=$1
ROLE_ID="customStorageAdmin"
TITLE="Custom Storage Admin"
DESCRIPTION="Custom role with specific permissions for managing storage objects."
PERMISSIONS="storage.multipartUploads.abort,storage.multipartUploads.create,storage.multipartUploads.list,storage.multipartUploads.listParts,storage.objects.create,storage.objects.delete,storage.objects.get,storage.objects.getIamPolicy,storage.objects.list,storage.objects.move,storage.objects.overrideUnlockedRetention,storage.objects.restore,storage.objects.setIamPolicy,storage.objects.setRetention,storage.objects.update"

echo "Checking for custom role '$ROLE_ID' in project '$PROJECT_ID'..."

# Check if the role already exists by trying to describe it.
gcloud iam roles describe "$ROLE_ID" --project="$PROJECT_ID" > /dev/null 2>&1

# $? will be 0 if the role exists, and non-zero otherwise.
if [ $? -eq 0 ]; then
    echo "Role '$ROLE_ID' already exists. Updating permissions to ensure they are current."
    gcloud iam roles update "$ROLE_ID" --project="$PROJECT_ID" \
      --title="$TITLE" \
      --description="$DESCRIPTION" \
      --permissions="$PERMISSIONS"

else
    echo "Role '$ROLE_ID' does not exist. Creating it now."
    gcloud iam roles create "$ROLE_ID" --project="$PROJECT_ID" \
      --title="$TITLE" \
      --description="$DESCRIPTION" \
      --permissions="$PERMISSIONS"
fi

if [ $? -eq 0 ]; then
    echo "Successfully ensured role '$ROLE_ID' is configured in project '$PROJECT_ID'."
else
    echo "Error: Failed to create or update role '$ROLE_ID'."
    exit 1
fi 