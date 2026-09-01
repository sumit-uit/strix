# Kiro + Strix Integration Setup Complete! 🎉

Your Strix installation is now fully configured to work with Kiro, the AI coding agent platform.

## What Was Set Up

### 1. ✅ Development Environment
- Installed Python dependencies with `uv`
- Docker verified and running
- Strix CLI installed and ready (version 1.5.3)
- Code quality tools configured (ruff, mypy, pyright, bandit)

### 2. ✅ Kiro-Specific Skill Created
**Location:** `skills/kiro-pentesting-with-strix/SKILL.md`

This skill provides Kiro with comprehensive guidance for:
- Running security scans during development
- Setting up automated testing hooks
- Integrating with CI/CD pipelines
- API security testing workflows
- Vulnerability remediation loops

### 3. ✅ Example Files Created

#### Workflow Examples
**File:** `examples/kiro-workflow-example.md`

Complete workflow examples including:
- Pre-commit security checks
- Pull request security gates
- API testing with authentication
- Continuous security monitoring
- Automated vulnerability fixing

#### Hook Configurations
**File:** `examples/kiro-hooks.json`

Ready-to-use Kiro hooks for:
- Real-time security scanning on file save
- Post-task security validation
- Pre-commit security gates
- API endpoint security checks
- Authentication code reviews
- Database query security checks
- Weekly deep security audits

#### Setup Script
**File:** `scripts/setup-kiro.sh`

One-command setup script that:
- Checks prerequisites
- Installs Strix if needed
- Configures LLM provider
- Sets up environment variables

### 4. ✅ Documentation
- `skills/README.md` - Overview of all available skills
- `examples/README.md` - Guide to using examples and hooks

## Quick Start Guide

### For First-Time Setup

Run the automated setup script:

```bash
./scripts/setup-kiro.sh
```

This will guide you through:
1. Docker verification
2. Strix installation (if needed)
3. LLM provider configuration
4. Environment variable setup

### Tell Kiro to Run Security Scans

Once set up, you can interact with Kiro naturally:

```
"Run a quick security scan on this codebase"
"Check for vulnerabilities in the API"
"Set up automated security testing"
"Test this endpoint for IDOR vulnerabilities"
"Scan the authentication module for security issues"
```

### Manual Configuration

If you prefer manual setup:

1. **Configure LLM Provider:**
   ```bash
   export STRIX_LLM="openai/gpt-5.4"  # or anthropic/claude-sonnet-4.6
   export LLM_API_KEY="your-api-key-here"
   ```

2. **Add to shell config:**
   ```bash
   echo 'export STRIX_LLM="openai/gpt-5.4"' >> ~/.zshrc
   echo 'export LLM_API_KEY="your-key"' >> ~/.zshrc
   source ~/.zshrc
   ```

3. **Test installation:**
   ```bash
   strix --version
   docker info
   strix -n -t https://example.com --scan-mode quick --max-budget 1
   ```

## Common Kiro Commands

### Quick Development Scan
```bash
strix -n -t ./ --scan-mode quick --max-budget 5
```

### Pre-Commit Check
```bash
strix -n -t ./ --scan-mode quick --max-budget 3
```

### PR Security Gate
```bash
strix -n -t ./ --scan-mode standard --max-budget 15
```

### API Security Test
```bash
strix -n -t https://api.example.com --max-budget 20 \
  --instruction "Focus on: authentication, authorization, IDOR"
```

### Deep Audit
```bash
strix -n -t ./ --scan-mode deep --max-budget 50
```

## Kiro Hooks Examples

### Hook 1: Scan on File Save
Create this hook in Kiro to automatically scan when files change:

```json
{
  "name": "Security Scan on Save",
  "when": {
    "type": "fileEdited",
    "patterns": ["*.py", "*.js", "*.ts"]
  },
  "then": {
    "type": "askAgent",
    "prompt": "Run a quick Strix security scan on the modified file"
  }
}
```

### Hook 2: Post-Task Security
Run security checks after completing tasks:

```json
{
  "name": "Post-Task Security",
  "when": {"type": "postTaskExecution"},
  "then": {
    "type": "runCommand",
    "command": "strix -n -t ./ --scan-mode quick --max-budget 5"
  }
}
```

### Hook 3: Manual Trigger
Create a button to run scans on-demand:

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

## Understanding Scan Results

After a scan completes, results are saved to `strix_runs/<run-name>/`:

- **`penetration_test_report.md`** - Executive summary (read first!)
- **`vulnerabilities/*.md`** - Individual vulnerability details with PoCs
- **`vulnerabilities.json`** - Structured findings for programmatic use
- **`vulnerabilities.csv`** - Spreadsheet-compatible format
- **`findings.sarif`** - SARIF 2.1.0 for GitHub Code Scanning
- **`run.json`** - Run metadata, status, and cost information

### Reading Results with Kiro

Tell Kiro to analyze results:
```
"Show me the latest security scan results"
"Summarize the critical vulnerabilities found"
"Create fixes for the SQL injection issues"
```

## Exit Codes (Important for Automation)

- **Exit 0** - No vulnerabilities found (in scanned areas)
- **Exit 1** - Fatal error (Docker down, missing config, etc.)
- **Exit 2** - Vulnerabilities detected

**Note:** Exit 0 doesn't guarantee full coverage if budget/turn limits were reached.

## Budget Guidelines

Choose budgets based on scan depth and time:

| Scan Type | Budget | Duration | Use Case |
|---|---|---|---|
| Quick | $2-5 | 5-10 min | Dev loops, file changes |
| Standard | $10-20 | 30 min | PR gates, feature testing |
| Deep | $50+ | 2+ hours | Release audits, compliance |

## Next Steps

1. **Run Your First Scan**
   ```bash
   strix -n -t ./ --scan-mode quick --max-budget 5
   ```

2. **Set Up Kiro Hooks**
   - Copy examples from `examples/kiro-hooks.json`
   - Create hooks in Kiro using the explorer view or command palette
   - Customize patterns and budgets for your workflow

3. **Integrate with CI/CD**
   - See `examples/kiro-workflow-example.md` for GitHub Actions examples
   - Use the `ci-security-scanning-with-strix` skill for other platforms

4. **Explore Advanced Features**
   - Multi-target scanning (code + deployed app)
   - API testing with OpenAPI/Swagger specs
   - Focused testing with custom instructions
   - Resume interrupted scans

## Troubleshooting

### Docker Not Running
```bash
# Check status
docker info

# Start Docker (macOS)
open -a Docker

# Start Docker (Linux)
sudo systemctl start docker
```

### Environment Variables Not Set
```bash
# Check current values
echo $STRIX_LLM
echo $LLM_API_KEY

# Set them (add to ~/.zshrc or ~/.bashrc to persist)
export STRIX_LLM="openai/gpt-5.4"
export LLM_API_KEY="your-key"
```

### Scan Hangs or Fails
```bash
# View run status
cat strix_runs/*/run.json | jq '.status'

# Check agent logs
cat strix_runs/*/agent.log

# Resume with more budget
strix -n --resume <run-name> --max-budget 20
```

## Resources

- **Kiro Skill:** `skills/kiro-pentesting-with-strix/SKILL.md`
- **Workflow Examples:** `examples/kiro-workflow-example.md`
- **Hook Examples:** `examples/kiro-hooks.json`
- **Setup Script:** `scripts/setup-kiro.sh`
- **Agent Guide:** `AGENTS.md`
- **CLI Docs:** https://docs.strix.ai
- **API Docs:** https://docs.app.strix.ai
- **Discord Community:** https://discord.gg/strix-ai

## Support

Need help?
- Join our Discord: https://discord.gg/strix-ai
- Check the docs: https://docs.strix.ai
- Open an issue: https://github.com/usestrix/strix/issues

## Contributing

Found a bug or have a feature request?
1. Check existing issues
2. Open a new issue with details
3. Submit a pull request

## Safety Reminder

⚠️ **Only scan targets you own or have explicit permission to test.**

Unauthorized security testing is illegal. You are responsible for:
- Obtaining proper authorization
- Staying within agreed scope
- Complying with local laws

---

**Happy pentesting with Kiro! 🔒🤖**
