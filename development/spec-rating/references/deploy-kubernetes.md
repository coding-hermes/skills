# Deployment topology: Kubernetes / orchestrated cluster

## What the spec must re-state (the orchestrator changes the answers)
- **Workload classes**: per machine — deployment, statefulset, job/cronjob,
  daemonset; and why (state lives in statefulsets with PVCs, never in
  deployments with emptyDir).
- **The storage reality**: which storage class (network-attached, its
  latency and durability), the PVC expansion story, and the statefulset
  scale-DOWN danger (the last replica's data).
- **Probes & lifecycle**: liveness vs readiness vs startup per service —
  and the probe config that avoids the kill-loop during slow starts.
- **Resource governance**: requests/limits per container (QoS class
  follows), the eviction order under node pressure, and the PDB that keeps
  capacity during node drains.
- **Networking**: service mesh or not (decided), ingress TLS, NetworkPolicy
  as the zero-trust enforcement, and the DNS assumption (every restart
  changes IPs; nothing may pin them).
- **Config & secrets**: ConfigMaps/Secrets delivery, the rollout of config
  changes, and the secret-rotation path.
- **The operator tasks**: node upgrades, cluster version skew policy,
  autoscaler behavior (HPA on what metric, the scale-from-zero cold start).

## Rating checks
- FAIL if stateful workloads run as stateless deployments.
- FAIL if probes are copy-pasted defaults that don't match the service's
  real startup/dependency profile.
- FAIL if no PDB exists for anything that must stay up during node ops.
