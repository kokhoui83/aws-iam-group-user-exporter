#!/usr/bin/env python3
"""
Generate CSV report of AWS Identity Store groups, users, and their permission sets.
CSV columns order: AccountName, AccountId, Group, PermissionSet, User, DisplayName, Email
"""

import boto3
import csv
import os
import time
from datetime import datetime, timedelta
from dotenv import load_dotenv


def get_accounts(org_client):
    accounts = {}
    paginator = org_client.get_paginator("list_accounts")
    for page in paginator.paginate():
        for acct in page.get("Accounts", []):
            accounts[acct["Id"]] = acct["Name"]
    return accounts


def get_permission_sets(sso_client, instance_arn):
    permission_sets = {}
    paginator = sso_client.get_paginator("list_permission_sets")
    for page in paginator.paginate(InstanceArn=instance_arn):
        for ps_arn in page.get("PermissionSets", []):
            details = sso_client.describe_permission_set(
                InstanceArn=instance_arn, PermissionSetArn=ps_arn
            )
            permission_sets[ps_arn] = details["PermissionSet"]["Name"]
    return permission_sets


def get_group_assignments(sso_client, instance_arn, accounts, permission_sets):
    group_permission_map = {}

    for account_id, account_name in accounts.items():
        for ps_arn, ps_name in permission_sets.items():
            paginator = sso_client.get_paginator("list_account_assignments")
            for page in paginator.paginate(
                InstanceArn=instance_arn,
                AccountId=account_id,
                PermissionSetArn=ps_arn
            ):
                for assignment in page.get("AccountAssignments", []):
                    if assignment["PrincipalType"] == "GROUP":
                        group_id = assignment["PrincipalId"]
                        group_permission_map.setdefault(group_id, set()).add(
                            (ps_name, account_name, account_id)
                        )
    return group_permission_map


def list_all_groups(identitystore, identity_store_id):
    groups = []
    paginator = identitystore.get_paginator("list_groups")
    for page in paginator.paginate(IdentityStoreId=identity_store_id):
        groups.extend(page.get("Groups", []))
    return groups


def list_group_memberships(identitystore, identity_store_id, group_id):
    memberships = []
    paginator = identitystore.get_paginator("list_group_memberships")
    for page in paginator.paginate(IdentityStoreId=identity_store_id, GroupId=group_id):
        memberships.extend(page.get("GroupMemberships", []))
    return memberships


def generate_report(identitystore, groups, group_permission_map, identity_store_id, output_file):
    """
    Generate the CSV file with group memberships and permissions.
    Multiple permission sets per user/group are concatenated as a comma-separated string.
    """
    fieldnames = [
        "AccountName",
        "AccountId",
        "Group",
        "GroupDescription",
        "PermissionSet",
        "User",
        "DisplayName",
        "Email",
    ]

    with open(output_file, mode="w", newline="", encoding="utf-8") as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()

        for group in groups:
            group_id = group["GroupId"]
            group_name = group.get("DisplayName", group_id)
            group_description = group.get("Description", "")

            memberships = list_group_memberships(identitystore, identity_store_id, group_id)
            permission_pairs = group_permission_map.get(group_id, set())

            # Map: (user_id) → list of (PermissionSet, AccountName, AccountId)
            user_permissions = {}
            for ps_name, acct_name, acct_id in permission_pairs:
                user_permissions.setdefault((acct_name, acct_id), []).append(ps_name)

            for membership in memberships:
                user = identitystore.describe_user(
                    IdentityStoreId=identity_store_id,
                    UserId=membership["MemberId"]["UserId"],
                )

                user_name = user.get("UserName", "")
                display_name = user.get("DisplayName", "")
                email = user.get("Emails", [{}])[0].get("Value", "")

                if user_permissions:
                    for (acct_name, acct_id), ps_list in user_permissions.items():
                        writer.writerow({
                            "AccountName": acct_name,
                            "AccountId": acct_id,
                            "Group": group_name,
                            "GroupDescription": group_description,
                            "PermissionSet": "; ".join(sorted(ps_list)),
                            "User": user_name,
                            "DisplayName": display_name,
                            "Email": email,
                        })
                else:
                    writer.writerow({
                        "AccountName": "",
                        "AccountId": "",
                        "Group": group_name,
                        "GroupDescription": group_description,
                        "PermissionSet": "",
                        "User": user_name,
                        "DisplayName": display_name,
                        "Email": email,
                    })


if __name__ == "__main__":
    load_dotenv()

    AWS_PROFILE = os.getenv("AWS_PROFILE")
    IDENTITY_STORE_ID = os.getenv("IDENTITY_STORE_ID")
    OUTPUT_FILE = os.getenv("OUTPUT_FILE", "identitystore-groups-users.csv")

    start_time = time.time()

    # boto3 session
    session_args = {}
    if AWS_PROFILE:
        session_args["profile_name"] = AWS_PROFILE
        print(f"ℹ️ Using AWS profile: {AWS_PROFILE}")

    session = boto3.Session(**session_args)
    sso_admin = session.client("sso-admin")
    identitystore = session.client("identitystore")
    org = session.client("organizations")

    # Detect Identity Store ID if not provided
    if not IDENTITY_STORE_ID:
        instances = sso_admin.list_instances()
        if not instances["Instances"]:
            raise RuntimeError("❌ No SSO instances found. Please set IDENTITY_STORE_ID.")
        IDENTITY_STORE_ID = instances["Instances"][0]["IdentityStoreId"]
        INSTANCE_ARN = instances["Instances"][0]["InstanceArn"]
    else:
        instances = sso_admin.list_instances()
        INSTANCE_ARN = instances["Instances"][0]["InstanceArn"]

    print(f"ℹ️ Using Identity Store ID: {IDENTITY_STORE_ID}")
    print(f"ℹ️ Using Instance ARN: {INSTANCE_ARN}")

    accounts = get_accounts(org)
    print(f"ℹ️ Found {len(accounts)} AWS accounts")

    permission_sets = get_permission_sets(sso_admin, INSTANCE_ARN)
    print(f"ℹ️ Found {len(permission_sets)} permission sets")

    group_permission_map = get_group_assignments(sso_admin, INSTANCE_ARN, accounts, permission_sets)

    groups = list_all_groups(identitystore, IDENTITY_STORE_ID)
    print(f"ℹ️ Found {len(groups)} groups")

    generate_report(identitystore, groups, group_permission_map, IDENTITY_STORE_ID, OUTPUT_FILE)

    elapsed = timedelta(seconds=round(time.time() - start_time))
    print(f"✅ Report generated: {OUTPUT_FILE}")
    print(f"⏱ Time taken: {elapsed}")
