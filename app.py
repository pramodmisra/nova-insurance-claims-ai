"""Nova Insurance Claims AI - Streamlit Application.

Hackathon entry for Amazon Nova AI Hackathon.
Uses Amazon Nova 2 Lite + Strands Agents SDK for agentic insurance claims processing.
"""

import streamlit as st
import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(__file__))

st.set_page_config(
    page_title="Nova Insurance Claims AI",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Custom CSS ────────────────────────────────────────────────────────────

st.markdown("""
<style>
    .pipeline-stage {
        padding: 12px 16px;
        border-radius: 8px;
        margin-bottom: 8px;
        border-left: 4px solid #ccc;
    }
    .stage-pending { border-left-color: #6c757d; background: #f8f9fa; }
    .stage-running { border-left-color: #ffc107; background: #fff8e1; }
    .stage-completed { border-left-color: #28a745; background: #e8f5e9; }
    .stage-failed { border-left-color: #dc3545; background: #fce4ec; }
    .metric-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 20px;
        border-radius: 12px;
        color: white;
        text-align: center;
    }
    .decision-approve { color: #28a745; font-weight: bold; font-size: 1.2em; }
    .decision-deny { color: #dc3545; font-weight: bold; font-size: 1.2em; }
    .decision-investigate { color: #ffc107; font-weight: bold; font-size: 1.2em; }
</style>
""", unsafe_allow_html=True)


# ── Data Loading ──────────────────────────────────────────────────────────

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")

if not os.path.exists(os.path.join(DATA_DIR, "claims.json")):
    st.warning("No data found. Generating synthetic data...")
    from src.generate_data import main as gen_main
    gen_main()
    st.rerun()


def load_data(name):
    with open(os.path.join(DATA_DIR, name)) as f:
        return json.load(f)


claims = load_data("claims.json")
applicants = load_data("applicants.json")
policies = load_data("policies.json")
medical = load_data("medical_records.json")


# ── Sidebar ───────────────────────────────────────────────────────────────

st.sidebar.image("https://img.icons8.com/3d-fluency/94/shield.png", width=60)
st.sidebar.title("Nova Claims AI")
st.sidebar.caption("Amazon Nova 2 Lite + Strands Agents")

mode = st.sidebar.radio(
    "Select Module",
    [
        "Multi-Agent Pipeline",
        "Claims Assessor",
        "Fraud Detector",
        "Underwriting",
        "Settlement Engine",
        "Compliance Check",
        "Risk Dashboard",
        "File New Claim",
        "Chat",
    ],
    index=0,
)

st.sidebar.markdown("---")
st.sidebar.markdown("**Portfolio Summary**")
active_policies = len([p for p in policies if p.get("status") == "Active"])
pending_claims = len([c for c in claims if c["status"] in ("Pending", "Under Review")])
high_risk = len([c for c in claims if c.get("fraud_indicators", 0) >= 3])
st.sidebar.metric("Applicants", len(applicants))
st.sidebar.metric("Active Policies", active_policies)
st.sidebar.metric("Pending Claims", pending_claims)
st.sidebar.metric("High Risk Flags", high_risk)


# ── Helpers ───────────────────────────────────────────────────────────────

def run_agent(agent_factory, prompt):
    """Create an agent, run the prompt, and return the response text."""
    try:
        agent = agent_factory()
        result = agent(prompt)
        return str(result)
    except Exception as e:
        return f"Error: {e}"


def show_explainable_ai(response_text, title="How Nova Decided"):
    """Display an Explainable AI panel with the agent's reasoning."""
    with st.expander(f"🧠 {title} (Explainable AI)", expanded=False):
        st.markdown("**AI Reasoning & Audit Trail**")
        st.info("This panel shows the AI agent's decision-making process for regulatory transparency and auditability.")
        st.markdown(response_text)
        st.caption(f"Model: Amazon Nova 2 Lite | Timestamp: {time.strftime('%Y-%m-%d %H:%M:%S UTC')}")


def show_decision_letter(letter_text):
    """Display a downloadable decision letter."""
    st.markdown("### 📄 Decision Letter")
    with st.container(border=True):
        st.markdown(letter_text)
    st.download_button(
        label="Download Decision Letter",
        data=letter_text,
        file_name=f"decision_letter_{time.strftime('%Y%m%d_%H%M%S')}.txt",
        mime="text/plain",
    )


# ══════════════════════════════════════════════════════════════════════════
#  FEATURE 1: Multi-Agent Pipeline with Visual Workflow
# ══════════════════════════════════════════════════════════════════════════

if mode == "Multi-Agent Pipeline":
    st.header("Multi-Agent Claims Pipeline")
    st.markdown("Process a claim through **5 specialized AI agents** in sequence. Watch each stage complete in real-time.")

    col_select, col_info = st.columns([1, 2])

    with col_select:
        claim_ids = [c["claim_id"] for c in claims]
        selected_claim = st.selectbox("Select Claim", claim_ids, key="pipeline_claim")
        claim = next(c for c in claims if c["claim_id"] == selected_claim)

        uploaded = st.file_uploader("Attach damage photo (optional)", type=["jpg", "jpeg", "png"], key="pipeline_img")
        img_path = None
        if uploaded:
            img_path = os.path.join(DATA_DIR, "pipeline_damage.jpg")
            with open(img_path, "wb") as f:
                f.write(uploaded.getvalue())
            st.image(uploaded, width=250)

    with col_info:
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Amount", f"${claim['claim_amount']:,.2f}")
        c2.metric("Type", claim["claim_type"])
        c3.metric("Fraud Score", f"{claim['fraud_indicators']}/5")
        c4.metric("Status", claim["status"])

    if st.button("▶ Run Full Pipeline", type="primary", use_container_width=True):
        from src.pipeline import run_claims_pipeline, PIPELINE_STAGES

        stage_icons = ["📋", "🔍", "⚖️", "📜", "✉️"]
        stage_containers = []
        progress_bar = st.progress(0, text="Initializing pipeline...")

        # Create visual stage tracker
        cols = st.columns(5)
        for i, (icon, name) in enumerate(zip(stage_icons, PIPELINE_STAGES)):
            with cols[i]:
                st.markdown(f"**{icon} Stage {i+1}**")
                st.caption(name)
                stage_containers.append(st.empty())
                stage_containers[i].warning("⏳ Pending")

        st.markdown("---")
        results_area = st.container()

        def progress_cb(idx, name, status):
            pct = int((idx + (1 if status == "completed" else 0.5)) / 5 * 100)
            progress_bar.progress(min(pct, 100), text=f"Stage {idx+1}: {name}")
            if status == "running":
                stage_containers[idx].info(f"🔄 Running...")
            elif status == "completed":
                stage_containers[idx].success(f"✅ Done")
            elif status == "failed":
                stage_containers[idx].error(f"❌ Failed")

        pipeline_result = run_claims_pipeline(
            claim_id=selected_claim,
            image_path=img_path,
            progress_callback=progress_cb,
        )

        progress_bar.progress(100, text="Pipeline complete!")

        with results_area:
            st.markdown("---")
            st.subheader("Pipeline Results")

            # Summary metrics
            mc1, mc2, mc3 = st.columns(3)
            mc1.metric("Total Duration", f"{pipeline_result.total_duration}s")
            mc2.metric("Stages Completed", f"{sum(1 for s in pipeline_result.stages if s.status.value == 'completed')}/5")
            mc3.metric("Claim ID", selected_claim)

            # Each stage result in expandable sections
            for i, stage in enumerate(pipeline_result.stages):
                icon = stage_icons[i]
                dur = f" ({stage.duration_secs}s)" if stage.duration_secs else ""
                with st.expander(f"{icon} Stage {i+1}: {stage.name}{dur}", expanded=(i == 2)):
                    st.markdown(stage.output)

            # Explainable AI panel
            full_reasoning = "\n\n---\n\n".join(
                f"**Stage {i+1}: {s.name}**\n\n{s.output}" for i, s in enumerate(pipeline_result.stages)
            )
            show_explainable_ai(full_reasoning, "Full Pipeline Reasoning Chain")

            # Decision Letter
            if pipeline_result.decision_letter:
                show_decision_letter(pipeline_result.decision_letter)


# ══════════════════════════════════════════════════════════════════════════
#  FEATURE 2: Claims Assessor (enhanced with Explainable AI)
# ══════════════════════════════════════════════════════════════════════════

elif mode == "Claims Assessor":
    st.header("Claims Assessment Agent")
    st.markdown("AI-powered single-agent claim assessment with explainable reasoning.")

    claim_ids = [c["claim_id"] for c in claims]
    selected = st.selectbox("Select Claim ID", claim_ids)
    claim = next(c for c in claims if c["claim_id"] == selected)

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Amount", f"${claim['claim_amount']:,.2f}")
    col2.metric("Type", claim["claim_type"])
    col3.metric("Fraud Score", f"{claim['fraud_indicators']}/5")
    col4.metric("Status", claim["status"])

    with st.expander("Raw Claim Data"):
        st.json(claim)

    uploaded = st.file_uploader("Upload damage photo (optional)", type=["jpg", "jpeg", "png"])
    img_path = None
    if uploaded:
        img_path = os.path.join(DATA_DIR, "uploaded_damage.jpg")
        with open(img_path, "wb") as f:
            f.write(uploaded.getvalue())
        st.image(uploaded, caption="Uploaded damage photo", width=400)

    if st.button("Assess This Claim", type="primary"):
        from src.agents import create_claims_assessor

        img_note = f" Also analyze the damage photo at {img_path}." if img_path else ""
        prompt = f"Assess insurance claim {selected}. Look up all relevant data for this claim and the associated applicant, check their policy, review medical records, find similar historical claims, and provide your full assessment with a recommendation.{img_note}"

        with st.spinner("Nova is assessing the claim..."):
            response = run_agent(create_claims_assessor, prompt)

        st.markdown("### Assessment Result")
        st.markdown(response)
        show_explainable_ai(response)


# ══════════════════════════════════════════════════════════════════════════
#  FEATURE 3: Fraud Detector
# ══════════════════════════════════════════════════════════════════════════

elif mode == "Fraud Detector":
    st.header("Fraud Detection Agent")

    tab1, tab2 = st.tabs(["Investigate Specific Claim", "Scan High-Risk Claims"])

    with tab1:
        claim_ids = [c["claim_id"] for c in claims]
        selected = st.selectbox("Select Claim ID to investigate", claim_ids, key="fraud_claim")

        if st.button("Investigate for Fraud", type="primary"):
            from src.agents import create_fraud_detector

            prompt = f"Investigate claim {selected} for potential fraud. Look up the claim, the applicant's profile, their full claim history, find similar claims, and assess all fraud indicators. Provide your fraud risk assessment."
            with st.spinner("Fraud analysis in progress..."):
                response = run_agent(create_fraud_detector, prompt)
            st.markdown("### Fraud Investigation Result")
            st.markdown(response)
            show_explainable_ai(response, "Fraud Detection Reasoning")

    with tab2:
        threshold = st.slider("Fraud indicator threshold", 1, 5, 3)
        flagged = [c for c in claims if c.get("fraud_indicators", 0) >= threshold]
        st.markdown(f"**{len(flagged)} claims** with fraud indicators >= {threshold}")

        if flagged:
            st.dataframe(
                [{
                    "Claim ID": c["claim_id"],
                    "Applicant": c["applicant_id"],
                    "Amount": f"${c['claim_amount']:,.2f}",
                    "Type": c["claim_type"],
                    "Fraud Score": c["fraud_indicators"],
                    "Status": c["status"],
                } for c in sorted(flagged, key=lambda x: x["fraud_indicators"], reverse=True)],
                use_container_width=True,
            )

        if st.button("Run AI Fraud Scan", type="primary"):
            from src.agents import create_fraud_detector

            prompt = f"Search for all claims with fraud indicators at or above {threshold}. For the top 5 most suspicious claims, provide a brief fraud assessment for each, and give an overall fraud exposure summary."
            with st.spinner("Scanning portfolio for fraud..."):
                response = run_agent(create_fraud_detector, prompt)
            st.markdown("### Fraud Scan Results")
            st.markdown(response)


# ══════════════════════════════════════════════════════════════════════════
#  FEATURE 4: Underwriting
# ══════════════════════════════════════════════════════════════════════════

elif mode == "Underwriting":
    st.header("Underwriting Agent")
    st.markdown("Evaluate an applicant for policy approval with explainable AI reasoning.")

    app_ids = [a["applicant_id"] for a in applicants]
    selected = st.selectbox("Select Applicant ID", app_ids)
    app = next(a for a in applicants if a["applicant_id"] == selected)

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Age", app["age"])
    col2.metric("Income", f"${app['income']:,}")
    col3.metric("Credit", app["credit_score"])
    col4.metric("Smoker", "Yes" if app["smoker"] else "No")

    with st.expander("Full Applicant Profile"):
        st.json(app)

    if st.button("Run Underwriting Assessment", type="primary"):
        from src.agents import create_underwriting_agent

        prompt = f"Evaluate applicant {selected} for insurance underwriting. Look up their full profile, medical records, any existing policies, and claim history. Provide your underwriting decision with detailed reasoning."
        with st.spinner("Running underwriting assessment..."):
            response = run_agent(create_underwriting_agent, prompt)
        st.markdown("### Underwriting Decision")
        st.markdown(response)
        show_explainable_ai(response, "Underwriting Reasoning")


# ══════════════════════════════════════════════════════════════════════════
#  FEATURE 5: Settlement Recommendation Engine
# ══════════════════════════════════════════════════════════════════════════

elif mode == "Settlement Engine":
    st.header("Settlement Recommendation Engine")
    st.markdown("AI-powered settlement amount recommendation based on historical data and claim analysis.")

    claim_ids = [c["claim_id"] for c in claims]
    selected = st.selectbox("Select Claim", claim_ids, key="settle_claim")
    claim = next(c for c in claims if c["claim_id"] == selected)

    col1, col2, col3 = st.columns(3)
    col1.metric("Claimed Amount", f"${claim['claim_amount']:,.2f}")
    col2.metric("Policy Limit", f"${claim['policy_limit']:,}")
    col3.metric("Claim Type", claim["claim_type"])

    if st.button("Generate Settlement Recommendation", type="primary"):
        from src.agents import create_settlement_agent

        prompt = f"""Recommend a settlement amount for claim {selected}.
Look up the claim details, find similar historical claims using find_similar_claims,
and get settlement benchmark data using get_settlement_comparables with claim type '{claim['claim_type']}' and amount {claim['claim_amount']}.
Provide your detailed settlement recommendation with confidence range."""

        with st.spinner("Analyzing settlement comparables..."):
            response = run_agent(create_settlement_agent, prompt)

        st.markdown("### Settlement Recommendation")
        st.markdown(response)
        show_explainable_ai(response, "Settlement Calculation Reasoning")


# ══════════════════════════════════════════════════════════════════════════
#  FEATURE 6: Regulatory Compliance Check
# ══════════════════════════════════════════════════════════════════════════

elif mode == "Compliance Check":
    st.header("Regulatory Compliance Checker")
    st.markdown("AI agent reviews claim decisions for regulatory compliance, bias, and legal risk.")

    claim_ids = [c["claim_id"] for c in claims]
    selected = st.selectbox("Select Claim to Review", claim_ids, key="comply_claim")
    claim = next(c for c in claims if c["claim_id"] == selected)

    col1, col2, col3 = st.columns(3)
    col1.metric("Amount", f"${claim['claim_amount']:,.2f}")
    col2.metric("Current Status", claim["status"])
    col3.metric("Fraud Score", f"{claim['fraud_indicators']}/5")

    if st.button("Run Compliance Review", type="primary"):
        from src.agents import create_compliance_agent

        prompt = f"""Review claim {selected} for regulatory compliance.
Look up the claim details, the applicant profile, their policy, and claim history.
Assess whether the current claim status of '{claim['status']}' is fair and compliant.
Check for bias, proper documentation, fair claims practices, and regulatory risks.
Provide your full compliance assessment."""

        with st.spinner("Running compliance review..."):
            response = run_agent(create_compliance_agent, prompt)

        st.markdown("### Compliance Review")
        st.markdown(response)
        show_explainable_ai(response, "Compliance Reasoning & Audit Trail")


# ══════════════════════════════════════════════════════════════════════════
#  FEATURE 7: Risk Dashboard with Charts
# ══════════════════════════════════════════════════════════════════════════

elif mode == "Risk Dashboard":
    st.header("Risk & Analytics Dashboard")

    import pandas as pd

    claims_df = pd.DataFrame(claims)
    apps_df = pd.DataFrame(applicants)
    policies_df = pd.DataFrame(policies)

    # ── Top KPI Row ───────────────────────────────────────────────────
    k1, k2, k3, k4, k5 = st.columns(5)
    total_exposure = claims_df["claim_amount"].sum()
    k1.metric("Total Exposure", f"${total_exposure:,.0f}")
    k2.metric("Avg Claim", f"${claims_df['claim_amount'].mean():,.0f}")
    k3.metric("Approval Rate", f"{len(claims_df[claims_df['status']=='Approved'])/len(claims_df)*100:.0f}%")
    k4.metric("High Risk Claims", len(claims_df[claims_df["fraud_indicators"] >= 3]))
    k5.metric("Avg Credit Score", f"{apps_df['credit_score'].mean():.0f}")

    st.markdown("---")

    # ── Charts Row 1 ──────────────────────────────────────────────────
    chart1, chart2 = st.columns(2)

    with chart1:
        st.subheader("Claims by Type")
        type_counts = claims_df["claim_type"].value_counts()
        st.bar_chart(type_counts)

    with chart2:
        st.subheader("Claims by Status")
        status_counts = claims_df["status"].value_counts()
        st.bar_chart(status_counts)

    # ── Charts Row 2 ──────────────────────────────────────────────────
    chart3, chart4 = st.columns(2)

    with chart3:
        st.subheader("Fraud Score Distribution")
        fraud_dist = claims_df["fraud_indicators"].value_counts().sort_index()
        st.bar_chart(fraud_dist)

    with chart4:
        st.subheader("Claim Amount Distribution")
        bins = pd.cut(claims_df["claim_amount"], bins=10)
        amount_dist = bins.value_counts().sort_index()
        amount_dist.index = [f"${int(i.left/1000)}K-${int(i.right/1000)}K" for i in amount_dist.index]
        st.bar_chart(amount_dist)

    # ── Charts Row 3 ──────────────────────────────────────────────────
    chart5, chart6 = st.columns(2)

    with chart5:
        st.subheader("Applicant Age Distribution")
        age_bins = pd.cut(apps_df["age"], bins=[20, 30, 40, 50, 60, 70, 80])
        age_dist = age_bins.value_counts().sort_index()
        age_dist.index = [f"{int(i.left)}-{int(i.right)}" for i in age_dist.index]
        st.bar_chart(age_dist)

    with chart6:
        st.subheader("Policy Status Breakdown")
        pol_status = policies_df["status"].value_counts()
        st.bar_chart(pol_status)

    # ── Risk Heatmap: Fraud by Claim Type ─────────────────────────────
    st.markdown("---")
    st.subheader("Fraud Risk by Claim Type")
    fraud_by_type = claims_df.groupby("claim_type")["fraud_indicators"].agg(["mean", "max", "count"])
    fraud_by_type.columns = ["Avg Fraud Score", "Max Fraud Score", "Total Claims"]
    fraud_by_type["Avg Fraud Score"] = fraud_by_type["Avg Fraud Score"].round(2)
    fraud_by_type = fraud_by_type.sort_values("Avg Fraud Score", ascending=False)
    st.dataframe(fraud_by_type, use_container_width=True)

    # ── High-Value Claims Table ───────────────────────────────────────
    st.subheader("Top 10 Highest-Value Claims")
    top_claims = claims_df.nlargest(10, "claim_amount")[
        ["claim_id", "applicant_id", "claim_type", "claim_amount", "fraud_indicators", "status"]
    ]
    top_claims["claim_amount"] = top_claims["claim_amount"].apply(lambda x: f"${x:,.2f}")
    st.dataframe(top_claims, use_container_width=True)

    # ── AI Portfolio Analysis ─────────────────────────────────────────
    st.markdown("---")
    if st.button("Generate AI Portfolio Analysis", type="primary"):
        from src.agents import create_portfolio_analyst

        prompt = "Analyze the full insurance portfolio. Get the portfolio summary, identify risk concentrations, analyze claims patterns, assess fraud exposure, and provide strategic recommendations."
        with st.spinner("AI analyzing portfolio..."):
            response = run_agent(create_portfolio_analyst, prompt)
        st.markdown("### AI Portfolio Analysis")
        st.markdown(response)


# ══════════════════════════════════════════════════════════════════════════
#  FEATURE 8: Smart Claim Intake Form
# ══════════════════════════════════════════════════════════════════════════

elif mode == "File New Claim":
    st.header("File a New Claim")
    st.markdown("Smart intake form with AI-powered validation and pre-fill.")

    # Step 1: Select applicant to pre-fill data
    app_ids = [f"{a['applicant_id']} - {a['name']}" for a in applicants]
    selected_app = st.selectbox("Select Policyholder", app_ids)
    app_id = selected_app.split(" - ")[0]
    app = next(a for a in applicants if a["applicant_id"] == app_id)

    # Find their policies
    app_policies = [p for p in policies if p["applicant_id"] == app_id]
    active_policies = [p for p in app_policies if p.get("status") == "Active"]

    if not active_policies:
        st.error(f"No active policies found for {app['name']}. Cannot file a claim.")
    else:
        st.success(f"Found {len(active_policies)} active policy(ies) for **{app['name']}**")

        # Pre-filled info
        with st.expander("Pre-filled Policyholder Information", expanded=True):
            col1, col2, col3 = st.columns(3)
            col1.text_input("Name", value=app["name"], disabled=True)
            col2.text_input("Email", value=app.get("email", ""), disabled=True)
            col3.text_input("Phone", value=app.get("phone", ""), disabled=True)

        # Policy selection
        policy_options = [f"{p['policy_id']} - {p['policy_type']} (${p['coverage_amount']:,})" for p in active_policies]
        selected_policy = st.selectbox("Select Policy", policy_options)
        policy_id = selected_policy.split(" - ")[0]
        policy = next(p for p in active_policies if p["policy_id"] == policy_id)

        st.info(f"Coverage: **${policy['coverage_amount']:,}** | Deductible: **${policy['deductible']:,}** | Expires: **{policy['end_date']}**")

        # Claim form
        st.markdown("### Claim Details")
        col1, col2 = st.columns(2)
        with col1:
            claim_type = st.selectbox("Claim Type", ["Auto Accident", "Medical", "Property Damage", "Theft", "Natural Disaster"])
            claim_amount = st.number_input("Claim Amount ($)", min_value=100.0, max_value=float(policy["coverage_amount"]), value=5000.0, step=500.0)
            incident_date = st.date_input("Incident Date")

        with col2:
            incident_location = st.text_input("Incident Location", placeholder="City, State")
            police_report = st.checkbox("Police report filed?")
            witnesses = st.number_input("Number of witnesses", min_value=0, max_value=10, value=0)

        description = st.text_area("Describe what happened", height=150, placeholder="Provide details about the incident...")

        uploaded_photo = st.file_uploader("Upload damage photo (optional)", type=["jpg", "jpeg", "png"], key="intake_photo")
        if uploaded_photo:
            st.image(uploaded_photo, width=300)

        # Validation warnings
        if claim_amount > policy["coverage_amount"]:
            st.error(f"Claim amount exceeds policy limit of ${policy['coverage_amount']:,}")
        if claim_amount > policy["coverage_amount"] * 0.8:
            st.warning("Claim amount is close to policy limit - this may trigger additional review.")

        col_submit, col_validate = st.columns(2)

        with col_validate:
            if st.button("AI Pre-Validate", type="secondary", use_container_width=True):
                from src.agents import create_claims_assessor

                prompt = f"""Pre-validate this new claim before submission:
- Policyholder: {app['name']} ({app_id})
- Policy: {policy_id} ({policy['policy_type']}, coverage ${policy['coverage_amount']:,}, deductible ${policy['deductible']:,})
- Policy expires: {policy['end_date']}
- Claim type: {claim_type}
- Claim amount: ${claim_amount:,.2f}
- Incident date: {incident_date}

Check if: the policy covers this claim type, the amount is within limits, and there are any issues.
Also look up the applicant's claim history for patterns.
Provide a brief validation result: READY TO SUBMIT or NEEDS ATTENTION with reasons."""

                with st.spinner("AI validating claim..."):
                    response = run_agent(create_claims_assessor, prompt)
                st.markdown("### Validation Result")
                st.markdown(response)

        with col_submit:
            if st.button("Submit Claim", type="primary", use_container_width=True):
                if not description:
                    st.error("Please provide a description of the incident.")
                else:
                    new_claim = {
                        "claim_id": f"CLM-{len(claims)+1:04d}",
                        "applicant_id": app_id,
                        "policy_id": policy_id,
                        "claim_type": claim_type,
                        "claim_amount": claim_amount,
                        "policy_limit": policy["coverage_amount"],
                        "claim_date": str(incident_date),
                        "status": "Pending",
                        "description": description,
                        "fraud_indicators": 0,
                        "damage_location": incident_location,
                        "witnesses": witnesses,
                        "police_report": police_report,
                    }
                    # Save to data
                    claims.append(new_claim)
                    with open(os.path.join(DATA_DIR, "claims.json"), "w") as f:
                        json.dump(claims, f, indent=2)

                    st.success(f"Claim **{new_claim['claim_id']}** submitted successfully! Status: Pending")
                    st.json(new_claim)
                    st.info("You can now process this claim through the Multi-Agent Pipeline.")


# ══════════════════════════════════════════════════════════════════════════
#  Chat
# ══════════════════════════════════════════════════════════════════════════

elif mode == "Chat":
    st.header("Chat with Claims AI")
    st.markdown("Ask anything about the insurance data. The AI agent has access to all applicants, policies, claims, medical records, and analytics tools.")

    if "messages" not in st.session_state:
        st.session_state.messages = []

    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    if prompt := st.chat_input("Ask about insurance data..."):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        from src.agents import create_claims_assessor

        with st.chat_message("assistant"):
            with st.spinner("Thinking..."):
                response = run_agent(create_claims_assessor, prompt)
            st.markdown(response)
        st.session_state.messages.append({"role": "assistant", "content": response})
