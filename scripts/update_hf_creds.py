#!/usr/bin/env python3
"""
Automatically refresh AWS credentials via SSO and push to HF Space.

Usage (SSO - recommended, one browser click):
  python scripts/update_hf_creds.py --sso

Manual fallback (paste creds from portal):
  python scripts/update_hf_creds.py --key ASIAXX --secret XX --token XX

From .env file:
  python scripts/update_hf_creds.py
"""

import argparse
import json
import os
import sys
import time
import webbrowser
from pathlib import Path

import boto3
from dotenv import load_dotenv
from huggingface_hub import HfApi

SPACE_ID = "pramodmisra/nova-insurance-claims-ai"
ENV_FILE = Path(__file__).resolve().parent.parent / ".env"

# AWS SSO configuration (from organizer portal)
SSO_START_URL = "https://slalom-hackathon.awsapps.com/start/#"
SSO_REGION = "eu-central-1"
SSO_ACCOUNT_ID = "121333002038"
SSO_ROLE_NAME = "slalom_IsbUsersPS"

# Where to cache the SSO access token locally
SSO_CACHE_FILE = Path(__file__).resolve().parent / ".sso_cache.json"

SECRETS = [
    "AWS_ACCESS_KEY_ID",
    "AWS_SECRET_ACCESS_KEY",
    "AWS_SESSION_TOKEN",
    "AWS_DEFAULT_REGION",
]


def get_creds_via_sso():
    """
    Use AWS SSO OIDC device authorization to get fresh credentials.
    Opens browser for user to approve, then fetches role credentials.
    """
    print("Starting AWS SSO login...")
    print(f"  Account: {SSO_ACCOUNT_ID}")
    print(f"  Role:    {SSO_ROLE_NAME}")
    print()

    # Step 1: Register OIDC client
    oidc = boto3.client("sso-oidc", region_name=SSO_REGION)
    registration = oidc.register_client(
        clientName="nova-hf-updater",
        clientType="public",
    )
    client_id = registration["clientId"]
    client_secret = registration["clientSecret"]

    # Step 2: Start device authorization
    authz = oidc.start_device_authorization(
        clientId=client_id,
        clientSecret=client_secret,
        startUrl=SSO_START_URL,
    )
    verification_url = authz["verificationUriComplete"]
    device_code = authz["deviceCode"]
    interval = authz.get("interval", 5)

    # Step 3: Open browser for user approval
    print(f"Opening browser for SSO approval...")
    print(f"  URL: {verification_url}")
    print()
    print(">> Approve the request in your browser, then wait here. <<")
    print()
    webbrowser.open(verification_url)

    # Step 4: Poll for token
    print("Waiting for approval", end="", flush=True)
    access_token = None
    for _ in range(60):  # ~5 min timeout
        time.sleep(interval)
        print(".", end="", flush=True)
        try:
            token_response = oidc.create_token(
                clientId=client_id,
                clientSecret=client_secret,
                grantType="urn:ietf:params:oauth:grant-type:device_code",
                deviceCode=device_code,
            )
            access_token = token_response["accessToken"]
            print(" Approved!")
            break
        except oidc.exceptions.AuthorizationPendingException:
            continue
        except oidc.exceptions.SlowDownException:
            interval += 2
            continue
        except oidc.exceptions.ExpiredTokenException:
            print("\nERROR: Authorization expired. Please try again.")
            sys.exit(1)

    if not access_token:
        print("\nERROR: Timed out waiting for approval.")
        sys.exit(1)

    # Cache the access token for potential reuse
    SSO_CACHE_FILE.write_text(json.dumps({
        "accessToken": access_token,
        "expiresAt": token_response.get("expiresIn", 28800) + int(time.time()),
    }))

    # Step 5: Get role credentials
    sso = boto3.client("sso", region_name=SSO_REGION)
    role_creds = sso.get_role_credentials(
        roleName=SSO_ROLE_NAME,
        accountId=SSO_ACCOUNT_ID,
        accessToken=access_token,
    )["roleCredentials"]

    return {
        "AWS_ACCESS_KEY_ID": role_creds["accessKeyId"],
        "AWS_SECRET_ACCESS_KEY": role_creds["secretAccessKey"],
        "AWS_SESSION_TOKEN": role_creds["sessionToken"],
        "AWS_DEFAULT_REGION": "us-east-1",
    }


def get_creds_from_env():
    """Load credentials from .env file."""
    load_dotenv(ENV_FILE, override=True)
    creds = {}
    for key in SECRETS:
        val = os.getenv(key)
        if val and val not in ("", "your_access_key_here", "your_secret_key_here"):
            creds[key] = val
    return creds


def get_creds_from_args(args):
    """Build credentials dict from CLI arguments."""
    creds = {"AWS_DEFAULT_REGION": args.region}
    if args.key:
        creds["AWS_ACCESS_KEY_ID"] = args.key
    if args.secret:
        creds["AWS_SECRET_ACCESS_KEY"] = args.secret
    if args.token:
        creds["AWS_SESSION_TOKEN"] = args.token
    return creds


def push_secrets(creds: dict):
    """Push secrets to the HF Space."""
    api = HfApi()

    required = ["AWS_ACCESS_KEY_ID", "AWS_SECRET_ACCESS_KEY"]
    for r in required:
        if r not in creds:
            print(f"ERROR: Missing required credential: {r}")
            sys.exit(1)

    print(f"\nUpdating secrets on HF Space: {SPACE_ID}")
    for key, value in creds.items():
        api.add_space_secret(SPACE_ID, key, value)
        display = value[:8] + "..." if len(value) > 12 else "***"
        print(f"  {key} = {display}")

    print("\nDone! HF Space will rebuild with new credentials in ~1-2 min.")


def main():
    parser = argparse.ArgumentParser(description="Refresh AWS creds → push to HF Space")
    parser.add_argument("--sso", action="store_true",
                        help="Use AWS SSO login (opens browser, one click)")
    parser.add_argument("--key", help="AWS_ACCESS_KEY_ID (manual mode)")
    parser.add_argument("--secret", help="AWS_SECRET_ACCESS_KEY (manual mode)")
    parser.add_argument("--token", help="AWS_SESSION_TOKEN (manual mode)")
    parser.add_argument("--region", default="us-east-1", help="AWS region for Bedrock")
    args = parser.parse_args()

    if args.sso:
        creds = get_creds_via_sso()
    elif args.key or args.secret:
        creds = get_creds_from_args(args)
    else:
        print(f"Reading credentials from {ENV_FILE}")
        print("TIP: Use --sso for automatic browser-based login\n")
        creds = get_creds_from_env()

    if not creds.get("AWS_ACCESS_KEY_ID"):
        print("ERROR: No credentials found.")
        print("  Use --sso for automatic login, or")
        print("  Update .env, or pass --key/--secret/--token")
        sys.exit(1)

    push_secrets(creds)


if __name__ == "__main__":
    main()
