# Ledger corruption repair (file-level)

When `~/.hermes/stand-in/ledger.json` is so malformed that the canonical
`ledger_board_reconcile.py` crashes on `json.load`, tolerant parsing is not
enough — every downstream lane (reconciler, digest, item counts) fails until
the file is repaired. Repair in place; this is data hygiene on the PM's own
tracking file, not code.

## The corruption class

The observed file carries ALL of these at once:

1. **Literal `\n` two-character sequences** where real newlines belong inside
   the main pretty-printed document (a bad writer escaped its own newlines).
2. **Invalid backslash escapes** (`\x`, trailing backslash, `\u` cut off).
3. **Raw control characters inside strings** (real newlines/tabs inside a
   string value, not escaped).
4. **Trailing JSONL documents appended after the main document** (each valid
   JSON on its own line, so the file is neither one JSON doc nor JSONL).

The defects STACK: a whole-text decode fails, and fixing one defect class with
a regex pass just moves the decode error to the next defect class. This is why
the fix must be a single string-aware pass, not iterated regexes.

## Repair recipe

Write the script to /tmp with the file tool (never an inline heredoc — the
hardline filter parses the heredoc body), then run it.

1. **Backup first**: timestamped copy beside the file (`ledger.json.bak-<ts>`),
   record its byte size.
2. **Normalize literal `\n`**: replace the two-char sequence `\n` with a real
   newline over the whole text.
3. **String-aware sanitize scan**: walk characters tracking in-string state
   (toggle on unescaped `"`). Inside strings: double any backslash not followed
   by a valid JSON escape char (`"\/bfnrtu`), copy `\u` plus its 4 hex digits
   intact, and escape raw control chars (`<0x20`) as `\n`/`\r`/`\t`/`\uXXXX`.
   Outside strings: copy verbatim.
4. **Shape-tolerant parse of ALL top-level docs**: `json.JSONDecoder().raw_decode`
   in a loop from each position (skip to next line on failure). Accept a dict
   with `items`, a bare item dict (has `id`/`project`), and a bare list. Merge
   items in document order.
5. **Dedupe** exact `(project, id, added_at, title-prefix)` tuples. Expect 0
   legitimate losses; if the unique count drops sharply, stop and investigate
   instead of writing.
6. **Atomic write**: `json.dump({"items": [...], "last_updated": ...}, indent=2)`
   to a temp file, `json.load` the temp back and assert the item count, then
   `os.replace` onto the ledger.
7. **Verify the repair by its outcome**: re-run the canonical reconciler dry —
   it must exit 0 and print `ledger items  : <count>` matching what you wrote.
   That line, not the repair script's own output, is the verification.

## Boundaries

- Never stamp any ledger item's status during a repair — repair changes
  ENCODING, not semantics. Verification/closure stays the reconciler's job
  (`--apply`) per Step 1a of the cycle.
- Keep the backup until at least one clean reconciler run has passed.
- The repair merges the trailing JSONL docs' items into the main document;
  that is the intended outcome (those items were otherwise invisible to
  json.load-based readers).
