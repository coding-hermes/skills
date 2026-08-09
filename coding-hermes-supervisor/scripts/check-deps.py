#!/usr/bin/env python3
"""
Multi-language dependency checker for coding-hermes projects.

Checks Go (go list -u -m), Python (pip list --outdated via venv),
Rust (cargo outdated if installed), and Node (pnpm/npm/yarn outdated)
for all known coding-hermes project directories.

Usage:
    python3 scripts/check-deps.py

Outputs a report suitable for generating Upgrade deps tasks in tasks.md.
"""

import subprocess, os, json, sys

HOME = os.path.expanduser('~')

# Known coding-hermes project dirs
PROJECTS = {
    'helios-work': '~/helios-work',
    'dexdat-memory': '~/dexdat-memory',
    'dexdat-core': '~/dexdat-core',
    'muster': '~/muster',
    'musterflow': '~/musterflow',
    'helix': '~/helix',
    'warpfs': '~/warpfs',
    'asce': '~/asce',
    'Kobayashi-Maru': '~/Kobayashi-Maru',
    'ai_plays_poke': '~/ai_plays_poke',
    'bunker': '~/bunker',
    'hermes4friends-infra': '~/hermes4friends-infra',
    'gitreins-poc': '~/gitreins-poc',
    'hivemind-work': '~/hivemind-work',
    'off-by-one': '~/off-by-one',
}


def check_go(wd):
    """Check Go dependencies via go list -u -m -json all."""
    go_mod = os.path.join(wd, 'go.mod')
    if not os.path.isfile(go_mod):
        return None

    r = subprocess.run(
        ['go', 'list', '-u', '-m', '-json', 'all'],
        cwd=wd, capture_output=True, text=True, timeout=120
    )
    if r.returncode != 0:
        return f"ERROR: go list failed: {r.stderr.strip()[:100]}"

    outdated = []
    for line in r.stdout.strip().split('\n'):
        line = line.strip()
        if not line:
            continue
        try:
            mod = json.loads(line)
        except json.JSONDecodeError:
            continue
        if 'Update' in mod:
            outdated.append(
                f"  {mod['Path']}: {mod['Version']} → {mod['Update']['Version']}"
            )

    if outdated:
        return f"OUTDATED ({len(outdated)})\n" + '\n'.join(outdated[:15])
    return "CLEAN"


def check_python(wd):
    """Check Python dependencies via pip list --outdated (project venv)."""
    venv_dirs = [
        os.path.join(wd, '.venv', 'bin', 'pip'),
        os.path.join(wd, 'venv', 'bin', 'pip'),
        os.path.join(wd, '.env', 'bin', 'pip'),
    ]
    pip_path = None
    for p in venv_dirs:
        if os.path.isfile(p):
            pip_path = p
            break

    # Also check for Python project markers
    pyproject = os.path.join(wd, 'pyproject.toml')
    req_txt = os.path.join(wd, 'requirements.txt')
    has_python = os.path.isfile(pyproject) or os.path.isfile(req_txt) or pip_path

    if not has_python:
        return None  # Not a Python project
    if not pip_path:
        return "SKIP (no venv)"

    r = subprocess.run(
        [pip_path, 'list', '--outdated', '--format=columns'],
        capture_output=True, text=True, timeout=60
    )
    if r.returncode != 0:
        return f"ERROR: {r.stderr.strip()[:100]}"

    lines = r.stdout.strip().split('\n')
    if len(lines) <= 2:
        return "CLEAN"

    out = [f"OUTDATED ({len(lines) - 2})"]
    for line in lines[2:]:
        out.append(f"  {line.strip()}")
    return '\n'.join(out[:25])  # cap at 25 lines


def check_rust(wd):
    """Check Rust dependencies via cargo outdated."""
    if not os.path.isfile(os.path.join(wd, 'Cargo.toml')):
        return None

    r = subprocess.run(
        ['which', 'cargo-outdated'],
        capture_output=True, text=True, timeout=5
    )
    if r.returncode != 0:
        return "SKIP (cargo-outdated not installed)"

    r = subprocess.run(
        ['cargo', 'outdated'],
        cwd=wd, capture_output=True, text=True, timeout=120
    )
    if r.returncode != 0:
        return f"ERROR: {r.stderr.strip()[:100]}"

    lines = [l.strip() for l in r.stdout.split('\n')
             if l.strip() and not l.startswith('Name')
             and not l.startswith('---') and len(l.strip()) > 10]
    if lines:
        return f"OUTDATED ({len(lines)})\n" + '\n'.join(f"  {l}" for l in lines[:10])
    return "CLEAN"


def check_node(wd):
    """Check Node dependencies via pnpm/npm/yarn outdated."""
    if not os.path.isfile(os.path.join(wd, 'package.json')):
        return None

    if os.path.isfile(os.path.join(wd, 'pnpm-lock.yaml')):
        cmd = ['pnpm', 'outdated', '--no-color']
    elif os.path.isfile(os.path.join(wd, 'yarn.lock')):
        cmd = ['yarn', 'outdated', '--no-color']
    else:
        cmd = ['npm', 'outdated', '--no-color']

    r = subprocess.run(cmd, cwd=wd, capture_output=True, text=True, timeout=60)
    # npm outdated returns 1 when outdated packages exist
    if r.returncode not in [0, 1]:
        return f"ERROR: {r.stderr.strip()[:100]}"

    lines = [l.strip() for l in r.stdout.split('\n')
             if l.strip() and not l.startswith('Package')]
    if lines:
        return f"OUTDATED ({len(lines)})\n" + '\n'.join(f"  {l}" for l in lines[:10])
    return "CLEAN"


def main():
    print("=" * 72)
    print("  Coding Hermes — Multi-Language Dependency Checker")
    print("=" * 72)

    any_outdated = False

    for name, wd in sorted(PROJECTS.items()):
        if not os.path.isdir(wd):
            print(f"\n--- {name} ---")
            print("  DIRECTORY NOT FOUND")
            continue

        print(f"\n--- {name} ({wd}) ---")

        for lang, check_fn in [
            ('Go', check_go),
            ('Python', check_python),
            ('Rust', check_rust),
            ('Node', check_node),
        ]:
            result = check_fn(wd)
            if result is None:
                continue  # Not applicable

            if result.startswith('OUTDATED'):
                any_outdated = True
                print(f"  🔶 {lang}: {result}")
            elif result.startswith('CLEAN'):
                print(f"  ✅ {lang}: up to date")
            elif result.startswith('SKIP'):
                print(f"  ⏭️  {lang}: {result[5:]}")
            elif result.startswith('ERROR'):
                print(f"  ⚠  {lang}: {result}")
            else:
                print(f"  ? {lang}: {result}")

    print("\n" + "=" * 72)
    if any_outdated:
        print("  🔶 Some projects have outdated dependencies.")
        print("  Add upgrade tasks via the supervisor's Phase 7.")
    else:
        print("  ✅ All dependencies up to date.")
    print("=" * 72)

    return 1 if any_outdated else 0


if __name__ == '__main__':
    sys.exit(main())
