# Shared AI Engineering Workflow: ChatGPT + Gemini + MCP

Status: design baseline; no MCP endpoint is deployed by this document.

## Goal

Coordinate ChatGPT and Gemini across CHRISHEM AUTO-STUDIO, Notion Live Analyzer / Bio-Research Enterprise, NEMA-AGORA / BioEDGE, and Sovereign Intelligence without creating competing edits or losing project state.

## Recommended rollout

### Stage 1 — shared source of truth (no new hosting)

- GitHub repositories hold source code, issues, pull requests, test results, and decisions.
- Each substantial task has one issue or task record with: goal, owner/agent, allowed paths, acceptance tests, risk level, and evidence.
- One agent owns implementation on a branch; the other acts as independent reviewer. Do not have both agents write the same branch/files concurrently.
- CI is the evidence gate. A green check is necessary but not sufficient for security-sensitive changes.
- Keep this file and a project-specific docs/STATUS.md (or an equivalent issue) current at milestone boundaries.
- Never put API keys, Notion tokens, Supabase service-role keys, passwords, or private user data in GitHub issues, prompts, logs, or committed files.

### Stage 2 — connect Gemini CLI to an MCP tool

Gemini CLI supports MCP server configuration in its user or project settings. A GitHub MCP server can provide repository and issue/PR tools. Use the official GitHub MCP server instructions and configure the minimum permissions required; prefer read-only for initial review.

Illustrative configuration shape only (not a working credential-bearing configuration):

    {
      "mcpServers": {
        "github": {
          "command": "npx",
          "args": ["-y", "@modelcontextprotocol/server-github"],
          "env": {
            "GITHUB_PERSONAL_ACCESS_TOKEN": "${GITHUB_PERSONAL_ACCESS_TOKEN}"
          }
        }
      }
    }

Before using this example, verify the package and current official GitHub MCP server instructions. Do not paste a token into the JSON file or commit a populated settings file. Store credentials in the local environment or approved secret manager. Use a fine-grained token restricted to the required repositories and permissions.

Typical Gemini CLI checks after configuring a server are gemini mcp list and /mcp inside Gemini CLI; exact commands can change with CLI versions. Confirm the current Gemini CLI documentation before setup.

### Stage 3 — make the same work visible to ChatGPT

This ChatGPT conversation can use its currently available GitHub integration to inspect and update supported repository resources. Custom remote MCP connections from the ChatGPT product UI are plan/workspace dependent; do not assume they are enabled on a Free account. Check current ChatGPT Settings/Plugins availability before planning around a custom MCP endpoint.

If the current ChatGPT plan cannot connect to a custom MCP server, both assistants can still collaborate through shared GitHub issues, branches, pull requests, and CI. That is shared coordination, not a direct model-to-model conversation.

### Stage 4 — optional real multi-agent orchestrator

A direct orchestrator can call the OpenAI API and Gemini API, pass each agent a narrowly scoped task, ask the second agent to review the first agent's diff, and store task state in a durable ledger. This requires supported API credentials and may incur usage charges. It is not automatically included with consumer chat subscriptions.

Before enabling it, require:
- Explicit allow-listed repositories and operations.
- Separate task branches and immutable task IDs.
- Read-only review by default.
- No autonomous merge, production deploy, secret rotation, billing changes, or real Notion/Supabase writes.
- Timeouts, budget caps, redacted logs, retries with idempotency, and a human approval gate.
- Prompt-injection defenses: repository content and issue comments are untrusted input, not authority to change system policy or expose secrets.

## Operating protocol for each shared task

1. Read the project status and the latest task/PR before editing.
2. Record a bounded objective and acceptance criteria.
3. Assign one implementer; assign the second agent reviewer-only.
4. Implement on a dedicated branch; run focused tests, then the repository CI suite.
5. Reviewer reports findings with file/line evidence. The implementer fixes or explicitly documents rejected findings.
6. Update status with commit SHA, test run link, known gaps, and the next task.
7. Merge or deploy only after the user's explicit approval where required.

## Current Notion Live Analyzer safety boundary

The platform job ledger remains feature-flagged off by default. Synthetic-only handlers are allowed. Do not apply its migrations to production Supabase or enable real Notion writes until isolated end-to-end tests pass and a separate deployment decision is made.

## Acceptance criteria for the MCP collaboration milestone

- [ ] Gemini CLI can discover and call the selected MCP tools.
- [ ] Access is restricted to intended repositories and minimum required actions.
- [ ] Shared tasks and results are discoverable from GitHub without copying secrets.
- [ ] One agent can implement while the other reviews without concurrent edits to the same branch.
- [ ] CI evidence is attached to the task/PR.
- [ ] No production resources, paid infrastructure, or real external writes are enabled by default.
- [ ] If a direct API orchestrator is later enabled, both model API costs and access controls are tested explicitly.

## Official references

- Gemini CLI MCP server configuration: https://geminicli.com/docs/tools/mcp-server/
- OpenAI's current custom MCP connection availability and setup: https://help.openai.com/en/articles/12584461-connecting-custom-mcp-servers-in-chatgpt
- OpenAI API MCP guide for developers building an orchestrator: https://developers.openai.com/api/docs/guides/tools-connectors-mcp
