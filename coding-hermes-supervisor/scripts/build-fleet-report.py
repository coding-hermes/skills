#!/usr/bin/env python3
"""Build fleet HTML report from JSON data + template."""
import json, sys, argparse, datetime, html

def build(data_path, template_path, output_path):
    with open(data_path) as f:
        data = json.load(f)

    with open(template_path) as f:
        tmpl = f.read()

    tmpl = tmpl.replace("%%GENERATED%%", f"Generated {data.get('generated', 'unknown')}")

    # --- metrics bar ---
    m = data.get("metrics", {})
    healthy = m.get("healthy", 0)
    warn = m.get("warn", 0)
    error = m.get("error", 0)
    paused = m.get("paused", 0)

    tmpl = tmpl.replace("%%METRICS_BAR%%", f"""
    <div style="display:flex;gap:12px;flex-wrap:wrap;margin:16px 0">
        <span style="background:#2e7d32;color:#fff;padding:6px 14px;border-radius:6px">🟢 Healthy: {healthy}</span>
        <span style="background:#f57f17;color:#fff;padding:6px 14px;border-radius:6px">🟡 Warn: {warn}</span>
        <span style="background:#c62828;color:#fff;padding:6px 14px;border-radius:6px">🔴 Error: {error}</span>
        <span style="background:#555;color:#fff;padding:6px 14px;border-radius:6px">⏸ Paused: {paused}</span>
        <span style="background:#1565c0;color:#fff;padding:6px 14px;border-radius:6px">📋 Pending: {m.get('total_pending_tasks', 0)}</span>
    </div>""")

    # --- fleet table ---
    fleet_rows = ""
    for f in data.get("fleet", []):
        status_icon = {"healthy": "🟢", "warn": "🟡", "error": "🔴", "stale": "⏳"}.get(f.get("status", ""), "❓")
        last_run = f.get("last_run", "never") or "never"
        if last_run != "never":
            last_run = last_run[:16].replace("T", " ")
        fleet_rows += f"""
        <tr>
            <td><strong>{html.escape(f.get('project', '?'))}</strong></td>
            <td style="font-size:12px;color:#888">{html.escape(f.get('workdir', '?'))}</td>
            <td>{html.escape(f.get('foreman_model', '?'))}</td>
            <td>{html.escape(f.get('foreman_provider', '?'))}</td>
            <td>{last_run}</td>
            <td>{status_icon} {html.escape(f.get('status', '?'))}</td>
            <td>{f.get('pending_tasks', 0)}</td>
            <td style="font-size:11px">{', '.join(f.get('worker_models_used', []) or ['none'])}</td>
        </tr>"""

    tmpl = tmpl.replace("%%FLEET_TABLE%%", fleet_rows)

    # --- what got done ---
    done = data.get("what_got_done", {})
    done_html = ""

    def card(title, items, key_fn):
        if not items:
            return ""
        rows = "".join(f"<li>{html.escape(key_fn(i))}</li>" for i in items)
        return f"""
        <details open>
            <summary style="cursor:pointer;font-weight:bold;font-size:14px">{title} ({len(items)})</summary>
            <ul style="margin:4px 0;padding-left:24px">{rows}</ul>
        </details>"""

    done_html += card("Tasks Resolved", done.get("tasks_resolved", []),
                      lambda t: f"{t.get('foreman','?')} — {t.get('task_id','?')}: {t.get('title','?')}")
    done_html += card("Commits Landed", done.get("commits_landed", []),
                      lambda c: f"[{c.get('project','?')}] {c.get('message','?')} ({c.get('author','?')})")
    done_html += card("Bugs Found → Queued", done.get("bugs_queued", []),
                      lambda b: f"[{b.get('project','?')}] {b.get('description','?')}")
    done_html += card("CI Regressions", done.get("ci_regressions", []),
                      lambda c: f"[{c.get('project','?')}] {c.get('run','?')} {'⚡ transient' if c.get('transient') else '🔴 real'}")
    done_html += card("Spec/Doc Fixes", done.get("spec_doc_fixes", []),
                      lambda s: f"[{s.get('project','?')}] {s.get('file','?')}")

    th = done.get("tool_health", {})
    if th:
        tool_rows = "".join(
            f"<tr><td>{html.escape(k)}</td><td>{v}</td></tr>"
            for k, v in sorted(th.items())
        )
        done_html += f"""
        <details open>
            <summary style="cursor:pointer;font-weight:bold;font-size:14px">Tool Health</summary>
            <table style="margin:4px 0;border-collapse:collapse">
                <tr style="background:#333;color:#fff"><th style="padding:4px 12px">Tool</th><th>Calls</th></tr>
                {tool_rows}
            </table>
        </details>"""

    tmpl = tmpl.replace("%%WHAT_GOT_DONE%%", done_html or "<p style='color:#888'>No activity this cycle.</p>")

    # --- issues ---
    issues = data.get("issues_detected", [])
    if issues:
        tmpl = tmpl.replace("%%ISSUES%%",
            "<ul>" + "".join(f"<li style='color:#c62828'>{html.escape(i)}</li>" for i in issues) + "</ul>")
    else:
        tmpl = tmpl.replace("%%ISSUES%%", "<p style='color:#2e7d32'>No issues detected ✅</p>")

    # --- changes made ---
    changes = data.get("changes_made", [])
    if changes:
        tmpl = tmpl.replace("%%CHANGES%%",
            "<ul>" + "".join(f"<li>{html.escape(c)}</li>" for c in changes) + "</ul>")
    else:
        tmpl = tmpl.replace("%%CHANGES%%", "<p style='color:#888'>No changes made this run.</p>")

    with open(output_path, 'w') as f:
        f.write(tmpl)

    print(f"✅ Report written to {output_path}")

if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--data", required=True)
    p.add_argument("--template", required=True)
    p.add_argument("--output", required=True)
    args = p.parse_args()
    build(args.data, args.template, args.output)
