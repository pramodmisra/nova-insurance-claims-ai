#!/usr/bin/env python3
"""
Keep HF Space alive by refreshing AWS credentials every 45 minutes.

Usage:
  1. Run once in a PowerShell window:
       python scripts/keep_alive.py

  2. It will open your browser for SSO login (one click)
  3. Then it auto-refreshes credentials every 45 minutes for ~8 hours
  4. When the SSO token expires, it opens the browser again for re-approval

Leave this running in a PowerShell window while you need the demo up.
"""

import json
import sys
import time
import webbrowser
from pathlib import Path

import boto3
from huggingface_hub import HfApi

SPACE_ID = "pramodmisra/nova-insurance-claims-ai"
SSO_START_URL = "https://slalom-hackathon.awsapps.com/start/#"
SSO_REGION = "eu-central-1"
SSO_ACCOUNT_ID = "121333002038"
SSO_ROLE_NAME = "slalom_IsbUsersPS"
SSO_CACHE_FILE = Path(__file__).resolve().parent / ".sso_cache.json"

REFRESH_INTERVAL = 45 * 60  # 45 minutes (credentials last 1 hour)


def sso_login():
    """Perform SSO device authorization. Opens browser for approval."""
    print("\n--- SSO Login Required ---")
    oidc = boto3.client("sso-oidc", region_name=SSO_REGION)

    registration = oidc.register_client(
        clientName="nova-hf-updater",
        clientType="public",
    )
    client_id = registration["clientId"]
    client_secret = registration["clientSecret"]

    authz = oidc.start_device_authorization(
        clientId=client_id,
        clientSecret=client_secret,
        startUrl=SSO_START_URL,
    )
    verification_url = authz["verificationUriComplete"]
    device_code = authz["deviceCode"]
    interval = authz.get("interval", 5)

    print(f"Opening browser: {verification_url}")
    print(">> Click 'Allow' in your browser <<\n")
    webbrowser.open(verification_url)

    print("Waiting for approval", end="", flush=True)
    for _ in range(60):
        time.sleep(interval)
        print(".", end="", flush=True)
        try:
            token_response = oidc.create_token(
                clientId=client_id,
                clientSecret=client_secret,
                grantType="urn:ietf:params:oauth:grant-type:device_code",
                deviceCode=device_code,
            )
            print(" Approved!")
            access_token = token_response["accessToken"]
            expires_at = int(time.time()) + token_response.get("expiresIn", 28800)
            SSO_CACHE_FILE.write_text(json.dumps({
                "accessToken": access_token,
                "expiresAt": expires_at,
            }))
            return access_token, expires_at
        except oidc.exceptions.AuthorizationPendingException:
            continue
        except oidc.exceptions.SlowDownException:
            interval += 2
            continue
        except oidc.exceptions.ExpiredTokenException:
            print("\nAuthorization expired. Retrying...")
            return sso_login()

    print("\nTimed out. Retrying...")
    return sso_login()


def get_sso_token():
    """Get a valid SSO access token, re-logging in if expired."""
    if SSO_CACHE_FILE.exists():
        data = json.loads(SSO_CACHE_FILE.read_text())
        if data["expiresAt"] > time.time() + 300:  # 5 min buffer
            return data["accessToken"], data["expiresAt"]
    return sso_login()


def refresh_credentials(access_token):
    """Fetch fresh role credentials and push to HF Space."""
    sso = boto3.client("sso", region_name=SSO_REGION)
    role_creds = sso.get_role_credentials(
        roleName=SSO_ROLE_NAME,
        accountId=SSO_ACCOUNT_ID,
        accessToken=access_token,
    )["roleCredentials"]

    cred_expires = role_creds["expiration"] / 1000

    secrets = {
        "AWS_ACCESS_KEY_ID": role_creds["accessKeyId"],
        "AWS_SECRET_ACCESS_KEY": role_creds["secretAccessKey"],
        "AWS_SESSION_TOKEN": role_creds["sessionToken"],
        "AWS_DEFAULT_REGION": "us-east-1",
    }

    api = HfApi()
    for key, value in secrets.items():
        api.add_space_secret(SPACE_ID, key, value)

    expires_str = time.strftime("%H:%M:%S", time.localtime(cred_expires))
    print(f"  Credentials refreshed (valid until {expires_str})")
    return cred_expires


def main():
    print("=" * 55)
    print("  Nova Insurance Claims AI - HF Space Keep-Alive")
    print("=" * 55)
    print(f"  Space: {SPACE_ID}")
    print(f"  Refresh interval: {REFRESH_INTERVAL // 60} minutes")
    print(f"  SSO token lasts: ~8 hours")
    print()
    print("  Leave this window open. Press Ctrl+C to stop.")
    print("=" * 55)

    access_token, token_expires = get_sso_token()

    cycle = 0
    try:
        while True:
            cycle += 1
            now = time.strftime("%H:%M:%S")

            # Check if SSO token is still valid
            if time.time() > token_expires - 300:
                print(f"\n[{now}] SSO token expiring, re-authenticating...")
                access_token, token_expires = sso_login()

            print(f"[{now}] Refresh #{cycle}", end="")
            try:
                cred_expires = refresh_credentials(access_token)
            except Exception as e:
                print(f"  ERROR: {e}")
                print("  Attempting SSO re-login...")
                access_token, token_expires = sso_login()
                cred_expires = refresh_credentials(access_token)

            sso_remaining = (token_expires - time.time()) / 3600
            next_refresh = time.strftime("%H:%M:%S",
                                         time.localtime(time.time() + REFRESH_INTERVAL))
            print(f"  Next refresh: {next_refresh} | SSO token: {sso_remaining:.1f}h left")

            time.sleep(REFRESH_INTERVAL)

    except KeyboardInterrupt:
        print(f"\n\nStopped. Credentials last pushed are valid for ~1 hour.")
        print("Run this script again when you need the demo back up.")


if __name__ == "__main__":
    main()
