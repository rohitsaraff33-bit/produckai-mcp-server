# Frequently Asked Questions (FAQ)

## General Questions

### What is ProduckAI MCP Server?

ProduckAI MCP Server is a Model Context Protocol (MCP) integration that brings enterprise-grade product feedback analysis directly into Claude Desktop. It enables you to collect feedback from multiple sources (Slack, Google Drive, Zoom, JIRA, CSV), cluster it using AI, generate insights, and create executive-ready PRDs—all using natural language.

### Do I need a ProduckAI account?

No! The MCP server works standalone. It connects to a local or self-hosted ProduckAI backend that you control. There's no cloud service or account required.

### What's the difference between the MCP Server and the Backend?

- **MCP Server** (this package): Claude Desktop integration that provides 50+ tools for natural language interaction
- **Backend** (separate): Python FastAPI service that stores data, runs clustering, and serves the REST API

Think of it like a client-server architecture where Claude Desktop uses the MCP Server to talk to your Backend.

### Is this open source?

Yes! Licensed under MIT. Both the MCP Server and Backend are open source.

---

## Installation & Setup

### What Python version do I need?

Python 3.11 or higher. We recommend 3.12 for best performance.

### Can I install this with pip?

Yes! Once published to PyPI:
```bash
pip install produckai-mcp-server
```

For now, install from source:
```bash
git clone <repo-url>
cd produckai-mcp-server
pip install -e .
```

### How do I configure Claude Desktop?

Add this to `~/Library/Application Support/Claude/claude_desktop_config.json` (macOS):

```json
{
  "mcpServers": {
    "produckai": {
      "command": "produckai-mcp",
      "env": {
        "PRODUCKAI_BACKEND_URL": "http://localhost:8000",
        "ANTHROPIC_API_KEY": "your-api-key-here"
      }
    }
  }
}
```

On Windows: `%APPDATA%\Claude\claude_desktop_config.json`

### Do I need to restart Claude Desktop after configuration?

Yes! Always restart Claude Desktop after modifying `claude_desktop_config.json`.

---

## Architecture & Design

### Does the MCP Server store data?

Minimal state only:
- OAuth tokens (encrypted in system keyring)
- Sync state (last sync timestamps)
- Configuration (in SQLite at `~/.produckai/state.db`)

All feedback data, insights, and PRDs are stored in the Backend.

### Can the MCP Server generate PRDs without the Backend?

**Partially.** The MCP Server contains the PRD generation logic and directly calls the Anthropic API, but it needs the Backend to retrieve insight data (customer feedback, ACV, segments, etc.).

**Flow:**
1. Backend stores and clusters feedback
2. MCP Server fetches insight via Backend API
3. MCP Server generates PRD using Anthropic API
4. PRD is returned to Claude Desktop (not stored anywhere)

### Why does it use Claude 3 Opus instead of Sonnet 4.5?

Model availability depends on your Anthropic API key tier. The code defaults to Opus because it's widely available. You can configure the model in `src/produckai_mcp/analysis/prd_generator.py:75`:

```python
model: str = "claude-3-5-sonnet-20241022",  # If your key has access
```

### What's the "6-dimension VOC scoring"?

Voice of Customer (VOC) scoring prioritizes insights based on:
1. **Customer Impact** (30%) - Enterprise tier, ACV, strategic accounts
2. **Frequency** (20%) - How many times mentioned
3. **Recency** (15%) - How recently mentioned
4. **Sentiment** (15%) - Urgency/frustration level
5. **Theme Alignment** (10%) - Fits company strategy
6. **Effort** (10%) - Implementation complexity

Score range: 0-100, calculated automatically during clustering.

---

## Data Sources & Integrations

### Can I upload CSV files directly from Claude Desktop?

**Not directly.** Claude Desktop stores uploaded files in an internal path (`/mnt/user-data/uploads/`) that the MCP Server cannot access.

**Workaround:**
1. Save the CSV to your local filesystem (e.g., `~/Downloads/feedback.csv`)
2. Provide the local path: `upload_csv_feedback(file_path='~/Downloads/feedback.csv')`

Or paste the CSV content directly into Claude Desktop and ask it to upload.

### What CSV format is required?

**Minimal:**
```csv
text,customer_name,source,created_at
"Need SSO support",Acme Corp,slack,2025-12-01T10:00:00
```

**Full format** (with optional metadata):
```csv
text,customer_name,source,created_at,metadata
"Need SSO support",Acme Corp,slack,2025-12-01T10:00:00,"{""priority"": ""high""}"
```

See `demo-data/feedback.csv` for examples.

### Do Slack/Google Drive integrations work offline?

No. All integrations require internet access and valid OAuth tokens. The MCP Server fetches data in real-time via APIs.

### How do I get Slack/JIRA/Zoom credentials?

See [INTEGRATIONS.md](INTEGRATIONS.md) for step-by-step guides for each integration.

---

## Clustering & Insights

### How long does clustering take?

**Depends on feedback volume:**
- 50 items: ~30 seconds
- 500 items: ~2-3 minutes
- 5,000 items: ~10-15 minutes

Clustering runs asynchronously in the Background. You can check status with `get_clustering_status()`.

### How many themes/insights will be generated?

Determined automatically by the clustering algorithm based on semantic similarity. Typical ranges:
- 50 feedback items → 5-10 themes
- 500 feedback items → 15-25 themes
- 5,000 feedback items → 30-50 themes

### Can I re-cluster with different parameters?

Yes! Just call `cluster_feedback()` again. Previous themes/insights will be archived (not deleted).

### What AI models are used for clustering?

- **Embeddings**: OpenAI `text-embedding-3-small` (default) or Anthropic embeddings
- **Theme naming**: Claude 3 Haiku (fast, cost-effective)
- **Insight generation**: Claude 3 Haiku

### Why are some insights not linked to themes?

**Two types of insights:**
1. **Theme-based insights** - Derived from clustered themes (most common)
2. **Competitive insights** - Cross-cutting patterns (e.g., "Competitors offer feature X")

Competitive insights have `theme_id: null` by design.

---

## PRD Generation

### What's included in a generated PRD?

Standard 2-page PRD with:
1. Header table (Status, Severity, Priority, ACV, Customers)
2. Opportunity & Evidence (with customer quotes)
3. Solution Hypothesis (testable metrics)
4. System Behavior & Guardrails (AI safety if applicable)
5. Success Metrics (Business, Operational, AI Quality)
6. Risks & Mitigation
7. Rough Roadmap (MVP → Enhancement → Optimization)
8. Appendix (customer breakdown, full quotes)

### How much does PRD generation cost?

**Estimated cost per PRD** (using Claude 3 Opus):
- Input tokens: ~2,000-4,000 tokens ($0.01-0.02)
- Output tokens: ~2,500 tokens ($0.04)
- **Total: ~$0.05-0.06 per PRD**

Costs vary based on insight complexity and number of customer quotes.

### Can I customize the PRD template?

Yes! Edit `src/produckai_mcp/analysis/prd_generator.py` method `_build_prompt()`. The template structure is defined in `docs/PRD_GENERATION_PROMPT.md`.

### Where are generated PRDs stored?

**Nowhere by default.** PRDs are returned directly to Claude Desktop. You can:
- Copy/paste into Google Docs
- Ask Claude to save as a file
- Export to Confluence, Notion, etc. (via Claude Desktop)

---

## Common Errors

### "Failed to connect to backend at http://localhost:8000"

**Cause:** Backend is not running.

**Solution:**
```bash
# Start the backend
cd <backend-directory>
uvicorn apps.api.main:app --host 0.0.0.0 --port 8000 --reload
```

See [TROUBLESHOOTING.md](TROUBLESHOOTING.md) for more details.

### "1 validation error for Feedback: source_id Field required"

**Cause:** CSV uploads don't have external IDs (like Slack message IDs).

**Solution:** This should be fixed in v0.7.0+. If you see this error, update to the latest version:
```bash
pip install --upgrade produckai-mcp-server
```

### "'str' object has no attribute 'value'"

**Cause:** Code tried to access `.value` on severity/priority fields (they're strings, not enums).

**Solution:** Fixed in v0.7.0+. Update your installation.

### "Error code: 404 - model: claude-3-5-sonnet-20241022"

**Cause:** Your Anthropic API key doesn't have access to that model.

**Solution:** Update `prd_generator.py` to use a model your key has access to:
```python
model: str = "claude-3-opus-20240229",  # Most widely available
```

### "max_tokens: 8000 > 4096"

**Cause:** Claude 3 Opus has a 4096 output token limit.

**Solution:** Fixed in v0.7.0+. Update or manually edit `prd_generator.py:101`:
```python
max_tokens=4096,  # Was 8000
```

---

## Performance & Scaling

### How much feedback can the system handle?

**Tested up to:**
- 10,000 feedback items
- 50 themes
- 100 insights

**Bottlenecks:**
- Clustering time increases linearly with feedback count
- Backend database size (use PostgreSQL for > 10K items)

### Can I use PostgreSQL instead of SQLite?

Yes! For the **Backend** (not MCP Server):
```bash
# Backend .env
DATABASE_URL=postgresql://user:pass@localhost:5432/produckai
```

The MCP Server always uses SQLite for local state (lightweight).

### Does it support multiple users?

**Backend:** Yes, designed for multi-user (add authentication)
**MCP Server:** No, it's a single-user CLI tool integrated with Claude Desktop

---

## Security & Privacy

### Are my API keys stored securely?

Yes! API keys are:
- Stored in system keyring (macOS Keychain, Windows Credential Manager, Linux Secret Service)
- Never logged or transmitted except to official APIs
- Not included in error messages

### Can I self-host everything?

Absolutely! Both MCP Server and Backend are designed for self-hosting. No data leaves your infrastructure except API calls to:
- Anthropic (for AI classification and PRD generation)
- OpenAI (for embeddings, optional)
- Integration APIs (Slack, Google, Zoom, JIRA - only if you enable them)

### Is feedback data encrypted?

- **In transit:** Yes (HTTPS for all API calls)
- **At rest:** Depends on your Backend setup (SQLite is not encrypted by default, PostgreSQL supports encryption)

---

## Contributing & Support

### How can I contribute?

See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines. We welcome:
- Bug reports and feature requests (GitHub Issues)
- Code contributions (Pull Requests)
- Documentation improvements
- Integration guides

### Where can I get help?

1. **Documentation:** Start with [README.md](README.md) and [INSTALLATION.md](INSTALLATION.md)
2. **Troubleshooting:** Check [TROUBLESHOOTING.md](TROUBLESHOOTING.md)
3. **GitHub Issues:** Report bugs or ask questions
4. **Community:** (Discord/Slack link - TBD)

### How do I report security vulnerabilities?

See [SECURITY.md](SECURITY.md) for our security policy and responsible disclosure process. **Do not** open public GitHub issues for security vulnerabilities.

---

## Roadmap & Future Features

### What's coming next?

See [CHANGELOG.md](CHANGELOG.md) and GitHub milestones. Planned features:
- **v0.8:** Advanced filtering (date ranges, segments, sources)
- **v0.9:** Export to Jira/Linear/Notion
- **v1.0:** Multi-language support
- **v1.1:** Custom AI models (Llama, Mistral, etc.)

### Can I request features?

Yes! Open a GitHub Issue with:
- **Use case:** Why you need this feature
- **Expected behavior:** What should happen
- **Alternatives:** What you're doing now as a workaround

We prioritize features based on community demand and alignment with the project vision.

---

## License & Legal

### What license is this under?

MIT License. You can use it commercially, modify it, and distribute it freely. See [LICENSE](LICENSE) for full terms.

### Can I use this in my company?

Yes! MIT license allows commercial use. No attribution required (but appreciated).

### Are there any usage restrictions?

No restrictions from the MIT license. However:
- Anthropic API: Subject to [Anthropic's Terms of Service](https://www.anthropic.com/legal/terms)
- OpenAI API: Subject to [OpenAI's Terms of Use](https://openai.com/policies/terms-of-use)
- Integration APIs: Subject to their respective terms (Slack, Google, Zoom, JIRA)

---

**Still have questions?** Open an issue on GitHub or check the [troubleshooting guide](TROUBLESHOOTING.md).
