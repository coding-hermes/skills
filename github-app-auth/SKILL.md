---
name: github-app-auth
description: Use when a host needs GitHub auth. Mint scoped App tokens.
version: 1.0.0
author: Hermes Agent
metadata:
  hermes:
    tags: [github, auth, credentials, fleet, tokens, security]
---

# GitHub App auth for a fleet

Give any machine GitHub access without putting a durable credential on it.

> Tools: the registration and minting scripts live in
> [`coding-hermes/gh-app-auth`](https://github.com/coding-hermes/gh-app-auth).

## Why this exists

A personal access token **cannot be created programmatically** — GitHub exposes no API
for it, so a PAT fleet implies a human in the web UI every time a token is issued or
expires, plus a 90-day secret duplicated onto every host. On hosts that execute
agent-authored code, that secret is the biggest single liability in the system.

A GitHub App authenticates as itself with a private key and mints **installation access
tokens that expire in one hour**, scoped per-repo and per-permission. That inverts the
model: one durable key on one host, and every worker holding only what it needs, briefly.

Reach for this whenever a task is about to paste a token into a config, an environment
file, or a worker's shell — that is the moment to mint instead.

## The model

```
one private key (0600, one host)
        │  signs an RS256 JWT (<=10 min)
        ▼
   App id ──► POST /app/installations/{id}/access_tokens
                        │
                        ▼
        installation token (1 hour, N repos, M permissions)
                        │
                        ▼
                  worker uses it, discards it
```

Three separate things are easy to conflate. Keep them distinct:

1. **Registering** the App — once, one click, yields id + private key.
2. **Installing** it on an owner — once per account/org; an uninstalled App reaches nothing.
3. **Minting** a token — every job, cheap, no human involved.

## Registering (once per fleet)

```bash
python3 scripts/gh-app-manifest.py --host 0.0.0.0 --port 8899 \
    --public-url http://<browser-reachable-ip>:8899
```

Open that URL and click through the single GitHub confirmation page. The flow POSTs an
App manifest, GitHub redirects back with a one-time code, and the code is exchanged for
the App id and private key. Nothing is filled in by hand.

`--public-url` is mandatory off-loopback: GitHub redirects the **browser**, so a
`127.0.0.1` callback dead-ends on the user's own machine.

## Installing and using

```bash
python3 scripts/gh-app-token.py install-url                    # install page
python3 scripts/gh-app-token.py list                           # what it can reach now
python3 scripts/gh-app-token.py token  <owner> --repos <repo>  # mint (stdout only)
python3 scripts/gh-app-token.py whoami <owner> --repos <repo>  # mint + prove
```

Consume it without ever logging it:

```bash
GH_TOKEN=$(python3 scripts/gh-app-token.py token <owner> --repos <repo>)
```

## Pitfalls

- **Registration is not installation.** An App authenticates fine while installed
  nowhere; `list` returning empty is the tell, not an auth failure.
- **The token is stdout-only by design** so a command substitution captures it instead of
  a log file. Do not add a print of it elsewhere.
- **One hour.** Mint per job; never cache a token in a config or env file.
- **Mint narrowly.** Pass `--repos` (and `--permissions` when the default set is wider
  than the job needs); scope is chosen at mint time, not enforced later.
- **The private key never leaves its host** and is never committed — `.gitignore` blocks
  `*.pem` and `gh-app*.json`.
- `administration: write` is only for creating repos. Drop it when the App only pushes.
