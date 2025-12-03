# Integration Setup Guide

Complete guide to setting up all ProduckAI integrations: Slack, Google Drive, Zoom, JIRA, and more.

## Table of Contents

- [Prerequisites](#prerequisites)
- [Slack Integration](#slack-integration)
- [Google Drive Integration](#google-drive-integration)
- [Zoom Integration](#zoom-integration)
- [JIRA Integration](#jira-integration)
- [CSV/Manual Upload](#csvmanual-upload)
- [Troubleshooting](#troubleshooting)
- [Best Practices](#best-practices)

---

## Prerequisites

Before setting up integrations, ensure you have:

- ✅ ProduckAI MCP Server installed ([Installation Guide](INSTALLATION.md))
- ✅ Claude Desktop configured and running
- ✅ Anthropic API key set in Claude config
- ✅ Admin access to the services you want to integrate

---

## Slack Integration

Sync customer feedback from Slack channels with AI-powered classification.

### Features

- 📥 Auto-sync messages from channels
- 🤖 AI classification (feedback vs noise)
- 👤 Automatic customer attribution
- 🔄 Delta sync (no duplicates)
- 🤖 Bot message filtering
- 📊 Sync status monitoring

### Step 1: Create Slack App

1. **Go to** [Slack API Apps](https://api.slack.com/apps)
2. **Click** "Create New App" → "From scratch"
3. **Name your app:** "ProduckAI Feedback Collector"
4. **Select workspace** where you want to install it
5. **Click** "Create App"

### Step 2: Configure OAuth & Permissions

1. **In your Slack app**, go to "OAuth & Permissions"
2. **Scroll to "Scopes"** → "Bot Token Scopes"
3. **Add these scopes:**
   ```
   channels:history    - Read public channel messages
   channels:read       - List public channels
   users:read          - Read user information
   ```
4. **Optional scopes** (for private channels):
   ```
   groups:history      - Read private channel messages
   groups:read         - List private channels
   ```

### Step 3: Install to Workspace

1. **Scroll to top** of "OAuth & Permissions" page
2. **Click** "Install to Workspace"
3. **Review permissions** and click "Allow"
4. **Copy** the "Bot User OAuth Token" (starts with `xoxb-`)

### Step 4: Configure in Claude Desktop

Add the Slack token to your Claude Desktop config:

**macOS:**
```bash
open ~/Library/Application\ Support/Claude/claude_desktop_config.json
```

**Linux:**
```bash
nano ~/.config/Claude/claude_desktop_config.json
```

**Windows:**
```powershell
notepad %APPDATA%\Claude\claude_desktop_config.json
```

**Add Slack token:**
```json
{
  "mcpServers": {
    "produckai": {
      "command": "produckai-mcp",
      "env": {
        "ANTHROPIC_API_KEY": "your-anthropic-key",
        "SLACK_BOT_TOKEN": "xoxb-your-slack-bot-token-here"
      }
    }
  }
}
```

### Step 5: Test in Claude Desktop

Restart Claude Desktop, then try:

```
"Setup Slack integration"
```

Expected: OAuth flow completes successfully

```
"List available Slack channels"
```

Expected: Shows channels the bot can access

### Step 6: First Sync

```
"Sync the #customer-feedback channel for the last 7 days"
```

Expected: Syncs messages, classifies with AI, extracts customer names

### Slack Configuration Options

**Bot Filters:**
```
"Configure bot filters to exclude GitHub, JIRA, and Slackbot"
```

**Customer Patterns:**
```
"Add customer pattern: exact_name 'Acme Corp'"
"Add customer pattern: email_domain '@acmecorp.com'"
```

**Sync Status:**
```
"Show Slack sync status"
```

### Slack Best Practices

✅ **Do:**
- Add bot to channels you want to monitor
- Use specific date ranges for first sync
- Configure bot filters before syncing
- Set up customer patterns for better attribution

❌ **Don't:**
- Sync channels with sensitive data
- Use the User Token (xoxp-) instead of Bot Token
- Sync more than 30 days initially (can be slow)
- Forget to re-add bot after channel renames

### Slack Costs

- **AI Classification:** ~$0.05 per 1,000 messages
- **First sync (10,000 messages):** ~$0.50
- **Daily delta syncs (100 messages):** ~$0.005
- **Monthly estimate:** ~$1-2 for active channels

---

## Google Drive Integration

Sync customer feedback from Google Docs, Sheets, and PDFs.

### Features

- 📄 Multi-format support (Docs, Sheets, PDFs)
- 🔄 Delta sync with change detection
- 🤖 AI-powered feedback extraction
- 📊 Smart Sheets parsing (auto-detect columns)
- 💬 Comment extraction from Docs
- 👤 Customer attribution from metadata

### Step 1: Create Google Cloud Project

1. **Go to** [Google Cloud Console](https://console.cloud.google.com)
2. **Click** "Select a project" → "New Project"
3. **Name:** "ProduckAI Integration"
4. **Click** "Create"

### Step 2: Enable APIs

1. **In your project**, go to "APIs & Services" → "Library"
2. **Search and enable** these APIs:
   - Google Drive API
   - Google Docs API
   - Google Sheets API
3. **Click "Enable"** for each

### Step 3: Create OAuth Credentials

1. **Go to** "APIs & Services" → "Credentials"
2. **Click** "Create Credentials" → "OAuth client ID"
3. **Configure consent screen** if prompted:
   - User Type: External (or Internal if Google Workspace)
   - App name: "ProduckAI"
   - User support email: your-email@company.com
   - Developer email: your-email@company.com
   - Scopes: Add Drive, Docs, Sheets (read-only)
   - Test users: Add your email
4. **Application type:** Desktop app
5. **Name:** "ProduckAI MCP Server"
6. **Click** "Create"
7. **Download JSON** credentials file

### Step 4: Save Credentials

**macOS/Linux:**
```bash
mkdir -p ~/.produckai/credentials
mv ~/Downloads/client_secret_*.json ~/.produckai/credentials/google_oauth.json
```

**Windows:**
```powershell
New-Item -ItemType Directory -Force -Path $env:USERPROFILE\.produckai\credentials
Move-Item $env:USERPROFILE\Downloads\client_secret_*.json $env:USERPROFILE\.produckai\credentials\google_oauth.json
```

### Step 5: Setup in Claude Desktop

In Claude Desktop:

```
"Setup Google Drive integration"
```

**What happens:**
1. Browser opens for OAuth authorization
2. Sign in to Google account
3. Grant permissions (read-only access)
4. Authorization completes automatically
5. Token stored securely in system keyring

### Step 6: First Sync

**Browse folders:**
```
"Browse my Google Drive folders"
```

**Preview before syncing:**
```
"Preview the 'Customer Interviews' folder"
```

**Sync folder:**
```
"Sync the 'Customer Interviews' folder"
```

Expected: Processes Docs, Sheets, PDFs with AI classification

### Google Drive Configuration

**Processing settings:**
```
"Configure Drive processing to use aggressive chunking for large documents"
```

**Sync status:**
```
"Show Google Drive sync status"
```

### Google Drive Best Practices

✅ **Do:**
- Preview folders before syncing (cost estimation)
- Use specific folders, not entire Drive
- Set up delta sync for efficiency
- Organize feedback in dedicated folders

❌ **Don't:**
- Sync folders with PII without review
- Sync huge folders (>1000 files) initially
- Mix feedback with non-feedback documents
- Use scanned PDFs (no OCR support yet)

### Google Drive Costs

- **AI Classification:** ~$0.01-0.05 per document
- **Typical folder (50 docs):** ~$0.50-2.00
- **Delta sync:** Only pays for changed files
- **Monthly estimate:** ~$5-10 for active folders

### Supported Formats

| Format | Support | Features |
|--------|---------|----------|
| **Google Docs** | ✅ Full | Structure, comments, headings |
| **Google Sheets** | ✅ Full | Auto-detect columns, surveys |
| **PDF** | ✅ Text only | Text extraction (no OCR) |
| **Google Slides** | ❌ | Not supported |
| **Images** | ❌ | Not supported |

---

## Zoom Integration

Auto-fetch meeting recordings and extract feedback from transcripts.

### Features

- 🎥 Auto-download cloud recordings
- 📝 VTT transcript parsing
- 🤖 AI-powered meeting analysis
- 😊 Sentiment analysis per meeting
- 🎯 Key topics and pain points extraction
- 👤 Customer attribution to meetings

### Step 1: Create Server-to-Server OAuth App

1. **Go to** [Zoom App Marketplace](https://marketplace.zoom.us/develop/create)
2. **Click** "Create" → "Server-to-Server OAuth"
3. **App Name:** "ProduckAI Meeting Analyzer"
4. **Click** "Create"

### Step 2: Configure App Information

1. **Company Name:** Your company
2. **Developer Contact:** your-email@company.com
3. **Click** "Continue"

### Step 3: Add Scopes

Add these scopes:

```
recording:read:admin      - Read cloud recordings
recording:read:list_user_recordings - List user recordings
user:read:list_users      - Read user list (for attribution)
meeting:read:meeting      - Read meeting details
```

**Click** "Continue"

### Step 4: Get Credentials

On the "Credentials" page, copy:
- Account ID
- Client ID
- Client Secret

### Step 5: Configure in Claude Desktop

Add Zoom credentials to your config:

```json
{
  "mcpServers": {
    "produckai": {
      "command": "produckai-mcp",
      "env": {
        "ANTHROPIC_API_KEY": "your-anthropic-key",
        "ZOOM_ACCOUNT_ID": "your-account-id",
        "ZOOM_CLIENT_ID": "your-client-id",
        "ZOOM_CLIENT_SECRET": "your-client-secret"
      }
    }
  }
}
```

### Step 6: Test in Claude Desktop

Restart Claude Desktop, then:

```
"Setup Zoom integration"
```

Expected: Validates credentials successfully

### Step 7: First Sync

```
"Sync Zoom recordings from the last 7 days"
```

Expected: Downloads recordings, extracts transcripts, analyzes with AI

### Zoom Analysis

**Analyze specific meeting:**
```
"Analyze Zoom meeting with ID 12345678"
```

**Get insights:**
```
"Show me Zoom meeting insights for the last month"
```

**Link to customer:**
```
"Link Zoom meeting 12345678 to customer 'Acme Corp'"
```

### Zoom Best Practices

✅ **Do:**
- Enable cloud recording for customer calls
- Use transcript feature (auto-generates VTT)
- Set specific date ranges for first sync
- Link meetings to customers for better VOC scoring

❌ **Don't:**
- Sync personal/internal meetings
- Process meetings without transcripts (no value)
- Sync very old meetings (relevancy)
- Share Zoom credentials insecurely

### Zoom Costs

- **AI Analysis:** ~$0.10-0.20 per hour of recording
- **Typical meeting (1 hour):** ~$0.15
- **Monthly (20 meetings):** ~$3-4
- **No cost for:** Downloading, transcript extraction

---

## JIRA Integration

Bidirectional sync between feedback and JIRA issues.

### Features

- 🔄 Bidirectional sync (feedback ↔ issues)
- 🎯 VOC-based prioritization
- 📝 Auto-generate issues from insights
- 💬 Extract feedback from JIRA comments
- 📊 Feedback coverage reports
- 🔗 Link feedback to existing issues

### Step 1: Generate JIRA API Token

1. **Go to** [Atlassian Account Security](https://id.atlassian.com/manage-profile/security/api-tokens)
2. **Click** "Create API token"
3. **Label:** "ProduckAI MCP Server"
4. **Click** "Create"
5. **Copy** the token (you won't see it again!)

### Step 2: Get Your JIRA Details

You'll need:
- **JIRA Server URL:** `https://yourcompany.atlassian.net`
- **Email:** The email you use to log into JIRA
- **API Token:** From Step 1

### Step 3: Configure in Claude Desktop

Add JIRA credentials:

```json
{
  "mcpServers": {
    "produckai": {
      "command": "produckai-mcp",
      "env": {
        "ANTHROPIC_API_KEY": "your-anthropic-key",
        "JIRA_SERVER_URL": "https://yourcompany.atlassian.net",
        "JIRA_EMAIL": "your-email@company.com",
        "JIRA_API_TOKEN": "your-jira-api-token"
      }
    }
  }
}
```

### Step 4: Test in Claude Desktop

Restart Claude Desktop:

```
"Setup JIRA integration with server URL https://yourcompany.atlassian.net"
```

Expected: Validates connection successfully

### Step 5: Browse Projects

```
"Browse JIRA projects"
```

Expected: Lists all accessible projects

### Step 6: Sync Feedback to JIRA

**Method 1: High-VOC Feedback**
```
"Calculate VOC scores for all insights"
"Sync top 5 insights to JIRA project PROD"
```

**Method 2: Specific Insight**
```
"Create JIRA issue in project PROD from insight about API rate limiting"
```

### Step 7: Sync JIRA to Feedback

```
"Sync feedback from JIRA project PROD tickets with label 'customer-feedback'"
```

Expected: Imports feedback from JIRA comments

### JIRA Configuration

**Configure field mapping:**
```
"Configure JIRA mapping for project PROD"
```

**Get sync status:**
```
"Show JIRA sync status"
```

**Feedback coverage report:**
```
"Show JIRA feedback report for project PROD"
```

### JIRA Best Practices

✅ **Do:**
- Use specific projects for feedback issues
- Set up VOC scoring before syncing
- Include customer quotes in issue descriptions
- Use labels for tracking (e.g., "customer-feedback")
- Configure field mapping per project

❌ **Don't:**
- Sync all feedback (be selective)
- Create duplicate issues (check first)
- Sync to wrong project
- Forget to link feedback to issues

### JIRA Priority Mapping

ProduckAI automatically maps VOC scores to JIRA priorities:

| VOC Score | JIRA Priority |
|-----------|---------------|
| 80-100 | Highest |
| 60-79 | High |
| 40-59 | Medium |
| 20-39 | Low |
| 0-19 | Lowest |

---

## CSV/Manual Upload

Quick feedback capture without integration setup.

### CSV Upload

**Template options:**
```
"Show me CSV templates"
```

**Download template:**
```
"Get the standard feedback CSV template"
```

**Upload CSV:**
```
"Upload CSV feedback from ~/Downloads/feedback.csv"
```

### CSV Format

**Minimum required columns:**
```csv
text,created_at
"Customer wants API rate limit increase",2025-01-15T10:30:00Z
"Dashboard is confusing",2025-01-16T14:20:00Z
```

**Full format (recommended):**
```csv
text,customer_name,source,created_at,severity,category
"API rate limits too low","Acme Corp","support-ticket",2025-01-15T10:30:00Z,"high","api"
"Dashboard confusing","TechStart","user-interview",2025-01-16T14:20:00Z,"medium","ui"
```

### Supported CSV Templates

1. **Standard Feedback** - General feedback collection
2. **Customer Interview** - Interview notes and quotes
3. **Support Tickets** - Customer support data

### Zoom Transcript Upload

**Upload VTT file:**
```
"Upload Zoom transcript from ~/Downloads/meeting-transcript.vtt"
```

**Format:** WebVTT (.vtt) files from Zoom cloud recordings

### Raw Feedback Capture

**Quick capture:**
```
"Capture this feedback: Customer XYZ requested SSO integration for enterprise deployment"
```

Expected: Creates feedback entry with AI classification

### Manual Upload Best Practices

✅ **Do:**
- Use consistent date format (ISO 8601)
- Include customer names when known
- Add source information
- Use severity when available
- Upload regularly (weekly recommended)

❌ **Don't:**
- Mix different feedback types in one CSV
- Use inconsistent date formats
- Include PII without consent
- Upload duplicate data

---

## Troubleshooting

### Slack Integration

**Problem: Bot can't see messages**

```bash
# Solution: Add bot to channel
# In Slack: /invite @ProduckAI
```

**Problem: "Invalid token" error**

```bash
# Check you're using Bot Token (xoxb-), not User Token (xoxp-)
# Regenerate token if needed
```

### Google Drive Integration

**Problem: OAuth fails**

```bash
# Solution: Check OAuth consent screen is configured
# Add your email to test users
# Enable all required APIs (Drive, Docs, Sheets)
```

**Problem: "Access denied" to folder**

```bash
# Solution: Share folder with your Google account
# Or make folder accessible to anyone with the link
```

### Zoom Integration

**Problem: No recordings found**

```bash
# Solution: Verify cloud recording is enabled
# Check date range (recordings expire after 30 days on free tier)
# Ensure user has host privileges
```

**Problem: No transcripts**

```bash
# Solution: Enable "Audio transcript" in Zoom settings
# Account > Settings > Recording > Advanced cloud recording settings
# Enable "Audio transcript"
```

### JIRA Integration

**Problem: "Authentication failed"**

```bash
# Solution: Generate new API token
# Verify email matches JIRA account
# Check server URL format (include https://)
```

**Problem: "Project not found"**

```bash
# Solution: Verify you have access to the project
# Use exact project key (case-sensitive)
# Check project permissions
```

### General Issues

**Problem: High API costs**

```bash
# Solution: Use delta sync instead of full sync
# Preview folders/channels before syncing
# Configure bot filters to reduce noise
# Set specific date ranges
```

**Problem: Poor classification accuracy**

```bash
# Solution: Configure customer patterns
# Add domain-specific keywords
# Review and manually tag edge cases
# Provide feedback examples in prompts
```

---

## Best Practices

### Security

✅ **Do:**
- Store credentials in Claude Desktop config (encrypted)
- Use read-only scopes when possible
- Rotate API tokens quarterly
- Review OAuth permissions before granting
- Use separate tokens for dev/prod

❌ **Don't:**
- Commit credentials to version control
- Share tokens via email/Slack
- Use overly broad scopes
- Grant access to personal accounts for company use

### Performance

✅ **Do:**
- Use delta sync for regular updates
- Preview folders/channels before syncing
- Set specific date ranges
- Configure bot filters to reduce noise
- Sync during off-hours for large datasets

❌ **Don't:**
- Sync entire Drive or all Slack history at once
- Run multiple syncs simultaneously
- Sync irrelevant data
- Skip previews for cost estimation

### Cost Optimization

✅ **Do:**
- Use delta sync (only new/changed data)
- Configure bot filters (reduce AI calls)
- Set up customer patterns (reduce AI calls)
- Preview before syncing (estimate costs)
- Use specific date ranges

❌ **Don't:**
- Sync everything "just in case"
- Process data multiple times
- Ignore cost estimates in previews
- Forget to configure filters

### Data Quality

✅ **Do:**
- Set up customer patterns for better attribution
- Configure bot filters to reduce noise
- Use specific sources (dedicated channels/folders)
- Review and manually tag edge cases
- Maintain consistent data formatting

❌ **Don't:**
- Mix feedback with non-feedback data
- Ignore low-quality data sources
- Skip manual review of critical feedback
- Use inconsistent naming conventions

---

## Next Steps

After setting up integrations:

1. **Test with small dataset** - Verify everything works
2. **Configure filters and patterns** - Improve accuracy
3. **Run clustering** - Generate themes and insights
4. **Calculate VOC scores** - Prioritize feedback
5. **Generate PRDs** - Create strategic documents
6. **Sync to JIRA** - Execute on insights

See [END_TO_END_WORKFLOW.md](docs/END_TO_END_WORKFLOW.md) for complete workflow guide.

---

## Support

Need help with integrations?

- 📖 [Installation Guide](INSTALLATION.md)
- 📚 [Full Documentation](README.md)
- 🔄 [Workflow Guide](docs/END_TO_END_WORKFLOW.md)
- 🐛 [Report Issues](https://github.com/produckai/produckai-mcp-server/issues)
- 💬 [Discussions](https://github.com/produckai/produckai-mcp-server/discussions)
- 📧 Email: contact@produckai.com

---

**Integrate once, sync forever. Transform feedback from every source into actionable PRDs.** 🚀
