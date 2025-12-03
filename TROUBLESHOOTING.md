# Troubleshooting Guide

This guide covers common issues and their solutions. For general questions, see [FAQ.md](FAQ.md).

## Table of Contents

1. [Installation Issues](#installation-issues)
2. [Connection & Backend Issues](#connection--backend-issues)
3. [Claude Desktop Integration](#claude-desktop-integration)
4. [Data Validation Errors](#data-validation-errors)
5. [PRD Generation Errors](#prd-generation-errors)
6. [Integration Issues](#integration-issues)
7. [Performance Issues](#performance-issues)
8. [Debugging Techniques](#debugging-techniques)

---

## Installation Issues

### Error: "python: command not found"

**Symptoms:**
```bash
$ python --version
zsh: command not found: python
```

**Cause:** Python not installed or not in PATH.

**Solution:**

**macOS:**
```bash
# Install Python 3.12 via Homebrew
brew install python@3.12

# Verify
python3 --version  # Should show 3.12.x
```

**Linux (Ubuntu/Debian):**
```bash
sudo apt update
sudo apt install python3.12 python3.12-venv python3-pip
```

**Windows:**
Download from [python.org](https://www.python.org/downloads/) and ensure "Add Python to PATH" is checked during installation.

---

### Error: "pip install failed - externally-managed-environment"

**Symptoms:**
```
error: externally-managed-environment

This environment is externally managed.
```

**Cause:** Python 3.11+ uses PEP 668 to prevent system-wide pip installs.

**Solution:** Always use virtual environments:

```bash
# Create virtual environment
python3 -m venv venv

# Activate
source venv/bin/activate  # macOS/Linux
# or
venv\Scripts\activate     # Windows

# Now install
pip install -e .
```

---

### Error: "ModuleNotFoundError: No module named 'mcp'"

**Cause:** Dependencies not installed or wrong Python environment.

**Solution:**

```bash
# Ensure virtual environment is activated
source venv/bin/activate

# Install dependencies
pip install -e ".[dev]"

# Verify MCP SDK installed
pip show mcp
```

---

## Connection & Backend Issues

### Error: "Failed to connect to backend at http://localhost:8000"

**Symptoms:**
```
ConnectionError: Failed to connect to backend at http://localhost:8000
Could not reach the backend API. Is the server running?
```

**Diagnosis:**
```bash
# Test if backend is running
curl http://localhost:8000/health

# Should return:
# {"status": "healthy", "version": "0.4.0"}
```

**Solutions:**

**1. Backend not running:**
```bash
# Navigate to backend directory
cd path/to/backend

# Start backend
uvicorn apps.api.main:app --host 0.0.0.0 --port 8000 --reload
```

**2. Backend running on different port:**
```bash
# Check what's running on 8000
lsof -i :8000

# If backend is on different port (e.g., 8001):
export PRODUCKAI_BACKEND_URL=http://localhost:8001
```

**3. Firewall blocking connection:**
```bash
# macOS: Allow Python through firewall
# System Settings → Network → Firewall → Options → Add Python

# Linux: Allow port 8000
sudo ufw allow 8000/tcp
```

---

### Error: "Backend returned 404 - Endpoint not found"

**Cause:** Backend version mismatch or wrong endpoint.

**Solution:**

```bash
# Check backend version
curl http://localhost:8000/health

# Expected version: 0.4.0+
# If older, update backend:
cd path/to/backend
git pull
pip install -e .
```

---

### Error: "Backend timeout after 60 seconds"

**Cause:** Clustering or large data query taking too long.

**Solution:**

Increase timeout in Claude Desktop config:

```json
{
  "mcpServers": {
    "produckai": {
      "command": "produckai-mcp",
      "env": {
        "PRODUCKAI_BACKEND_URL": "http://localhost:8000",
        "PRODUCKAI_BACKEND_TIMEOUT": "300"
      }
    }
  }
}
```

Or create `~/.produckai/config.yaml`:
```yaml
backend:
  url: http://localhost:8000
  timeout: 300  # 5 minutes
```

---

## Claude Desktop Integration

### Issue: MCP Server not showing up in Claude Desktop

**Diagnosis:**

1. **Check config file location:**
   ```bash
   # macOS
   cat ~/Library/Application\ Support/Claude/claude_desktop_config.json

   # Windows
   type %APPDATA%\Claude\claude_desktop_config.json

   # Linux
   cat ~/.config/Claude/claude_desktop_config.json
   ```

2. **Check config syntax:**
   ```bash
   # Validate JSON
   python3 -m json.tool < ~/Library/Application\ Support/Claude/claude_desktop_config.json
   ```

**Solutions:**

**1. Fix config syntax:**
```json
{
  "mcpServers": {
    "produckai": {
      "command": "produckai-mcp",
      "env": {
        "PRODUCKAI_BACKEND_URL": "http://localhost:8000"
      }
    }
  }
}
```

**2. Use absolute path if `produckai-mcp` not in PATH:**
```json
{
  "mcpServers": {
    "produckai": {
      "command": "/full/path/to/venv/bin/python",
      "args": ["-m", "produckai_mcp.server"],
      "env": {
        "PRODUCKAI_BACKEND_URL": "http://localhost:8000"
      }
    }
  }
}
```

**3. Restart Claude Desktop:**
   - Quit Claude Desktop completely (Cmd+Q on macOS)
   - Reopen Claude Desktop
   - Check logs: `~/Library/Logs/Claude/mcp*.log`

---

### Error: Claude Desktop shows "MCP Server crashed"

**Check logs:**

```bash
# macOS
tail -f ~/Library/Logs/Claude/mcp-server-produckai.log

# Look for Python errors
```

**Common causes:**

**1. Import error (missing dependency):**
```
ModuleNotFoundError: No module named 'anthropic'
```

**Solution:**
```bash
source venv/bin/activate
pip install -e ".[dev]"
```

**2. Permission error:**
```
PermissionError: [Errno 13] Permission denied: '/Users/name/.produckai/state.db'
```

**Solution:**
```bash
chmod 755 ~/.produckai
chmod 644 ~/.produckai/state.db
```

**3. Port already in use (OAuth flows):**
```
OSError: [Errno 48] Address already in use: ('', 8765)
```

**Solution:**
```bash
# Kill process using port 8765
lsof -ti:8765 | xargs kill -9
```

---

## Data Validation Errors

### Error: "1 validation error for Feedback: source_id Field required"

**Full error:**
```
pydantic_core._pydantic_core.ValidationError: 1 validation error for Feedback
source_id
  Field required [type=missing]
```

**Cause:** CSV uploads don't have external IDs (fixed in v0.7.0+).

**Solution:**

**Option 1: Update to v0.7.0+**
```bash
pip install --upgrade produckai-mcp-server
```

**Option 2: Manual fix** (if on older version):

Edit `src/produckai_mcp/api/models.py` line 44:
```python
# Before:
source_id: str

# After:
source_id: Optional[str] = None
```

---

### Error: "'NoneType' object has no attribute 'strftime'"

**Full error:**
```python
AttributeError: 'NoneType' object has no attribute 'strftime'
  File "clustering.py", line 410, in _format_themes_for_display
    lines.append(f"Created: {theme.created_at.strftime('%Y-%m-%d')}")
```

**Cause:** `created_at` is `None` or already a string (fixed in v0.7.0+).

**Solution:**

Update `src/produckai_mcp/tools/processing/clustering.py` around line 410:

```python
# Before:
lines.append(f"Created: {theme.created_at.strftime('%Y-%m-%d')}")

# After:
if theme.created_at:
    # created_at is already a string in ISO format
    lines.append(f"Created: {theme.created_at[:10]}")  # Extract date part
```

---

### Error: "'str' object has no attribute 'value'"

**Full error:**
```python
AttributeError: 'str' object has no attribute 'value'
  File "insights.py", line 250
    severity_emoji.get(insight.severity.value, "⚪")
```

**Cause:** Backend returns severity as string, not enum (fixed in v0.7.0+).

**Solution:**

Update `src/produckai_mcp/tools/query/insights.py`:

```python
# Remove all .value accesses:
# Before:
severity_emoji.get(insight.severity.value, "⚪")

# After:
severity_emoji.get(insight.severity, "⚪")
```

Use batch replacement:
```bash
cd src/produckai_mcp/tools/query
sed -i '' 's/insight\.severity\.value/insight.severity/g' insights.py
sed -i '' 's/insight\.priority\.value/insight.priority/g' insights.py
```

---

### Error: "theme_id Field required" in PRD generation

**Full error:**
```
pydantic_core._pydantic_core.ValidationError: 1 validation error for PRDMetadata
theme_id
  Input should be a valid string [type=string_type, input_value=None]
```

**Cause:** Backend not returning `theme_id` in insight responses.

**Solution:**

**Backend fix** - Edit `apps/api/api/themes.py`:

Add `theme_id` to response schemas (lines 34, 57):
```python
class InsightListResponse(BaseModel):
    theme_id: Optional[str] = None  # Add this line

class InsightDetailResponse(BaseModel):
    theme_id: Optional[str] = None  # Add this line
```

Add to response building (lines 245, 448):
```python
theme_id=str(insight.theme_id) if insight.theme_id else None,
```

Then restart backend.

---

## PRD Generation Errors

### Error: "404 - model: claude-3-5-sonnet-20241022"

**Full error:**
```json
{
  "type": "error",
  "error": {
    "type": "not_found_error",
    "message": "model: claude-3-5-sonnet-20241022"
  }
}
```

**Cause:** Your Anthropic API key doesn't have access to Sonnet models.

**Diagnosis:**
```python
# Test API key
from anthropic import Anthropic
client = Anthropic(api_key="your-key")

# Try different models
models_to_test = [
    "claude-3-opus-20240229",
    "claude-3-5-sonnet-20240620",
    "claude-3-5-sonnet-20241022",
]

for model in models_to_test:
    try:
        response = client.messages.create(
            model=model,
            max_tokens=100,
            messages=[{"role": "user", "content": "Hi"}]
        )
        print(f"✅ {model} works")
    except Exception as e:
        print(f"❌ {model} failed: {e}")
```

**Solution:**

Update `src/produckai_mcp/analysis/prd_generator.py`:

```python
# Line 28 - Default model
generation_model: str = "claude-3-opus-20240229"  # Change to available model

# Line 75 - Function parameter default
async def generate_prd(
    self,
    insight: Insight,
    model: str = "claude-3-opus-20240229",  # Change here too
    include_appendix: bool = True,
) -> GeneratedPRD:
```

---

### Error: "max_tokens: 8000 > 4096"

**Full error:**
```json
{
  "type": "error",
  "error": {
    "type": "invalid_request_error",
    "message": "max_tokens: 8000 > 4096, which is the maximum allowed for claude-3-opus-20240229"
  }
}
```

**Cause:** Claude 3 Opus has 4096 max output tokens, code requested 8000.

**Solution:**

Edit `src/produckai_mcp/analysis/prd_generator.py` line 101:

```python
# Before:
max_tokens=8000,

# After:
max_tokens=4096,  # Claude 3 Opus limit
```

---

### Error: "ANTHROPIC_API_KEY not set"

**Symptoms:**
```
PRD generation failed: ANTHROPIC_API_KEY environment variable not set
```

**Solution:**

**Option 1: Set in Claude Desktop config:**
```json
{
  "mcpServers": {
    "produckai": {
      "command": "produckai-mcp",
      "env": {
        "PRODUCKAI_BACKEND_URL": "http://localhost:8000",
        "ANTHROPIC_API_KEY": "sk-ant-api03-..."
      }
    }
  }
}
```

**Option 2: Set in system environment:**
```bash
# macOS/Linux - Add to ~/.zshrc or ~/.bashrc
export ANTHROPIC_API_KEY="sk-ant-api03-..."

# Windows - System Properties → Environment Variables
setx ANTHROPIC_API_KEY "sk-ant-api03-..."
```

**Option 3: Store in .env file:**
```bash
echo "ANTHROPIC_API_KEY=sk-ant-api03-..." >> ~/.produckai/.env
```

---

## Integration Issues

### Issue: "File not found: /mnt/user-data/uploads/file.csv"

**Cause:** Claude Desktop uploaded file to internal path that MCP Server can't access.

**Solution:**

**Workaround:**
1. Save CSV to your local filesystem first
2. Provide local path:
   ```
   "Upload this feedback: ~/Downloads/feedback.csv"
   ```

**Or paste CSV content directly:**
```
"Upload this CSV:
text,customer_name,source,created_at
Need SSO,Acme Corp,slack,2025-12-01T10:00:00
API slow,BigCo,jira,2025-12-01T11:00:00"
```

**Technical explanation:**
Claude Desktop stores uploads at `/mnt/user-data/uploads/` which is an internal virtual mount not accessible to external processes. This is a Claude Desktop limitation, not a bug in ProduckAI MCP Server.

---

### Error: "Slack OAuth failed - redirect_uri mismatch"

**Full error:**
```
Slack OAuth failed: invalid_redirect_uri
The redirect_uri (http://localhost:8765/callback) does not match
```

**Solution:**

1. Go to [Slack App Settings](https://api.slack.com/apps)
2. Select your app → OAuth & Permissions
3. Add redirect URL: `http://localhost:8765/callback`
4. Save changes
5. Retry `setup_slack_integration()`

---

### Error: "Google OAuth failed - access_denied"

**Cause:** Required scopes not enabled or user declined authorization.

**Required Google Drive scopes:**
- `https://www.googleapis.com/auth/drive.readonly`
- `https://www.googleapis.com/auth/drive.metadata.readonly`

**Solution:**

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. APIs & Services → Credentials
3. Edit OAuth 2.0 Client
4. Ensure redirect URI: `http://localhost:8765/callback`
5. APIs & Services → Enabled APIs → Enable Google Drive API
6. Retry authorization

---

### Error: "JIRA authentication failed - 401 Unauthorized"

**Diagnosis:**
```bash
# Test JIRA credentials
curl -u "your-email@company.com:your-api-token" \
  https://yourcompany.atlassian.net/rest/api/3/myself

# Should return your user info
```

**Solutions:**

**1. Generate new API token:**
- Go to [Atlassian Account Settings](https://id.atlassian.com/manage-profile/security/api-tokens)
- Create API token
- Copy token (you can't view it again!)
- Update config

**2. Check email/domain:**
```bash
# Email must match your JIRA account
JIRA_EMAIL=your-email@company.com  # Not personal email!
JIRA_SERVER_URL=https://yourcompany.atlassian.net  # Not .com!
```

---

## Performance Issues

### Issue: Clustering taking too long (>10 minutes)

**Diagnosis:**
```bash
# Check feedback count
curl http://localhost:8000/api/feedback/stats

# Check clustering status
curl http://localhost:8000/api/clustering/status
```

**Solutions:**

**1. Increase timeout:**
```yaml
# ~/.produckai/config.yaml
backend:
  timeout: 600  # 10 minutes
```

**2. Reduce feedback batch:**
```python
# Cluster only recent feedback
cluster_feedback(
    start_date="2025-11-01",
    end_date="2025-12-01"
)
```

**3. Check backend logs:**
```bash
# Backend should show progress
INFO:     Clustering 5000 feedback items...
INFO:     Generated embeddings (30s)
INFO:     Running HDBSCAN clustering (45s)
INFO:     Generating theme labels (20s)
INFO:     Creating insights (60s)
```

---

### Issue: High memory usage during clustering

**Symptoms:**
- Backend using >4GB RAM
- System becoming slow
- OOM (Out of Memory) errors

**Solutions:**

**1. Use PostgreSQL instead of SQLite:**
```bash
# Install PostgreSQL
brew install postgresql  # macOS
sudo apt install postgresql  # Linux

# Configure backend
DATABASE_URL=postgresql://user:pass@localhost:5432/produckai
```

**2. Process in smaller batches:**
```python
# Instead of clustering all at once:
cluster_feedback()

# Cluster by time period:
cluster_feedback(start_date="2025-11-01", end_date="2025-11-15")
cluster_feedback(start_date="2025-11-16", end_date="2025-11-30")
```

**3. Increase system resources:**
- Docker: Increase memory limit to 8GB
- System: Close other applications

---

## Debugging Techniques

### Enable Debug Logging

**MCP Server:**

```json
{
  "mcpServers": {
    "produckai": {
      "command": "produckai-mcp",
      "env": {
        "LOG_LEVEL": "DEBUG",
        "LOG_FILE": "~/.produckai/logs/mcp-server.log"
      }
    }
  }
}
```

**Backend:**
```bash
# Set log level
export LOG_LEVEL=DEBUG

# Start with verbose logging
uvicorn apps.api.main:app --log-level debug
```

**View logs:**
```bash
# MCP Server logs
tail -f ~/.produckai/logs/mcp-server.log

# Backend logs (if running in terminal)
# Logs appear in real-time

# Claude Desktop logs
tail -f ~/Library/Logs/Claude/mcp-server-produckai.log
```

---

### Test Backend Directly

**Bypass MCP Server to isolate issues:**

```bash
# 1. Test health endpoint
curl http://localhost:8000/health

# 2. Upload test feedback
curl -X POST http://localhost:8000/api/feedback \
  -H "Content-Type: application/json" \
  -d '{
    "text": "Need SSO support",
    "source": "test",
    "account": "Test Corp",
    "created_at": "2025-12-01T10:00:00"
  }'

# 3. Get feedback
curl http://localhost:8000/api/feedback

# 4. Trigger clustering
curl -X POST http://localhost:8000/api/clustering/cluster

# 5. Get themes
curl http://localhost:8000/api/themes
```

---

### Test PRD Generation Locally

**Bypass both MCP Server and Backend:**

```python
# test_prd.py
import asyncio
from anthropic import AsyncAnthropic

async def test_prd():
    client = AsyncAnthropic(api_key="your-api-key")

    response = await client.messages.create(
        model="claude-3-opus-20240229",
        max_tokens=4096,
        temperature=0.7,
        messages=[{
            "role": "user",
            "content": "Generate a 1-page PRD for SSO integration feature."
        }]
    )

    print(response.content[0].text)

asyncio.run(test_prd())
```

Run:
```bash
python test_prd.py
```

---

### Verify Database State

**Check SQLite database:**

```bash
# Open database
sqlite3 ~/.produckai/state.db

# List tables
.tables

# Check sync state
SELECT * FROM sync_state;

# Check OAuth tokens (encrypted)
SELECT integration, created_at FROM oauth_tokens;

# Exit
.quit
```

**Check Backend database:**

```bash
# If using SQLite
sqlite3 ./produckai.db
SELECT COUNT(*) FROM feedback;
SELECT COUNT(*) FROM themes;
SELECT COUNT(*) FROM insights;

# If using PostgreSQL
psql produckai
SELECT COUNT(*) FROM feedback;
```

---

### Network Diagnostics

**Check port availability:**

```bash
# Check if backend is listening on 8000
lsof -i :8000

# Check if port is blocked
nc -zv localhost 8000

# Test with curl
curl -v http://localhost:8000/health
```

**Check DNS/network:**

```bash
# If using remote backend
ping backend.company.com
nslookup backend.company.com
curl -v https://backend.company.com/health
```

---

## Still Having Issues?

### Collect Diagnostic Info

Run this script to collect debugging information:

```bash
#!/bin/bash
# diagnose.sh

echo "=== System Info ==="
uname -a
python3 --version

echo -e "\n=== MCP Server Info ==="
pip show produckai-mcp-server

echo -e "\n=== Backend Status ==="
curl -s http://localhost:8000/health || echo "Backend not responding"

echo -e "\n=== Recent MCP Logs ==="
tail -20 ~/Library/Logs/Claude/mcp-server-produckai.log 2>/dev/null || echo "No logs found"

echo -e "\n=== Database Status ==="
ls -lh ~/.produckai/state.db 2>/dev/null || echo "No database found"

echo -e "\n=== Network Tests ==="
lsof -i :8000 || echo "Port 8000 not in use"
```

Run and share output:
```bash
chmod +x diagnose.sh
./diagnose.sh > diagnostic-report.txt
```

### Get Help

1. **Search existing issues:** [GitHub Issues](https://github.com/produckai/mcp-server/issues)
2. **Open new issue:** Include diagnostic report
3. **Join community:** (Discord/Slack link - TBD)
4. **Email support:** contact@produckai.com

### Report Security Issues

**Do NOT** open public issues for security vulnerabilities. See [SECURITY.md](SECURITY.md) for responsible disclosure.

---

**Last Updated:** 2025-12-02
**Version:** 0.7.0
