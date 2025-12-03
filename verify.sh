#!/bin/bash
# Quick verification script for ProduckAI MCP Server

set -e

echo "============================================"
echo "ProduckAI MCP Server - Verification Script"
echo "============================================"
echo ""

# Check Python version
echo "✓ Checking Python version..."
python3 --version

if [ ! -d "venv" ]; then
    echo "✗ Virtual environment not found!"
    echo "  Run: python3 -m venv venv"
    exit 1
fi

echo "✓ Virtual environment exists"

# Activate venv
source venv/bin/activate

echo "✓ Activated virtual environment"

# Check if package is installed
if ! command -v produckai-mcp &> /dev/null; then
    echo "✗ Package not installed!"
    echo "  Run: pip install -e ."
    exit 1
fi

echo "✓ Package is installed"

# Check CLI
echo "✓ Testing CLI..."
produckai-mcp --version

# Check Python syntax
echo "✓ Checking Python syntax..."
python3 -m py_compile src/produckai_mcp/*.py src/produckai_mcp/**/*.py

echo ""
echo "============================================"
echo "✅ Basic verification passed!"
echo "============================================"
echo ""
echo "Next steps:"
echo "1. Run tests: pytest"
echo "2. Run setup: produckai-mcp setup"
echo "3. Check status: produckai-mcp status"
echo ""
