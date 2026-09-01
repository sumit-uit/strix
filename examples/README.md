# Strix Examples

This directory contains practical examples and configurations for using Strix in various scenarios.

## Quick Links

- **[Kiro Workflow Examples](kiro-workflow-example.md)** - Comprehensive guide for using Strix with Kiro
- **[Kiro Hooks](kiro-hooks.json)** - Pre-configured automation hooks for Kiro
- **[Setup Script](../scripts/setup-kiro.sh)** - One-command setup for Kiro integration

## What's Included

### 1. Kiro Integration

**File:** `kiro-workflow-example.md`

Complete workflow examples showing how to use Strix with the Kiro AI coding agent:
- Basic security scanning workflows
- Pre-commit security checks
- Pull request security gates
- API security testing
- Continuous monitoring setup
- Automated vulnerability remediation

**File:** `kiro-hooks.json`

Ready-to-use Kiro hooks for automating security testing:
- Scan on file save
- Post-task security validation
- Pre-commit security gate
- API endpoint security checks
- Authentication code review
- Database query security
- Weekly deep audits

### 2. Setup Scripts

**File:** `../scripts/setup-kiro.sh`

One-command setup script that:
- Checks prerequisites (Docker)
- Installs Strix if needed
- Configures LLM provider
- Sets up environment variables
- Installs Kiro skill

Usage:
```bash
cd /path/to/strix
./scripts/setup-kiro.sh
```

## Quick Start

### For Kiro Users

1. **Run setup:**
   ```bash
   ./scripts/setup-kiro.sh
   ```

2. **Copy hooks to Kiro:**
   ```bash
   # Manually create hooks in Kiro using examples from:
   cat examples/kiro-hooks.json
   ```

3. **Tell Kiro to scan:**
   ```
   "Run a quick security scan on this codebase"
   ```

### For Other AI Agents

Install the skills:
```bash
npx skills add usestrix/strix
```

Skills available:
- `penetration-testing-with-strix`
- `managed-pentesting-with-strix`
- `fix-security-vulnerabilities-with-strix`
- `ci-security-scanning-with-strix`
- `kiro-pentesting-with-strix`

## Common Workflows

### Development Workflow

```bash
# Quick check during development
strix -n -t ./ --scan-mode quick --max-budget 3

# Standard check before commit
strix -n -t ./ --scan-mode standard --max-budget 10

# Deep audit before release
strix -n -t ./ --scan-mode deep --max-budget 50
```

### CI/CD Workflow

```yaml
# Add to .github/workflows/security.yml
- name: Security Scan
  run: strix -n -t ./ --scan-mode quick --max-budget 5
  env:
    STRIX_LLM: ${{ secrets.STRIX_LLM }}
    LLM_API_KEY: ${{ secrets.LLM_API_KEY }}
```

### API Testing Workflow

```bash
# Test with OpenAPI spec
strix -n -t ./openapi.yaml -t https://api.example.com

# Test with credentials
strix -n -t https://api.example.com \
  --instruction "Credentials: user@example.com:pass123"

# Focus on specific vulnerabilities
strix -n -t https://api.example.com \
  --instruction "Focus on: IDOR, broken access control, injection"
```

## Hook Examples by Use Case

### 1. Real-time Security (Aggressive)

Scan immediately when sensitive files change:
```json
{
  "name": "Instant Security Check",
  "when": {
    "type": "fileEdited",
    "patterns": ["**/auth/*.py", "**/api/*.js", "**/sql/*.ts"]
  },
  "then": {
    "type": "runCommand",
    "command": "strix -n -t ./ --scan-mode quick --max-budget 2"
  }
}
```

### 2. Balanced Approach

Ask agent to review, not auto-scan:
```json
{
  "name": "Security Review Prompt",
  "when": {
    "type": "fileEdited",
    "patterns": ["*.py", "*.js", "*.ts"]
  },
  "then": {
    "type": "askAgent",
    "prompt": "Consider running a security scan if this change touches sensitive code"
  }
}
```

### 3. Manual Trigger (Conservative)

User decides when to scan:
```json
{
  "name": "Manual Security Scan",
  "when": {"type": "userTriggered"},
  "then": {
    "type": "runCommand",
    "command": "strix -n -t ./ --scan-mode standard --max-budget 15"
  }
}
```

## Environment Setup

### Required Environment Variables

```bash
# LLM Provider (required)
export STRIX_LLM="openai/gpt-5.4"        # or anthropic/claude-sonnet-4.6
export LLM_API_KEY="your-api-key"

# Optional
export LLM_API_BASE="http://localhost:1234"  # for local models
export PERPLEXITY_API_KEY="your-key"         # for search capabilities
export STRIX_REASONING_EFFORT="high"         # high|medium|low
```

### Add to Shell Config

```bash
# ~/.zshrc or ~/.bashrc
export STRIX_LLM="openai/gpt-5.4"
export LLM_API_KEY="sk-..."

# Then restart terminal or:
source ~/.zshrc  # or ~/.bashrc
```

## Troubleshooting

### Docker Issues

```bash
# Check if Docker is running
docker info

# Start Docker (macOS)
open -a Docker

# Start Docker (Linux)
sudo systemctl start docker
```

### Strix Not Found

```bash
# Install Strix
curl -sSL https://strix.ai/install | bash

# Or with pipx
pipx install strix-agent

# Verify installation
strix --version
```

### LLM Configuration Issues

```bash
# Verify environment variables
echo $STRIX_LLM
echo $LLM_API_KEY

# Test with minimal scan
strix -n -t https://example.com --scan-mode quick --max-budget 1
```

### Scan Failures

```bash
# Check run status
cat strix_runs/*/run.json | jq '.status'

# View agent logs
cat strix_runs/*/agent.log

# Resume with more budget
strix -n --resume <run-name> --max-budget 20
```

## Best Practices

### 1. Budget Management

Start small and scale up:
```bash
# First time: test with small budget
strix -n -t ./ --scan-mode quick --max-budget 1

# Once confident: normal usage
strix -n -t ./ --scan-mode quick --max-budget 5

# Deep audits: higher budget
strix -n -t ./ --scan-mode deep --max-budget 50
```

### 2. Scan Modes

Choose based on time/thoroughness tradeoff:
- `quick` - 5-10 minutes, $2-5, good for dev loops
- `standard` - 30 minutes, $10-20, good for PR gates
- `deep` - 2+ hours, $50+, good for audits

### 3. Instructions

Be specific:
```bash
# ❌ Vague
--instruction "check security"

# ✅ Specific
--instruction "Focus on JWT validation and session management in the auth module. Test credentials: admin@test.com:Test123"
```

### 4. Results Management

```bash
# Read latest report
cat strix_runs/$(ls -t strix_runs | head -1)/penetration_test_report.md

# Filter critical findings
cat strix_runs/*/vulnerabilities.json | \
  jq '.[] | select(.severity=="critical")'

# Export to GitHub
cp strix_runs/*/findings.sarif .github/code-scanning/
```

## Additional Resources

- **Documentation:** https://docs.strix.ai
- **Skills:** `../skills/` directory
- **Agent Guide:** `../AGENTS.md`
- **Contributing:** `../CONTRIBUTING.md`
- **Discord:** https://discord.gg/strix-ai

## Contributing Examples

Have a cool workflow or integration? Add it here:

1. Create a new markdown file in `examples/`
2. Follow the existing format
3. Include practical, tested examples
4. Submit a pull request

Examples we'd love to see:
- GitLab CI/CD integration
- Jenkins pipeline
- Azure DevOps
- Kubernetes security scanning
- Terraform security checks
- Custom hooks for specific frameworks
- Team workflow patterns

## License

All examples are provided under the Apache 2.0 license, same as Strix.
