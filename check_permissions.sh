#!/bin/bash

# This script checks the IAM roles for a specified user or service account on a Google Cloud project.
#
# Usage:
# ./check_permissions.sh [PROJECT_ID] [MEMBER_EMAIL]
#
# Example (for a user):
# ./check_permissions.sh my-gcp-project user@example.com
#
# Example (for a service account):
# ./check_permissions.sh my-gcp-project my-sa@my-gcp-project.iam.gserviceaccount.com

# --- Script Start ---

if [ "$#" -ne 2 ]; then
    echo "Usage: $0 [PROJECT_ID] [MEMBER_EMAIL]"
    exit 1
fi

PROJECT_ID=$1
MEMBER_EMAIL=$2

# Determine if the member is a user or a service account
if [[ $MEMBER_EMAIL == *.gserviceaccount.com ]]; then
  MEMBER_TYPE="serviceAccount"
else
  MEMBER_TYPE="user"
fi

echo "Checking permissions for $MEMBER_TYPE: $MEMBER_EMAIL on project: $PROJECT_ID"
echo "---"

gcloud projects get-iam-policy "$PROJECT_ID" \
  --flatten="bindings[].members" \
  --filter="bindings.members:$MEMBER_TYPE:$MEMBER_EMAIL" \
  --format="table(bindings.role)" 