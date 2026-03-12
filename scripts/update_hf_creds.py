#!/usr/bin/env python3
"""
Push AWS credentials from .env to Hugging Face Space secrets.

Usage:
  1. Update your .env file with fresh AWS credentials
  2. Run: python scripts/update_hf_creds.py

Or pass credentials directly:
  python scripts/update_hf_creds.py \
    --key ASIAXXX --secret XXXXX --token XXXXX
"""

import argparse
import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from huggingface_hub import HfApi

SPACE_ID = "pramodmisra/nova-insurance-claims-ai"
ENV_FILE = Path(__file__).resolve().parent.parent / ".env"

SECRETS = [
    "AWS_ACCESS_KEY_ID",
    "AWS_SECRET_ACCESS_KEY",
    "AWS_SESSION_TOKEN",
    "AWS_DEFAULT_REGION",
]


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

    print(f"Updating secrets on HF Space: {SPACE_ID}")
    for key, value in creds.items():
        api.add_space_secret(SPACE_ID, key, value)
        display = value[:8] + "..." if len(value) > 12 else "***"
        print(f"  {key} = {display}")

    print("\nDone! HF Space will rebuild automatically with new credentials.")


def main():
    parser = argparse.ArgumentParser(description="Push AWS creds to HF Space")
    parser.add_argument("--key", help="AWS_ACCESS_KEY_ID")
    parser.add_argument("--secret", help="AWS_SECRET_ACCESS_KEY")
    parser.add_argument("--token", help="AWS_SESSION_TOKEN")
    parser.add_argument("--region", default="us-east-1", help="AWS region")
    args = parser.parse_args()

    if args.key or args.secret:
        creds = get_creds_from_args(args)
    else:
        print(f"Reading credentials from {ENV_FILE}")
        creds = get_creds_from_env()

    if not creds.get("AWS_ACCESS_KEY_ID"):
        print("ERROR: No credentials found. Update .env or pass --key/--secret/--token")
        sys.exit(1)

    push_secrets(creds)


if __name__ == "__main__":
    main()
