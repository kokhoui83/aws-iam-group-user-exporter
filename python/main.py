#!/usr/bin/env python3
"""
identitystore-groups-users.py
Generate CSV report of AWS Identity Store groups and their users.
- Supports AWS_PROFILE and IDENTITY_STORE_ID (via env or .env file)
- Adds generation timestamp
"""

import boto3
import csv
import os
import time
from datetime import datetime
from dotenv import load_dotenv

# Load .env if available
load_dotenv()

# Read environment variables
AWS_PROFILE = os.getenv("AWS_PROFILE")
IDENTITY_STORE_ID = os.getenv("IDENTITY_STORE_ID")
OUTPUT_FILE = os.getenv("OUTPUT_FILE", "identitystore-groups-users.csv")

# Start timer
start_time = time.time()

# boto3 session
session_args = {}
if AWS_PROFILE:
    session_args["profile_name"] = AWS_PROFILE
    print(f"ℹ️ Using AWS profile: {AWS_PROFILE}")

session = boto3.Session(**session_args)
sso_admin = session.client("sso-admin")
identitystore = session.client("identitystore")

# Auto-detect Identity Store ID if not set
if not IDENTITY_STORE_ID:
    print("ℹ️ No IDENTITY_STORE_ID provided, detecting automatically...")
    instances = sso_admin.list_instances()
    if not instances["Instances"]:
        raise RuntimeError("❌ No SSO instances found. Please set IDENTITY_STORE_ID.")
    IDENTITY_STORE_ID = instances["Instances"][0]["IdentityStoreId"]

print(f"ℹ️ Using Identity Store ID: {IDENTITY_STORE_ID}")

# Fetch groups
groups = identitystore.list_groups(IdentityStoreId=IDENTITY_STORE_ID)["Groups"]

# Write CSV
with open(OUTPUT_FILE, mode="w", newline="", encoding="utf-8") as csvfile:
    writer = csv.writer(csvfile)
    writer.writerow([f"# Generated at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"])
    writer.writerow(["Group", "User", "DisplayName", "Email"])

    for group in groups:
        group_id = group["GroupId"]
        group_name = group.get("DisplayName", group_id)

        # List group memberships
        memberships = identitystore.list_group_memberships(
            IdentityStoreId=IDENTITY_STORE_ID,
            GroupId=group_id
        )["GroupMemberships"]

        for membership in memberships:
            user_id = membership["MemberId"]["UserId"]

            user = identitystore.describe_user(
                IdentityStoreId=IDENTITY_STORE_ID,
                UserId=user_id
            )

            user_name = user.get("UserName", "")
            display_name = user.get("DisplayName", "")
            email = user.get("Emails", [{}])[0].get("Value", "")

            writer.writerow([group_name, user_name, display_name, email])

end_time = time.time()
elapsed = round(end_time - start_time, 2)

print(f"✅ Report generated: {OUTPUT_FILE}")
print(f"⏱ Time taken: {elapsed} seconds")
