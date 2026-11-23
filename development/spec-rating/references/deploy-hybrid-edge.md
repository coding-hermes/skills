# Deployment topology: hybrid / edge (cloud + on-prem + devices)

## What the spec must re-state when the system spans trust boundaries
- **The seam map**: what runs where, and per seam — the latency, bandwidth,
  and AVAILABILITY of the link (the office loses internet: what keeps
  working? named per feature).
- **Sync semantics**: which side is source-of-truth per data class, the
  conflict rule for offline edits on both sides (last-write-wins is a
  decision with named casualties), and the sync backlog behavior.
- **The store-and-forward answer**: what queues locally when the cloud is
  unreachable, its local capacity bound, and the flush order on reconnect.
- **Version skew**: edge nodes updated on their own schedule — the API
  compat window is wider, and the cloud side tolerates N-versions-old
  callers (stated, tested).
- **Security across seams**: per-edge identity (device certs, not shared
  keys), the bootstrap/enrollment flow for a new edge node, and the
  compromise story (revoke one edge without redeploying the fleet).
- **Observability**: edge telemetry survives the outage (local buffer) and
  arrives eventually — the monitoring treats edge as async always.

## Rating checks
- FAIL if any edge feature assumes the cloud link is up.
- FAIL if conflicts are 'impossible' without a stated reason.
- FAIL if one shared credential exists across edge nodes.
