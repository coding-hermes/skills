# Deployment topology: cloud-managed (AWS/GCP with budget)

Budget changes the default answers: managed services replace self-run ones,
and the spec must re-derive each decision in that light — managed is a
trade: less ops, more coupling to their limits, their outages, their bill.

## What the spec must re-state for this topology
- **Service map**: per machine — managed equivalent chosen (RDS/Aurora,
  SQS, ElastiCache, S3, Lambda/ECS/EKS) or self-run on EC2, and WHY per
  choice (managed is not automatically right: portability, cost at scale,
  feature gaps).
- **HA geometry**: multi-AZ for state, multi-region for the DR answer (the
  RTO/RPO per class: pilot-light vs warm vs active-active, costed).
- **The managed failure modes**: their outages are yours (the dependency
  rows name the provider status page as a detection source), their quotas
  (service limits — raised how, in advance, not during the incident),
  their restart semantics (RDS maintenance windows, failover timing).
- **Lock-in accounting**: per managed service, the exit cost (data export,
  API compatibility, the re-run of the IaC) — stated, not ignored.
- **Cost model**: per service at stated traffic — compute, storage,
  REQUESTS, egress (the surprise line items), plus the budget alerts and
  the anomaly detection. The 2x-growth bill is computed, not feared.
- **Network**: VPC topology, private subnets for state, the egress paths,
  and the zero-trust answer (security groups are the perimeter — named).
- **IaC discipline**: the whole topology is code (Terraform/Pulumi/CDK),
  reviewed, and reproducible-from-repo; console-clicks are drift.

## Rating checks
- FAIL if any managed service's quota is load-bearing and not pre-raised.
- FAIL if egress/data-transfer cost is absent from the cost model.
- FAIL if the topology is only reproducible by hand (no IaC).
- FAIL if multi-AZ is claimed but the failover behavior of each managed
  stateful service is unstated.
