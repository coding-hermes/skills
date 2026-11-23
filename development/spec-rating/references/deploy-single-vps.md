# Deployment topology: single VPS (the honest small deploy)

The workhorse topology: one box, docker-compose or systemd, everything on
it. Most projects live here longest; the spec that pretends otherwise is
lying about its own stage.

## What the spec must re-state
- **Everything-on-one-box consequences**: noisy neighbors between services
  (the memory/cgroup limits per service), the shared disk IO budget, and
  the OOM-killer order (who dies first under pressure — named, not
  discovered).
- **The upgrade treadmill**: OS + runtime + app updates on ONE box means
  coordinated downtime — the maintenance window, the snapshot-before-upgrade,
  and the roll-back-when-broken path (the VM snapshot IS the rollback).
- **Backups**: off-box (object storage or another host), versioned, restore-
  tested; the disk-is-the-backup fallacy named and avoided.
- **TLS/edge**: the reverse proxy (Caddy/nginx), cert renewal, and the
  HTTP->HTTPS story.
- **The scaling ceiling**: stated honestly — vertical growth until the box
  is the bottleneck, THEN the migration path (which service leaves first,
  and where it goes).
- **Monitoring**: the single-box canary (disk full, memory, cert expiry,
  service up) with alerts that reach a human — one-box outages are total
  outages; detection is the only mitigation.

## Rating checks
- FAIL if no per-service resource limits exist (one leak kills everything).
- FAIL if backups live on the same disk/host as the data.
- FAIL if the box's death has no rebuild-from-scratch path (IaC or a
  documented setup script, restore-tested).
