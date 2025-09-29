#!/bin/bash
# identitystore-groups-users.sh
# Generate CSV report of Identity Store groups and their members
# Supports AWS_PROFILE, IDENTITY_STORE_ID env vars, reads .env file, and tracks execution time

set -euo pipefail

# Load .env if exists
if [[ -f ".env" ]]; then
  echo "ℹ️ Loading environment variables from .env file"
  export $(grep -v '^#' .env | xargs)
fi

START_TIME=$(date +%s)

# Optional AWS_PROFILE handling
AWS_PROFILE_OPT=""
if [[ -n "${AWS_PROFILE:-}" ]]; then
  AWS_PROFILE_OPT="--profile $AWS_PROFILE"
  echo "ℹ️ Using AWS profile: $AWS_PROFILE"
fi

# Use env var if provided, otherwise auto-detect
IDENTITY_STORE_ID="${IDENTITY_STORE_ID:-}"

if [[ -z "$IDENTITY_STORE_ID" ]]; then
  echo "ℹ️ No IDENTITY_STORE_ID provided, detecting automatically..."
  IDENTITY_STORE_ID=$(aws sso-admin list-instances $AWS_PROFILE_OPT \
    --query "Instances[0].IdentityStoreId" \
    --output text)
fi

if [[ -z "$IDENTITY_STORE_ID" || "$IDENTITY_STORE_ID" == "None" ]]; then
  echo "❌ Could not determine Identity Store ID. Please set IDENTITY_STORE_ID."
  exit 1
fi

OUTPUT_FILE="${OUTPUT_FILE:-identitystore-groups-users.csv}"
GENERATED_AT=$(date +"%Y-%m-%d %H:%M:%S")

# Add timestamp comment at the top of CSV
echo "# Generated at: $GENERATED_AT" > "$OUTPUT_FILE"
echo "Group,User" >> "$OUTPUT_FILE"

# Loop through all groups
for groupId in $(aws identitystore list-groups \
  --identity-store-id "$IDENTITY_STORE_ID" \
  $AWS_PROFILE_OPT \
  --query "Groups[].GroupId" \
  --output text); do

  groupName=$(aws identitystore describe-group \
    --identity-store-id "$IDENTITY_STORE_ID" \
    --group-id "$groupId" \
    $AWS_PROFILE_OPT \
    --query "DisplayName" --output text)

  # Loop through users in each group
  for userId in $(aws identitystore list-group-memberships \
    --identity-store-id "$IDENTITY_STORE_ID" \
    --group-id "$groupId" \
    $AWS_PROFILE_OPT \
    --query "GroupMemberships[].MemberId.UserId" \
    --output text); do

      userName=$(aws identitystore describe-user \
        --identity-store-id "$IDENTITY_STORE_ID" \
        --user-id "$userId" \
        $AWS_PROFILE_OPT \
        --query "UserName" --output text)

      echo "$groupName,$userName" >> "$OUTPUT_FILE"
  done
done

END_TIME=$(date +%s)
ELAPSED=$((END_TIME - START_TIME))

echo "✅ Report generated: $OUTPUT_FILE"
echo "⏱ Time taken: $ELAPSED seconds"
