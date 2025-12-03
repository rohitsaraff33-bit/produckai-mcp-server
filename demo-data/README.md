# Demo Data

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
