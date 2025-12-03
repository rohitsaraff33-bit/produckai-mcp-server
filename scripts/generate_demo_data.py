#!/usr/bin/env python
"""Generate demo data for testing ProduckAI MCP Server."""

import csv
import json
from datetime import datetime, timedelta
from pathlib import Path
import random

# Sample customer names
CUSTOMERS = [
    "Acme Corp",
    "TechStart Inc",
    "BigCo Enterprises",
    "StartupXYZ",
    "MegaRetail",
    "FinanceHub",
    "HealthTech Solutions",
    "EduPlatform",
]

# Sample feedback templates
FEEDBACK_TEMPLATES = [
    {
        "category": "API Performance",
        "templates": [
            "We're hitting API rate limits during peak hours",
            "API response time is too slow (>2 seconds)",
            "Need higher rate limits for enterprise plan",
            "API timeout errors during batch operations",
        ],
    },
    {
        "category": "User Management",
        "templates": [
            "SSO integration not working with Okta",
            "Need role-based access control",
            "Can't bulk invite users via CSV",
            "User permissions are confusing",
        ],
    },
    {
        "category": "Reporting",
        "templates": [
            "Need dashboard for executive metrics",
            "Can't export data to Excel",
            "Want scheduled email reports",
            "Charts are not interactive",
        ],
    },
    {
        "category": "Mobile App",
        "templates": [
            "Mobile app crashes on iOS 17",
            "Need offline mode for mobile",
            "Push notifications not working",
            "Mobile UI is not responsive",
        ],
    },
]


def generate_feedback_csv(output_path: Path, num_items: int = 50):
    """Generate CSV file with sample feedback."""
    feedback_items = []

    for i in range(num_items):
        # Pick random category and template
        category = random.choice(FEEDBACK_TEMPLATES)
        template = random.choice(category["templates"])

        # Add variation
        customer = random.choice(CUSTOMERS)
        date = datetime.now() - timedelta(days=random.randint(0, 90))

        feedback_items.append({
            "text": f"{template} - {customer}",
            "customer_name": customer,
            "source": "demo",
            "created_at": date.isoformat(),
            "metadata": json.dumps({
                "category": category["category"],
                "priority": random.choice(["high", "medium", "low"]),
            }),
        })

    # Write CSV
    with open(output_path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["text", "customer_name", "source", "created_at", "metadata"])
        writer.writeheader()
        writer.writerows(feedback_items)

    print(f"✅ Generated {num_items} feedback items: {output_path}")


def generate_demo_readme(output_dir: Path):
    """Generate README for demo data."""
    readme = """# Demo Data

This directory contains sample data for testing ProduckAI MCP Server.

## Files

- `feedback.csv` - 50 sample feedback items
- `customers.json` - Customer metadata (segment, ACV)

## Usage

1. Start Claude Desktop with ProduckAI MCP Server
2. Ask Claude: "Upload the demo feedback CSV at ./demo-data/feedback.csv"
3. Ask Claude: "Run clustering and generate insights"
4. Ask Claude: "Generate a PRD for the top insight"

## Expected Results

After processing demo data, you should see:
- ~4-6 themes (API, User Management, Reporting, Mobile)
- ~5-8 insights with VOC scores
- Ability to generate PRDs from top insights

## Customization

Edit `generate_demo_data.py` to:
- Add more feedback categories
- Adjust customer names
- Change date ranges
- Modify priorities
"""

    with open(output_dir / "README.md", "w") as f:
        f.write(readme)

    print(f"✅ Generated demo README: {output_dir / 'README.md'}")


def generate_customers_json(output_path: Path):
    """Generate customer metadata JSON."""
    customers = []

    segments = ["enterprise", "mid-market", "smb", "startup"]
    acv_ranges = {
        "enterprise": (100000, 500000),
        "mid-market": (25000, 100000),
        "smb": (5000, 25000),
        "startup": (1000, 5000),
    }

    for customer in CUSTOMERS:
        segment = random.choice(segments)
        acv_min, acv_max = acv_ranges[segment]

        customers.append({
            "name": customer,
            "segment": segment,
            "acv": random.randint(acv_min, acv_max),
            "strategic": random.random() < 0.2,  # 20% strategic
        })

    with open(output_path, "w") as f:
        json.dump(customers, f, indent=2)

    print(f"✅ Generated customer metadata: {output_path}")


if __name__ == "__main__":
    # Create demo-data directory
    demo_dir = Path(__file__).parent.parent / "demo-data"
    demo_dir.mkdir(exist_ok=True)

    # Generate files
    generate_feedback_csv(demo_dir / "feedback.csv", num_items=50)
    generate_customers_json(demo_dir / "customers.json")
    generate_demo_readme(demo_dir)

    print("\n" + "="*60)
    print("DEMO DATA GENERATION COMPLETE")
    print("="*60)
    print(f"Location: {demo_dir}")
    print("\nNext steps:")
    print("1. Start Claude Desktop")
    print("2. Upload demo-data/feedback.csv")
    print("3. Follow demo-data/README.md instructions")
    print("="*60)
