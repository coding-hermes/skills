# Modules

One module per file (or one file per flow containing its modules). A module
exists because a flow step needed it; every module names exactly one flow.

## MOD-01 — <name>

flow: FLOW-01
owns: <the data/state/decision this module is the single writer of>
does-not-own: <what a neighbour owns — this is what stops double implementation>
inputs: <...>
outputs: <...>
collaborators: <MOD-nn, CT-nn>
failure modes: <dependency → direction (fail closed / open / degraded)>
invariants upheld: <which overview invariants this module protects>
concurrency: <single writer per id? optimistic version check? none?>
config: <ENV_NAME (type, default, validation)>
observability: <metric / log field / trace span>

### Requirements

| id | statement | attaches to | assertion | evidence |
|---|---|---|---|---|
| R-001 | must <behaviour> | module: MOD-01 | test: TestThing | fact: FACT-01 |

### Submodules

#### SUB-01.1 — <name>

module: MOD-01
contract: <signature with exact types>
pre: <...>
post: <...>
errors: <ErrX, ErrY>
side effects: <none / which store>
ordering/idempotency: <...>
test: TestSubThing

<!-- A module with no submodules must declare, in place of this section: -->
<!-- leaf: yes — reason: <why no further decomposition is needed> -->
