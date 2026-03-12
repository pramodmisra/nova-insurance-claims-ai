#!/usr/bin/env python3
"""
Lightweight credential refresh — reads cached SSO token, pushes fresh
AWS credentials to HF Space. Designed to run from Windows Task Scheduler.

If the SSO token has expired, exits with code 1 (you need to re-run keep_alive.py
or update_hf_creds.py --sso to get a new token via browser).
"""

import json
import sys
import time
from pathlib import Path

import boto3
from huggingface_hub import HfApi

SPACE_ID = "pramodmisra/nova-insurance-claims-ai"
SSO_REGION = "eu-central-1"
SSO_ACCOUNT_ID = "121333002038"
SSO_ROLE_NAME = "slalom_IsbUsersPS"
SSO_CACHE_FILE = Path(__file__).resolve().parent / ".sso_cache.json"
LOG_FILE = Path(__file__).resolve().parent / "refresh.log"


def log(msg):
    ts = time.strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{ts}] {msg}"
    print(line)
    with open(LOG_FILE, "a") as f:
        f.write(line + "\n")


def main():
    # Load cached SSO token
    if not SSO_CACHE_FILE.exists():
        log("ERROR: No SSO cache found. Run: python scripts/keep_alive.py")
        sys.exit(1)

    cache = json.loads(SSO_CACHE_FILE.read_text())
    access_token = cache["accessToken"]
    token_expires = cache["expiresAt"]

    # Check if SSO token is still valid (with 5 min buffer)
    remaining = token_expires - time.time()
    if remaining < 300:
        log(f"ERROR: SSO token expired. Run: python scripts/keep_alive.py")
        sys.exit(1)

    log(f"SSO token valid for {remaining / 3600:.1f}h")

    # Fetch fresh role credentials
    try:
        sso = boto3.client("sso", region_name=SSO_REGION)
        role_creds = sso.get_role_credentials(
            roleName=SSO_ROLE_NAME,
            accountId=SSO_ACCOUNT_ID,
            accessToken=access_token,
        )["roleCredentials"]
    except Exception as e:
        log(f"ERROR: Failed to get role credentials: {e}")
        sys.exit(1)

    cred_expires = role_creds["expiration"] / 1000
    cred_expires_str = time.strftime("%H:%M:%S", time.localtime(cred_expires))

    # Push to HF Space
    try:
        api = HfApi()
        secrets = {
            "AWS_ACCESS_KEY_ID": role_creds["accessKeyId"],
            "AWS_SECRET_ACCESS_KEY": role_creds["secretAccessKey"],
            "AWS_SESSION_TOKEN": role_creds["sessionToken"],
            "AWS_DEFAULT_REGION": "us-east-1",
        }
        for key, value in secrets.items():
            api.add_space_secret(SPACE_ID, key, value)
    except Exception as e:
        log(f"ERROR: Failed to push to HF: {e}")
        sys.exit(1)

    log(f"OK: Credentials pushed to HF Space (valid until {cred_expires_str})")


if __name__ == "__main__":
    main()
