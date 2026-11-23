# Storage: embedded / local (SQLite, RocksDB, LMDB, on-device)

## What a complete embedded-storage spec documents
- Engine choice per device class and the resource envelope that forces it.
- Schema/migration ON DEVICE: versions ship in the wild; the migration runs on a
  user's machine, can fail, and must be recoverable (backup-then-migrate or fail loud).
- Concurrency model: single-writer reality (WAL mode? multi-process?), busy timeouts.
- Durability: synchronous vs normal commit, fsync policy, and the corruption window
  on power loss per setting.
- Size ceiling and VACUUM/compaction policy (or the file grows forever).

## The questions the spec must answer
- What happens when the file is corrupted (power loss, disk full): detect, rebuild, restore?
- What is the concurrent-access story: two processes, or app + background sync?
- What ships in the initial file, and how do templates/fixtures update?

## Rating checks
- FAIL if migration-on-open has no failure path.
- FAIL if durability settings are unstated for data the user cannot re-create.
- FAIL if no size bound or compaction policy exists for an append-heavy workload.
