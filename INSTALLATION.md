# Installation Guide

Complete installation guide for ProduckAI MCP Server across all platforms.

## Table of Contents

- [Prerequisites](#prerequisites)
- [Quick Install (Recommended)](#quick-install-recommended)
- [Platform-Specific Instructions](#platform-specific-instructions)
  - [macOS](#macos)
  - [Linux](#linux)
  - [Windows](#windows)
- [Claude Desktop Configuration](#claude-desktop-configuration)
- [Verification](#verification)
- [Troubleshooting](#troubleshooting)
- [Development Installation](#development-installation)
- [Upgrading](#upgrading)
- [Uninstallation](#uninstallation)

---

## Prerequisites

### Required

- **Python 3.11+** (3.11, 3.12, or 3.13 recommended)
- **pip** (Python package manager)
- **Claude Desktop** ([download here](https://claude.ai/download))
- **Anthropic API Key** ([get one here](https://console.anthropic.com/settings/keys))

### Optional (for integrations)

- **OpenAI API Key** - For embeddings (optional, can use ProduckAI backend)
- **Slack OAuth** - For Slack integration
- **Google Cloud Project** - For Google Drive integration
- **JIRA Account** - For JIRA integration
- **Zoom Account** - For Zoom integration

---

## Quick Install (Recommended)

This is the fastest way to get started:

```bash
# 1. Install the package
pip install produckai-mcp-server

# 2. Verify installation
produckai-mcp --version
# Expected: produckai-mcp-server v0.7.0

# 3. Test the command works
which produckai-mcp
# Expected: /path/to/python/bin/produckai-mcp
```

**Next:** [Configure Claude Desktop](#claude-desktop-configuration)

---

## Platform-Specific Instructions

### macOS

#### Option 1: System Python (Recommended)

```bash
# Check Python version
python3 --version
# Should be 3.11 or higher

# Install package
pip3 install produckai-mcp-server

# Verify
produckai-mcp --version
```

#### Option 2: Homebrew Python

```bash
# Install Python via Homebrew
brew install python@3.11

# Install package
pip3 install produckai-mcp-server

# Verify
produckai-mcp --version
```

#### Option 3: pyenv (For Multiple Python Versions)

```bash
# Install pyenv
brew install pyenv

# Install Python 3.11
pyenv install 3.11.9
pyenv global 3.11.9

# Install package
pip install produckai-mcp-server

# Verify
produckai-mcp --version
```

**Claude Desktop Config Location:**
```
~/Library/Application Support/Claude/claude_desktop_config.json
```

---

### Linux

#### Ubuntu/Debian

```bash
# Install Python 3.11+
sudo apt update
sudo apt install python3.11 python3.11-venv python3-pip

# Install package
pip3 install produckai-mcp-server

# Add to PATH if needed
export PATH="$HOME/.local/bin:$PATH"
echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.bashrc

# Verify
produckai-mcp --version
```

#### Fedora/RHEL/CentOS

```bash
# Install Python 3.11+
sudo dnf install python3.11 python3-pip

# Install package
pip3 install produckai-mcp-server

# Add to PATH if needed
export PATH="$HOME/.local/bin:$PATH"

# Verify
produckai-mcp --version
```

#### Arch Linux

```bash
# Install Python
sudo pacman -S python python-pip

# Install package
pip install produckai-mcp-server

# Verify
produckai-mcp --version
```

**Claude Desktop Config Location:**
```
~/.config/Claude/claude_desktop_config.json
```

---

### Windows

#### Option 1: Official Python Installer (Recommended)

1. **Download Python 3.11+** from [python.org](https://www.python.org/downloads/)
2. **Run installer**:
   - ✅ Check "Add Python to PATH"
   - ✅ Check "Install pip"
3. **Open Command Prompt or PowerShell**:

```powershell
# Verify Python
python --version
# Should be 3.11 or higher

# Install package
pip install produckai-mcp-server

# Verify
produckai-mcp --version
```

#### Option 2: Microsoft Store

```powershell
# Install Python from Microsoft Store
# Search for "Python 3.11" or "Python 3.12"

# Install package
pip install produckai-mcp-server

# Verify
produckai-mcp --version
```

#### Option 3: Anaconda/Miniconda

```powershell
# Create conda environment
conda create -n produckai python=3.11
conda activate produckai

# Install package
pip install produckai-mcp-server

# Verify
produckai-mcp --version
```

**Claude Desktop Config Location:**
```
%APPDATA%\Claude\claude_desktop_config.json
```

---

## Claude Desktop Configuration

After installing the package, configure Claude Desktop to use the MCP server.

### Step 1: Create or Edit Config File

**macOS:**
```bash
# Create directory if needed
mkdir -p ~/Library/Application\ Support/Claude

# Edit config file
open ~/Library/Application\ Support/Claude/claude_desktop_config.json
```

**Linux:**
```bash
# Create directory if needed
mkdir -p ~/.config/Claude

# Edit config file
nano ~/.config/Claude/claude_desktop_config.json
```

**Windows:**
```powershell
# Create directory if needed
New-Item -ItemType Directory -Force -Path $env:APPDATA\Claude

# Edit config file
notepad %APPDATA%\Claude\claude_desktop_config.json
```

### Step 2: Add ProduckAI Configuration

Add this configuration to your `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "produckai": {
      "command": "produckai-mcp",
      "env": {
        "ANTHROPIC_API_KEY": "your-anthropic-api-key-here"
      }
    }
  }
}
```

**Important:** Replace `your-anthropic-api-key-here` with your actual API key from https://console.anthropic.com/settings/keys

### Step 3: Add Optional API Keys

If you plan to use integrations, add their API keys:

```json
{
  "mcpServers": {
    "produckai": {
      "command": "produckai-mcp",
      "env": {
        "ANTHROPIC_API_KEY": "your-anthropic-api-key-here",
        "OPENAI_API_KEY": "your-openai-api-key-here",
        "SLACK_BOT_TOKEN": "xoxb-your-slack-bot-token",
        "JIRA_SERVER_URL": "https://yourcompany.atlassian.net",
        "JIRA_EMAIL": "your-email@company.com",
        "JIRA_API_TOKEN": "your-jira-api-token",
        "ZOOM_ACCOUNT_ID": "your-zoom-account-id",
        "ZOOM_CLIENT_ID": "your-zoom-client-id",
        "ZOOM_CLIENT_SECRET": "your-zoom-client-secret"
      }
    }
  }
}
```

### Step 4: Restart Claude Desktop

**macOS:**
```bash
# Completely quit Claude Desktop
# Then reopen from Applications
```

**Linux:**
```bash
# Kill Claude process
pkill -9 claude
# Restart Claude Desktop
```

**Windows:**
```powershell
# Close Claude Desktop completely
# Reopen from Start Menu
```

---

## Verification

### Step 1: Check MCP Server Connection

Open Claude Desktop and type:

```
"List available tools"
```

You should see ProduckAI tools listed, including:
- `ping_backend`
- `capture_raw_feedback`
- `upload_csv_feedback`
- `run_clustering`
- And 46 more tools...

### Step 2: Test Basic Functionality

Try the ping command:

```
"Ping the ProduckAI backend"
```

Expected response: Backend connection status

### Step 3: Try Demo Data

Upload the demo data to test the complete workflow:

```
"Upload the demo feedback CSV at ./demo-data/feedback.csv"
```

---

## Troubleshooting

### Problem: Command Not Found

```bash
# Error: produckai-mcp: command not found
```

**Solution:** Add Python bin directory to PATH

**macOS/Linux:**
```bash
# Find where pip installed the package
pip show produckai-mcp-server

# Add to PATH (example)
export PATH="$HOME/.local/bin:$PATH"
# Or
export PATH="$(python3 -m site --user-base)/bin:$PATH"

# Make permanent
echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.bashrc
source ~/.bashrc
```

**Windows:**
```powershell
# Find installation path
pip show produckai-mcp-server

# Add to PATH via System Properties > Environment Variables
# Or use:
$env:PATH += ";$env:LOCALAPPDATA\Programs\Python\Python311\Scripts"
```

### Problem: MCP Server Not Appearing in Claude

**Check 1: Verify config file location**

```bash
# macOS
cat ~/Library/Application\ Support/Claude/claude_desktop_config.json

# Linux
cat ~/.config/Claude/claude_desktop_config.json

# Windows
type %APPDATA%\Claude\claude_desktop_config.json
```

**Check 2: Verify command path**

```bash
which produckai-mcp  # macOS/Linux
where produckai-mcp  # Windows
```

**Check 3: Check Claude Desktop logs**

**macOS:**
```bash
tail -f ~/Library/Logs/Claude/mcp*.log
```

**Linux:**
```bash
tail -f ~/.cache/Claude/logs/mcp*.log
```

**Windows:**
```powershell
Get-Content $env:APPDATA\Claude\logs\mcp*.log -Tail 50
```

**Check 4: Restart Claude Desktop completely**

Make sure to fully quit (not just minimize) and reopen.

### Problem: API Connection Failed

```bash
# Error: Failed to connect to backend
```

**Solution 1: Check API key**

Verify your Anthropic API key is correct:
```bash
# Test API key manually
export ANTHROPIC_API_KEY="your-key"
python3 -c "from anthropic import Anthropic; print(Anthropic().messages.create(model='claude-3-haiku-20240307', max_tokens=10, messages=[{'role':'user','content':'hi'}]))"
```

**Solution 2: Check network connectivity**

```bash
# Test backend connection
curl -I https://api.anthropic.com
```

### Problem: Python Version Too Old

```bash
# Error: requires Python 3.11 or higher
```

**Solution:** Upgrade Python

**macOS (Homebrew):**
```bash
brew install python@3.11
```

**Linux (Ubuntu/Debian):**
```bash
sudo apt update
sudo apt install python3.11
```

**Windows:**
Download and install from [python.org](https://www.python.org/downloads/)

### Problem: Permission Denied

```bash
# Error: Permission denied when installing
```

**Solution:** Install in user directory

```bash
# Don't use sudo, install for user only
pip install --user produckai-mcp-server
```

### Problem: Import Errors

```bash
# Error: ModuleNotFoundError: No module named 'produckai_mcp'
```

**Solution:** Reinstall package

```bash
pip uninstall produckai-mcp-server
pip install --force-reinstall produckai-mcp-server
```

### Problem: Multiple Python Versions

**Solution:** Use specific Python version

```bash
# Use python3.11 specifically
python3.11 -m pip install produckai-mcp-server

# Verify
python3.11 -m pip show produckai-mcp-server
```

---

## Development Installation

For contributing or customizing ProduckAI:

### Step 1: Clone Repository

```bash
git clone https://github.com/produckai/produckai-mcp-server.git
cd produckai-mcp-server
```

### Step 2: Create Virtual Environment

```bash
# Create venv
python3 -m venv venv

# Activate venv
# macOS/Linux:
source venv/bin/activate
# Windows:
venv\Scripts\activate
```

### Step 3: Install in Development Mode

```bash
# Install with dev dependencies
pip install -e ".[dev]"

# Verify
produckai-mcp --version
```

### Step 4: Run Tests

```bash
# Run all tests
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

### Step 5: Configure Claude Desktop

Use the **full path** to the venv command in your config:

```json
{
  "mcpServers": {
    "produckai": {
      "command": "/absolute/path/to/produckai-mcp-server/venv/bin/produckai-mcp",
      "env": {
        "ANTHROPIC_API_KEY": "your-key"
      }
    }
  }
}
```

---

## Upgrading

### From PyPI (Standard Installation)

```bash
# Upgrade to latest version
pip install --upgrade produckai-mcp-server

# Verify new version
produckai-mcp --version

# Restart Claude Desktop
```

### From Development Installation

```bash
cd produckai-mcp-server
git pull origin main
source venv/bin/activate  # macOS/Linux
pip install -e ".[dev]"

# Restart Claude Desktop
```

### Breaking Changes

See [CHANGELOG.md](CHANGELOG.md) for breaking changes between versions.

**No breaking changes so far** - All versions are backward compatible.

---

## Uninstallation

### Remove Package

```bash
# Uninstall package
pip uninstall produckai-mcp-server

# Remove config from Claude Desktop
# Edit: ~/Library/Application Support/Claude/claude_desktop_config.json
# Remove the "produckai" section from mcpServers
```

### Remove Data (Optional)

ProduckAI stores local data in `~/.produckai/`:

```bash
# View what's stored
ls -la ~/.produckai/

# Remove all data (optional)
rm -rf ~/.produckai/

# This removes:
# - SQLite database (state.db)
# - Logs (logs/)
# - OAuth tokens (stored in system keyring)
```

### Remove OAuth Tokens

```bash
# OAuth tokens are stored in system keyring
# macOS: Keychain Access app
# Linux: Use keyring utility
# Windows: Credential Manager
```

---

## Next Steps

After installation:

1. **Read the [README.md](README.md)** for feature overview
2. **Try the [Quick Start Guide](README.md#first-use)** with demo data
3. **Explore the [End-to-End Workflow](docs/END_TO_END_WORKFLOW.md)**
4. **Set up integrations** (Slack, Google Drive, JIRA, Zoom)
5. **Join the community** on GitHub Discussions

---

## Getting Help

If you encounter issues not covered here:

1. **Check [Troubleshooting](#troubleshooting)** section above
2. **Search [GitHub Issues](https://github.com/produckai/produckai-mcp-server/issues)**
3. **Ask in [GitHub Discussions](https://github.com/produckai/produckai-mcp-server/discussions)**
4. **Email support**: contact@produckai.com

---

## System Requirements Summary

| Component | Requirement |
|-----------|-------------|
| **Python** | 3.11, 3.12, or 3.13 |
| **Operating System** | macOS 11+, Ubuntu 20.04+, Windows 10+ |
| **RAM** | 2 GB minimum, 4 GB recommended |
| **Disk Space** | 500 MB for installation + data |
| **Network** | Internet connection for API calls |
| **Claude Desktop** | Latest version recommended |

---

**Installation complete! Ready to transform your feedback into PRDs.** 🚀
