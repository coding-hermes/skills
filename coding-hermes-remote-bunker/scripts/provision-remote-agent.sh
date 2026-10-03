#!/usr/bin/env bash
# provision-remote-agent.sh — bring ONE remote agent to a working state, reproducibly.
#
# Every step here was exercised on the live fleet (boxes 02/03/04 and a rebuilt box 01) before being
# written down. Nothing is inferred from documentation.
#
# What it sets up, in order:
#   1. gh CLI in the AGENT'S HOME (survives every exec: the home is a bind mount)
#   2. git identity for the agent
#   3. a RESTRICTED credential + the agent clones ITS OWN repo, then gh becomes git's credential helper
#   4. a voice on the bus: crier-mcp + the agent's own key + the config entry
#   5. a Hermes gateway unit for that agent on the host (one unit per agent, one port per agent)
#   6. memory: a DuckBrain MCP entry pointing at the shared store over the tailnet
#
# Usage:
#   provision-remote-agent.sh --agent <name> --host <box-ip> [--port 8642] [--repo <owner/name>]
#                             [--duckbrain-url http://<host>:3000/mcp] [--check-only]
#
# Requires, on the machine you RUN it from:
#   * root SSH (or a sudo-capable user) to the box
#   * the fleet bus URL + token, and a private key per agent (PKCS#8 PEM ed25519)
#   * a GitHub App that can mint a token scoped to the agent's repository
#
# It is idempotent: every step skips when already satisfied, and it re-reads state instead of
# trusting the log.
set -euo pipefail

AGENT=""; HOST=""; PORT=""; REPO=""; DUCK_URL=""; CHECK_ONLY=0
BUS_URL="${BUS_URL:-http://127.0.0.1:8767}"
BIN_DIR="${BIN_DIR:-$HOME/bin}"          # where the shippable binaries live on THIS machine
KEY_DIR="${KEY_DIR:-$HOME/crier-fleet/keys}"
TOKEN_FILE="${TOKEN_FILE:-$HOME/.hermes/secrets/crier-fleet.env}"
GH_TOKEN_FILE="${GH_TOKEN_FILE:-}"       # optional: a pre-minted token file

while [ $# -gt 0 ]; do
  case "$1" in
    --agent) AGENT="$2"; shift 2 ;;
    --host) HOST="$2"; shift 2 ;;
    --port) PORT="$2"; shift 2 ;;
    --repo) REPO="$2"; shift 2 ;;
    --duckbrain-url) DUCK_URL="$2"; shift 2 ;;
    --check-only) CHECK_ONLY=1; shift ;;
    *) echo "unknown flag: $1" >&2; exit 2 ;;
  esac
done
[ -n "$AGENT" ] && [ -n "$HOST" ] || { echo "need --agent and --host" >&2; exit 2; }

# THE TRAP, stated once because it costs an hour every time:
#   the Unix USER and the HOME are "bunker-<agent>"; the AGENT ID is the bare name.
#   Using the bare name for ownership or su fails with 'invalid user' / 'user does not exist'.
USER_NAME="bunker-${AGENT}"
HOME_DIR="/home/${USER_NAME}"
PORT="${PORT:-8642}"

say() { printf '  %-22s %s\n' "$1" "$2"; }

if [ "$CHECK_ONLY" = 1 ]; then
  ssh -o BatchMode=yes "root@${HOST}" "
    h=${HOME_DIR}
    printf '  gh=%s repo=%s bus=%s key=%s gateway=%s duckbrain=%s\n' \
      \"\$([ -x \$h/.local/bin/gh ] && echo yes || echo NO)\" \
      \"\$([ -d \$h/${AGENT}/.git ] && echo yes || echo NO)\" \
      \"\$([ -x \$h/.local/bin/crier-mcp ] && echo yes || echo NO)\" \
      \"\$([ -f \$h/.crier/agent.key ] && echo yes || echo NO)\" \
      \"\$(systemctl is-active hermes-gateway-${AGENT} 2>/dev/null || echo absent)\" \
      \"\$(grep -c duckbrain \$h/.hermes/config.yaml 2>/dev/null)\""
  exit 0
fi

echo "== ${AGENT} @ ${HOST} (user ${USER_NAME}, home ${HOME_DIR}, gateway port ${PORT}) =="

# ---------------------------------------------------------------- 1 + 2. toolchain + identity
echo "-- toolchain and identity"
ssh -o BatchMode=yes "root@${HOST}" "
  set -e
  h=${HOME_DIR}; u=${USER_NAME}
  [ -d \$h ] || { echo '  FATAL: no home at' \$h; exit 1; }
  install -d -m 755 -o \$u -g \$u \$h/.local/bin
  if [ ! -x \$h/.local/bin/gh ]; then
    VER=\$(curl -fsSL https://api.github.com/repos/cli/cli/releases/latest \
          | grep -oE '\"tag_name\": *\"v[0-9.]+\"' | head -1 | grep -oE 'v[0-9.]+')
    [ -n \"\$VER\" ] || { echo '  gh: could not resolve the latest release tag'; exit 1; }
    curl -fsSL -o /tmp/gh.tgz \"https://github.com/cli/cli/releases/download/\${VER}/gh_\${VER#v}_linux_amd64.tar.gz\"
    tar -xzf /tmp/gh.tgz -C /tmp
    install -m 755 /tmp/gh_\${VER#v}_linux_amd64/bin/gh \$h/.local/bin/gh
    rm -rf /tmp/gh.tgz /tmp/gh_\${VER#v}_linux_amd64
    echo '  gh: installed' \$VER
  else
    echo '  gh: already present'
  fi
  printf '[user]\n\tname = %s\n\temail = %s\n' '${GIT_NAME:-fleet-agent}' '${GIT_EMAIL:-agent@example.invalid}' > \$h/.gitconfig
  chown \$u:\$u \$h/.gitconfig
  echo '  identity: ' \$(git -C \$h config --file \$h/.gitconfig user.email)
"

# ---------------------------------------------------------------- 3. credential + clone
if [ -n "$REPO" ]; then
  echo "-- credential + clone (the AGENT clones, not root)"
  if [ -n "$GH_TOKEN_FILE" ] && [ -f "$GH_TOKEN_FILE" ]; then
    scp -q -o BatchMode=yes "$GH_TOKEN_FILE" "root@${HOST}:/tmp/agent.gh.token"
    ssh -o BatchMode=yes "root@${HOST}" "
      u=${USER_NAME}; h=${HOME_DIR}
      install -m 600 -o \$u -g \$u /tmp/agent.gh.token \$h/.gh-token
      rm -f /tmp/agent.gh.token
      echo '  token: installed (0600, agent-owned)'
    "
  else
    echo "  token: SKIPPED (pass --gh-token-file); the clone will fail without one"
  fi
  ssh -o BatchMode=yes "root@${HOST}" "
    u=${USER_NAME}; h=${HOME_DIR}
    su -s /bin/sh \$u -c \"
      set -e
      export GH_TOKEN=\\\$(cat \$h/.gh-token)
      export PATH=\$h/.local/bin:/usr/bin:/bin
      [ -d \$h/${AGENT}/.git ] || gh repo clone ${REPO} \$h/${AGENT}
      gh auth setup-git                    # makes plain git use the gh credential helper
      cd \$h/${AGENT} && git fetch --quiet && git push --dry-run origin HEAD >/dev/null && echo '  clone + push path: OK'
    \"
  "
fi

# ---------------------------------------------------------------- 4. voice on the bus
echo "-- voice on the bus"
if [ -x "${BIN_DIR}/crier-mcp" ] && [ -f "${KEY_DIR}/${AGENT}.key" ]; then
  scp -q -o BatchMode=yes "${BIN_DIR}/crier-mcp" "root@${HOST}:/tmp/crier-mcp"
  scp -q -o BatchMode=yes "${KEY_DIR}/${AGENT}.key" "root@${HOST}:/tmp/agent.key"
  TOKEN=$(sed -n 's/^CR_AUTH_TOKEN=//p' "$TOKEN_FILE")
  {
    printf '  crier:\n    command: %s/.local/bin/crier-mcp\n    args: []\n    enabled: true\n    env:\n' "$HOME_DIR"
    printf '      CRIER_HTTP_URL: %s\n      CRIER_AGENT_ID: %s\n      CRIER_AUTH_TOKEN: %s\n      CRIER_AGENT_PRIVATE_KEY_FILE: %s/.crier/agent.key\n' \
      "$BUS_URL" "$AGENT" "$TOKEN" "$HOME_DIR"
  } > /tmp/agent-mcp-block.yaml
  scp -q -o BatchMode=yes /tmp/agent-mcp-block.yaml "root@${HOST}:/tmp/mcp-block.yaml"
  rm -f /tmp/agent-mcp-block.yaml
  ssh -o BatchMode=yes "root@${HOST}" "
    set -e
    u=${USER_NAME}; h=${HOME_DIR}; cfg=\$h/.hermes/config.yaml
    install -d -m 755 -o \$u -g \$u \$h/.local/bin
    install -d -m 700 -o \$u -g \$u \$h/.crier
    install -m 755 -o \$u -g \$u /tmp/crier-mcp \$h/.local/bin/crier-mcp
    install -m 600 -o \$u -g \$u /tmp/agent.key \$h/.crier/agent.key
    rm -f /tmp/crier-mcp /tmp/agent.key
    [ -f \$cfg ] || { echo '  FATAL: no \$cfg'; exit 1; }
    cp -a \$cfg \$cfg.bak-\$(date +%Y%m%d-%H%M%S)
    if grep -q CRIER_AGENT_ID \$cfg; then
      echo '  config: already wired'
    elif grep -q '^mcp_servers:' \$cfg; then
      # INSERT under the existing key. Appending a second mcp_servers: block is invalid YAML —
      # this is the failure mode where an agent gets the binary and no wiring, silently.
      python3 - \$cfg /tmp/mcp-block.yaml <<'PY'
import sys
cfg, block = sys.argv[1], open(sys.argv[2], encoding='utf-8').read().rstrip('\n')
lines = open(cfg, encoding='utf-8').read().splitlines()
out, done = [], False
for ln in lines:
    out.append(ln)
    if not done and ln.startswith('mcp_servers:'):
        out.append(block); done = True
open(cfg, 'w', encoding='utf-8').write('\n'.join(out) + '\n')
print('  config: crier inserted under the existing mcp_servers:')
PY
    else
      { echo; echo 'mcp_servers:'; cat /tmp/mcp-block.yaml; } >> \$cfg
      echo '  config: mcp_servers block appended'
    fi
    chown \$u:\$u \$cfg; rm -f /tmp/mcp-block.yaml
    grep -q CRIER_AGENT_ID \$cfg && echo '  config: read back OK'
  "
else
  say "voice" "SKIPPED — need ${BIN_DIR}/crier-mcp and ${KEY_DIR}/${AGENT}.key on this machine"
fi

# ---------------------------------------------------------------- 5. gateway unit
echo "-- gateway unit (host-side, one per agent)"
ssh -o BatchMode=yes "root@${HOST}" "
  set -e
  u=${USER_NAME}; h=${HOME_DIR}
  unit=/etc/systemd/system/hermes-gateway-${AGENT}.service
  if [ -f \$unit ]; then echo '  unit: already present'; else
    cat > \$unit <<EOF
[Unit]
Description=Hermes gateway for agent ${AGENT} (api_server on :${PORT})
After=network-online.target

[Service]
Type=simple
User=\$u
Environment=HOME=\$h
Environment=HERMES_HOME=\$h/.hermes
Environment=PATH=\$h/.local/bin:/usr/local/bin:/usr/bin:/bin
ExecStart=\$h/.local/bin/hermes gateway run --port ${PORT}
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF
  fi
  systemctl daemon-reload
  systemctl enable --now hermes-gateway-${AGENT}.service >/dev/null 2>&1 || true
  echo '  unit: ' \$(systemctl is-active hermes-gateway-${AGENT}.service)
  ss -ltn | grep -q ':${PORT}' && echo '  listening on :${PORT}' || echo '  WARNING: nothing on :${PORT} yet'
"

# ---------------------------------------------------------------- 6. DuckBrain (shared store)
if [ -n "$DUCK_URL" ]; then
  echo "-- memory (DuckBrain over the tailnet — ONE store, never a per-box copy)"
  ssh -o BatchMode=yes "root@${HOST}" "
    u=${USER_NAME}; h=${HOME_DIR}; cfg=\$h/.hermes/config.yaml
    grep -q duckbrain \$cfg 2>/dev/null && { echo '  duckbrain: already present'; exit 0; }
    python3 - \$cfg '${DUCK_URL}' <<'PY'
import sys
cfg, url = sys.argv[1], sys.argv[2]
lines = open(cfg, encoding='utf-8').read().splitlines()
block = ['  duckbrain:', '    url: %s' % url, '    enabled: true']
out, done = [], False
for ln in lines:
    out.append(ln)
    if not done and ln.startswith('mcp_servers:'):
        out.extend(block); done = True
if not done:
    out += ['', 'mcp_servers:'] + block
open(cfg, 'w', encoding='utf-8').write('\n'.join(out) + '\n')
print('  duckbrain: wired to the shared store')
PY
    chown \$u:\$u \$cfg
  "
fi

echo
echo "== verify (re-read the box; never trust the log above) =="
bash "$0" --agent "$AGENT" --host "$HOST" --port "$PORT" --check-only
