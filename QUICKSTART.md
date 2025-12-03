# ProduckAI MCP Server - Quick Start

Get from zero to your first PRD in 10 minutes!

## What You'll Build

By the end of this guide, you'll have:
- ✅ ProduckAI MCP Server installed
- ✅ Integrated with Claude Desktop
- ✅ Generated insights from demo feedback
- ✅ Created your first AI-powered PRD

## Prerequisites

- **Python 3.11+** ([download](https://www.python.org/downloads/))
- **Claude Desktop** ([download](https://claude.ai/download))
- **Anthropic API Key** ([get one](https://console.anthropic.com/settings/keys))

---

## Step 1: Install (2 minutes)

```bash
# Install from PyPI
pip install produckai-mcp-server

# Verify installation
produckai-mcp --version
# Expected: produckai-mcp-server v0.7.0
```

**✅ Installation complete!**

---

## Step 2: Configure Claude Desktop (3 minutes)

### macOS

```bash
# Open Claude config file
open ~/Library/Application\ Support/Claude/claude_desktop_config.json
```

### Linux

```bash
# Create directory if needed
mkdir -p ~/.config/Claude

# Edit config file
nano ~/.config/Claude/claude_desktop_config.json
```

### Windows

```powershell
# Edit config file
notepad %APPDATA%\Claude\claude_desktop_config.json
```

### Add This Configuration

```json
{
  "mcpServers": {
    "produckai": {
      "command": "produckai-mcp",
      "env": {
        "ANTHROPIC_API_KEY": "sk-ant-your-key-here"
      }
    }
  }
}
```

**Replace** `sk-ant-your-key-here` with your actual API key.

### Restart Claude Desktop

- **macOS**: Cmd+Q to quit, then reopen
- **Linux**: Kill and restart the app
- **Windows**: Close completely and reopen

**✅ Claude Desktop configured!**

---

## Step 3: Verify Connection (1 minute)

Open Claude Desktop and try:

```
"List the available ProduckAI tools"
```

You should see **50 tools** listed, including:
- `upload_csv_feedback`
- `run_clustering`
- `calculate_voc_scores`
- `generate_prd`
- And 46 more...

**✅ Connection verified!**

---

## Step 4: Try Demo Workflow (4 minutes)

Now let's process some demo feedback and generate a PRD!

### 4.1 Download Demo Data

```bash
# Create a directory for testing
mkdir produckai-demo
cd produckai-demo

# Download demo data
curl -O https://raw.githubusercontent.com/produckai/produckai-mcp-server/main/demo-data/feedback.csv
```

**Or** if you cloned the repo:
```bash
# Demo data is already in demo-data/feedback.csv
```

### 4.2 Upload Feedback

In Claude Desktop, type:

```
"Upload the demo feedback CSV at ./demo-data/feedback.csv"
```

**Expected:** Claude uploads 50 feedback items

### 4.3 Run Clustering

```
"Run clustering on the feedback to identify themes"
```

**Expected:** Claude generates 5-10 themes from the feedback

### 4.4 View Top Themes

```
"Show me the top 5 themes by feedback count"
```

**Expected:** List of themes with insights

### 4.5 Calculate VOC Scores

```
"Calculate VOC scores for all insights"
```

**Expected:** Insights ranked by priority (0-100 scale)

### 4.6 Generate Your First PRD

```
"Generate a PRD for the highest-priority insight"
```

**Expected:** A complete, strategic PRD document!

### 4.7 Export the PRD

```
"Export that PRD to ~/Documents/my-first-prd.md"
```

**Expected:** PRD saved to your Documents folder

**✅ First PRD generated!** 🎉

---

## What You Just Did

In 10 minutes, you:
1. ✅ Installed ProduckAI MCP Server
2. ✅ Integrated with Claude Desktop
3. ✅ Uploaded 50 feedback items
4. ✅ Generated themes using AI clustering
5. ✅ Prioritized with VOC scoring
6. ✅ Generated a strategic PRD
7. ✅ Exported to markdown

**This is the complete ProduckAI workflow!**

---

## Complete Tool Catalog (50 Tools)

### 📥 Ingestion (21 tools)

**Slack** (6 tools):
- Setup, list channels, sync, status, filters, tagging

**Google Drive** (6 tools):
- Setup, browse, sync, preview, status, config

**Zoom** (5 tools):
- Setup, sync recordings, analyze, insights, linking

**JIRA** (8 tools):
- Setup, browse, bidirectional sync, mapping, reports

**Manual** (5 tools):
- CSV upload, Zoom transcript, raw capture, templates

### ⚙️ Processing (4 tools)
- `run_clustering` - Generate themes
- `generate_embeddings` - Create vectors
- `get_themes` - List all themes
- `get_theme_details` - Deep-dive

### 🔍 Query (4 tools)
- `search_insights` - NLP search
- `get_insight_details` - Full insight
- `search_feedback` - Search raw feedback
- `get_customer_feedback` - Customer view

### 🎯 VOC Scoring (4 tools)
- `calculate_voc_scores` - 6-dimension scoring
- `get_top_feedback_by_voc` - Priority list
- `configure_voc_weights` - Customize
- `get_voc_trends` - Track changes

### 📄 PRD Generation (6 tools)
- `generate_prd` - Create PRD
- `list_prds` - Browse PRDs
- `get_prd` - View full PRD
- `update_prd_status` - Workflow
- `regenerate_prd` - Update
- `export_prd` - Export

### 🏥 Management (11 tools)
- Status, health, sync monitoring

---

## Next Steps

### Set Up Real Integrations

#### Slack Integration
```
"Setup Slack integration"
```
Follow the OAuth flow to connect your workspace.

#### Google Drive Integration
```
"Setup Google Drive integration"
```
Connect your Google account to sync documents.

#### JIRA Integration
```
"Setup JIRA integration with server URL https://yourcompany.atlassian.net"
```
Provide your JIRA credentials to sync issues.

### Weekly Workflow Example

```
Monday: "Sync Slack #customer-feedback for the last 7 days"
Tuesday: "Run clustering to identify themes"
Wednesday: "Calculate VOC scores and show top 5"
Thursday: "Generate a PRD for the top insight"
Friday: "Sync the PRD to JIRA project PROD"
```

**Result:** Weekly PRDs backed by customer evidence!

---

## Troubleshooting

### ProduckAI tools not showing in Claude?

1. **Check config file location**:
   ```bash
   # macOS
   cat ~/Library/Application\ Support/Claude/claude_desktop_config.json

   # Linux
   cat ~/.config/Claude/claude_desktop_config.json

   # Windows
   type %APPDATA%\Claude\claude_desktop_config.json
   ```

2. **Verify command is in PATH**:
   ```bash
   which produckai-mcp  # macOS/Linux
   where produckai-mcp  # Windows
   ```

3. **Check API key is set**:
   ```bash
   # In your config, verify ANTHROPIC_API_KEY is set
   ```

4. **Restart Claude Desktop completely**:
   - Don't just minimize - fully quit and reopen

### Command not found?

Add Python bin to PATH:

```bash
# macOS/Linux
export PATH="$HOME/.local/bin:$PATH"
echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.bashrc

# Windows (PowerShell)
$env:PATH += ";$env:LOCALAPPDATA\Programs\Python\Python311\Scripts"
```

### Need more help?

- 📖 [Full Installation Guide](INSTALLATION.md)
- 📚 [Complete Documentation](README.md)
- 🔄 [End-to-End Workflow](docs/END_TO_END_WORKFLOW.md)
- 🐛 [Report Issues](https://github.com/produckai/produckai-mcp-server/issues)

---

## Alternative: Development Installation

Want to contribute or customize? Install from source:

```bash
# Clone repository
git clone https://github.com/produckai/produckai-mcp-server.git
cd produckai-mcp-server

# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install in development mode
pip install -e ".[dev]"

# Run tests
pytest
```

Then configure Claude Desktop with full path to venv command:

```json
{
  "mcpServers": {
    "produckai": {
      "command": "/full/path/to/produckai-mcp-server/venv/bin/produckai-mcp",
      "env": {
        "ANTHROPIC_API_KEY": "your-key"
      }
    }
  }
}
```

---

## Key Features

### 🎯 Smart Prioritization
6-dimension VOC scoring:
- Customer Impact (30%)
- Frequency (20%)
- Recency (15%)
- Sentiment (15%)
- Theme Alignment (10%)
- Effort (10%)

### 📊 Multi-Source Ingestion
- **Slack** - Channels, DMs, threads
- **Google Drive** - Docs, Sheets, PDFs
- **Zoom** - Meeting recordings, transcripts
- **JIRA** - Issues, comments, tickets
- **CSV** - Bulk uploads, exports

### 🤖 AI-Powered Analysis
- **Clustering** - Automatic theme discovery
- **Customer Attribution** - AI name extraction
- **Sentiment Analysis** - Urgency detection
- **PRD Generation** - Claude Sonnet 4.5

### 📄 Strategic PRDs
- Executive summaries with ACV
- Evidence-backed problem statements
- Segment-aware (Enterprise vs SMB)
- Persona-specific framing
- Risk assessment and dependencies

---

## Performance & Cost

### Speed
- Feedback sync: ~1-2 seconds per item
- Clustering: ~1-2 minutes for 100 items
- PRD generation: ~10-15 seconds per PRD

### Cost (AI APIs)
- Embeddings: ~$0.01 per 100 items
- Clustering: ~$0.20 per 100 items
- PRD Generation: ~$0.05-0.10 per PRD
- **Monthly (100 PRDs):** ~$5-10 total

---

## Current Status

| Metric | Value |
|--------|-------|
| **Version** | 0.7.0 |
| **Total Tools** | 50 |
| **Integrations** | 5 (Slack, Drive, Zoom, JIRA, CSV) |
| **License** | MIT |
| **Status** | ✅ Production Ready |

---

## Community

- **GitHub**: [produckai/produckai-mcp-server](https://github.com/produckai/produckai-mcp-server)
- **Issues**: [Report bugs](https://github.com/produckai/produckai-mcp-server/issues)
- **Discussions**: [Ask questions](https://github.com/produckai/produckai-mcp-server/discussions)
- **Email**: contact@produckai.com

---

**From feedback to PRD in 10 minutes. Start transforming your product process today!** 🚀
