# Security Policy

## Supported Versions

We provide security updates for the following versions of ProduckAI MCP Server:

| Version | Supported          |
| ------- | ------------------ |
| 0.7.x   | :white_check_mark: |
| 0.6.x   | :white_check_mark: |
| < 0.6   | :x:                |

## Reporting a Vulnerability

We take the security of ProduckAI MCP Server seriously. If you discover a security vulnerability, please follow these guidelines:

### What to Report

Please report any security issues that could affect:
- **Authentication & Authorization** - Unauthorized access to data
- **Data Privacy** - Exposure of sensitive customer data or API keys
- **Code Injection** - SQL injection, command injection, etc.
- **API Security** - Issues with API integrations (Slack, JIRA, etc.)
- **Dependency Vulnerabilities** - Critical vulnerabilities in dependencies

### How to Report

**Please DO NOT report security vulnerabilities through public GitHub issues.**

Instead, please report security vulnerabilities by emailing:

**security@produckai.com**

Include the following information in your report:
- **Type of vulnerability** (e.g., code injection, authentication bypass)
- **Affected component** (e.g., Slack integration, PRD generation)
- **Steps to reproduce** the vulnerability
- **Potential impact** of the vulnerability
- **Suggested fix** (if you have one)
- **Your contact information** for follow-up

### What to Expect

1. **Acknowledgment**: We'll acknowledge receipt of your report within **48 hours**

2. **Initial Assessment**: We'll provide an initial assessment within **5 business days**, including:
   - Confirmation of the vulnerability
   - Severity rating (Critical, High, Medium, Low)
   - Estimated timeline for fix

3. **Status Updates**: We'll keep you informed of progress:
   - Weekly updates for Critical/High severity issues
   - Bi-weekly updates for Medium/Low severity issues

4. **Resolution**: Once fixed, we'll:
   - Release a patch version
   - Publish a security advisory (with your credit, if desired)
   - Notify affected users

### Disclosure Policy

- **Coordinated Disclosure**: We follow responsible disclosure practices
- **Embargo Period**: We request a 90-day embargo before public disclosure
- **Public Advisory**: We'll publish a security advisory after the fix is released
- **CVE Assignment**: We'll work with you to assign a CVE if appropriate

## Security Best Practices

When using ProduckAI MCP Server, follow these best practices:

### API Key Management

- **Never commit API keys** to version control
- **Use environment variables** for all sensitive credentials
- **Rotate keys regularly** (quarterly recommended)
- **Use separate keys** for development, staging, and production
- **Revoke compromised keys** immediately

### Configuration Security

```json
// ✅ Good: Use environment variables in Claude Desktop config
{
  "mcpServers": {
    "produckai": {
      "command": "produckai-mcp",
      "env": {
        "ANTHROPIC_API_KEY": "${ANTHROPIC_API_KEY}"
      }
    }
  }
}

// ❌ Bad: Hardcoded API keys
{
  "mcpServers": {
    "produckai": {
      "command": "produckai-mcp",
      "env": {
        "ANTHROPIC_API_KEY": "sk-ant-1234567890..."
      }
    }
  }
}
```

### Integration Security

- **OAuth over API tokens** when possible (Slack, Google Drive)
- **Principle of least privilege** - Only request necessary scopes
- **Review permissions** before authorizing integrations
- **Audit access logs** regularly

### Data Privacy

- **Customer data is local** - ProduckAI stores data in local SQLite
- **API calls are direct** - No data sent to third-party servers (except integration APIs)
- **Embeddings optional** - You can disable OpenAI embeddings if desired
- **Backup security** - Encrypt backups if they contain sensitive data

### Dependency Security

We use the following tools to ensure dependency security:
- **pip-audit** - Scan for known vulnerabilities
- **Dependabot** - Automated dependency updates
- **Safety** - Check for security issues in dependencies

To check your installation:
```bash
pip install pip-audit
pip-audit
```

## Security Features

ProduckAI MCP Server includes the following security features:

### Input Validation

- **SQL injection protection** - Parameterized queries only
- **Path traversal prevention** - File path validation
- **Input sanitization** - All user inputs are validated

### Authentication

- **API key validation** - Keys are validated before use
- **Token expiration** - OAuth tokens are refreshed automatically
- **Credential encryption** - Credentials stored with encryption (when applicable)

### Logging

- **No sensitive data in logs** - API keys and tokens are redacted
- **Audit trail** - Key operations are logged for review
- **Log rotation** - Logs are rotated to prevent disk fill

### Rate Limiting

- **API rate limiting** - Respect integration API limits
- **Backoff strategies** - Automatic retry with exponential backoff
- **Quota tracking** - Monitor API usage

## Known Security Considerations

### Local Execution

ProduckAI MCP Server runs **locally on your machine** as part of Claude Desktop:
- It has **file system access** within your user permissions
- It can **make network requests** to integration APIs
- It **stores data locally** in SQLite database

**Recommendation**: Review the code before running if you have security concerns.

### Third-Party Integrations

ProduckAI connects to third-party services:
- **Slack** - Reads messages and user data
- **Google Drive** - Accesses files you grant permission to
- **Zoom** - Downloads meeting recordings and transcripts
- **JIRA** - Reads and writes issues

**Recommendation**: Use OAuth and review permissions carefully.

### AI Model Usage

ProduckAI uses AI models (Anthropic Claude, OpenAI):
- **Customer feedback is sent** to AI APIs for processing
- **PRD generation requires** Anthropic API access
- **Embeddings (optional)** are generated via OpenAI

**Recommendation**: Review your organization's AI usage policies before deploying.

## Compliance

### Data Processing

- **GDPR**: User responsible for data processing agreements with customers
- **CCPA**: User responsible for consumer privacy rights
- **SOC 2**: ProduckAI is a client-side tool; users maintain data control

### Data Retention

- **Local storage only** - All data stored in local SQLite database
- **User-controlled deletion** - Users can delete data at any time
- **No telemetry** - ProduckAI does not send usage telemetry

## Security Roadmap

We're working on the following security enhancements:

- [ ] **Secrets management integration** (HashiCorp Vault, AWS Secrets Manager)
- [ ] **End-to-end encryption** for stored credentials
- [ ] **Audit log export** for compliance
- [ ] **Role-based access control** for team deployments
- [ ] **Security scanning** in CI/CD pipeline

## Contact

For security-related questions or concerns:
- **Security vulnerabilities**: security@produckai.com
- **General security questions**: GitHub Discussions
- **Security features/requests**: GitHub Issues (use [FEATURE] tag)

## Acknowledgments

We appreciate security researchers who help keep ProduckAI secure. Researchers who report valid security vulnerabilities will be:
- **Credited** in the security advisory (if desired)
- **Thanked** in the CHANGELOG
- **Listed** in our Hall of Fame (coming soon)

Thank you for helping keep ProduckAI and our users secure!
