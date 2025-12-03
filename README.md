# ProduckAI MCP Server

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![MCP Protocol](https://img.shields.io/badge/MCP-Compatible-green.svg)](https://modelcontextprotocol.io)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
[![Community](https://img.shields.io/badge/Community-Contributions%20Welcome-brightgreen.svg)](https://github.com/rohitsaraff33-bit/produckai-mcp-server/blob/main/CONTRIBUTING.md)

> Transform scattered voice of customer feedback into actionable insights using AI-powered analysis and seamless Claude Desktop integration.

## 🌟 What is ProduckAI?

**ProduckAI MCP Server** brings enterprise-grade product feedback analysis directly into your AI workflows. Seamlessly integrate with Claude Desktop to analyze customer feedback, generate insights, prioritize features, and create executive-ready PRDs—all using natural language.

### Key Value Proposition

- **70% faster** Scattered VOC -> AI-powered generation
- **Multi-source ingestion**: Slack, Google Drive, Zoom, JIRA, CSV
- **Smart prioritization**: 6-dimension VOC scoring
- **Evidence-backed decisions**: Every PRD linked to customer quotes
- **50 specialized tools**: Complete workflow from collection to execution

 ### Why Open Source?

  Product management is evolving with AI, but most tools are closed source and expensive. **This project exists to democratize AI-powered product management** for teams of all sizes.

  By open sourcing this MCP server, we're creating a platform where:
  - 🤝 **PMs share learnings** - Your feedback analysis insights help others prioritize better
  - 🔧 **Engineers build together** - Improve clustering algorithms, add integrations, enhance AI prompts
  - 📚 **Community grows knowledge** - Document best practices, share PRD templates, teach new PMs

  **This isn't just a tool—it's a movement to make product management more data-driven, evidence-based, and accessible to everyone.**

  If you're a PM who's ever struggled with feedback overload, or an engineer building tools for PMs, **this project is for you**. Contribute,learn, and help shape the future of AI-assisted product management.

---

## ✨ Features

### 📥 Multi-Source Feedback Collection
- **Slack** - Auto-sync channels with AI-powered customer detection
- **Google Drive** - Process docs, PDFs with OCR
- **Zoom** - Auto-fetch recordings, AI transcript analysis
- **JIRA** - Bidirectional sync with issue tracking
- **CSV/Manual** - Bulk upload or quick capture

### 🧠 AI-Powered Analysis
- **Semantic Clustering** - Group similar feedback automatically
- **Insight Generation** - AI creates actionable themes
- **Sentiment Detection** - Identify urgent vs nice-to-have
- **Customer Attribution** - Auto-match feedback to customers

### 🎯 Smart Prioritization
- **VOC Scoring** - 6-dimension scoring (0-100):
  - Customer Impact (30%) - Tier, revenue, strategic
  - Frequency (20%) - How often mentioned
  - Recency (15%) - How recent
  - Sentiment (15%) - Urgency level
  - Theme Alignment (10%) - Strategic fit
  - Effort (10%) - Implementation complexity

### 📄 PRD Generation
- **AI-Powered PRDs** - Strategic documents from insights
- **Evidence-Based** - Includes direct customer quotes
- **Segment-Aware** - Tailored for Enterprise vs SMB
- **Risk Assessment** - Effort-based implementation risks
- **Version Tracking** - PRD history and updates

### 🔄 JIRA Integration
- **Bidirectional Sync** - Issues ↔ Feedback
- **Auto-Priority** - VOC score → JIRA priority
- **Issue Creation** - Generate epics from insights
- **Linkage Tracking** - Trace feedback to issues

---

## 🚀 Quick Start

### Prerequisites

- Python 3.11+
- Anthropic API Key ([get one here](https://console.anthropic.com/settings/keys))
- Claude Desktop ([download](https://claude.ai/download))

### Installation

```bash
pip install produckai-mcp-server
```

### Configuration

1. **Create environment file:**
   ```bash
   cp .env.example .env
   # Edit .env and add your ANTHROPIC_API_KEY
   ```

2. **Configure Claude Desktop** (`~/Library/Application Support/Claude/claude_desktop_config.json`):
   ```json
   {
     "mcpServers": {
       "produckai": {
         "command": "produckai-mcp",
         "env": {
           "ANTHROPIC_API_KEY": "your-api-key-here"
         }
       }
     }
   }
   ```

3. **Restart Claude Desktop**

### First Use

Try these commands in Claude:

```
"Upload the demo feedback CSV at ./demo-data/feedback.csv"
"Run clustering and show me the top themes"
"Calculate VOC scores and show top 5 insights"
"Generate a PRD for the highest-priority insight"
```

---

## 🛠️ Available Tools (50 Total)

### 📥 Ingestion (21 tools)
- **Slack**: setup, sync channels, tag customers, bot filters
- **Google Drive**: setup, browse, sync folders, preview, processing config
- **Zoom**: setup, sync recordings, analyze meetings, insights, customer linking
- **JIRA**: setup, browse projects, bidirectional sync, mapping, reports
- **Manual**: CSV upload, Zoom transcript, raw capture, templates

### ⚙️ Processing (4 tools)
- `run_clustering` - Generate themes and insights
- `generate_embeddings` - Create vector embeddings
- `get_themes` - List all themes
- `get_theme_details` - Deep-dive on theme

### 🔍 Query (4 tools)
- `search_insights` - Natural language search
- `get_insight_details` - Full insight data
- `search_feedback` - Search raw feedback
- `get_customer_feedback` - Customer-specific view

### 🎯 VOC Scoring (4 tools)
- `calculate_voc_scores` - Score feedback/themes
- `get_top_feedback_by_voc` - Priority-ranked list
- `configure_voc_weights` - Customize algorithm
- `get_voc_trends` - Track changes over time

### 📄 PRD Generation (6 tools)
- `generate_prd` - Create PRD from insight
- `list_prds` - Browse generated PRDs
- `get_prd` - View full PRD
- `update_prd_status` - Workflow tracking
- `regenerate_prd` - Update after changes
- `export_prd` - Export to markdown

### 🏥 Management (11 tools)
- Status checks, sync monitoring, health checks, configuration

### 📊 Quick Reference

| Integration | Setup Time | Cost/Month | Key Features |
|-------------|------------|------------|--------------|
| **Slack** | 10 min | $1-2 | AI classification, delta sync, bot filtering |
| **Google Drive** | 15 min | $5-10 | Multi-format, comments, auto-detect |
| **Zoom** | 10 min | $3-4 | Auto-download, AI analysis, sentiment |
| **JIRA** | 5 min | Free | Bidirectional, VOC priority, evidence |
| **CSV** | 0 min | Free | Bulk upload, templates, quick capture |

| Feature | Time | Cost | Output |
|---------|------|------|--------|
| **Clustering** (100 items) | 1-2 min | $0.20 | Themes & insights |
| **VOC Scoring** (100 items) | 10 sec | $0.01 | Priority ranking (0-100) |
| **PRD Generation** | 10-15 sec | $0.05-0.10 | Strategic document |

---

## 📖 Complete Workflow Example

### Weekly Feedback Triage (20 minutes)

```bash
# Monday: Collect feedback
"Sync Slack #customer-feedback channel for the last 7 days"
"Sync Zoom recordings from the past week"
"Upload the quarterly feedback CSV"

# Tuesday: Analyze
"Run clustering to identify themes"
"Show me the top 10 themes by feedback count"

# Wednesday: Prioritize
"Calculate VOC scores for all insights"
"Show me the top 5 highest-priority insights"

# Thursday: Document
"Generate a PRD for the top insight about API rate limiting"
"Export the PRD to ~/Documents/PRDs/"

# Friday: Execute
"Sync the top 3 insights to JIRA project PROD"
"Show JIRA sync status"
```

**Result:** 3 executive-ready PRDs, synced to JIRA, evidence-backed by customer feedback.

---

## 🏗️ Architecture

```
┌─────────────────┐
│  Data Sources   │  Slack, Drive, Zoom, JIRA, CSV
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  MCP Server     │  50 tools, state management, AI classification
│  (This Package) │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  ProduckAI API  │  Clustering, insights, embeddings
│  (Optional)     │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Claude Desktop │  Natural language interface
└─────────────────┘
```

**Deployment Model:** Local single-user (each PM runs their own instance)

---

## 🧪 Demo Data

Try ProduckAI with sample data:

```bash
# Generate demo data (50 feedback items)
python scripts/generate_demo_data.py

# In Claude:
"Upload demo-data/feedback.csv"
"Run clustering"
"Generate PRD for top insight"
```

See [demo-data/README.md](demo-data/README.md) for details.

---

## 🔐 Integration Setup

### Slack
1. Create Slack App: https://api.slack.com/apps
2. Add scopes: `channels:history`, `channels:read`, `users:read`
3. Install to workspace
4. In Claude: `"Setup Slack integration"`

### Google Drive
1. Create GCP project: https://console.cloud.google.com
2. Enable Google Drive API
3. Create OAuth credentials (Desktop app)
4. In Claude: `"Setup Google Drive integration"`

### JIRA
1. Generate API token: https://id.atlassian.com/manage/api-tokens
2. In Claude: `"Setup JIRA integration with server URL, email, and token"`

### Zoom
1. Create OAuth app: https://marketplace.zoom.us/develop/create
2. Add scope: `recording:read:admin`
3. In Claude: `"Setup Zoom integration"`

See [docs/](docs/) for detailed setup guides.

---

## 📚 Documentation

- [Installation Guide](INSTALLATION.md)
- [Quick Start Guide](QUICKSTART.md)
- [Integration Setup](INTEGRATIONS.md)
- [End-to-End Workflow](docs/END_TO_END_WORKFLOW.md)
- [Open Source Roadmap](docs/OPEN_SOURCE_ROADMAP.md)
- [Phase Implementation Docs](docs/)
  - [Phase 5: JIRA & VOC](docs/PHASE_5_COMPLETE.md)
  - [Phase 6: PRD Generation](docs/PHASE_6_COMPLETE.md)
- [PRD Generation Prompt](docs/PRD_GENERATION_PROMPT.md)
- [Contributing Guide](CONTRIBUTING.md)

---

## 🧑‍💻 Development

### Setup

```bash
# Clone repository
git clone https://github.com/produckai/produckai-mcp-server.git
cd produckai-mcp-server

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install in development mode
pip install -e ".[dev]"
```

### Testing

```bash
# Run tests
pytest

# Run with coverage
pytest --cov

# Run linting
ruff check .

# Format code
black .

# Type checking
mypy src/
```

### Code Quality

We use:
- **Black** for code formatting
- **Ruff** for linting
- **MyPy** for type checking
- **Pytest** for testing

See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

---

## 🐛 Troubleshooting

### MCP Server Not Appearing in Claude

1. Check config: `cat ~/Library/Application\ Support/Claude/claude_desktop_config.json`
2. Verify command: `which produckai-mcp`
3. Check logs: `tail -f ~/.produckai/logs/mcp-server.log`
4. Restart Claude Desktop completely

### API Connection Issues

```bash
# Test Anthropic API
export ANTHROPIC_API_KEY=your-key
python -c "from anthropic import Anthropic; print(Anthropic().messages.create(model='claude-3-haiku-20240307', max_tokens=10, messages=[{'role':'user','content':'hi'}]))"
```

### Common Issues

- **"Command not found"** - Ensure `produckai-mcp` is in PATH
- **"Connection refused"** - Check API keys are set
- **"Import error"** - Reinstall: `pip install --force-reinstall produckai-mcp-server`

See [docs/TROUBLESHOOTING.md](docs/) for more.

---

## 🤝 Contributing

We welcome contributions! Here's how:

1. **Fork** the repository
2. **Create** a feature branch: `git checkout -b feature/your-feature`
3. **Commit** your changes: `git commit -m "Add feature"`
4. **Push** to your fork: `git push origin feature/your-feature`
5. **Open** a Pull Request

See [CONTRIBUTING.md](CONTRIBUTING.md) for detailed guidelines.

**Areas We Need Help:**
- 📖 Documentation improvements
- 🐛 Bug fixes and testing
- ✨ New integration sources
- 🌍 Internationalization
- 🎨 UI/UX improvements

---

## 📊 Performance & Cost

### Speed
- **Feedback sync:** ~1-2 seconds per item
- **Clustering:** ~1-2 minutes for 100 items
- **PRD generation:** ~10-15 seconds per PRD

### Cost (AI APIs)
- **Embeddings:** ~$0.01 per 100 items (OpenAI)
- **Clustering/Insights:** ~$0.20 per 100 items (Claude Haiku)
- **PRD Generation:** ~$0.05-0.10 per PRD (Claude Sonnet)
- **Monthly (100 PRDs):** ~$5-10 total

---

## 📄 License

MIT License - see [LICENSE](LICENSE) for details.

---

## 🙏 Acknowledgments

- Built with [MCP SDK](https://modelcontextprotocol.io)
- Powered by [Anthropic Claude](https://anthropic.com)
- Inspired by product teams everywhere

---

## 🔗 Links

- [Issues](https://github.com/produckai/produckai-mcp-server/issues) - Report bugs
- [Discussions](https://github.com/produckai/produckai-mcp-server/discussions) - Ask questions
- [Changelog](CHANGELOG.md) - Release notes
- [Security Policy](SECURITY.md) - Report vulnerabilities

---

## ⭐ Star History

If you find this project useful, please star it! It helps others discover ProduckAI.

---

## 📧 Contact & Community

  ### Get in Touch
  - **Creator:** Rohit Saraf ([rohitsaraff33@gmail.com](mailto:rohitsaraff33@gmail.com))
  - **Issues:** [GitHub Issues](https://github.com/rohitsaraff33-bit/produckai-mcp-server/issues) - Bug reports, feature requests
  - **Discussions:** [GitHub Discussions](https://github.com/rohitsaraff33-bit/produckai-mcp-server/discussions) - Questions, ideas, showcases

  ### Vision & Community
  This project was built for **product managers, by product managers**. The goal is to create a thriving open source community where builders
  enhance integrations, improve insight generation logic, and share learnings so the entire PM community benefits.

  **We especially welcome contributions in:**
  - 🔌 **Integration enhancements** - New data sources (Linear, Notion, Confluence, etc.)
  - 🧠 **Insight generation** - Advanced clustering algorithms, sentiment analysis improvements
  - 📊 **Analytics & metrics** - New VOC scoring dimensions, priority frameworks
  - 📝 **PRD templates** - Industry-specific or company-specific variations
  - 🌍 **Localization** - Multi-language support for global teams

  **Whether you're a PM improving your workflow or an engineer building better tools for PMs, your contributions help everyone in the product 
  community. Let's build this together!**

  ---

  **Built with ❤️ by [Rohit Saraf](mailto:rohitsaraff33@gmail.com) and the product management community**

---

**Made with ❤️ by the ProduckAI community**
