"""Generate synthetic insurance data for local development and demo."""

import json
import random
import os
from datetime import datetime, timedelta
from faker import Faker
from decimal import Decimal

fake = Faker()

OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "..", "data")


def decimal_to_float(obj):
    if isinstance(obj, Decimal):
        return float(obj)
    elif isinstance(obj, dict):
        return {k: decimal_to_float(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [decimal_to_float(v) for v in obj]
    return obj


def generate_applicants(count=100):
    occupations = [
        "Software Engineer", "Teacher", "Doctor", "Lawyer", "Nurse",
        "Manager", "Sales Rep", "Accountant", "Engineer", "Consultant",
        "Construction Worker", "Truck Driver", "Firefighter", "Chef",
    ]
    health_statuses = ["Excellent", "Good", "Fair", "Poor"]

    applicants = []
    for i in range(count):
        age = random.randint(21, 70)
        applicants.append({
            "applicant_id": f"APP-{i+1:04d}",
            "name": fake.name(),
            "age": age,
            "gender": random.choice(["Male", "Female"]),
            "occupation": random.choice(occupations),
            "income": random.randint(30000, 200000),
            "health_status": random.choice(health_statuses),
            "smoker": random.choice([True, False]),
            "bmi": round(random.uniform(18.5, 38.0), 1),
            "exercise_frequency": random.choice(["Never", "Rarely", "Weekly", "Daily"]),
            "family_history": {
                "heart_disease": random.choice([True, False]),
                "diabetes": random.choice([True, False]),
                "cancer": random.choice([True, False]),
            },
            "previous_claims": random.randint(0, 5),
            "credit_score": random.randint(300, 850),
            "address": fake.address().replace("\n", ", "),
            "phone": fake.phone_number(),
            "email": fake.email(),
            "created_date": fake.date_between(start_date="-2y", end_date="today").isoformat(),
        })
    return applicants


def generate_policies(applicants):
    policy_types = ["Auto", "Home", "Health", "Life", "Disability"]
    policies = []
    for i, app in enumerate(applicants):
        start = fake.date_between(start_date="-3y", end_date="-6m")
        end = start + timedelta(days=365)
        policies.append({
            "policy_id": f"POL-{i+1:04d}",
            "applicant_id": app["applicant_id"],
            "policy_type": random.choice(policy_types),
            "coverage_amount": random.choice([50000, 100000, 250000, 500000, 1000000]),
            "premium_monthly": round(random.uniform(50, 500), 2),
            "deductible": random.choice([500, 1000, 2000, 5000]),
            "start_date": start.isoformat(),
            "end_date": end.isoformat(),
            "status": random.choice(["Active", "Active", "Active", "Expired", "Cancelled"]),
        })
    return policies


def generate_claims(applicants, policies, count=200):
    claim_types = ["Auto Accident", "Medical", "Property Damage", "Theft", "Natural Disaster"]
    claims = []
    for i in range(count):
        app = random.choice(applicants)
        matching_policies = [p for p in policies if p["applicant_id"] == app["applicant_id"]]
        policy = random.choice(matching_policies) if matching_policies else random.choice(policies)

        claim_date = fake.date_between(start_date="-1y", end_date="today")
        days_since_policy = (claim_date - datetime.fromisoformat(policy["start_date"]).date()).days

        fraud_score = random.choices([0, 1, 2, 3, 4, 5], weights=[30, 25, 20, 12, 8, 5])[0]

        claims.append({
            "claim_id": f"CLM-{i+1:04d}",
            "applicant_id": app["applicant_id"],
            "policy_id": policy["policy_id"],
            "claim_type": random.choice(claim_types),
            "claim_amount": round(random.uniform(500, policy["coverage_amount"] * 0.8), 2),
            "policy_limit": policy["coverage_amount"],
            "claim_date": claim_date.isoformat(),
            "days_since_policy_start": max(0, days_since_policy),
            "status": random.choice(["Pending", "Under Review", "Approved", "Denied", "Under Investigation"]),
            "description": fake.text(max_nb_chars=300),
            "fraud_indicators": fraud_score,
            "damage_location": fake.city() + ", " + fake.state_abbr(),
            "witnesses": random.randint(0, 3),
            "police_report": random.choice([True, False]),
        })
    return claims


def generate_medical_records(applicants):
    conditions = ["Hypertension", "Type 2 Diabetes", "Asthma", "Arthritis", "Depression", "Anxiety", "GERD", "Migraine"]
    medications = ["Lisinopril", "Metformin", "Albuterol", "Ibuprofen", "Sertraline", "Atorvastatin", "Omeprazole"]

    records = []
    for app in applicants:
        records.append({
            "applicant_id": app["applicant_id"],
            "last_checkup": fake.date_between(start_date="-1y", end_date="today").isoformat(),
            "blood_pressure": f"{random.randint(90, 180)}/{random.randint(60, 120)}",
            "cholesterol": random.randint(150, 300),
            "blood_sugar": random.randint(70, 200),
            "weight_lbs": random.randint(120, 300),
            "height_inches": random.randint(60, 78),
            "chronic_conditions": random.sample(conditions, random.randint(0, 3)),
            "medications": random.sample(medications, random.randint(0, 3)),
            "allergies": random.sample(["Peanuts", "Shellfish", "Penicillin", "Latex", "None"], random.randint(0, 2)),
            "surgeries": random.sample(["Appendectomy", "Knee Surgery", "Cardiac Stent", "Gallbladder Removal", "None"], random.randint(0, 2)),
            "hospitalizations_last_5y": random.randint(0, 3),
            "smoker": app["smoker"],
            "alcohol_use": random.choice(["None", "Social", "Moderate", "Heavy"]),
        })
    return records


def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    print("Generating synthetic insurance data...")
    applicants = generate_applicants(100)
    policies = generate_policies(applicants)
    claims = generate_claims(applicants, policies, 200)
    medical_records = generate_medical_records(applicants)

    for name, data in [
        ("applicants.json", applicants),
        ("policies.json", policies),
        ("claims.json", claims),
        ("medical_records.json", medical_records),
    ]:
        path = os.path.join(OUTPUT_DIR, name)
        with open(path, "w") as f:
            json.dump(decimal_to_float(data), f, indent=2)
        print(f"  Wrote {len(data)} records to {path}")

    print("Done! Data files are in the data/ directory.")


if __name__ == "__main__":
    main()
