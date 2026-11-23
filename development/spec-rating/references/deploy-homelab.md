# Deployment topology: home lab / self-hosted (commodity machines, non-distributed)

The same spec deploys here with a DIFFERENT set of answers. This file forces
them. The scale assumption: a couple of machines on a home network, no
managed anything, physical ownership of every failure.

## What the spec must re-state for this topology
- **HA answer**: there is none — single-box failure IS the outage. The spec
  states the recovery story instead: bare-metal restore or reinstall +
  restore-from-backup, with the measured RTO (it's hours, not seconds; say so).
- **Backups**: on hardware you OWN (a second machine, a USB disk), versioned,
  and TESTED by an actual restore — the restore drill is a scheduled chore
  with an owner, or the backup is a wish.
- **Databases**: SQLite or a single-instance Postgres/MySQL on one box. No
  replicas, no failover. The spec drops any distributed claim and states the
  consistency reality: one writer, local disk, fsync is your durability.
- **Capacity**: the ceiling is the hardware you have — the capacity section
  quotes the actual machines (RAM, disk, cores) and the measured fit.
- **Network**: LAN latency is microseconds, but the public exposure story
  (port forwards? VPN/tailnet? reverse proxy with TLS?) is a security
  decision stated here — homelab services exposed by accident are the
  classic incident.
- **Power/environment**: the machine survives a brownout how? Ups? The
  auto-restart after power loss (BIOS setting + service enablement) is part
  of the spec — self-hosted means YOU own the power story.
- **Updates**: unattended-upgrades policy, the kernel-reboot cadence, and
  the 'we updated and it broke' rollback (snapshot before upgrade).

## Rating checks
- FAIL if the spec promises multi-AZ behaviors it cannot deliver on one box.
- FAIL if backups exist but no restore has ever been performed (date it or fail).
- FAIL if the public-exposure answer is 'it's on my LAN' with open ports.
