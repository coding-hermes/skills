#!/usr/bin/env python3
"""current-models-report — what models are actually current, and what to use for what.

Standalone, stdlib-only, read-only. Point it at a models.dev cache (and optionally a router
registry) and it writes one markdown document:

  * WHAT IS CURRENT    — models released inside the freshness window, with provider reach
  * WHAT YOU CANNOT USE — current models with no registry row, or with no tier row
                          (a model with no tier is invisible to chain resolution)
  * WHAT TO USE        — per-category picks from the tier table, marked measured vs declared,
                          plus the declared fallback ladder

Quick start (no registry, no keys):

    # grab the public models.dev registry once
    curl -fsSL https://models.dev/api.json -o models-dev.json
    python3 current-models-report.py --cache models-dev.json

With a router registry (models.jsonl + model_tier.jsonl + fallback_lanes.jsonl):

    python3 current-models-report.py --cache models-dev.json \\
        --tables ./data/tables --write current-models.md

Exit codes: 0 clean, 2 staleness threshold breached, 3 the cache is missing or unreadable.
Only exit 2 means "the data is getting old" — that is the code to alert on.

Defaults are a convenience for the reference layout (~/.hermes/models_dev_cache.json and
~/task-router/data/tables); nothing here requires that layout. Every path is a flag.
"""
from __future__ import annotations

import argparse
import collections
import datetime as dt
import json
import os
import pathlib
import sys

HOME = pathlib.Path.home()
DEFAULT_CACHE = HOME / ".hermes/models_dev_cache.json"
DEFAULT_TABLES = HOME / "task-router/data/tables"

# Non-dialogue model families: present in the registry feed, irrelevant to chain routing.
NON_CHAT = ("embed", "rerank", "whisper", "tts", "-audio", "moderation",
            "dall-e", "flux", "sdxl", "stable-diffusion", "veo-", "sora",
            "seedream", "seedance", "kling", "upscal", "guard-", "ocr",
            "gpt-image", "imagen-", "hailuo", "runway", "midjourney", "nano-banana")

MEASURED_PREFIXES = ("bench", "measured", "live-probe", "probe")
DECLARED_PREFIXES = ("family", "estimate", "inherited")


def norm(model_id: str) -> str:
    """Provider prefixes (`z-ai/`), snapshot tags (`:0731`) and alias markers (`~`) differ
    between a registry row and a feed entry for the same weights."""
    s = (model_id or "").strip().lower()
    s = s.split("/")[-1]
    s = s.split(":")[0]
    return s.lstrip("~")


def source_class(src: str) -> str:
    s = (src or "").lower()
    if s.startswith(MEASURED_PREFIXES):
        return "measured"
    if s.startswith(DECLARED_PREFIXES):
        return "declared"
    return "other"


def load_jsonl(path: pathlib.Path) -> list[dict]:
    rows: list[dict] = []
    if not path.exists():
        return rows
    for line in path.read_text(errors="replace").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            rows.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return rows


def is_chat_like(name: str, model_id: str) -> bool:
    hay = f"{name} {model_id}".lower()
    return not any(tag in hay for tag in NON_CHAT)


def collect_feed(cache: dict) -> dict:
    """feed -> {norm_id: {name, family, dates:set, providers:set}}"""
    universe: dict[str, dict] = {}
    for provider, pobj in (cache or {}).items():
        if not isinstance(pobj, dict):
            continue
        # Accept both the nested shape ({"models": {...}}) and a flat provider->models map.
        models = pobj.get("models") if isinstance(pobj.get("models"), dict) else pobj
        for mid, m in models.items():
            if not isinstance(m, dict):
                continue
            if not any(k in m for k in ("release_date", "last_updated", "cost", "limit", "family")):
                continue  # provider metadata key, not a model
            name = m.get("name") or mid
            if not is_chat_like(name, mid):
                continue
            release = str(m.get("release_date") or m.get("last_updated") or "")[:10]
            for key in {mid, m.get("canonical_model_id") or mid}:
                entry = universe.setdefault(
                    norm(key),
                    {"name": name, "family": m.get("family") or "", "dates": set(), "providers": set()},
                )
                if release:
                    entry["dates"].add(release)
                entry["providers"].add(provider)
    return universe


def display(path: pathlib.Path) -> str:
    """Never bake an absolute home path into a document that may be published."""
    try:
        return "~/" + str(pathlib.Path(path).resolve().relative_to(HOME))
    except ValueError:
        return str(path)


def build_report(cache_path: pathlib.Path, tables_dir: pathlib.Path, window_days: int,
                 max_age_days: int, today: dt.date) -> tuple[str, dict, int]:
    problems: list[str] = []
    cache_age = (today - dt.date.fromtimestamp(cache_path.stat().st_mtime)).days
    if cache_age > 7:
        problems.append(f"registry feed snapshot is {cache_age} days old (refresh job may be broken)")

    cache = json.loads(cache_path.read_text())
    universe = collect_feed(cache)

    first = next((v for v in cache.values() if isinstance(v, dict)), {})
    if not universe and not isinstance(first.get("models"), dict):
        problems.append("feed has no recognisable model entries (unsupported shape?)")

    registry = load_jsonl(tables_dir / "models.jsonl")
    tiers = load_jsonl(tables_dir / "model_tier.jsonl")
    fallback = load_jsonl(tables_dir / "fallback_lanes.jsonl")
    has_registry = bool(registry)

    reg_by_model: dict[str, list[dict]] = collections.defaultdict(list)
    for row in registry:
        reg_by_model[norm(row.get("model"))].append(row)

    rel_dates = sorted(str(r["release_date"])[:10] for r in registry if r.get("release_date"))
    newest_reg = rel_dates[-1] if rel_dates else None
    reg_age = (today - dt.date.fromisoformat(newest_reg)).days if newest_reg else None

    per_cat: dict[str, list[tuple]] = collections.defaultdict(list)
    best_perf: dict[str, float] = {}
    tier_cats: collections.Counter = collections.Counter()
    for t in tiers:
        m = norm(t.get("model"))
        tier_cats[m] += 1
        perf = t.get("perf")
        if isinstance(perf, (int, float)):
            per_cat[t.get("category") or "?"].append((float(perf), m, str(t.get("tier_source") or "")))
            best_perf[m] = max(best_perf.get(m, 0.0), float(perf))

    cutoff = (today - dt.timedelta(days=window_days)).isoformat()
    current = sorted(
        ((max(e["dates"]), n, e) for n, e in universe.items() if e["dates"] and max(e["dates"]) >= cutoff),
        reverse=True,
    )

    untracked = [c for c in current if has_registry and c[1] not in reg_by_model]
    blind = [c for c in current if has_registry and c[1] in reg_by_model and tier_cats.get(c[1], 0) == 0]

    if has_registry and reg_age is not None and reg_age > max_age_days:
        problems.append(f"registry carries nothing newer than {newest_reg} ({reg_age} days old)")
    if has_registry and current and len(untracked) / len(current) > 0.5:
        problems.append(f"{len(untracked)}/{len(current)} current models have no registry row")

    recs: dict[str, list[tuple]] = {}
    for cat, rows in per_cat.items():
        ranked = sorted(rows, key=lambda r: (source_class(r[2]) == "measured", r[0]), reverse=True)
        seen: dict[str, tuple] = {}
        for perf, model, src in ranked:
            if model in seen:
                continue
            seen[model] = (perf, model, src)
            if len(seen) >= 5:
                break
        recs[cat] = list(seen.values())

    # A model that tops several categories is one entry per MODEL, not one per category.
    top_counts: dict[str, int] = {}
    for rows in recs.values():
        if rows:
            top_counts[rows[0][1]] = top_counts.get(rows[0][1], 0) + 1
    dominant = sorted(
        ((m, c) for m, c in top_counts.items() if c >= 5),
        key=lambda mc: (-mc[1], mc[0]),
    )

    summary = {
        "date": today.isoformat(),
        "feed_snapshot": dt.date.fromtimestamp(cache_path.stat().st_mtime).isoformat(),
        "feed_age_days": cache_age,
        "distinct_models": len(universe),
        "current_models": len(current),
        "window_days": window_days,
        "registry_rows": len(registry),
        "registry_present": has_registry,
        "registry_newest_release": newest_reg,
        "registry_newest_age_days": reg_age,
        "release_date_coverage": f"{len(rel_dates)}/{len(registry)}" if registry else "n/a",
        "untracked_current": len(untracked) if has_registry else None,
        "blind_ranked": len(blind) if has_registry else None,
        "categories": len(recs),
        "dominant_models": [{"model": m, "categories": c} for m, c in dominant],
        "problems": problems,
        "status": "STALE" if problems else "OK",
    }

    out: list[str] = []
    add = out.append
    add("# Current models")
    add("")
    add(f"Generated {today.isoformat()} from the registry feed snapshot of "
        f"{summary['feed_snapshot']} ({cache_age}d old)"
        + (f" and router tables at `{display(tables_dir)}`." if has_registry else "; no router tables supplied, so this is the feed view only."))
    add("")
    add("**Generated file — not hand-edited.** Regenerate with `scripts/current-models-report.py "
        "--write`; local edits are lost on the next run.")
    add("")
    add("## Status")
    add("")
    add(f"- status: **{summary['status']}**")
    add(f"- current (released in last {window_days}d): **{len(current)}** of {len(universe)} distinct dialogue-ish models")
    if has_registry:
        add(f"- registry newest release: **{newest_reg}** ({reg_age}d old); release_date coverage {len(rel_dates)}/{len(registry)}")
        add(f"- current models with NO registry row: **{len(untracked)}**")
        add(f"- registry models with NO tier row (never selectable): **{len(blind)}**")
    if problems:
        add("")
        add("Threshold breaches:")
        out.extend(f"- {p}" for p in problems)

    if recs:
        add("")
        add("## Recommended per category")
        add("")
        add("Rank comes from the tier table. A model absent from it is invisible to chain "
            "resolution, however good it is. `measured` outranks `declared`; ties read as "
            "equivalent, not ordered.")
        add("")
        for cat in sorted(recs, key=lambda c: -len(per_cat[c])):
            rows = recs[cat][:3]
            if rows:
                picks = "; ".join(f"{m} ({p:.2f}, {source_class(s)})" for p, m, s in rows)
                add(f"- **{cat}** — {picks}")
        if dominant:
            add("")
            add("Saturation warning: " + ", ".join(f"`{m}` tops {c} categories" for m, c in dominant)
                + " — one battery is dominating the table; category leadership is weak evidence.")

    if untracked:
        add("")
        add(f"## Current models missing from the registry ({len(untracked)})")
        add("")
        add("Sorted by provider reach. Each needs a registry row (and a tier) before any chain "
            "can select it.")
        add("")
        for released, n, e in sorted(untracked, key=lambda r: -len(r[2]["providers"]))[:40]:
            add(f"- `{n}` — {e['name'][:40]} | released {released} | {len(e['providers'])} providers | family {e['family'] or '?'}")

    if blind:
        add("")
        add(f"## Tracked but untiered ({len(blind)} current, sample)")
        add("")
        for released, n, e in sorted(blind, key=lambda r: -len(r[2]["providers"]))[:15]:
            add(f"- `{n}` — released {released} | {len(e['providers'])} providers | {len(reg_by_model[n])} lane(s) | tier_cats=0")

    if fallback:
        add("")
        add("## Fallback ladder (declared order)")
        add("")
        add("Access is not asserted: the ladder names intent, and each caller filters it against "
            "the providers and keys it actually holds.")
        add("")
        for f in sorted(fallback, key=lambda r: (r.get("order") or 99)):
            add(f"- {f.get('order')}. `{f.get('provider')}/{f.get('model')}` (key env `{f.get('key_env')}`)")

    add("")
    add("## Newest 25")
    add("")
    for released, n, e in current[:25]:
        state = ""
        if has_registry:
            state = ", in registry" if n in reg_by_model else ", MISSING from registry"
            state += f", tier_cats={tier_cats.get(n, 0)}"
        add(f"- {released} `{n}` — {len(e['providers'])} providers{state}")
    add("")

    return "\n".join(out), summary, (2 if problems else 0)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        description="Generate a current-models reference from a models.dev snapshot, "
                    "optionally joined with a router registry.",
        epilog="Quick start: curl -fsSL https://models.dev/api.json -o models-dev.json && "
               "python3 current-models-report.py --cache models-dev.json",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    ap.add_argument("--cache", type=pathlib.Path,
                    default=pathlib.Path(os.environ.get("MODELS_DEV_CACHE", DEFAULT_CACHE)),
                    help=f"models.dev snapshot JSON (default: {display(DEFAULT_CACHE)})")
    ap.add_argument("--tables", type=pathlib.Path,
                    default=pathlib.Path(os.environ.get("ROUTER_TABLES", DEFAULT_TABLES)),
                    help="directory holding models.jsonl / model_tier.jsonl / fallback_lanes.jsonl "
                         "(optional — omit for a feed-only report)")
    ap.add_argument("--window", type=int, default=int(os.environ.get("MODEL_WINDOW_DAYS", "90")),
                    help="how many days back counts as current (default 90)")
    ap.add_argument("--max-age", type=int, default=int(os.environ.get("MODEL_MAX_AGE_DAYS", "21")),
                    help="registry staleness ceiling in days (default 21)")
    ap.add_argument("--write", nargs="?", const=pathlib.Path("current-models.md"), type=pathlib.Path,
                    metavar="PATH", help="write markdown to PATH instead of stdout")
    ap.add_argument("--json", action="store_true", help="print the machine summary instead of markdown")
    args = ap.parse_args(argv)

    if not args.cache.exists():
        print(f"error: registry feed cache not found: {args.cache}\n"
              f"hint: curl -fsSL https://models.dev/api.json -o models-dev.json "
              f"then pass --cache models-dev.json", file=sys.stderr)
        return 3

    try:
        report, summary, code = build_report(args.cache, args.tables, args.window,
                                            args.max_age, dt.date.today())
    except json.JSONDecodeError as exc:
        print(f"error: cache is not valid JSON ({exc}); re-fetch it", file=sys.stderr)
        return 3

    if args.json:
        print(json.dumps(summary, indent=2))
        return code
    if args.write:
        dest = args.write
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(report)
        print(f"wrote {dest}", file=sys.stderr)
    else:
        print(report)
    return code


if __name__ == "__main__":
    sys.exit(main())
