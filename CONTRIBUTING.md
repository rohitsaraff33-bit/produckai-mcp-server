# Contributing to ProduckAI MCP Server

Thank you for your interest in contributing to ProduckAI! 🎉

We welcome contributions of all kinds: bug reports, feature requests, documentation improvements, and code contributions.

## Table of Contents

- [Code of Conduct](#code-of-conduct)
- [How Can I Contribute?](#how-can-i-contribute)
- [Development Setup](#development-setup)
- [Pull Request Process](#pull-request-process)
- [Coding Standards](#coding-standards)
- [Testing Guidelines](#testing-guidelines)
- [Documentation](#documentation)

---

## Code of Conduct

This project adheres to a Code of Conduct that all contributors are expected to follow. Please read [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md) before contributing.

---

## How Can I Contribute?

### Reporting Bugs

Before creating a bug report, please check existing issues to avoid duplicates.

**When reporting a bug, include:**
- **Clear title** and description
- **Steps to reproduce** the issue
- **Expected behavior** vs actual behavior
- **Environment details:** OS, Python version, package version
- **Screenshots** if applicable
- **Error messages** and stack traces

Use the [bug report template](.github/ISSUE_TEMPLATE/bug_report.md) when creating an issue.

### Suggesting Features

We love new ideas! Before suggesting a feature:
- Check if it's already been suggested
- Consider if it fits the project's scope
- Think about how it benefits users

Use the [feature request template](.github/ISSUE_TEMPLATE/feature_request.md) when creating a suggestion.

### Improving Documentation

Documentation is crucial! You can help by:
- Fixing typos and improving clarity
- Adding examples and use cases
- Translating documentation
- Creating tutorials and guides

### Contributing Code

We welcome code contributions! See [Development Setup](#development-setup) below.

---

## Development Setup

### Prerequisites

- Python 3.11 or higher
- pip or conda
- git
- Anthropic API Key (for testing PRD generation)

### Step 1: Fork and Clone

```bash
# Fork the repository on GitHub, then:
git clone https://github.com/YOUR_USERNAME/produckai-mcp-server.git
cd produckai-mcp-server
```

### Step 2: Create Virtual Environment

```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### Step 3: Install in Development Mode

```bash
pip install -e ".[dev]"
```

This installs the package in editable mode with all development dependencies.

### Step 4: Configure Environment

```bash
cp .env.example .env
# Edit .env and add your API keys
```

### Step 5: Run Tests

```bash
pytest
```

---

## Pull Request Process

### 1. Create a Branch

```bash
git checkout -b feature/your-feature-name
# or
git checkout -b fix/your-bug-fix
```

Branch naming conventions:
- `feature/` - New features
- `fix/` - Bug fixes
- `docs/` - Documentation changes
- `refactor/` - Code refactoring
- `test/` - Adding or updating tests

### 2. Make Your Changes

- Write clear, concise commit messages
- Follow the [coding standards](#coding-standards)
- Add tests for new features
- Update documentation as needed

### 3. Test Your Changes

```bash
# Run tests
pytest

# Run linting
ruff check .

# Run formatting
black .

# Run type checking
mypy src/
```

### 4. Commit Your Changes

```bash
git add .
git commit -m "feat: add new feature X"
```

**Commit message conventions:**
- `feat:` - New feature
- `fix:` - Bug fix
- `docs:` - Documentation changes
- `style:` - Code style changes (formatting, etc.)
- `refactor:` - Code refactoring
- `test:` - Adding or updating tests
- `chore:` - Maintenance tasks

### 5. Push and Create Pull Request

```bash
git push origin feature/your-feature-name
```

Then create a pull request on GitHub.

**Pull Request Checklist:**
- [ ] Tests pass (`pytest`)
- [ ] Linting passes (`ruff check .`)
- [ ] Code is formatted (`black .`)
- [ ] Documentation is updated
- [ ] CHANGELOG.md is updated (for significant changes)
- [ ] PR description explains the changes
- [ ] PR is linked to related issues

---

## Coding Standards

### Python Style

We follow **PEP 8** with some modifications:
- Line length: 100 characters (enforced by Black)
- Use Black for formatting
- Use Ruff for linting

### Code Quality Tools

```bash
# Format code
black .

# Lint code
ruff check .

# Fix auto-fixable issues
ruff check --fix .

# Type checking
mypy src/
```

### Type Hints

All functions should have type hints:

```python
def my_function(param1: str, param2: int) -> Dict[str, Any]:
    """Function description.

    Args:
        param1: Description of param1
        param2: Description of param2

    Returns:
        Description of return value
    """
    return {"result": param2}
```

### Docstrings

Use **Google-style docstrings**:

```python
def example_function(arg1: str, arg2: int = 5) -> bool:
    """Brief one-line description.

    Longer description if needed. Explain what the function does,
    not how it does it (that's what code comments are for).

    Args:
        arg1: Description of arg1
        arg2: Description of arg2 (default: 5)

    Returns:
        Description of return value

    Raises:
        ValueError: When arg1 is empty

    Example:
        >>> example_function("test", 10)
        True
    """
    if not arg1:
        raise ValueError("arg1 cannot be empty")
    return len(arg1) > arg2
```

### Error Handling

- Use specific exception types
- Always log errors with context
- Provide helpful error messages

```python
try:
    result = risky_operation()
except SpecificError as e:
    logger.error(f"Failed to perform operation: {str(e)}", exc_info=True)
    return {
        "status": "error",
        "message": f"Operation failed: {str(e)}"
    }
```

---

## Testing Guidelines

### Writing Tests

- **Test file naming:** `test_*.py`
- **Test function naming:** `test_*`
- **Use pytest fixtures** for setup/teardown
- **Mock external dependencies** (APIs, databases)

```python
import pytest
from unittest.mock import Mock, patch

def test_feature_works():
    """Test that feature works as expected."""
    result = my_function("input")
    assert result == "expected_output"

def test_feature_handles_errors():
    """Test that feature handles errors gracefully."""
    with pytest.raises(ValueError):
        my_function(None)

@pytest.mark.asyncio
async def test_async_feature():
    """Test async functionality."""
    result = await async_function()
    assert result is not None
```

### Running Tests

```bash
# Run all tests
pytest

# Run specific test file
pytest tests/test_specific.py

# Run with coverage
pytest --cov

# Run with verbose output
pytest -v

# Run specific test function
pytest tests/test_specific.py::test_function_name
```

### Test Coverage

We aim for **80%+ code coverage**. Check coverage with:

```bash
pytest --cov --cov-report=html
# Open htmlcov/index.html to view report
```

---

## Documentation

### Updating Documentation

When adding features or making changes:
- Update relevant documentation in `docs/`
- Update docstrings in code
- Add examples to README if applicable
- Update CHANGELOG.md for significant changes

### Documentation Structure

```
docs/
├── INSTALLATION.md          # Installation guide
├── END_TO_END_WORKFLOW.md   # Complete workflow guide
├── PHASE_*.md               # Phase implementation docs
├── API_REFERENCE.md         # API documentation
└── TROUBLESHOOTING.md       # Common issues
```

### Writing Documentation

- Use clear, concise language
- Include code examples
- Add screenshots/diagrams when helpful
- Keep it up-to-date with code changes

---

## Review Process

### What We Look For

- **Code quality:** Clean, readable, maintainable
- **Tests:** Good coverage, meaningful assertions
- **Documentation:** Clear and complete
- **Commit history:** Logical, clear messages
- **No breaking changes** (unless discussed)

### Timeline

- We aim to review PRs within **3-5 business days**
- Complex PRs may take longer
- Feel free to ping if no response after 1 week

### Getting Your PR Merged

1. Address reviewer feedback
2. Ensure all CI checks pass
3. Get approval from at least one maintainer
4. Squash commits if requested
5. Maintainer will merge

---

## Community

### Get Help

- **GitHub Discussions:** For questions and discussions
- **GitHub Issues:** For bugs and feature requests
- **Email:** contact@produckai.com

### Stay Updated

- Watch the repository for updates
- Follow release notes in CHANGELOG.md
- Join discussions for roadmap planning

---

## Recognition

Contributors will be:
- Listed in CHANGELOG.md for their contributions
- Mentioned in release notes
- Added to GitHub contributors list

---

## License

By contributing, you agree that your contributions will be licensed under the [MIT License](LICENSE).

---

## Questions?

Don't hesitate to ask! We're here to help:
- Open a [GitHub Discussion](../../discussions)
- Comment on an issue
- Reach out via email

Thank you for contributing to ProduckAI! 🚀
