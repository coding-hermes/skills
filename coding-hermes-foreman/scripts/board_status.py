#!/usr/bin/env python3
"""JSONL board status read — counts by status, header meta, last events.

Usage: python3 board_status.py [board_dir]
Defaults: board_dir=.coding-hermes/board  (run from repo root)

Reads the canonical JSONL store directly (board.db retired 2026-09-03).
For richer queries use boardctl (github.com/coding-hermes/boardctl).
"""
import json, os, sys

def main():
    root = sys.argv[1] if len(sys.argv) > 1 else '.coding-hermes/board'
    counts = {}
    in_progress = []
    with open(os.path.join(root, 'tasks.jsonl')) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            t = json.loads(line)
            st = t.get('status', 'unknown')
            counts[st] = counts.get(st, 0) + 1
            if st == 'in_progress':
                in_progress.append((t.get('id'), t.get('title')))
    print('status counts:', sorted(counts.items()))
    print('in_progress:', in_progress)
    try:
        with open(os.path.join(root, 'board.jsonl')) as f:
            hdr = json.load(f)
        print('meta:', {k: hdr.get(k) for k in ('project', 'last_tick', 'ticks_total', 'ticks_idle', 'last_commit', 'updated_at')})
    except Exception as e:
        print('meta read err:', e)
    events = []
    with open(os.path.join(root, 'events.jsonl')) as f:
        for line in f:
            line = line.strip()
            if line:
                events.append(json.loads(line))
    for e in events[-5:]:
        print('event:', e.get('id'), e.get('event_type'), e.get('task_id'), e.get('tick_number'))

if __name__ == '__main__':
    main()
