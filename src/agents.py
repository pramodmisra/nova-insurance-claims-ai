"""Insurance Claims AI Agents powered by Amazon Nova + Strands Agents SDK."""

import json
import base64
import os
import boto3
from strands import Agent, tool
from strands.models import BedrockModel

from src.config import (
    AWS_REGION, NOVA_MODEL_ID, INFERENCE_CONFIG, REASONING_CONFIG,
)

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data")

# ── Local data loaders (swap for DynamoDB in production) ──────────────────

def _load_json(filename):
    path = os.path.join(DATA_DIR, filename)
    if not os.path.exists(path):
        return []
    with open(path) as f:
        return json.load(f)


def _find(records, key, value):
    return [r for r in records if r.get(key) == value]


# ── Tools that the agents can call ────────────────────────────────────────

@tool
def lookup_applicant(applicant_id: str) -> str:
    """Look up an insurance applicant's profile by their ID (e.g. APP-0001).
    Returns full demographic, health, and financial information."""
    results = _find(_load_json("applicants.json"), "applicant_id", applicant_id)
    if not results:
        return json.dumps({"error": f"Applicant {applicant_id} not found"})
    return json.dumps(results[0], indent=2)


@tool
def lookup_policy(policy_id: str) -> str:
    """Look up an insurance policy by its ID (e.g. POL-0001).
    Returns coverage details, premium, deductible, and status."""
    results = _find(_load_json("policies.json"), "policy_id", policy_id)
    if not results:
        return json.dumps({"error": f"Policy {policy_id} not found"})
    return json.dumps(results[0], indent=2)


@tool
def lookup_policies_for_applicant(applicant_id: str) -> str:
    """Look up all policies belonging to an applicant."""
    results = _find(_load_json("policies.json"), "applicant_id", applicant_id)
    if not results:
        return json.dumps({"error": f"No policies found for {applicant_id}"})
    return json.dumps(results, indent=2)


@tool
def lookup_claim(claim_id: str) -> str:
    """Look up an insurance claim by its ID (e.g. CLM-0001).
    Returns claim details including amount, type, status, and fraud indicators."""
    results = _find(_load_json("claims.json"), "claim_id", claim_id)
    if not results:
        return json.dumps({"error": f"Claim {claim_id} not found"})
    return json.dumps(results[0], indent=2)


@tool
def lookup_claims_for_applicant(applicant_id: str) -> str:
    """Look up all claims filed by an applicant."""
    results = _find(_load_json("claims.json"), "applicant_id", applicant_id)
    if not results:
        return json.dumps({"error": f"No claims found for {applicant_id}"})
    return json.dumps(results, indent=2)


@tool
def lookup_medical_record(applicant_id: str) -> str:
    """Look up an applicant's medical records including conditions, medications, and vitals."""
    results = _find(_load_json("medical_records.json"), "applicant_id", applicant_id)
    if not results:
        return json.dumps({"error": f"No medical records found for {applicant_id}"})
    return json.dumps(results[0], indent=2)


@tool
def search_high_risk_claims(fraud_threshold: int = 3) -> str:
    """Find all claims with fraud indicators at or above the given threshold (0-5).
    Useful for identifying suspicious claims that need investigation."""
    claims = _load_json("claims.json")
    high_risk = [c for c in claims if c.get("fraud_indicators", 0) >= fraud_threshold]
    high_risk.sort(key=lambda c: c["fraud_indicators"], reverse=True)
    return json.dumps(high_risk[:20], indent=2)


@tool
def get_portfolio_summary() -> str:
    """Get a summary of the entire insurance portfolio including counts,
    averages, and risk distribution across all applicants, policies, and claims."""
    applicants = _load_json("applicants.json")
    policies = _load_json("policies.json")
    claims = _load_json("claims.json")

    if not applicants:
        return json.dumps({"error": "No data loaded. Run generate_data.py first."})

    total_claim_amount = sum(c.get("claim_amount", 0) for c in claims)
    pending_claims = [c for c in claims if c.get("status") in ("Pending", "Under Review")]
    high_fraud = [c for c in claims if c.get("fraud_indicators", 0) >= 3]

    return json.dumps({
        "total_applicants": len(applicants),
        "total_policies": len(policies),
        "total_claims": len(claims),
        "active_policies": len([p for p in policies if p.get("status") == "Active"]),
        "pending_claims": len(pending_claims),
        "avg_claim_amount": round(total_claim_amount / len(claims), 2) if claims else 0,
        "total_claim_exposure": round(total_claim_amount, 2),
        "high_risk_claims": len(high_fraud),
        "avg_applicant_age": round(sum(a.get("age", 0) for a in applicants) / len(applicants), 1),
        "smoker_pct": round(len([a for a in applicants if a.get("smoker")]) / len(applicants) * 100, 1),
        "avg_credit_score": round(sum(a.get("credit_score", 0) for a in applicants) / len(applicants), 0),
    }, indent=2)


@tool
def find_similar_claims(claim_id: str) -> str:
    """Find historical claims similar to the given claim based on type, amount range,
    and applicant profile. Returns up to 5 comparable claims with their outcomes.
    Useful for benchmarking settlement amounts and detecting patterns."""
    claims = _load_json("claims.json")
    target = next((c for c in claims if c.get("claim_id") == claim_id), None)
    if not target:
        return json.dumps({"error": f"Claim {claim_id} not found"})

    same_type = [c for c in claims if c["claim_type"] == target["claim_type"] and c["claim_id"] != claim_id]
    amount = target.get("claim_amount", 0)
    lo, hi = amount * 0.5, amount * 1.5

    similar = [c for c in same_type if lo <= c.get("claim_amount", 0) <= hi]
    similar.sort(key=lambda c: abs(c.get("claim_amount", 0) - amount))
    similar = similar[:5]

    if not similar:
        return json.dumps({"message": "No similar claims found", "target_type": target["claim_type"]})

    amounts = [c["claim_amount"] for c in similar]
    approved = [c for c in similar if c.get("status") == "Approved"]

    return json.dumps({
        "target_claim": claim_id,
        "target_type": target["claim_type"],
        "target_amount": amount,
        "similar_claims": similar,
        "stats": {
            "count": len(similar),
            "avg_amount": round(sum(amounts) / len(amounts), 2),
            "min_amount": round(min(amounts), 2),
            "max_amount": round(max(amounts), 2),
            "approval_rate": f"{len(approved)}/{len(similar)}",
            "avg_fraud_score": round(sum(c.get("fraud_indicators", 0) for c in similar) / len(similar), 1),
        },
    }, indent=2)


@tool
def get_settlement_comparables(claim_type: str, claim_amount: float) -> str:
    """Get settlement benchmark data for a given claim type and amount.
    Analyzes all historical claims of the same type to provide statistical
    ranges for settlement amounts, approval rates, and processing times."""
    claims = _load_json("claims.json")
    same_type = [c for c in claims if c["claim_type"] == claim_type]
    if not same_type:
        return json.dumps({"error": f"No claims of type '{claim_type}' found"})

    amounts = [c["claim_amount"] for c in same_type]
    approved = [c for c in same_type if c.get("status") == "Approved"]
    denied = [c for c in same_type if c.get("status") == "Denied"]
    approved_amounts = [c["claim_amount"] for c in approved] if approved else [0]

    import statistics
    return json.dumps({
        "claim_type": claim_type,
        "requested_amount": claim_amount,
        "historical_stats": {
            "total_claims": len(same_type),
            "approval_rate_pct": round(len(approved) / len(same_type) * 100, 1) if same_type else 0,
            "denial_rate_pct": round(len(denied) / len(same_type) * 100, 1) if same_type else 0,
            "avg_claim_amount": round(statistics.mean(amounts), 2),
            "median_claim_amount": round(statistics.median(amounts), 2),
            "std_dev": round(statistics.stdev(amounts), 2) if len(amounts) > 1 else 0,
            "avg_approved_amount": round(statistics.mean(approved_amounts), 2),
            "percentile_25": round(sorted(amounts)[len(amounts) // 4], 2),
            "percentile_75": round(sorted(amounts)[3 * len(amounts) // 4], 2),
        },
        "recommendation": {
            "suggested_range_low": round(statistics.mean(approved_amounts) * 0.85, 2),
            "suggested_range_high": round(statistics.mean(approved_amounts) * 1.15, 2),
            "confidence": "High" if len(same_type) > 20 else "Medium" if len(same_type) > 10 else "Low",
        },
    }, indent=2)


@tool
def analyze_damage_image(image_path: str) -> str:
    """Analyze a damage photo (vehicle, property, etc.) using Amazon Nova's
    multimodal capabilities. Provide the local file path to the image.
    Returns a detailed damage assessment."""
    if not os.path.exists(image_path):
        return json.dumps({"error": f"Image file not found: {image_path}"})

    ext = image_path.rsplit(".", 1)[-1].lower()
    fmt_map = {"jpg": "jpeg", "jpeg": "jpeg", "png": "png", "gif": "gif", "webp": "webp"}
    fmt = fmt_map.get(ext, "jpeg")

    with open(image_path, "rb") as f:
        img_bytes = base64.b64encode(f.read()).decode("utf-8")

    client = boto3.client("bedrock-runtime", region_name=AWS_REGION)
    body = {
        "schemaVersion": "messages-v1",
        "system": [{"text": "You are an expert insurance damage assessor. Analyze the image and provide a detailed assessment of visible damage, estimated severity (Minor/Moderate/Severe/Total Loss), affected areas, and estimated repair cost range."}],
        "messages": [{
            "role": "user",
            "content": [
                {"image": {"format": fmt, "source": {"bytes": img_bytes}}},
                {"text": "Analyze this damage image for an insurance claim. Describe the damage, severity, and estimated repair costs."}
            ]
        }],
        "inferenceConfig": {"maxTokens": 2000, "temperature": 0.3}
    }

    response = client.invoke_model(
        modelId="us.amazon.nova-lite-v1:0",
        body=json.dumps(body),
    )
    result = json.loads(response["body"].read())
    output_text = result["output"]["message"]["content"][0]["text"]
    return output_text


# ── Agent Definitions ─────────────────────────────────────────────────────

def _nova_model():
    """Create a BedrockModel instance for Amazon Nova 2 Lite."""
    return BedrockModel(
        model_id=NOVA_MODEL_ID,
        region_name=AWS_REGION,
        temperature=INFERENCE_CONFIG["temperature"],
        top_p=INFERENCE_CONFIG["topP"],
        max_tokens=INFERENCE_CONFIG["maxTokens"],
        streaming=True,
    )


SHARED_TOOLS = [
    lookup_applicant,
    lookup_policy,
    lookup_policies_for_applicant,
    lookup_claim,
    lookup_claims_for_applicant,
    lookup_medical_record,
    search_high_risk_claims,
    get_portfolio_summary,
    find_similar_claims,
    get_settlement_comparables,
]


def create_claims_assessor() -> Agent:
    """Agent that reviews a claim end-to-end: validates documents, checks policy,
    assesses damage, detects fraud, and makes a recommendation."""
    return Agent(
        model=_nova_model(),
        system_prompt="""You are an expert Insurance Claims Assessor AI Agent.

Your job is to thoroughly evaluate insurance claims by:
1. Looking up the claim details and the associated applicant profile
2. Checking the applicant's policy coverage and status
3. Reviewing medical records if relevant
4. Analyzing the claim for fraud indicators
5. Cross-referencing claim history for patterns
6. Providing a final recommendation: APPROVE, DENY, or INVESTIGATE

For every claim you assess, provide:
- Claim Summary (type, amount, date)
- Policy Validation (is the policy active? does coverage apply?)
- Risk Factors (fraud score, suspicious patterns, claim history)
- Medical Relevance (if applicable)
- Your Recommendation with detailed reasoning
- Confidence Score (0-100)

Always use the available tools to gather real data before making your assessment.
Be thorough but concise. Flag any red flags clearly.""",
        tools=[*SHARED_TOOLS, analyze_damage_image],
    )


def create_fraud_detector() -> Agent:
    """Agent specialized in detecting fraudulent claims."""
    return Agent(
        model=_nova_model(),
        system_prompt="""You are a Fraud Detection Specialist AI Agent for insurance claims.

Your expertise is identifying fraudulent or suspicious insurance claims by:
1. Analyzing fraud indicator scores
2. Checking claim timing relative to policy start (claims filed very soon after policy start are suspicious)
3. Comparing claim amounts to policy limits (claims near the limit are suspicious)
4. Looking at applicant claim history (frequent claimants are suspicious)
5. Identifying inconsistencies in claim descriptions
6. Cross-referencing multiple data sources

For every analysis, provide:
- Fraud Risk Score (0-100)
- Red Flags Identified (specific, evidence-based)
- Pattern Analysis (timing, amounts, frequency)
- Investigation Priority (Low / Medium / High / Critical)
- Recommended Actions (approve, investigate further, deny, refer to SIU)

Always back your findings with data from the tools. Never make accusations without evidence.""",
        tools=SHARED_TOOLS,
    )


def create_underwriting_agent() -> Agent:
    """Agent that makes underwriting decisions for new applications."""
    return Agent(
        model=_nova_model(),
        system_prompt="""You are a Senior Underwriting AI Agent for insurance applications.

Your job is to evaluate insurance applications and make underwriting decisions by:
1. Reviewing the applicant's full profile (demographics, income, occupation)
2. Analyzing medical records and health risk factors
3. Evaluating financial stability (credit score, income)
4. Checking claim history
5. Assessing family history risk factors
6. Calculating risk-adjusted premium recommendations

For every application, provide:
- Decision: APPROVE / CONDITIONAL APPROVE / DECLINE
- Risk Score (0-100, where 100 = highest risk)
- Risk Category: Low / Medium / High / Very High
- Key Risk Factors identified
- Premium Adjustment Recommendation (percentage)
- Conditions (if conditional approval)
- Detailed reasoning for your decision

Use all available tools to gather data. Be fair, thorough, and transparent in your reasoning.""",
        tools=SHARED_TOOLS,
    )


def create_portfolio_analyst() -> Agent:
    """Agent that provides portfolio-level analytics and insights."""
    return Agent(
        model=_nova_model(),
        system_prompt="""You are an Insurance Portfolio Analytics AI Agent.

Your role is to analyze the overall insurance portfolio and provide business intelligence:
1. Portfolio health metrics and trends
2. Risk distribution across the book of business
3. Claims pattern analysis
4. Fraud exposure assessment
5. Profitability indicators
6. Strategic recommendations

Use the portfolio summary and individual data lookup tools to build your analysis.
Present findings in a clear, executive-summary style with actionable recommendations.""",
        tools=SHARED_TOOLS,
    )


def create_compliance_agent() -> Agent:
    """Agent specialized in regulatory compliance review of claim decisions."""
    return Agent(
        model=_nova_model(),
        system_prompt="""You are a Regulatory Compliance Officer for an insurance company.

Your job is to review claim decisions for compliance with insurance regulations:
1. Fair Claims Settlement Practices - is the decision fair and evidence-based?
2. Anti-Discrimination - no bias based on protected characteristics
3. Timely Processing - handled within regulatory timeframes?
4. Proper Documentation - sufficient evidence for the decision?
5. Coverage Interpretation - policy interpreted fairly for the policyholder?
6. Bad Faith Assessment - could the decision be seen as acting in bad faith?
7. State/Federal Regulations - does the decision comply with applicable laws?

For every review provide:
- COMPLIANCE STATUS: PASS / CONDITIONAL PASS / FAIL
- REGULATORY FLAGS: specific issues found
- BIAS CHECK: assessment of fairness across protected classes
- DOCUMENTATION STATUS: adequate / needs improvement
- RISK OF DISPUTE: Low / Medium / High
- RECOMMENDATIONS: changes needed before finalizing

Be thorough - protecting the company from regulatory action is critical.""",
        tools=SHARED_TOOLS,
    )


def create_settlement_agent() -> Agent:
    """Agent specialized in recommending optimal settlement amounts."""
    return Agent(
        model=_nova_model(),
        system_prompt="""You are a Settlement Recommendation Specialist for insurance claims.

Your job is to recommend an optimal settlement amount by:
1. Analyzing the claim details and damage assessment
2. Reviewing policy coverage limits and deductibles
3. Comparing to similar historical claims using the settlement comparables tool
4. Considering the fraud risk level
5. Factoring in policy terms and conditions

For every recommendation provide:
- RECOMMENDED SETTLEMENT: exact dollar amount
- SETTLEMENT RANGE: low-end to high-end with confidence level
- CALCULATION BREAKDOWN: how you arrived at the number
- COMPARABLE CLAIMS: what similar claims settled for
- POLICY IMPACT: how this affects deductible, limits, future premiums
- CONFIDENCE LEVEL: Low / Medium / High (with percentage)

Always use the get_settlement_comparables and find_similar_claims tools for data-driven recommendations.""",
        tools=SHARED_TOOLS,
    )
