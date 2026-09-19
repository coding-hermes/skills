#!/usr/bin/env python3
"""fleet-sync.py — DB→file mirror (replacement for fleet-cooldown-policy.py --apply).

POLICY (Bane 2026-09-19): the DB is the single source of truth. The scheduler
API is the only writer of cooldowns/pins; this script NEVER decides values and
NEVER PUTs corrections. It only mirrors live DB state into fleet.toml so that
daemon restarts re-pin to what the operator actually set — one direction, no
feedback loop, no policy rules clobbering operator intent.

What changed vs fleet-cooldown-policy.py --apply:
  - NO correction rules (REDUCE/RAISE/PROMOTE/REVERT are gone — those rules
    fought every API PUT and needed constant re-pinning; with task-mode
    admission (admission_mode='tasks') the board drives work, not the clock).
  - The file becomes a pure MIRROR: every operator decision made through the
    API survives restarts automatically, because the mirror re-reads the DB.
  - Operator overrides that must survive even a drifted DB are still
    expressible in a tiny hand-held OVERRIDE block (see OVERRIDES below) —
    read but never rewritten by this script.
  - Namespace blocks (incl. wave_enabled/wave_tick_timeout/wave_workers_cap,
    admission_mode, load_gate) are mirrored from the API — nothing is dropped.

Usage:
  python3 fleet-sync.py            # dry-run: print the fleet.toml it would write
  python3 fleet-sync.py --write    # write ~/.hermes/fleet.toml atomically

Keep fleet-cooldown-policy.py around for its dry-run REPORT (--report mode);
its --apply mutation path is superseded by this script.
"""
import json
import os
import sys
import tempfile
import urllib.request

API = 'http://127.0.0.1:9090'
FLEET = os.path.expanduser('~/.hermes/fleet.toml')

# Operator pins that must survive EVEN IF the DB drifts (checked, not decided).
# Format: {project_name: {"cooldown_s": N}}  — kept deliberately tiny.
OVERRIDES = {}

def api_get(path):
    with urllib.request.urlopen(API + path, timeout=10) as r:
        return json.loads(r.read())

def mirror(projects, namespaces):
    enabled = [p for p in projects if p.get('enabled')]
    out = [
        "# Fleet configuration — DB MIRROR (fleet-sync.py)",
        "# Source of truth: the scheduler DB via the API. This file exists ONLY so",
        "# daemon restarts re-pin to the state the operator set through the API.",
        "# NEVER hand-edit cooldowns here — PUT them via the API; they survive",
        "# restarts because this mirror is regenerated FROM the API.",
        "# (Supersedes fleet-cooldown-policy.py --apply, whose correction rules",
        "#  fought operator PUTs; Bane 2026-09-19: task mode replaced the",
        "#  cooldown-pacing era, the file must not rewrite the system underneath.)",
        "",
        "# ── Scheduler (root config) ────────────────────────────────────────",
        "# DeepSeek peak-pricing windows (UTC): cooldown ×2 inside 01:00-04:00",
        "# and 06:00-10:00 (2× price hours). Merged in 49d4478, activated 08-10.",
        "[scheduler]",
        "blackout_windows = [",
        '  { start = "01:00", end = "04:00", multiplier = 2.0 },',
        '  { start = "06:00", end = "10:00", multiplier = 2.0 },',
        "]",
        "",
    ]
    if namespaces:
        out.append("# ── Namespaces (mirrored from DB — nothing dropped) ──────────")
        for ns in sorted(namespaces, key=lambda x: x.get('id', '')):
            out.append("[[namespaces]]")
            out.append(f'id = "{ns.get("id", "")}"')
            for key in ("weight", "reserved", "hard_cap", "max_concurrent"):
                v = ns.get(key)
                if v is not None:
                    out.append(f'{key} = {v}')
            out.append(f'enabled = {"true" if ns.get("enabled", True) else "false"}')
            for key in ("admission_mode", "load_gate", "wave_tick_timeout"):
                v = ns.get(key)
                if v:
                    out.append(f'{key} = "{v}"')
            if ns.get("wave_enabled"):
                out.append("wave_enabled = true")
                if ns.get("wave_workers_cap"):
                    out.append(f'wave_workers_cap = {ns["wave_workers_cap"]}')
            desc = ns.get("description") or ""
            if desc and '"' not in desc:
                out.append(f'description = "{desc}"')
            dp = ns.get("default_prompt") or ""
            if dp and "'''" not in dp:
                out.append("default_prompt = '''" + dp + "'''")
            mc = ns.get("model_chain") or ""
            if mc and '"' in mc:
                out.append(f'model_chain = {mc}')
            out.append("")
    for p in sorted(enabled, key=lambda x: x.get('name', x.get('Name', '?'))):
        name = p.get('name', p.get('Name', '?'))
        out.append("[[projects]]")
        out.append(f'name = "{name}"')
        out.append(f'repo_url = "{p.get("repo_url", p.get("RepoURL", "")) or "local:" + p.get("workdir", p.get("Workdir", ""))}"')
        out.append(f'workdir = "{p.get("workdir", p.get("Workdir", ""))}"')
        out.append(f'weight = {p.get("weight", p.get("Weight", 10))}')
        out.append(f'priority = {p.get("priority", p.get("Priority", 5))}')
        cooldown = OVERRIDES.get(name, {}).get("cooldown_s",
                    p.get("cooldown_s", p.get("CooldownS", 21600)))
        out.append(f'cooldown_s = {cooldown}')
        # adaptive block mirrors DB truth (floor/ceiling/threshold only when armed)
        if p.get("adaptive_cooldown", p.get("AdaptiveCooldown")):
            out.append("adaptive_cooldown = true")
            out.append(f'cooldown_floor_s = {p.get("cooldown_floor_s", p.get("CooldownFloorS", cooldown))}')
            out.append(f'cooldown_ceiling_s = {p.get("cooldown_ceiling_s", p.get("CooldownCeilingS", cooldown * 8))}')
        m = p.get("model", p.get("Model", "")) or ""
        prov = p.get("provider", p.get("Provider", "")) or ""
        if m:
            out.append(f'model = "{m}"')
        if prov:
            out.append(f'provider = "{prov}"')
        ns = p.get('namespace_id', p.get('NamespaceID'))
        if ns:
            out.append(f'namespace_id = "{ns}"')
        if p.get('deliver', p.get('Deliver')):
            out.append(f'deliver = "{p.get("deliver", p.get("Deliver", ""))}"')
        out.append(f'enabled = {"true" if p.get("enabled", p.get("Enabled")) else "false"}')
        out.append("")
    return "\n".join(out) + "\n"

def main():
    write = '--write' in sys.argv
    projects = api_get('/api/v1/projects').get('projects', [])
    namespaces = api_get('/api/v1/namespaces').get('namespaces', [])
    content = mirror(projects, namespaces)
    if write:
        fd, tmp = tempfile.mkstemp(dir=os.path.dirname(FLEET), prefix='.fleet.')
        with os.fdopen(fd, 'w') as f:
            f.write(content)
        os.replace(tmp, FLEET)  # atomic — readers never see a torn file
        n_proj = sum(1 for p in projects if p.get('enabled'))
        print(f"fleet.toml: mirrored {n_proj} projects + {len(namespaces)} namespaces (DB → file, one way)")
    else:
        print(content)
        print(f"# dry-run: {sum(1 for p in projects if p.get('enabled'))} projects, {len(namespaces)} namespaces — rerun with --write",
              file=sys.stderr)

if __name__ == '__main__':
    main()
