#!/usr/bin/env python3
"""Set ONE board row's JSON- or text-valued field, with full assertions.

WHY THIS EXISTS
    The skill ships two narrower repairs:
      board-row-repair.py     - dotted paths, but every value is a STRING
      board-row-reasoning.py  - only the `reasoning` field
    Neither can correct the PRIMARY `acceptance` array, which is the field a
    foreman is actually judged against: `boardctl update --acceptance-criteria`
    writes a separate `acceptance_criteria` field and leaves the canonical
    array untouched, so an unsatisfiable criterion survives every writer call.
    This sets any key from a JSON file (arrays/objects) or a text file, on one
    physical line, and refuses anything ambiguous.

USAGE
    # dry run (default) - prints the changed keys and writes nothing
    board-row-set-json.py <tasks.jsonl> <row-id> --json acceptance=acc.json

    # apply
    board-row-set-json.py <tasks.jsonl> <row-id> \
        --json acceptance=acc.json \
        --text reasoning=reasoning.txt \
        --write

    Both flags are repeatable. `--json key=path` json.load()s the file (so an
    array stays an array); `--text key=path` stores the file's bytes as a
    string, which is how `reasoning` must be carried.

WHAT IT GUARANTEES (all assertions run BEFORE any write)
    * exactly one line parses to the requested id
    * every non-target line is byte-identical afterwards
    * the line count is unchanged
    * the row keeps its id and its top-level KEY ORDER
    * the row keeps its own JSON spacing style

    That last point is not cosmetic. Boards are written by several writers and
    mix styles line by line - `{"id": "X", "title": ...}` from one, compact
    `{"id":"X",...}` from another. A helper that hardcodes compact separators
    silently restyles the row it edits, so a one-field change reads as a whole
    row rewrite and the reviewer can no longer see what moved.

VERIFY AFTERWARDS (a board path may be marked -diff, so plain git diff lies)
    git diff --text --numstat -- <board>            # +1/-1, line count UNCHANGED
    git diff --text -U0 -- <board> | grep -c '^-'   # exactly 1 removed line
    jq -r 'select(.id=="<row>") | .id' <board> | wc -l   # exactly 1
"""

import json
import os
import sys


def style_of(line):
    """Match the row's existing spacing so the diff stays one line of content."""
    return (
        (', ', ': ') if '": ' in line else (',', ':')
    )


def parse_pairs(argv):
    json_sets, text_sets, write = [], [], False
    i = 0
    while i < len(argv):
        tok = argv[i]
        if tok == '--write':
            write = True
            i += 1
            continue
        if tok in ('--json', '--text'):
            if i + 1 >= len(argv) or '=' not in argv[i + 1]:
                sys.exit('ABORT: %s expects key=path' % tok)
            key, _, path = argv[i + 1].partition('=')
            (json_sets if tok == '--json' else text_sets).append((key.strip(), path))
            i += 2
            continue
        sys.exit('ABORT: unknown argument %r' % tok)
    return json_sets, text_sets, write


def main():
    argv = sys.argv[1:]
    if len(argv) < 2:
        print(__doc__.strip(), file=sys.stderr)
        return 2
    board, row_id = argv[0], argv[1]
    json_sets, text_sets, write = parse_pairs(argv[2:])
    if not (json_sets or text_sets):
        sys.exit('ABORT: no --json/--text assignments given; nothing to do')

    text = open(board, encoding='utf-8').read()
    trailing = text.endswith('\n')
    lines = text.split('\n')
    if trailing:
        lines = lines[:-1]

    hits = []
    for idx, line in enumerate(lines):
        if not line.strip():
            continue
        try:
            obj = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(obj, dict) and obj.get('id') == row_id:
            hits.append(idx)
    if len(hits) != 1:
        sys.exit(
            'ABORT: %r matched %d rows (want exactly 1). Duplicate ids must be '
            'resolved first; zero means the row is not on this board.' % (row_id, len(hits))
        )

    target = hits[0]
    original = lines[target]
    row = json.loads(original)
    before_keys = list(row.keys())
    sep = style_of(original)

    for key, path in json_sets:
        with open(path, encoding='utf-8') as fh:
            row[key] = json.load(fh)
    for key, path in text_sets:
        with open(path, encoding='utf-8') as fh:
            row[key] = fh.read()

    if list(row.keys()) != before_keys:
        sys.exit('ABORT: top-level key order changed; refusing to rewrite a row whose shape moved')
    new_line = json.dumps(row, ensure_ascii=False, separators=sep)
    if json.loads(new_line).get('id') != row_id:
        sys.exit('ABORT: reserialized row lost its id')

    out = list(lines)
    out[target] = new_line
    if len(out) != len(lines):
        sys.exit('ABORT: line count changed')
    for idx, (old, new) in enumerate(zip(lines, out)):
        if idx != target and old != new:
            sys.exit('ABORT: non-target line %d changed' % (idx + 1))
    if new_line == original:
        print('NO-OP: row already carries these values; nothing written')
        return 0

    changed = sorted(k for k in before_keys if json.loads(original).get(k) != row.get(k))
    print('row %s at line %d/%d' % (row_id, target + 1, len(lines)))
    print('changed keys: %s' % ', '.join(changed))
    for key in changed:
        value = row.get(key)
        print('  %s: %s' % (key, ('%d entries' % len(value)) if isinstance(value, list)
                            else ('%d chars' % len(value)) if isinstance(value, str) else type(value).__name__))
    if not write:
        print('DRY RUN: pass --write to apply')
        return 0

    tmp = board + '.tmp-setjson'
    with open(tmp, 'w', encoding='utf-8') as fh:
        fh.write('\n'.join(out) + ('\n' if trailing else ''))
    os.replace(tmp, board)
    print('WROTE %s' % board)
    print('next: git diff --text --numstat -- %s (expect +1/-1, line count unchanged)' % board)
    return 0


if __name__ == '__main__':
    sys.exit(main())
