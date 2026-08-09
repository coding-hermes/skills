#!/bin/bash
# Fix a stuck scheduler — kills stale running ticks via SQLite.
# Usage: bash scripts/clear-stuck-ticks.sh
DB=~/.hermes/coding-hermes/scheduler.db
if [ ! -f "$DB" ]; then
    echo "ERROR: DB not found at $DB"
    exit 1
fi
python3 -c "
import sqlite3
db = sqlite3.connect('$DB')
db.execute(\"UPDATE ticks SET status='timeout', outcome='timeout', completed_at=datetime('now') WHERE status='running'\")
n = db.total_changes
db.commit()
print(f'Cleared {n} stuck ticks')
"
# Force eval to rebalance
sleep 1
curl -s -X POST http://127.0.0.1:9090/api/v1/evaluate > /dev/null
echo "Evaluation triggered"
