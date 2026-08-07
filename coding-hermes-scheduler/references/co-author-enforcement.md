# CODING_HERMES_CO_AUTHOR — Git Co-Author Enforcement

## Setup (single source of truth)

```bash
# Add to ~/.hermes/.env
echo 'CODING_HERMES_CO_AUTHOR="Your Name <you@example.com>"' >> ~/.hermes/.env
```

## Usage (foreman, agents, workers)

Every coding-hermes agent reads from the same source:

```bash
CO_AUTHOR=$(grep CODING_HERMES_CO_AUTHOR ~/.hermes/.env | cut -d= -f2- | tr -d '"')
# If unset → prompt user for co-author name/email, save to .env, then continue

# Every commit:
git commit -m "message" -m "Co-authored-by: $CO_AUTHOR"
```

## Foreman skill integration

The `coding-hermes-foreman` skill (Step 0 / Self-Heal) reads `CODING_HERMES_CO_AUTHOR`
from `~/.hermes/.env`. If the env var is missing, it prompts the user and saves the
response before proceeding.

## Git commit template (global, for agent direct commits)

```bash
cat > ~/.gitmessage << 'EOF'

Co-authored-by: Your Name <you@example.com>
EOF
git config --global commit.template ~/.gitmessage
```

Note: `commit.template` only applies to interactive `git commit` (no `-m`).
When using `git commit -m`, always include the co-author trailer explicitly:

```bash
git commit -m "message" -m "Co-authored-by: Your Name <you@example.com>"
```

## Verification

```bash
# Check last commit has co-author
git log -1 --format='%B' | grep "Co-authored-by"

# Check all commits in a range
git log --format='%h %B' --since="7 days ago" | grep -c "Co-authored-by"
```

## History

- 2026-07-18: Established `CODING_HERMES_CO_AUTHOR` env var as single source of truth
- 2026-07-18: Foreman skill updated to read from .env, prompt user if missing
- 2026-07-18: Name corrected: handle → Real Name
