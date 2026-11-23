# Cross-cutting: machines & dependencies inventory

## What a complete machines section documents
- One line per machine: name, owns-what, depends-on-what, resource envelope, restart cost.
- Third-party dependencies: per dependency — the SLA, the failure mode it imports,
  the quota/rate limit, and the exit cost (how hard to replace).
- The trust boundary map: which machine trusts which, on what evidence (network
  position, mTLS, tokens).
- Capacity math at target load: the sum of per-machine envelopes covers the traffic
  patterns section, with headroom stated (usually 2x for N-1 survival).

## Rating checks
- FAIL if any machine exists in the diagram but not in the inventory (or vice versa).
- FAIL if a third-party quota is load-bearing and unstated.
- FAIL if no machine pair has a stated trust mechanism (everything-on-one-VLAN is
  an implicit answer that must be made explicit).
