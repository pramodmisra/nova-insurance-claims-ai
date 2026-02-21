"""Configuration for Nova Insurance Claims AI Agent."""

import os
from dotenv import load_dotenv

load_dotenv()

# AWS
AWS_REGION = os.getenv("AWS_DEFAULT_REGION", "us-east-1")
NOVA_MODEL_ID = "us.amazon.nova-2-lite-v1:0"

# DynamoDB tables
APPLICANTS_TABLE = "nova-claims-applicants"
CLAIMS_TABLE = "nova-claims-records"
POLICIES_TABLE = "nova-claims-policies"

# S3
S3_BUCKET_PREFIX = "nova-claims-hackathon"

# Nova inference settings
INFERENCE_CONFIG = {
    "temperature": 0.3,
    "topP": 0.9,
    "maxTokens": 10000,
}

REASONING_CONFIG = {
    "type": "enabled",
    "maxReasoningEffort": "medium",
}
