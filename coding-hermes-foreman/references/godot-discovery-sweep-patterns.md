# Godot Discovery Sweep Patterns

Godot projects have unique discovery-sweep signals that don't exist in standard
language ecosystems. These are additions to the standard 1.5a–1.5g sweep in the
foreman skill.

## 1.5h — Godot `.import` File Hygiene

Godot auto-generates a `.import` companion file for every asset (textures,
fonts, audio, 3D models). These files contain the import configuration
(compression, filtering, flags). They MUST be tracked in git — without them,
other developers get different import settings.

**Detection:**
```bash
git status --short | grep "\.import"
```

Any `??` (untracked) `.import` file means an asset was added or modified
without its import config being committed.

**Resolution:**
```bash
git add <path>/*.import
```

These are safe to track — they're small text files (~30 lines each).
Never gitignore `*.import` — doing so breaks reproducible Godot builds.

**Proven:** Escalation Doctrine 2026-07-15 — 4 untracked `.import` files
(game_icon.png, 3 Rajdhani fonts) surfaced during empty-board discovery
sweep. Assets existed on disk but import configs weren't committed.

## 1.5i — Godot `.godot/` Cache Directory

The `.godot/` directory is the editor's local cache (UID files, import state).
It MUST be in `.gitignore` — it's machine-specific and regenerated on first
editor open.

```gitignore
# Godot editor cache
.godot/
```

**Detection:** `git status` shows `?? .godot/` — if `.gitignore` is missing
this pattern, add it. Already covered in the foreman's `.gitignore` templates
for Godot projects.

## 1.5j — Stale Counts in AGENTS.md / README.md

Godot projects accumulate files fast during expansion phases. AGENTS.md
and README.md often contain line-count and file-count claims that go stale.

**Detection:**
```bash
# Compare claimed vs actual
grep -n "Lines of Code\|Total Test\|\.gd files" README.md AGENTS.md
find src/ -name "*.gd" | wc -l          # actual .gd count
find src/ -name "*test*.gd" | wc -l     # actual test count
wc -l $(find src/ -name "*.gd") | tail -1  # actual line count
```

**Fix:** Replace stale counts with verified numbers. Mechanical fix — foreman
can do directly (no worker needed).

**Proven:** Escalation Doctrine 2026-07-15 — AGENTS.md claimed `~30,000+`
lines; actual count was `~198,000` (391 .gd files, 184 test files).

## Godot-Specific Discovery Sweep Priority

When running a discovery sweep on a Godot project, add these checks AFTER
the standard 1.5a (build/headless boot) but BEFORE 1.5c (spec alignment):

1. Headless boot verification (`timeout 35 godot --headless --path .`)
2. `.import` file hygiene (`git status | grep "\.import"`)
3. `.godot/` gitignore check
4. Stale count verification in AGENTS.md / README.md
5. Then continue with standard 1.5c–1.5g

The headless boot is the Godot equivalent of `go build ./...` — it catches
parse errors, missing resources, and autoload init failures in one command.
