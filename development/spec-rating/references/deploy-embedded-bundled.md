# Deployment topology: embedded/bundled (the store ships inside the product)

When the storage engine or service ships INSIDE the app (SQLite in a mobile
app, an embedded DB in a device, a bundled sidecar), the 'deployment' is the
application update itself.

## What the spec must re-state
- **Schema migrations ride the app update**: the migration runs on millions
  of devices in the wild, on first launch after update, possibly on a
  battery-critical phone — it must be fast (measured on the low-end device),
  interruptible, and recoverable (backup-then-migrate or journal-replay).
- **Downgrade reality**: users CAN downgrade (app stores allow it); can the
  new schema open in the old app? The compat answer or the wipe warning.
- **Corruption at scale**: power loss during write on a device = corruption
  window; the detection (integrity check cadence) and the rebuild path
  (re-sync from server? re-derive? last-export?) — stated per data class.
- **Size budget**: the DB file's growth curve on-device, the compaction/
  vacuum policy, and the storage-pressure behavior (the OS may revoke
  space; what gets evicted).
- **Multi-process access**: app + widgets/extensions/background sync
  opening the same file — the concurrency mode (WAL, busy timeout) and the
  cross-process notification.
- **Sync** (if server-backed): the conflict rule, the sync trigger
  (foreground? push?), and the partial-sync visibility to the user.

## Rating checks
- FAIL if a migration has no low-end-device timing measurement.
- FAIL if corruption recovery is 'restore from backup' when no backup
  exists on-device.
- FAIL if the DB grows unbounded with no compaction on a device with
  finite storage.
