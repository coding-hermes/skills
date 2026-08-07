# coding-hermes-config

**Status:** Active  
**Category:** infrastructure  
**Layer:** Foundation (Phase 0)

---

## Purpose

This skill handles ALL configuration for coding-hermes. It is loaded FIRST by every other coding-hermes skill. It asks the user for their specific setup — API keys, model names, provider names, workdir paths, repo URLs — and stores them in DuckBrain under `/fleet/config/`. No other coding-hermes skill should contain hardcoded credentials, model names, or paths.

---

## Trigger

- Any coding-hermes skill loads this skill first.
- User runs `/fleet setup` or `/fleet config`.
- First-time initialization of a coding-hermes project.

---

## What You Ask The User

### Step 1 — Provider Keys

Ask which LLM providers they have access to. For each one they confirm, ask for:

| Provider | Config Key | What To Ask |
|----------|-----------|-------------|
| DeepSeek | `deepseek_api_key` | "Do you have a DeepSeek API key? If so, paste it." |
| OpenAI | `openai_api_key` | "Do you have an OpenAI API key? If so, paste it." |
| Anthropic | `anthropic_api_key` | "Do you have an Anthropic API key? If so, paste it." |
| xAI / Grok | `xai_api_key` | "Do you have xAI/Grok credentials? If so, paste your key." |
| OpenRouter | `openrouter_api_key` | "Do you use OpenRouter? If so, paste your key." |
| Google Gemini | `google_api_key` | "Do you have a Google AI API key? If so, paste it." |
| MiniMax | `minimax_api_key` | "Do you have a MiniMax API key? If so, paste it." |
| ZhipuAI / GLM | `zhipuai_api_key` | "Do you have a ZhipuAI/GLM API key? If so, paste it." |
| Codex | `codex_api_key` | "Do you have Codex credentials? If so, paste your key." |

Store each key in DuckBrain: `/fleet/config/keys/<provider>` with value `{"api_key": "sk-..."}`.

**NEVER ask the user to store keys in files.** Always use DuckBrain or a secrets manager. If no secrets manager is available, guide them to set environment variables instead.

### Step 2 — Model Assignment

For each provider they configured, ask which model they want to use for each role:

| Role | Description | Default |
|------|------------|---------|
| **Foreman** | Inspects, plans, delegates. Needs reasoning. Cheap is OK. | `deepseek-chat` |
| **Worker (Go)** | Writes Go code. Needs precision. | `deepseek-chat` |
| **Worker (Python)** | Writes Python. Needs precision. | `deepseek-chat` |
| **Worker (TypeScript)** | Writes TS/React. Needs precision. | `deepseek-chat` |
| **Worker (General)** | Fallback for any language. | `deepseek-chat` |
| **Spec Writer** | Writes detailed specs. Needs structure. | `deepseek-chat` |

Store in DuckBrain: `/fleet/config/model-assignments/<role>` with value `{"model": "...", "provider": "..."}`.

### Step 3 — Workdir Paths

For each project they want managed:

1. Ask: "What projects do you want coding-hermes to manage?"
2. For each project, ask: "Where is the repo cloned on your machine?"
3. Ask: "What's the GitHub org/repo for this project?" (e.g., `myorg/myrepo`)
4. Ask: "How important is this project? (0-10)" → maps to priority
5. Ask: "How resource-heavy is each foreman tick? (0-10)" → maps to weight

Store in DuckBrain: `/fleet/config/projects/<name>` with full config.

### Step 4 — Scheduler Setup

1. Ask: "Where should the scheduler database live?" (default: `~/.hermes/coding-hermes/scheduler.db`)
2. Ask: "What port should the scheduler listen on?" (default: `9090`)
3. Ask: "Max concurrent foreman spawns?" (default: `8`)
4. Ask: "Weight budget?" (default: `100`)
5. Ask: "Fastest tick interval?" (default: `20m`)
6. Ask: "Slowest tick interval?" (default: `24h`)

### Step 5 — Hermes Plugin Setup

1. Confirm: "Should I register the coding-hermes plugin with Hermes?"
2. If yes, guide: `ln -s <repo>/plugin ~/.hermes/plugins/coding-hermes`
3. Ask: "Should I create a trigger cron to hit the scheduler every minute?"
4. If yes, explain: "This replaces 33 static cron jobs with ONE trigger cron."

---

## DuckBrain Schema

All config lives under `/fleet/config/`:

```
/fleet/config/
├── keys/
│   ├── deepseek       → {"api_key": "sk-..."}
│   ├── openai         → {"api_key": "sk-..."}
│   └── ...
├── model-assignments/
│   ├── foreman        → {"model": "deepseek-chat", "provider": "deepseek"}
│   ├── worker-go      → {"model": "...", "provider": "..."}
│   └── ...
├── projects/
│   ├── my-project     → {"repo": "myorg/myproject", "workdir": "/home/me/myproject", ...}
│   └── ...
└── scheduler/
    └── settings       → {"db_path": "...", "port": 9090, "budget": 100, ...}
```

---

## After Setup

Once config is complete, tell the user:

```
Setup complete. Your fleet is configured:

• Providers: <list>
• Foreman model: <model> @ <provider>
• Worker models: <list>
• Projects: <N> configured
• Scheduler: <db> on :<port>

Next steps:
1. Build the scheduler binary: `git clone https://github.com/coding-hermes/scheduler && cd scheduler && make build`
2. Create `fleet.toml` from `fleet.example.toml` (one `[[projects]]` block per repo)
3. Run the daemon: `./bin/schedulerd -db ~/.hermes/coding-hermes/scheduler.db -config fleet.toml -listen 127.0.0.1:9090 --namespace-mode --max-concurrent 4 --min-interval 30s --tick-timeout 7200s --gateway-url http://127.0.0.1:8642 --gateway-key "$API_SERVER_KEY"`
4. Verify: `curl http://127.0.0.1:9090/api/v1/health`

> Full step-by-step install (prerequisites, gateway key, systemd service,
> cron-job migration): the **Getting Started** section of the skills repo
> README — https://github.com/coding-hermes/skills#getting-started
```

---

## Pitfalls

- **Never prompt for config mid-task.** Ask all config questions at the START.
- **Never write keys to files.** Use DuckBrain or env vars only.
- **Never assume defaults exist.** If no config found, STOP and run this skill.
- **Config skill loads first.** All other coding-hermes skills call `skill_view("coding-hermes-config")` before doing anything.
