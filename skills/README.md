# Strix Skills for AI Coding Agents

This directory contains skills that enable AI coding agents (like Kiro, Claude Code, Cursor, Codex, etc.) to use Strix for autonomous penetration testing.

## Available Skills

### 1. **penetration-testing-with-strix**
Run headless pentests against code, URLs, domains, or IPs. Covers both open-source CLI (self-hosted) and managed cloud modes. Returns validated findings with proof-of-concept exploits.

**Use when:** User asks to pentest, hack, security-scan, or find vulnerabilities.

### 2. **managed-pentesting-with-strix**
Drive the managed [app.strix.ai](https://app.strix.ai) platform via REST API. No local Docker or LLM key needed. Includes team dashboards, scheduling, PR reviews, and downloadable reports.

**Use when:** No local infrastructure available or team collaboration is needed.

### 3. **fix-security-vulnerabilities-with-strix**
Remediate findings from Strix scans and re-run to verify fixes. Automates the vulnerability → patch → validation loop.

**Use when:** Vulnerabilities found and need to be fixed and verified.

### 4. **ci-security-scanning-with-strix**
Add PR scanning to CI/CD pipelines. Works with GitHub Actions, GitLab CI, and other CI platforms.

**Use when:** Setting up automated security testing in CI/CD.

### 5. **kiro-pentesting-with-strix** ✨ NEW
Kiro-specific integration with examples of hooks, workflows, and best practices tailored for the Kiro AI coding environment.

**Use when:** Running Strix from Kiro with automated hooks and development workflows.

## Installation for Agents

Install all skills in your AI coding agent:

```bash
npx skills add usestrix/strix
```

This makes all five skills available to your agent.

## For Kiro Users

Kiro users can leverage the `kiro-pentesting-with-strix` skill for deep integration:

### Quick Setup

1. **Install Strix**:
   ```bash
   curl -sSL https://strix.ai/install | bash
   ```

2. **Configure LLM**:
   ```bash
   export STRIX_LLM="openai/gpt-5.4"
   export LLM_API_KEY="your-api-key"
   ```

3. **Run from Kiro**:
   Tell Kiro to run security scans using commands like:
   - "Run a security scan on this codebase"
   - "Check for vulnerabilities in the API"
   - "Set up a pre-commit security hook"

### Kiro Automation Examples

**Auto-scan on save:**
```json
{
  "name": "Security Scan on Save",
  "when": {"type": "fileEdited", "patterns": ["*.py", "*.js"]},
  "then": {"type": "askAgent", "prompt": "Run quick Strix scan"}
}
```

**Post-task validation:**
```json
{
  "name": "Post-Task Security",
  "when": {"type": "postTaskExecution"},
  "then": {"type": "runCommand", "command": "strix -n -t ./ --scan-mode quick --max-budget 5"}
}
```

See `kiro-pentesting-with-strix/SKILL.md` for comprehensive examples.

## Skill Format

Each skill follows the [SKILL.md specification](https://agentskills.io):

- YAML frontmatter with metadata
- Markdown documentation with usage examples
- Best practices and troubleshooting guides
- Integration examples for different scenarios

## Documentation

- **CLI Docs**: [docs.strix.ai](https://docs.strix.ai)
- **API Docs**: [docs.app.strix.ai](https://docs.app.strix.ai)
- **Agent Docs**: [AGENTS.md](../AGENTS.md)
- **LLM Context**: [docs.strix.ai/llms.txt](https://docs.strix.ai/llms.txt)

## Contributing

To add or improve skills:

1. Create/edit skill in `skills/<skill-name>/SKILL.md`
2. Follow SKILL.md format with YAML frontmatter
3. Include practical examples and troubleshooting
4. Test with actual agent workflows
5. Submit a PR

## License

All skills are licensed under Apache 2.0, same as the Strix project.

## Support

- **Discord**: [discord.gg/strix-ai](https://discord.gg/strix-ai)
- **Issues**: [github.com/usestrix/strix/issues](https://github.com/usestrix/strix/issues)
- **Docs**: [docs.strix.ai](https://docs.strix.ai)
