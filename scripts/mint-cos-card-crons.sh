#!/bin/bash
# Mint per-project COS card-manager crons: one per ENABLED foreman, staggered
# 15-min slots from 08:00 local (load-safe: max ~1 concurrent card manager).
set -uo pipefail
TOKEN_NOTE="(per-project card managers restored 2026-11-16 per operator ruling: 1 fleet census + 1 card-manager per project)"

python3 - > /tmp/cos-card-crons.txt <<'PY'
import sqlite3
c = sqlite3.connect('file:~/.hermes/coding-hermes/scheduler.db?mode=ro', uri=True)
c.row_factory = sqlite3.Row
rows = c.execute("""select name, workdir, repo_url from projects
    where name like '%-foreman' and enabled=1 order by name""").fetchall()
slot = 0
for r in rows:
    fam = r['name'][:-len('-foreman')] if r['name'].endswith('-foreman') else r['name']
    wd = r['workdir'] or ''
    if not wd or 'stand-in' in wd.lower():
        continue
    m = (slot * 15) % 60
    h = 8 + (slot * 15) // 60
    print('%s|%s|%d %d * * *|%s' % (fam, wd, m, h, r['repo_url'] or ''))
    slot += 1
PY

N=0
while IFS='|' read -r fam wd sched repo; do
  [ -d "$wd/.coding-hermes/board" ] || { echo "  skip $fam (no board at $wd)"; continue; }
  hermes cron create "$sched" \
    "You are the per-project Chief of Staff for $fam — CARD MANAGER scope (operator design 2026-11-16: one fleet census cron + one card-manager cron per project). Work ONLY on this project's kanban cards (board: $wd/.coding-hermes/board/tasks.jsonl${repo:+, repo: $repo}). Your job: (1) verify every card's claimed state against board and repo truth — statuses, [tag] title prefixes, project linkage, stale closes; (2) repair drift you can EVIDENCE (one writer per board, gate on board quiescence mtime >10min, renumber never delete); (3) every in-flight card you touch must be subscribed: hermes kanban notify-subscribe <id> --platform telegram --chat-id <cos-channel> --thread-id 182477 --chat-type thread --delivery-mode notify+wake (a card is born subscribed); (4) do NOT work the tasks yourself and do NOT duplicate the 07:00 fleet analysis pass. Write evidence to DuckBrain ns cos under /per-project/$fam/<date>. Stay quiet unless drift was found or a blocker needs the operator." \
    --name "cos-$fam-cards" \
    --deliver local \
    --workdir "$wd" \
    --skill coding-hermes-cos \
    >/dev/null 2>&1 && N=$((N+1)) || echo "  FAIL: cos-$fam-cards"
done < /tmp/cos-card-crons.txt
echo "created: $N card-manager crons"
