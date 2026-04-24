#!/bin/bash
# Cloud Build GitHub trigger setup script
# Run this once to create the push-and-deploy trigger for tiktok-manager
#
# Prerequisites:
#   - gcloud CLI authenticated with appropriate permissions
#   - GitHub repository connected to Cloud Build in GCP console
#     (Cloud Build > Triggers > Connect repository)

set -euo pipefail

PROJECT_ID="autogpt-406113"
REGION="asia-northeast1"
REPO_OWNER="sphink-jp"
REPO_NAME="claude_agent"
TRIGGER_NAME="tiktok-manager-push-deploy"
BRANCH_PATTERN="^main$"
INCLUDED_FILES="tiktok-manager/**"
CONFIG_FILE="tiktok-manager/cloudbuild.yaml"

echo "Creating Cloud Build trigger: ${TRIGGER_NAME}"
echo "  Project : ${PROJECT_ID}"
echo "  Region  : ${REGION}"
echo "  Repo    : ${REPO_OWNER}/${REPO_NAME}"
echo "  Branch  : ${BRANCH_PATTERN}"
echo "  Filter  : ${INCLUDED_FILES}"
echo ""

gcloud builds triggers create github \
  --project="${PROJECT_ID}" \
  --region="${REGION}" \
  --name="${TRIGGER_NAME}" \
  --repo-owner="${REPO_OWNER}" \
  --repo-name="${REPO_NAME}" \
  --branch-pattern="${BRANCH_PATTERN}" \
  --build-config="${CONFIG_FILE}" \
  --included-files="${INCLUDED_FILES}" \
  --description="Push-and-deploy: tiktok-manager on push to main"

echo ""
echo "Trigger created successfully."
echo "Verify at: https://console.cloud.google.com/cloud-build/triggers?project=${PROJECT_ID}"
