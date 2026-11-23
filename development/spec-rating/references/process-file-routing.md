# File routing — signal to files

Rung 2 of the ladder asks which of 88 resource files apply. That is a lookup,
not a judgment. Use this table instead of choosing by name proximity.

Procedure: (1) find the project SHAPE below, take its minimum set; (2) scan the
SIGNALS table and add every file whose signal appears; (3) write the skip list
with a one-line reason per skipped family. A skipped family with no reason is a
rating finding.

## Project shapes (minimum set — start here)

### S — small web app with login and search (1-100 users, one box)
process-workhorse-guide · process-spec-as-memory · process-prd-to-specs ·
sdlc-intent-to-project · sdlc-module-template · sdlc-repo-layout ·
cross-flows · cross-failures · cross-security · security-lifecycle ·
platform-web-service · protocols-http · storage-sql · caching-inprocess ·
cross-data-traffic · cross-config · cross-slo · cross-capacity ·
sdlc-cicd · sdlc-code-review · sdlc-testing-methodology · deploy-single-vps ·
telemetry-logs · telemetry-metrics · deps-selection · deps-maintenance ·
cross-docs · privacy-rules

### L — single-region web service, multi-instance (up to ~50k users)
S plus: storage-search (only if search is a feature) · caching-distributed ·
patterns-consistency · cross-data-migration · telemetry-audit (only if there is
a privileged action) · telemetry-tracing · cross-security · cross-privacy ·
cross-cost · protocols-realtime (only if push is a feature) · deploy-kubernetes

### C — CLI tool
process-workhorse-guide · process-spec-as-memory · sdlc-intent-to-project ·
sdlc-module-template · sdlc-layout-by-language · platform-cli ·
cross-flows · cross-failures · cross-compat · cross-config ·
cross-docs · deps-selection · cross-release · sdlc-cicd ·
security-supply-chain · telemetry-logs

### D — always-on daemon / worker
C minus platform-cli, plus: platform-daemon · patterns-consistency ·
protocols-rpc-queue (if it consumes work) · telemetry-metrics ·
cross-rollout · cross-slo · deploy-single-vps

### M — mobile client with a backend
process-workhorse-guide · process-spec-as-memory · sdlc-intent-to-project ·
sdlc-module-template · platform-mobile-app · platform-web-service ·
protocols-http · protocols-realtime · storage-embedded · cross-compat ·
cross-flows · cross-failures · cross-release · cross-rollout ·
cross-security · privacy-rules · telemetry-logs · telemetry-metrics ·
cross-i18n (if localized) · sdlc-cicd

### E — embedded / firmware
process-workhorse-guide · process-spec-as-memory · sdlc-intent-to-project ·
sdlc-module-template · platform-embedded · storage-embedded ·
cross-flows · cross-failures · cross-compat · cross-release ·
deploy-embedded-bundled · security-supply-chain · telemetry-logs ·
cross-config

### P — data pipeline / batch system
process-workhorse-guide · process-spec-as-memory · sdlc-intent-to-project ·
sdlc-module-template · paradigms-data-pipeline · storage-sql ·
cross-data-migration · cross-data-traffic · cross-flows · cross-failures ·
cross-observability · telemetry-logs · telemetry-metrics ·
cross-cost · cross-capacity · deps-selection · cross-balance

### X — distributed / multi-node service
L plus: platform-distributed · paradigms-concurrency · paradigms-sync-async ·
paradigms-interaction-patterns · patterns-consistency · cross-state-machines ·
cross-data-migration · deploy-hybrid-edge or deploy-cloud-managed

## Signals — add these files when the phrase is true

| If the system… | Load |
|---|---|
| stores any PII, or serves EU/California users | privacy-rules, cross-privacy |
| has login, sessions, or API keys | cross-security, platform-web-service (`auth tier`), protocols-http (401/403) |
| has privileged/admin actions | telemetry-audit, cross-security |
| touches money, subscriptions, or invoicing | thirdparty-payments, patterns-consistency, cross-security |
| calls a third-party API | thirdparty-apis |
| receives webhooks | thirdparty-webhooks |
| logs in via a third party (Google/Apple/GitHub) | thirdparty-oauth |
| sends email, SMS, or push | thirdparty-messaging |
| calls an LLM or model endpoint | thirdparty-ml-models, cross-cost |
| has full-text search or faceted browse | storage-search (small corpus: see its N<1000 lane) |
| has a cache | caching-inprocess; + caching-distributed if multi-instance; + caching-cdn if public HTTP |
| has background jobs or queues | protocols-rpc-queue, patterns-consistency |
| pushes data to clients | protocols-realtime or paradigms-sync-async |
| has a schema migration | cross-data-migration, storage-sql (expand/contract) |
| must keep data after deletion requests | privacy-rules, telemetry-audit (retention vs erasure) |
| is multi-tenant | cross-security (isolation), storage-sql (tenant key), cross-capacity |
| deploys to more than one target | cross-deployment + the matching deploy-* file per target |
| has uptime commitments | cross-slo, telemetry-metrics, cross-failures |
| is shipped to users who cannot be forced to upgrade | cross-compat, cross-release, platform-mobile-app / platform-embedded |
| reads config from files/env | cross-config |
| has more than one machine | cross-machines, cross-data-traffic |
| must be built by several agents or people | sdlc-module-template, sdlc-code-review, cross-process |
| must be localised | cross-i18n |
| has a UI that must be accessible | cross-accessibility |
| ships on a licence or consumes OSS | cross-licensing-compliance, deps-selection |
| needs dashboards for the operator | cross-reporting, telemetry-metrics |
| is optimised for speed | cross-performance |

## Skip list (write it, do not skip silently)

For each family not loaded — platforms, deployment topologies, storage kinds,
caching, dependencies, third-party, cross-cutting — write one line:

    SKIP <family>: <reason the domain does not exist in this system>

Examples that are legitimate: "SKIP mobile: no client app"; "SKIP storage-search:
corpus is 3 users' bookmarks, SQLite FTS5 covers it"; "SKIP caching-distributed:
single instance". A skip line whose reason is "not enough time" is a rating FAIL.

## Small-N rule (right-sizing)

For fewer than 1000 users, one instance, and no external SLA, the following are
answered at reduced depth and the reduction SAID OUT LOUD in the spec:
shard/replica plans, multi-region topology, alias-swap reindex runbooks,
distributed caching, blue/green rollout, chaos drills. Write "N/A at this scale
because <fact>" — that is a valid answer; silence is not, and neither is
specifying a search cluster for 30 MB of data.
