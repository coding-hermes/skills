#!/usr/bin/env python3
"""Doc-writer single-board injector: append DOC-<N> task rows + audit event.

Validated 2026-09-03 on 31 boards (57 rows). Append-only; mirrors the LAST
task row's key-set + serialization style; parsed-id dedupe; DOC numbering
continues past any DOC-<n> seen in tasks.jsonl ids AND events.jsonl.

Usage:
    docwriter_inject_rows.py <board_dir> <run_date_UTC_YYYY-MM-DD> <specs.json>
        <tasks_filename=tasks.jsonl> <events_filename=events.jsonl>

specs.json = JSON list of [title, reasoning] pairs (or {"title","reasoning"}).

Writes: appended task rows + one audit event
{"doc_writer_run": "<date>", "injected": [ids]} (detail = escaped JSON string,
event_type=audit, actor=doc-writer, id=max+1). Prints APPENDED/EVENT lines.
"""
import json, re, sys, datetime

def parse_row(ln):
    return json.loads(ln)

def detect_style(last_line):
    sep = (',', ':') if ', ' not in last_line else None
    esc = '\\u' in last_line
    return sep, esc

def main():
    board_dir, run_date, specs_json = sys.argv[1], sys.argv[2], json.loads(sys.argv[3])
    tf_name = sys.argv[4] if len(sys.argv) > 4 else "tasks.jsonl"
    ef_name = sys.argv[5] if len(sys.argv) > 5 else "events.jsonl"
    tf = f"{board_dir}/{tf_name}"
    ef = f"{board_dir}/{ef_name}"

    tlines = [l for l in open(tf).read().splitlines() if l.strip()]
    existing_ids = set()
    doc_nums = []
    for l in tlines:
        try:
            r = parse_row(l)
            if isinstance(r, dict) and r.get('id') is not None:
                existing_ids.add(str(r['id']))
                m = re.search(r'DOC-(\d+)', str(r['id']))
                if m: doc_nums.append(int(m.group(1)))
        except Exception:
            pass
    elines = [l for l in open(ef).read().splitlines() if l.strip()]
    for l in elines:
        for m in re.finditer(r'"DOC-(\d+)"', l):
            doc_nums.append(int(m.group(1)))
    next_doc = (max(doc_nums) + 1) if doc_nums else 1

    # Board open-state token: most common among open-ish statuses
    open_counts = {}
    for l in tlines:
        try:
            r = parse_row(l)
            s = str(r.get('status', ''))
            if s and s not in ('complete', 'completed', 'done'):
                open_counts[s] = open_counts.get(s, 0) + 1
        except Exception:
            pass
    open_token = 'pending'
    if open_counts:
        cand = max(open_counts, key=open_counts.get)
        if cand in ('pending', 'todo', 'open', 'in_progress', 'in-progress', 'queued'):
            open_token = cand
    print(f"BOARD open_token={open_token} open_counts={open_counts}")

    # last row as key template (skip header-like rows)
    last_row = None
    for l in reversed(tlines):
        try:
            r = parse_row(l)
            if isinstance(r, dict) and len(r) > 3:
                last_row = r
                break
        except Exception:
            continue
    if last_row is None:
        print("NO_TEMPLATE_ROW"); sys.exit(2)
    keys = list(last_row.keys())
    sep, esc = detect_style(tlines[-1])
    now_iso = datetime.datetime.now(datetime.timezone.utc).isoformat()
    now_space = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M:%S.%f")

    content_keys = ('detail', 'description', 'review_notes', 'foreman_note', 'worker_summary',
                    'guard_result', 'ci_result', 'blocked_reason', 'commit_hash', 'files_changed',
                    'lines_added', 'lines_removed', 'completed_at', 'dispatched_at', 'blocked_since',
                    'primary_model', 'primary_provider', 'fallback_model', 'fallback_provider')
    list_keys = ('capability_tags', 'labels', 'depends_on', 'blocks', 'acceptance_criteria')

    def new_row(spec):
        row = dict(last_row)
        row['id'] = spec['_id']
        row['title'] = spec['title']
        row['status'] = open_token
        if 'worker_status' in keys:
            row['worker_status'] = open_token
        tpl_prio = last_row.get('priority')
        row['priority'] = 3 if isinstance(tpl_prio, int) else 'P3'
        tpl_cplx = last_row.get('complexity')
        if isinstance(tpl_cplx, int):
            row['complexity'] = 3
        else:
            row['complexity'] = '3'
        for k in content_keys:
            if k in keys:
                row[k] = None
        for k in list_keys:
            if k in keys:
                row[k] = []
        if 'attempts' in keys:
            row['attempts'] = 0
        if 'source' in keys:
            row['source'] = 'doc-writer'
        if 'created_by' in keys:
            row['created_by'] = 'doc-writer'
        for tk in ('created_at', 'updated_at'):
            if tk in keys:
                tpl_v = str(last_row.get(tk, ''))
                if re.match(r'^\d{4}-\d{2}-\d{2}$', tpl_v):
                    row[tk] = now_iso[:10]
                elif 'T' in tpl_v:
                    row[tk] = now_iso
                else:
                    row[tk] = now_space
        if 'ts' in keys:
            row['ts'] = now_iso
        rnote = spec['reasoning']
        if 'reasoning' in keys:
            if isinstance(last_row.get('reasoning'), dict):
                row['reasoning'] = {'note': rnote}
            else:
                row['reasoning'] = rnote
        if 'detail' in keys:
            row['detail'] = rnote
        if 'description' in keys:
            row['description'] = rnote
        return row

    created = []
    for spec0 in tasks_specs if False else specs_json:
        if isinstance(spec0, list):
            spec = {"title": spec0[0], "reasoning": spec0[1]}
        else:
            spec = spec0
        tid = f"DOC-{next_doc}"
        next_doc += 1
        if tid in existing_ids:
            print(f"SKIP_EXISTS {tid}"); continue
        row = new_row(dict(spec, _id=tid))
        with open(tf, "a") as f:
            f.write(json.dumps(row, ensure_ascii=esc, separators=sep) + "\n")
        created.append(tid)
        existing_ids.add(tid)
        print(f"APPENDED {tid}")

    # audit event
    ev_template = None
    for l in reversed(elines):
        try:
            r = parse_row(l)
            if isinstance(r, dict) and len(r) > 2:
                ev_template = r
                break
        except Exception:
            continue
    if ev_template is None:
        print("NO_EVENT_TEMPLATE"); sys.exit(3)
    ev = dict(ev_template)
    maxid = 0
    for l in elines:
        try:
            r = parse_row(l)
            if isinstance(r, dict) and isinstance(r.get('id'), int):
                maxid = max(maxid, r['id'])
        except Exception:
            pass
    detail_obj = {"doc_writer_run": run_date, "injected": created}
    now_utc = datetime.datetime.now(datetime.timezone.utc)
    if 'timestamp' in ev:
        ev['timestamp'] = now_utc.strftime("%Y-%m-%d %H:%M:%S.000000")
        ev['id'] = maxid + 1
        ev['event_type'] = 'audit'
        ev['task_id'] = None
        ev['actor'] = 'doc-writer'
        ev['detail'] = json.dumps(detail_obj)
        if 'tick_number' in ev:
            ev['tick_number'] = None
    elif 'ts' in ev and 'timestamp' not in ev:
        ev['ts'] = now_utc.strftime("%Y-%m-%dT%H:%M:%SZ")
        ev['kind'] = 'audit'
        ev['actor'] = 'doc-writer'
        ev['detail'] = json.dumps(detail_obj)
    else:
        print("UNKNOWN_EVENT_SCHEMA"); sys.exit(4)
    sep2, esc2 = detect_style(elines[-1]) if elines else (None, False)
    with open(ef, "a") as f:
        f.write(json.dumps(ev, ensure_ascii=esc2, separators=sep2) + "\n")
    print(f"EVENT_APPENDED id={ev.get('id')} injected={created}")

if __name__ == '__main__':
    main()
