# Nova Insurance Claims AI

**Agentic AI-powered insurance claims processing platform built with Amazon Nova 2 Lite and Strands Agents SDK.**

> Entry for the [Amazon Nova AI Hackathon](https://amazon-nova.devpost.com/) | Category: **Agentic AI**

![Python](https://img.shields.io/badge/Python-3.11-blue)
![Amazon Nova](https://img.shields.io/badge/Amazon%20Nova-2%20Lite-orange)
![Strands Agents](https://img.shields.io/badge/Strands%20Agents-SDK-green)
![Streamlit](https://img.shields.io/badge/Streamlit-UI-red)

## Live Demo

**[Try it on Hugging Face Spaces](https://pramodmisra-nova-insurance-claims-ai.hf.space)**

## What It Does

Nova Insurance Claims AI automates the entire insurance claims lifecycle using a **multi-agent AI pipeline**. Each claim flows through 5 specialized AI agents that collaborate to deliver transparent, explainable decisions:

```
Claim Filed --> Document Review --> Fraud Detection --> Decision --> Compliance Check --> Letter Generated
    [Agent 1]        [Agent 2]        [Agent 3]        [Agent 4]        [Agent 5]
```

### Key Features

| Feature | Description |
|---------|-------------|
| **Multi-Agent Pipeline** | 5-stage autonomous pipeline with visual progress tracking |
| **Explainable AI** | Every decision shows Nova's reasoning chain for regulatory transparency |
| **Fraud Detection** | Pattern-based fraud analysis with risk scoring (0-100) |
| **Settlement Engine** | Data-driven settlement recommendations with confidence intervals |
| **Compliance Checker** | Automated regulatory compliance review and bias detection |
| **Risk Dashboard** | Interactive charts for portfolio analytics and risk visualization |
| **Smart Claim Intake** | AI-powered form with pre-fill and real-time validation |
| **Decision Letters** | Auto-generated professional policyholder notifications |

## How It Uses Amazon Nova

- **Amazon Nova 2 Lite** (`us.amazon.nova-2-lite-v1:0`) via Amazon Bedrock for all AI reasoning
- **Multimodal capabilities** for damage photo analysis (image + text)
- **Extended thinking/reasoning** for transparent decision-making
- **Strands Agents SDK** (AWS open-source) for agent orchestration with 11 custom tools
- **6 specialized AI agents**, each with distinct expertise and system prompts

## Architecture

```
                    Streamlit UI (9 modules)
                           |
                    Strands Agents SDK
                           |
            +----+----+----+----+----+----+
            |    |    |    |    |    |    |
         Claims Fraud Under- Settle- Comp- Port-
         Assess Detect writing ment  liance folio
            |    |    |    |    |    |    |
            +----+----+----+----+----+----+
                           |
                  11 Custom Tools
            (data lookup, similarity search,
             settlement benchmarks, damage
             photo analysis, portfolio stats)
                           |
                Amazon Nova 2 Lite (Bedrock)
```

## Dataset

Uses real insurance claims data from [Kaggle](https://www.kaggle.com/datasets/mexwell/insurance-claims):
- **1,000 real claims** with 40 features each
- **247 fraud cases** (24.7%) with fraud labels
- Incident types: Multi-vehicle Collision, Single Vehicle Collision, Vehicle Theft, Parked Car
- Rich details: severity, bodily injuries, vehicle info, policy terms, witness counts

## Quick Start

### Prerequisites
- Python 3.10+
- AWS account with Bedrock access to Amazon Nova models

### Setup

```bash
# Clone
git clone https://github.com/pramodmisra/nova-insurance-claims-ai.git
cd nova-insurance-claims-ai

# Virtual environment
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Configure AWS credentials
export AWS_ACCESS_KEY_ID="your_key"
export AWS_SECRET_ACCESS_KEY="your_secret"
export AWS_SESSION_TOKEN="your_token"  # if using temporary credentials
export AWS_DEFAULT_REGION="us-east-1"

# Load real data (or use python -m src.generate_data for synthetic)
python -m src.load_real_data

# Run
streamlit run app.py
```

### Docker

```bash
docker build -t nova-claims-ai .
docker run -p 7860:7860 \
  -e AWS_ACCESS_KEY_ID=... \
  -e AWS_SECRET_ACCESS_KEY=... \
  -e AWS_SESSION_TOKEN=... \
  -e AWS_DEFAULT_REGION=us-east-1 \
  nova-claims-ai
```

## Project Structure

```
nova-insurance-claims-ai/
├── app.py                  # Streamlit UI (9 modules)
├── Dockerfile              # HF Spaces / Docker deployment
├── requirements.txt        # Python dependencies
├── src/
│   ├── config.py           # AWS/Nova configuration
│   ├── agents.py           # 6 AI agents + 11 tools
│   ├── pipeline.py         # Multi-agent pipeline orchestrator
│   ├── generate_data.py    # Synthetic data generator
│   └── load_real_data.py   # Kaggle dataset converter
└── data/
    ├── applicants.json     # 1,000 policyholder profiles
    ├── policies.json       # 1,000 insurance policies
    ├── claims.json         # 1,000 claims with fraud labels
    ├── medical_records.json# 1,000 medical records
    └── raw/
        └── insurance_claims.csv  # Source Kaggle dataset
```

## Tech Stack

| Component | Technology |
|-----------|-----------|
| AI Model | Amazon Nova 2 Lite via Amazon Bedrock |
| Agent Framework | Strands Agents SDK (AWS open-source) |
| Frontend | Streamlit |
| Data | Kaggle Insurance Claims (1,000 real records) |
| Deployment | Hugging Face Spaces (Docker) |
| Language | Python 3.11 |

## Author

**Pramod Misra** - Analytics leader in insurance AI
[LinkedIn](https://www.linkedin.com/in/pramodmisra/) | [GitHub](https://github.com/pramodmisra)

#AmazonNova
