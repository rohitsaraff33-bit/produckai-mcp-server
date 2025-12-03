# ProduckAI MCP Server - Testing Guide

This document explains how to test and verify the MCP server implementation.

## Prerequisites

1. **Python 3.11+** installed
2. **ProduckAI backend** running:
   ```bash
   cd /path/to/produckai
   docker-compose up -d
   ```
   Verify it's running: `curl http://localhost:8000/health`

## Phase 0: Foundation Testing

### Step 1: Create Virtual Environment

```bash
cd mcp-server
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### Step 2: Install Dependencies

```bash
# Upgrade pip
pip install --upgrade pip

# Install package in development mode
pip install -e ".[dev]"
```

This will install:
- Core MCP SDK
- HTTP clients (httpx, aiohttp)
- Configuration (pydantic, pyyaml)
- CLI tools (click, rich)
- Integration SDKs (google-api-python-client, slack-sdk, jira)
- AI/LLM (anthropic, openai)
- Development tools (pytest, black, ruff, mypy)

### Step 3: Verify Installation

```bash
# Check CLI is installed
produckai-mcp --version

# Should output: produckai-mcp, version 0.1.0
```

### Step 4: Run Unit Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=src/produckai_mcp --cov-report=html

# Run specific test file
pytest tests/unit/test_config.py
pytest tests/unit/test_database.py
```

Expected output:
```
============================= test session starts ==============================
collected 7 items

tests/unit/test_config.py .....                                          [ 71%]
tests/unit/test_database.py ..                                           [100%]

============================== 7 passed in 0.15s ===============================
```

### Step 5: Test Configuration Management

```bash
# Run setup (creates ~/.produckai/config.yaml)
produckai-mcp setup

# Check status
produckai-mcp status

# View sync status
produckai-mcp sync-status
```

Expected output from `setup`:
```
🚀 ProduckAI MCP Server Setup

✓ Config directory: /Users/username/.produckai
✓ Configuration saved: /Users/username/.produckai/config.yaml
Testing backend connection...
✓ Backend is reachable at http://localhost:8000
Configuring Claude Desktop...
✓ Claude Desktop configured: /Users/username/Library/Application Support/Claude/claude_desktop_config.json

Setup complete!

Next steps:
  1. Restart Claude Desktop
  2. Look for ProduckAI tools in Claude
  3. Try: 'ping backend' to test the connection
```

### Step 6: Manual MCP Server Test

You can test the MCP server directly without Claude Desktop:

```bash
# Activate virtual environment
cd mcp-server
source venv/bin/activate

# Run the server (it will wait for MCP protocol messages on stdin/stdout)
python -m produckai_mcp.server
```

The server will start and wait for MCP protocol messages. You should see in the logs:
```
============================================================
ProduckAI MCP Server Starting
Version: 0.1.0
Backend URL: http://localhost:8000
Config directory: /Users/username/.produckai
============================================================
Database initialized: /Users/username/.produckai/state.db
Server initialization complete
Server running with stdio transport
```

Press `Ctrl+C` to stop.

### Step 7: Test with Claude Desktop

1. **Ensure setup was completed:**
   ```bash
   produckai-mcp setup
   ```

2. **Restart Claude Desktop completely:**
   - Quit Claude Desktop (Cmd+Q on Mac)
   - Start Claude Desktop again

3. **Verify server appears:**
   - Open Claude Desktop settings
   - Go to "Developer" section
   - Look for "produckai" in MCP servers list

4. **Test basic tools:**

   **Test 1: Echo**
   ```
   You: "Test the echo tool with message: Hello from ProduckAI!"
   Claude: [Uses echo tool]
   Echo: Hello from ProduckAI!
   ```

   **Test 2: Ping Backend**
   ```
   You: "Ping the ProduckAI backend to check if it's running"
   Claude: [Uses ping_backend tool]
   ✅ Backend is healthy!

   Backend URL: http://localhost:8000
   Status: ok
   Connection successful.
   ```

   **Test 3: Pipeline Status**
   ```
   You: "Show me the pipeline status"
   Claude: [Uses get_pipeline_status tool]
   📊 ProduckAI Pipeline Status

   Feedback:
     • Total: 0
     • With embeddings: 0
     • Without embeddings: 0

   Analysis:
     • Themes: 0
     • Insights: 0

   Last Clustering: Never run
   ```

## Troubleshooting

### Issue: "produckai-mcp: command not found"

**Solution:**
```bash
# Make sure virtual environment is activated
source venv/bin/activate

# Reinstall in development mode
pip install -e .
```

### Issue: "Backend connection failed"

**Solution:**
```bash
# Check if backend is running
curl http://localhost:8000/health

# If not running, start it:
cd /path/to/produckai
docker-compose up -d

# Check logs:
docker-compose logs -f api
```

### Issue: "Claude Desktop doesn't show ProduckAI"

**Solution:**
```bash
# Check Claude Desktop config
cat ~/Library/Application\ Support/Claude/claude_desktop_config.json

# Should contain:
{
  "mcpServers": {
    "produckai": {
      "command": "/path/to/python",
      "args": ["-m", "produckai_mcp.server"]
    }
  }
}

# If missing, run setup again:
produckai-mcp setup

# Completely restart Claude Desktop
```

### Issue: "MCP server crashes immediately"

**Solution:**
```bash
# Check logs
tail -f ~/.produckai/logs/mcp-server.log

# Run server directly to see errors
python -m produckai_mcp.server

# Check Python version (must be 3.11+)
python --version
```

### Issue: "Import errors when running tests"

**Solution:**
```bash
# Ensure all dependencies are installed
pip install -e ".[dev]"

# Check for version conflicts
pip list | grep -E "(pydantic|httpx|mcp)"

# If issues persist, recreate venv:
deactivate
rm -rf venv
python3 -m venv venv
source venv/bin/activate
pip install -e ".[dev]"
```

## Verification Checklist

Phase 0 is complete when:

- [ ] Virtual environment created and activated
- [ ] Package installed without errors
- [ ] CLI command `produckai-mcp` works
- [ ] All unit tests pass (7/7)
- [ ] `produckai-mcp setup` runs successfully
- [ ] `produckai-mcp status` shows backend is healthy
- [ ] Configuration files created in `~/.produckai/`
- [ ] State database created and schema initialized
- [ ] Claude Desktop config updated
- [ ] MCP server appears in Claude Desktop settings
- [ ] All 3 test tools work in Claude:
  - [ ] `echo` tool works
  - [ ] `ping_backend` tool connects successfully
  - [ ] `get_pipeline_status` tool returns data

## Next Steps

Once Phase 0 is verified, proceed to:

**Phase 1**: Manual Ingestion & Basic Query
- Implement `capture_raw_feedback()` tool
- Implement CSV upload tools
- Implement insight search tools
- Test end-to-end feedback workflow

## Development Tips

### Running tests in watch mode

```bash
# Install pytest-watch
pip install pytest-watch

# Run tests automatically on file changes
ptw
```

### Code formatting

```bash
# Format code
black src tests

# Check code style
ruff check src tests

# Type check
mypy src
```

### Debugging MCP server

Add breakpoints in your code and run with debugger:

```python
# In server.py or any tool handler
import pdb; pdb.set_trace()
```

Then run:
```bash
python -m pdb -m produckai_mcp.server
```

### Viewing MCP protocol messages

Set log level to DEBUG to see MCP protocol messages:

```yaml
# In ~/.produckai/config.yaml
server:
  log_level: DEBUG
```

Then check logs:
```bash
tail -f ~/.produckai/logs/mcp-server.log
```

## Success Criteria

Phase 0 is successfully completed when:

1. ✅ All Python modules compile without errors
2. ✅ All unit tests pass
3. ✅ CLI commands work correctly
4. ✅ MCP server starts without errors
5. ✅ Server registers with Claude Desktop
6. ✅ Basic tools (echo, ping_backend, get_pipeline_status) work
7. ✅ Configuration management works
8. ✅ State database initializes correctly
9. ✅ Logging works and log files are created
10. ✅ Backend connection works

**Status**: 🎉 PHASE 0 COMPLETE!

You now have a solid foundation to build the remaining tools and integrations.
