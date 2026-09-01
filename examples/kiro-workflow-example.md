# Kiro + Strix Workflow Examples

This document provides real-world examples of using Strix with Kiro for automated security testing.

## Table of Contents

1. [Basic Workflow](#basic-workflow)
2. [Pre-Commit Security Check](#pre-commit-security-check)
3. [Pull Request Security Gate](#pull-request-security-gate)
4. [API Security Testing](#api-security-testing)
5. [Continuous Security Monitoring](#continuous-security-monitoring)
6. [Vulnerability Remediation Loop](#vulnerability-remediation-loop)

---

## Basic Workflow

### Step 1: Initial Setup

Tell Kiro to set up Strix:

```
You: "Set up Strix for security testing in this project"
```

Kiro will:
1. Check if Docker is running
2. Install Strix if needed
3. Configure LLM provider
4. Run a test scan

### Step 2: Run First Scan

```
You: "Run a quick security scan on this codebase"
```

Kiro will execute:
```bash
strix -n -t ./ --scan-mode quick --max-budget 5
```

### Step 3: Review Results

```
You: "Show me the security scan results"
```

Kiro will read and summarize:
- `strix_runs/latest/penetration_test_report.md`
- Critical and high-severity findings
- Recommended fixes

---

## Pre-Commit Security Check

Automate security checks before committing code.

### Manual Check

```
You: "Check for security issues before I commit this code"
```

Kiro runs:
```bash
strix -n -t ./ --scan-mode quick --max-budget 3
```

If vulnerabilities found (exit code 2):
```
Kiro: "⚠️ Found 3 vulnerabilities:
1. SQL Injection in user_controller.py (HIGH)
2. XSS in template.html (MEDIUM)
3. Insecure password storage in auth.py (CRITICAL)

Should I create fixes for these issues?"
```

### Automated Hook

Create a Kiro hook for automatic checks:

```json
{
  "name": "Pre-Commit Security",
  "when": {"type": "promptSubmit"},
  "then": {
    "type": "askAgent",
    "prompt": "Before the user commits, run: strix -n -t ./ --scan-mode quick --max-budget 3"
  }
}
```

---

## Pull Request Security Gate

Test code before creating PRs.

### Interactive Mode

```
You: "I'm ready to create a PR. Run a comprehensive security check first."
```

Kiro executes:
```bash
# Scan the diff against main branch
strix -n -t ./ --scan-mode standard --scope-mode diff --diff-base origin/main --max-budget 15
```

Results:
```
Kiro: "Security scan complete:
✅ No critical issues in changed files
⚠️ 1 medium-severity finding: Potential IDOR in new API endpoint
📊 Scanned 12 changed files, 847 lines of code

Details in: strix_runs/pr-scan-2024-08-20/penetration_test_report.md

Should I proceed with PR creation?"
```

### GitHub Actions Integration

```
You: "Set up automated security scanning in GitHub Actions"
```

Kiro creates `.github/workflows/strix-security.yml`:

```yaml
name: Strix Security Scan

on:
  pull_request:
    branches: [main, develop]

jobs:
  security-scan:
    runs-on: ubuntu-latest

    steps:
      - name: Checkout code
        uses: actions/checkout@v6
        with:
          fetch-depth: 0

      - name: Install Strix
        run: curl -sSL https://strix.ai/install | bash

      - name: Run security scan
        env:
          STRIX_LLM: ${{ secrets.STRIX_LLM }}
          LLM_API_KEY: ${{ secrets.LLM_API_KEY }}
        run: |
          strix -n -t ./ --scan-mode quick --max-budget 5

      - name: Upload SARIF results
        uses: github/codeql-action/upload-sarif@v3
        if: always()
        with:
          sarif_file: strix_runs/*/findings.sarif

      - name: Comment PR with results
        if: always()
        uses: actions/github-script@v7
        with:
          script: |
            const fs = require('fs');
            const report = fs.readFileSync('strix_runs/*/penetration_test_report.md', 'utf8');
            github.rest.issues.createComment({
              issue_number: context.issue.number,
              owner: context.repo.owner,
              repo: context.repo.repo,
              body: `## 🔒 Strix Security Scan Results\n\n${report}`
            });
```

---

## API Security Testing

Test APIs with authentication and specific focus areas.

### Test Local API

```
You: "Test the API running on localhost:8000 for security issues.
Focus on authentication and authorization flaws."
```

Kiro runs:
```bash
strix -n -t http://localhost:8000 \
  --scan-mode standard \
  --max-budget 20 \
  --instruction "Focus on: broken authentication, broken access control, IDOR, privilege escalation, JWT attacks"
```

### Test with Credentials

```
You: "Test the staging API with these test credentials:
- Email: test@example.com
- Password: TestPass123
- API Key: test_sk_abc123xyz"
```

Kiro executes:
```bash
strix -n -t https://api.staging.example.com \
  --scan-mode standard \
  --max-budget 25 \
  --instruction "
    Credentials:
    - Email: test@example.com
    - Password: TestPass123
    - API Key: test_sk_abc123xyz

    Focus on:
    - Broken access control
    - IDOR vulnerabilities
    - Privilege escalation
    - API key exposure
    - Rate limiting bypass
  "
```

### OpenAPI/Swagger Testing

```
You: "Test our API using the OpenAPI spec in docs/openapi.yaml"
```

Kiro runs:
```bash
strix -n \
  -t ./docs/openapi.yaml \
  -t https://api.example.com \
  --scan-mode standard \
  --max-budget 30
```

This tests all endpoints defined in the spec against the live API.

---

## Continuous Security Monitoring

Set up ongoing security monitoring.

### Daily Security Scans

```
You: "Set up daily security scans and notify me of any findings"
```

Kiro creates a cron job or scheduled task:

```bash
# Crontab entry (runs at 2 AM daily)
0 2 * * * cd /path/to/project && strix -n -t ./ --scan-mode standard --max-budget 20 && \
  if [ $? -eq 2 ]; then \
    mail -s "Security Issues Found" user@example.com < strix_runs/*/penetration_test_report.md; \
  fi
```

### Hook for Continuous Monitoring

```json
{
  "name": "File Change Security Monitor",
  "when": {
    "type": "fileEdited",
    "patterns": ["**/*.py", "**/*.js", "**/*.ts"]
  },
  "then": {
    "type": "askAgent",
    "prompt": "Files changed. Run quick security scan on modified files to detect new vulnerabilities early."
  }
}
```

### Slack Notifications

```
You: "Send security scan results to our #security Slack channel"
```

Kiro creates a script:

```bash
#!/bin/bash
# scan-and-notify.sh

strix -n -t ./ --scan-mode standard --max-budget 20

if [ $? -eq 2 ]; then
  # Vulnerabilities found
  REPORT=$(cat strix_runs/*/penetration_test_report.md)

  curl -X POST -H 'Content-type: application/json' \
    --data "{\"text\":\"🚨 Security Scan Alert\n\n$REPORT\"}" \
    $SLACK_WEBHOOK_URL
fi
```

---

## Vulnerability Remediation Loop

Automated detect → fix → verify workflow.

### Step 1: Detect Vulnerabilities

```
You: "Scan for SQL injection vulnerabilities"
```

Kiro runs:
```bash
strix -n -t ./ \
  --scan-mode standard \
  --instruction "Focus exclusively on SQL injection and database security issues" \
  --max-budget 15
```

Results:
```
Kiro: "Found 2 SQL injection vulnerabilities:

1. HIGH - SQL Injection in user_search()
   File: app/controllers/user_controller.py:42
   PoC: ?search=' OR '1'='1

2. MEDIUM - Unsafe query concatenation
   File: app/models/product.py:128
   PoC: ?category=1' UNION SELECT password FROM users--
"
```

### Step 2: Generate Fixes

```
You: "Create fixes for these SQL injection issues"
```

Kiro analyzes vulnerabilities and creates patches:

```python
# Before (vulnerable)
def user_search(query):
    sql = f"SELECT * FROM users WHERE name = '{query}'"
    return db.execute(sql)

# After (fixed)
def user_search(query):
    sql = "SELECT * FROM users WHERE name = ?"
    return db.execute(sql, (query,))
```

### Step 3: Verify Fixes

```
You: "Verify the fixes resolved the vulnerabilities"
```

Kiro re-runs Strix on the fixed code:

```bash
strix -n -t ./ \
  --scan-mode standard \
  --instruction "Re-test SQL injection vulnerabilities in user_controller.py and product.py" \
  --max-budget 10
```

Results:
```
Kiro: "✅ Verification complete:
- SQL injection in user_search(): FIXED
- Unsafe query in product.py: FIXED

No SQL injection vulnerabilities detected in re-scan."
```

### Automated Remediation Hook

Create a hook for automatic fix attempts:

```json
{
  "name": "Auto-Fix Security Issues",
  "when": {"type": "postToolUse", "toolTypes": "shell"},
  "then": {
    "type": "askAgent",
    "prompt": "If Strix found vulnerabilities, analyze them, propose fixes, and re-run Strix to verify. Iterate until all critical and high severity issues are resolved."
  }
}
```

---

## Advanced Examples

### Multi-Target Comprehensive Scan

```
You: "Run a comprehensive security audit of our entire stack:
- Local source code
- Staging API at api.staging.example.com
- Production site at www.example.com (read-only, no exploits)"
```

Kiro executes:
```bash
strix -n \
  -t ./ \
  -t https://api.staging.example.com \
  -t https://www.example.com \
  --scan-mode deep \
  --max-budget 100 \
  --instruction "
    Production site (www.example.com): Read-only testing, no exploitation
    Staging API: Full testing including exploitation
    Source code: White-box analysis
  "
```

### Business Logic Testing

```
You: "Test for business logic flaws in our payment processing"
```

Kiro runs:
```bash
strix -n -t https://app.example.com \
  --scan-mode standard \
  --max-budget 30 \
  --instruction "
    Focus on business logic vulnerabilities:
    - Payment amount manipulation
    - Race conditions in transactions
    - Discount/coupon abuse
    - Order total tampering
    - Multi-use promotional codes
    - Refund policy bypass

    Test flows:
    1. Add items to cart
    2. Apply discounts
    3. Process payment
    4. Request refund
  "
```

### Resume Interrupted Scan

```
You: "Resume the security scan that was interrupted yesterday"
```

Kiro lists available runs and resumes:
```bash
# List runs
ls -la strix_runs/

# Resume specific run
strix -n --resume strix_runs/scan-2024-08-19-important
```

---

## Tips for Kiro Users

### Optimize Budget Usage

```
Development:    --max-budget 3-5    (quick checks)
Pre-commit:     --max-budget 5-10   (focused scans)
PR reviews:     --max-budget 10-20  (comprehensive)
Production:     --max-budget 50+    (deep audits)
```

### Effective Instructions

Be specific about what to test:

```bash
# ❌ Vague
--instruction "Check security"

# ✅ Specific
--instruction "Test authentication: focus on JWT validation, session fixation, and password reset flows. Use credentials admin@example.com:Password123"
```

### Interpret Exit Codes

```bash
strix -n -t ./ --max-budget 5
EXIT_CODE=$?

if [ $EXIT_CODE -eq 0 ]; then
  echo "✅ No vulnerabilities (in scanned areas)"
elif [ $EXIT_CODE -eq 1 ]; then
  echo "❌ Scan failed (check logs)"
elif [ $EXIT_CODE -eq 2 ]; then
  echo "⚠️  Vulnerabilities found (review report)"
fi
```

### Parallel Scanning

Run multiple targeted scans in parallel:

```bash
# Scan different components simultaneously
strix -n -t ./api --instruction "Focus on API security" --max-budget 10 &
strix -n -t ./web --instruction "Focus on XSS and CSRF" --max-budget 10 &
strix -n -t ./auth --instruction "Focus on authentication" --max-budget 10 &
wait

# Combine results
cat strix_runs/*/vulnerabilities.json | jq -s 'add'
```

---

## Troubleshooting with Kiro

### Issue: Docker Not Running

```
You: "The scan failed with a Docker error"

Kiro: "Let me check Docker status..."
```

```bash
docker info

# If Docker is down:
# macOS: open -a Docker
# Linux: sudo systemctl start docker
```

### Issue: Budget Exhausted

```
You: "The scan stopped early due to budget limits"

Kiro: "The scan hit the budget cap. Options:
1. Review partial results: cat strix_runs/*/penetration_test_report.md
2. Resume with more budget: strix -n --resume <run-name> --max-budget 20
3. Use quick mode for faster, cheaper scans"
```

### Issue: No Vulnerabilities but Suspicious

```
You: "The scan found nothing, but I'm not convinced"

Kiro: "Let's run a deeper scan with specific instructions..."
```

```bash
strix -n -t ./ \
  --scan-mode deep \
  --max-budget 50 \
  --instruction "
    Deep analysis required. Focus on:
    - Complex business logic flaws
    - Race conditions
    - Second-order vulnerabilities
    - Time-based attacks
  "
```

---

## Summary

Kiro + Strix provides powerful security automation:

1. **Setup once** with `scripts/setup-kiro.sh`
2. **Scan anywhere** - code, APIs, sites, repos
3. **Automate checks** with hooks and CI/CD
4. **Fix and verify** in a continuous loop
5. **Monitor continuously** with scheduled scans

For more details, see:
- `skills/kiro-pentesting-with-strix/SKILL.md`
- `AGENTS.md`
- https://docs.strix.ai
