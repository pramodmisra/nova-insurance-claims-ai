"""Multi-Agent Claims Processing Pipeline.

Orchestrates a claim through multiple specialized agents in sequence:
  1. Document Review & Data Gathering
  2. Fraud Detection & Risk Scoring
  3. Final Decision & Settlement Recommendation
  4. Compliance Check
  5. Decision Letter Generation

Each stage produces a structured result that feeds into the next stage.
"""

import json
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional

from strands import Agent
from strands.models import BedrockModel

from src.config import AWS_REGION, NOVA_MODEL_ID, INFERENCE_CONFIG
from src.agents import (
    SHARED_TOOLS,
    analyze_damage_image,
    find_similar_claims,
    _nova_model,
)


class StageStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class StageResult:
    name: str
    status: StageStatus = StageStatus.PENDING
    output: str = ""
    reasoning: str = ""
    started_at: Optional[float] = None
    completed_at: Optional[float] = None
    duration_secs: float = 0.0
    tools_used: list = field(default_factory=list)


@dataclass
class PipelineResult:
    claim_id: str
    stages: list = field(default_factory=list)
    started_at: Optional[float] = None
    completed_at: Optional[float] = None
    final_decision: str = ""
    settlement_range: str = ""
    compliance_notes: str = ""
    decision_letter: str = ""

    @property
    def total_duration(self):
        if self.started_at and self.completed_at:
            return round(self.completed_at - self.started_at, 1)
        return 0.0

    @property
    def current_stage_idx(self):
        for i, s in enumerate(self.stages):
            if s.status in (StageStatus.RUNNING, StageStatus.PENDING):
                return i
        return len(self.stages)


PIPELINE_STAGES = [
    "Document Review & Data Gathering",
    "Fraud Detection & Risk Analysis",
    "Decision & Settlement Recommendation",
    "Regulatory Compliance Check",
    "Decision Letter Generation",
]


def _run_stage(agent: Agent, prompt: str, stage: StageResult) -> StageResult:
    """Run a single pipeline stage with timing and error handling."""
    stage.status = StageStatus.RUNNING
    stage.started_at = time.time()
    try:
        result = agent(prompt)
        stage.output = str(result)
        stage.status = StageStatus.COMPLETED
    except Exception as e:
        stage.output = f"Error in {stage.name}: {e}"
        stage.status = StageStatus.FAILED
    stage.completed_at = time.time()
    stage.duration_secs = round(stage.completed_at - stage.started_at, 1)
    return stage


def run_claims_pipeline(
    claim_id: str,
    image_path: str = None,
    progress_callback=None,
) -> PipelineResult:
    """Run the full multi-agent claims processing pipeline.

    Args:
        claim_id: The claim ID to process (e.g. CLM-0001)
        image_path: Optional path to a damage photo
        progress_callback: Optional callable(stage_index, stage_name, status)
    """
    pipeline = PipelineResult(
        claim_id=claim_id,
        stages=[StageResult(name=name) for name in PIPELINE_STAGES],
        started_at=time.time(),
    )

    def notify(idx, status):
        if progress_callback:
            progress_callback(idx, pipeline.stages[idx].name, status)

    # ── Stage 1: Document Review & Data Gathering ─────────────────────────
    notify(0, "running")
    stage1_agent = Agent(
        model=_nova_model(),
        system_prompt="""You are a Document Review Specialist. Your ONLY job in this pipeline stage is to:
1. Look up the claim details
2. Look up the applicant's profile
3. Look up all policies for the applicant
4. Look up the applicant's medical records
5. Look up the applicant's full claim history
6. Find similar historical claims

Compile ALL the data you find into a structured summary with these sections:
- CLAIM DETAILS: (type, amount, date, status, description)
- APPLICANT PROFILE: (name, age, occupation, income, health status, credit score)
- POLICY DETAILS: (policy type, coverage, premium, status, dates)
- MEDICAL SUMMARY: (conditions, medications, risk factors)
- CLAIM HISTORY: (number of past claims, patterns)
- SIMILAR CLAIMS: (comparable historical claims and their outcomes)

Be thorough. The next agents in the pipeline depend on your data gathering.""",
        tools=[*SHARED_TOOLS, find_similar_claims, analyze_damage_image],
    )

    img_note = f" Also analyze the damage photo at {image_path}." if image_path else ""
    stage1_prompt = f"Gather all data for claim {claim_id}. Look up the claim, the applicant, their policies, medical records, claim history, and find similar past claims.{img_note}"

    _run_stage(stage1_agent, stage1_prompt, pipeline.stages[0])
    notify(0, pipeline.stages[0].status.value)

    gathered_data = pipeline.stages[0].output

    # ── Stage 2: Fraud Detection & Risk Analysis ──────────────────────────
    notify(1, "running")
    stage2_agent = Agent(
        model=_nova_model(),
        system_prompt="""You are a Fraud Detection Specialist in a claims processing pipeline.
You receive gathered data from the previous stage. Your job is to:
1. Analyze fraud indicators in the claim
2. Check timing patterns (claim filed soon after policy start = suspicious)
3. Compare claim amount to policy limit (near-limit claims = suspicious)
4. Review claim history for frequency patterns
5. Check for inconsistencies

Provide a structured fraud analysis:
- FRAUD RISK SCORE: (0-100)
- RED FLAGS: (list specific evidence-based concerns)
- PATTERN ANALYSIS: (timing, amounts, frequency)
- RISK LEVEL: (Low / Medium / High / Critical)
- RECOMMENDATION: (Clear / Needs Investigation / Suspicious / Likely Fraud)

You may use tools to look up additional data if needed.""",
        tools=SHARED_TOOLS,
    )

    stage2_prompt = f"""Analyze claim {claim_id} for fraud based on this gathered data:

{gathered_data}

Provide your fraud risk assessment. Use tools to look up any additional data you need."""

    _run_stage(stage2_agent, stage2_prompt, pipeline.stages[1])
    notify(1, pipeline.stages[1].status.value)

    fraud_analysis = pipeline.stages[1].output

    # ── Stage 3: Decision & Settlement Recommendation ─────────────────────
    notify(2, "running")
    stage3_agent = Agent(
        model=_nova_model(),
        system_prompt="""You are a Senior Claims Adjudicator in a claims processing pipeline.
You receive data gathering results AND fraud analysis from previous stages.
Your job is to make the FINAL DECISION on the claim:

1. Weigh the evidence from data review and fraud analysis
2. Check policy coverage applies to this claim type
3. Verify the claim is within policy limits
4. Consider the fraud risk assessment
5. Determine the appropriate action

Provide a structured decision:
- DECISION: (APPROVE / DENY / INVESTIGATE FURTHER)
- CONFIDENCE: (0-100%)
- APPROVED AMOUNT: (if approving, the recommended settlement amount)
- SETTLEMENT RANGE: ($X,XXX - $X,XXX with confidence interval)
- KEY FACTORS: (top 3-5 factors that drove your decision)
- CONDITIONS: (any conditions on the approval)
- REASONING: (detailed explanation of your decision logic)

Be fair, thorough, and transparent.""",
        tools=SHARED_TOOLS,
    )

    stage3_prompt = f"""Make a final decision on claim {claim_id}.

DATA GATHERED:
{gathered_data}

FRAUD ANALYSIS:
{fraud_analysis}

Provide your decision with settlement recommendation."""

    _run_stage(stage3_agent, stage3_prompt, pipeline.stages[2])
    notify(2, pipeline.stages[2].status.value)

    decision_output = pipeline.stages[2].output
    pipeline.final_decision = decision_output

    # ── Stage 4: Regulatory Compliance Check ──────────────────────────────
    notify(3, "running")
    stage4_agent = Agent(
        model=_nova_model(),
        system_prompt="""You are a Regulatory Compliance Officer reviewing an insurance claim decision.
Your job is to ensure the decision complies with insurance regulations:

1. Fair Claims Settlement Practices - was the decision fair and evidence-based?
2. Anti-Discrimination - no bias based on protected characteristics (age, gender, race)
3. Timely Processing - was the claim handled within regulatory timeframes?
4. Proper Documentation - is there sufficient evidence for the decision?
5. Coverage Interpretation - was the policy interpreted fairly for the policyholder?
6. Bad Faith Assessment - could this decision be seen as acting in bad faith?

Provide a structured compliance review:
- COMPLIANCE STATUS: (PASS / CONDITIONAL PASS / FAIL)
- REGULATORY FLAGS: (any issues found)
- BIAS CHECK: (assessment of fairness)
- DOCUMENTATION STATUS: (adequate / needs improvement)
- RECOMMENDATIONS: (any changes needed before finalizing)
- RISK OF DISPUTE: (Low / Medium / High)

Be thorough - protecting the company from regulatory action is critical.""",
        tools=SHARED_TOOLS,
    )

    stage4_prompt = f"""Review this claim decision for regulatory compliance:

CLAIM: {claim_id}

DATA GATHERED:
{gathered_data}

FRAUD ANALYSIS:
{fraud_analysis}

DECISION:
{decision_output}

Check for compliance issues, bias, and regulatory risks."""

    _run_stage(stage4_agent, stage4_prompt, pipeline.stages[3])
    notify(3, pipeline.stages[3].status.value)

    compliance_output = pipeline.stages[3].output
    pipeline.compliance_notes = compliance_output

    # ── Stage 5: Decision Letter Generation ───────────────────────────────
    notify(4, "running")
    stage5_agent = Agent(
        model=_nova_model(),
        system_prompt="""You are a Professional Communications Specialist for an insurance company.
Your job is to generate a formal decision letter to the policyholder.

The letter should be:
- Professional and empathetic in tone
- Clear about the decision (approved/denied/under investigation)
- Specific about the claim details and amounts
- Transparent about the reasoning (without revealing internal fraud scores)
- Include next steps for the policyholder
- Include appeal rights if denied
- Include contact information for questions

Format it as a proper business letter with:
- Date
- Reference numbers (claim ID, policy ID)
- Salutation
- Body paragraphs
- Next steps
- Closing
- Signature block (from "Claims Department, Nova Insurance AI")

Do NOT reveal internal fraud scores or investigation details to the policyholder.""",
        tools=SHARED_TOOLS,
    )

    stage5_prompt = f"""Generate a professional decision letter to the policyholder for claim {claim_id}.

DECISION:
{decision_output}

COMPLIANCE NOTES:
{compliance_output}

Look up the applicant's name and address for the letter header. Write the letter."""

    _run_stage(stage5_agent, stage5_prompt, pipeline.stages[4])
    notify(4, pipeline.stages[4].status.value)

    pipeline.decision_letter = pipeline.stages[4].output
    pipeline.completed_at = time.time()

    return pipeline
