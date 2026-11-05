# Containers and orchestration

A container is a packaging decision; supervision is a runtime decision. Most fleet outages are not
packaging failures — they are the absence of a decision about *who restarts this and how do I know
it is alive*. Judge those two separately.

## Docker

Minimum for a service:

```dockerfile
FROM <runtime> AS build
# ... build
FROM <runtime>-slim
COPY --from=build /out/app /app
USER 65532                                  # never root
HEALTHCHECK --interval=30s --timeout=3s --start-period=20s \
  CMD ["/app", "healthcheck"]               # or curl -fsS localhost:PORT/health
ENTRYPOINT ["/app"]
```

- **`HEALTHCHECK` is not readiness.** A container healthcheck tells the runtime the process is
  sane; readiness tells the *scheduler* whether to send traffic. A service behind a load balancer
  needs the second one, and it belongs to the application, not the Dockerfile.
- **Pin the base image by digest** for anything that runs unattended. `:latest` is a silent
  supply-chain update.
- **Never bake secrets into layers.** `COPY .env` is permanent in image history even if a later
  layer deletes the file.
- **No host state the container cannot see.** A containerised lane that expects a socket, a
  mounted path or a `docker` binary on the host must mount it explicitly and fail loudly when it
  is missing — the classic failure is a mount that silently produces an empty directory.

### Compose without `restart:` is a P2

```yaml
services:
  app:
    restart: unless-stopped        # without this, one OOM ends the service until a human notices
    healthcheck: {test: [...], interval: 30s, retries: 3}
    deploy:
      resources:
        limits: {cpus: "2", memory: 2G}
```

`restart: "no"` is a decision; a missing key is an omission. The census treats them the same
because it cannot tell them apart — say which one you meant in the compose file.

## Kubernetes

A raw `Deployment` without these is a pod that will be restarted by nobody and paged by no one:

- `readinessProbe` + `livenessProbe` (different endpoints; liveness must not depend on a
  dependency being up, or a database blip restarts every replica),
- `resources.requests` **and** `limits` — requests only means the pod can be starved silently,
- `replicas` ≥ 2 or an explicit note that single-replica is intended,
- a `PodDisruptionBudget` for anything with replicas > 1,
- `securityContext` (non-root, read-only root filesystem where possible).

Helm or Kustomize is a preference; **a committed, reproducible manifest is not**. `kubectl apply`
from a laptop leaves the cluster's shape in nobody's repository.

## Deciding between supervisor, container runtime and orchestrator

| the thing | choose | why |
|---|---|---|
| one binary, one host, no HA | systemd unit (`Restart=always`, `RestartSec=5`) | simplest thing that survives a crash and a reboot |
| one binary + reproducible deps | compose with `restart:` | same, plus a portable definition |
| several services, rolling updates, HA | k8s (or an equivalent) | the scheduler owns restarts and placement |
| a batch job | a timer/`CronJob` with a deadline | "always running" is the wrong model |

Whatever is chosen, the census's `scheduling` check asks one question: **if this process exits at
3am, what brings it back?** If the answer is "someone notices", that is a P2 finding, not a
deployment.

## Containerised agents and lanes

A lane that runs inside a container cannot see the host: no host `docker` socket unless mounted, no
host paths unless mounted, no host clock assumptions. Before containerising a lane, check it does
not depend on:

- a git repository at a path the container does not mount,
- an SSH key or cloud credential resolved from a host home directory,
- a shared scratch directory whose free space was never bounded (a container that fills the host
  disk fails every sibling on that host, not just itself).

Bounding scratch space and pinning memory are not optimisations; they are what stops one lane from
taking the machine down for the rest of the fleet.
