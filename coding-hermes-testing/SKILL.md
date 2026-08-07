---
name: coding-hermes-testing
description: Front-to-Back / Back-to-Front comprehensive testing — wire verification, structural validation, negative testing, visual rendering, encryption-key correctness. Goes beyond basic unit/integration into real system validation.
version: 1.0.0
category: software-development
---

# Front-to-Back / Back-to-Front Testing

**Real validation, not just "the data is in the output."** This skill defines a comprehensive testing methodology that verifies correctness at every layer — from the user's typing finger to the database bytes and back out through every service, every render path, every exit point.

## Why This Exists

Standard testing (unit → integration → e2e) catches syntactic correctness: "did the API return 200?", "is the name field present in the JSON?". It misses:

- **Structural correctness:** Is the field in the right object, at the right depth, with the right nesting?
- **Render correctness:** The API returned the right value, but does it overflow the text box at 320px? Is the color contrast WCAG AA?
- **Wire correctness:** Input → Service A → Queue → Service B → Database → read path → renders. Did every hop preserve the data correctly?
- **Encryption-key correctness:** We encrypted it, but did we use the PRODUCTION key? The ORGANIZATION's key? A key that meets key-strength policy?
- **Negative testing:** What happens with 1000-character names? Unicode boundary characters? SQL injection in the middle name field? A negative number where only positive makes sense?
- **Type/index correctness:** The value is in the database, but is the column the right type? Is the index covering the query? Is the collation correct for the language?

This skill provides the prompt templates, file structure conventions, and testing dimension checklists to make LLM agents produce this level of testing.

## Core Concepts

### Front-to-Back (Write Path Verification)

Trace data from the entry point through every service, every queue, every transform, to its final resting place. Verify at each hop:

```
User Input → API Gateway → Auth → Validation → Service Logic
    → Message Queue → Worker → Database Write
    → Event Log → Audit Trail → Notification
```

At each hop, verify:
1. **The value** is correct (standard assertion)
2. **The structure** is correct (the JSON shape, the proto message, the column type)
3. **The wiring** is correct (Service A sent to Service B via the correct channel, not a different one)
4. **The side effects** are correct (logs written, events emitted, caches invalidated)

### Back-to-Front (Read Path Verification)

Trace data from storage back through every service, every transform, every render, to the user's eyes:

```
Database → ORM/Driver → Service → API Response → Client Parse → Component Render → User Sees
```

At each hop, verify:
1. **The data** is byte-for-byte what was written
2. **The transforms** are correct (timezone conversion, currency formatting, markdown→HTML)
3. **The render** is correct (DOM placement, CSS layout, color contrast, overflow)
4. **The exit paths** are correct (HTTP status, error body shape, redirect URL)

## Testing Dimensions

For every operation being tested, evaluate ALL of these dimensions. An operation is NOT fully tested until every dimension is covered.

### 1. Positive Path (Happy Path)
- ✅ Correct inputs produce correct outputs
- ✅ Correct inputs produce correct side effects
- ✅ The full chain works end-to-end

### 2. Structural Verification
- Is the output JSON at the correct nesting depth?
- Are required fields present? Are optional fields absent when not requested?
- Is the response envelope correct (`data` wrapper, pagination metadata, error shape)?
- Does the GraphQL shape match the schema? The protobuf match the .proto?

### 3. Render/Visual Verification
- Does the text overflow the container at mobile breakpoints?
- Is the color contrast WCAG AA (4.5:1 for normal text)?
- Do emoji/unicode characters render correctly?
- Does the layout reflow correctly at 320px / 768px / 1024px?
- Are error states rendered visibly (not hidden behind z-index, not white-on-white)?

### 4. Type & Index Correctness
- Is the database column the correct type (VARCHAR vs TEXT, INT vs BIGINT, TIMESTAMP vs TIMESTAMPTZ)?
- Are the indexes correct (covering the query, correct column order, not redundant)?
- Is the collation correct for the language (utf8mb4 vs latin1, case-sensitive vs insensitive)?
- Are foreign keys enforced? Are cascade rules correct?

### 5. Encryption & Key Correctness
- Was the data encrypted (not just base64-encoded and called "encrypted")?
- Was the CORRECT key used (production key, not staging/test/dev)?
- Does the key meet organization key-strength policy (AES-256-GCM, not AES-128-ECB)?
- Is the key stored in the correct HSM/vault, not hardcoded?
- Can we decrypt it with the expected key and get the original plaintext?
- Does key rotation work? Old data decryptable with old key, new data with new key?

### 6. Negative & Boundary Testing
- **Length boundaries:** 0 chars, 1 char, 255 chars, 256 chars, 1000 chars, 65535 chars
- **Type boundaries:** Negative numbers, zero, MAX_INT, floats for integer fields, null vs empty string
- **Unicode boundaries:** Emoji, combining characters, RTL text, zero-width joiners, surrogate pairs
- **Injection-ish:** `' OR 1=1 --`, `<script>`, `../../../etc/passwd`, NUL bytes
- **Protocol boundaries:** HTTP methods that shouldn't work (DELETE on a GET endpoint), wrong Content-Type
- **Auth boundaries:** No token, expired token, wrong-role token, tampered token

### 7. Cross-Service Wire Verification
- Does the message format survive the queue (JSON → RabbitMQ → JSON intact)?
- Are the right services subscribed to the right topics/queues?
- Is the event schema version compatible between producer and consumer?
- Are retry/DLQ paths working (poison message → DLQ, not infinite retry)?
- Is idempotency working (same message twice → no double-write)?

### 8. Log & Audit Trail Verification
- Is every write logged at the correct level (INFO for normal, WARN for degraded, ERROR for failure)?
- Do logs contain the right structured fields (trace_id, user_id, operation)?
- Is the audit trail complete (who did what when, with what old/new values)?
- Are logs NOT containing PII/secrets in plaintext?

### 9. Exit Path Verification
- Does the error response match the API contract exactly?
- Are the right HTTP status codes used (400 vs 422, 401 vs 403, 500 vs 502)?
- Are redirect URLs correct and safe (no open redirect)?
- Does the error page render correctly in each supported browser?
- Are CORS headers correct? CSP headers? Security headers present?

## Testing File Structure

Each project creates a `tests/` directory inside `.coding-hermes/` alongside `tasks.md`. Structure:

```
.coding-hermes/
├── board/
│   ├── tasks.jsonl           # Task board (JSONL canonical store — git-tracked)
│   ├── events.jsonl          # Event log (JSONL canonical store — git-tracked)
│   ├── board.db              # DuckDB cache (untracked, rebuildable)
│   └── schema.sql            # Table definitions
├── tests/                # Testing directory
│   ├── _index.md         # Testing manifest — what's tested, what's not
│   ├── f2b/              # Front-to-Back tests (write paths)
│   │   ├── auth/         # Auth write tests
│   │   ├── data/         # Data mutation tests
│   │   └── events/       # Event emission tests
│   ├── b2f/              # Back-to-Front tests (read paths)
│   │   ├── api/          # API read tests
│   │   ├── render/       # Visual render tests
│   │   └── export/       # Data export tests
│   ├── negative/         # Negative/boundary tests
│   ├── crypto/           # Encryption key tests
│   ├── wiring/           # Cross-service wire tests
│   ├── structure/        # Schema/structure tests
│   └── audit/            # Log/audit trail tests
├── prompts/              # LLM testing prompts
│   ├── f2b-write.md      # F2B write path prompt
│   ├── b2f-read.md       # B2F read path prompt
│   ├── negative.md       # Negative testing prompt
│   ├── visual.md         # Visual/render testing prompt
│   └── crypto.md         # Encryption verification prompt
└── test-state.toml       # Test state tracking (TOML format)
```

### test-state.toml Format

```toml
[project]
name = "hermes-canopy"
last_full_test = "2026-07-24T12:00:00Z"
test_coverage = {
  f2b = 7,     # 7 write paths tested
  b2f = 12,    # 12 read paths tested
  negative = 3,
  visual = 2,
  crypto = 0,  # ⚠️ untested
  wiring = 1,
  structure = 5,
  audit = 0,   # ⚠️ untested
}

[[untested_paths]]
path = "POST /api/cards → cards table → render in CardView"
reason = "CardView render not implemented yet"
dimensions_missing = ["visual", "structure", "render"]

[[untested_paths]]
path = "User login → JWT issue → encrypted claims"
reason = "Key rotation not tested"
dimensions_missing = ["crypto"]

[[known_gaps]]
dimension = "crypto"
finding = "AES key stored in config.yaml, not HSM"
severity = "critical"
task_ref = "BE-13"
```

## Prompt Templates

### F2B Write Path Testing Prompt

```
You are a Front-to-Back testing agent testing {project_name}.

Operation: {operation_description}
Write path: {entry_point} → {hop1} → {hop2} → ... → {final_store}

For each hop in the write path, verify:
1. VALUE: Is the data byte-for-byte correct?
2. STRUCTURE: Is the field at the right depth? Right type? Right nesting?
3. WIRING: Did it arrive via the correct channel? Correct queue/topic?
4. SIDE EFFECTS: Were logs written? Events emitted? Caches invalidated?

At the final store ({database}/{queue}/{file}):
- Is the column type correct? (INT not VARCHAR, TIMESTAMPTZ not TIMESTAMP)
- Are indexes covering the query path?
- If encrypted: is the correct key used? (Verify by decrypting with expected key)
- Is the audit trail complete?

Negative cases to test:
- {negative_case_1}
- {negative_case_2}
- {negative_case_3}

Output a test report with:
- ✅ PASS for each verification point
- ❌ FAIL with exact mismatch details (expected X, got Y, at hop Z)
- ⚠️  UNTESTABLE with reason (e.g., "no HSM access to verify key storage")

File the report in: .coding-hermes/tests/f2b/{category}/{operation_name}.md
```

### B2F Read Path Testing Prompt

```
You are a Back-to-Front testing agent testing {project_name}.

Operation: {operation_description}
Read path: {data_store} → {service1} → {service2} → ... → {exit_point}

At each hop, verify:
1. DATA: Is the value byte-for-byte what was written in the F2B test?
2. TRANSFORM: Is the transformation correct? (timezone, currency, encoding, serialization)
3. PRESENTATION: At the exit point (API response, HTML page, CLI output), verify:
   - Structure: correct JSON shape, correct HTML nesting
   - Render: no text overflow, correct color contrast, correct layout at 320/768/1024px
   - Content: all expected fields present, no extra fields, correct order

Exit path verification:
- HTTP: status code correct, headers correct (CORS, CSP, security), body shape correct
- CLI: exit code correct, stdout correct, stderr empty (or correct for --verbose)
- HTML: DOM structure correct, CSS applied correctly, JS interactivity works

Test with browser rendering when applicable:
- Open the page at {url}
- Verify with browser_vision that {visual_check_1}, {visual_check_2}
- Check text overflow at 320px width
- Check color contrast meets WCAG AA

File the report in: .coding-hermes/tests/b2f/{category}/{operation_name}.md
```

### Negative Testing Prompt

```
You are a negative/boundary testing agent for {project_name}.

Target: {operation} at {endpoint_or_function}

Test these boundary categories:

1. LENGTH:
   - Empty string, 1 char, 254 chars, 255 chars, 256 chars, 1000 chars, 65535 chars
   - JSON body: 1KB, 1MB, 10MB (if applicable)

2. TYPE:
   - null instead of string, number instead of string, array instead of object
   - Negative number where only positive makes sense
   - Float where integer expected (and vice versa)
   - Boolean "true" as string vs boolean true

3. UNICODE:
   - Emoji: 😀🔥🇺🇳👨‍👩‍👧‍👦 (single, multi-codepoint, ZWJ sequences)
   - RTL text: مرحبا بالعالم injected in LTR fields
   - Combining characters: café written as c + a + f + é (two ways)
   - Zero-width characters: zero-width space, zero-width joiner, zero-width non-joiner
   - Surrogate pairs and unicode normalization forms (NFC vs NFD)

4. INJECTION-ADJACENT:
   - SQL: '; DROP TABLE users; --, ' OR '1'='1
   - XSS: <script>alert(1)</script>, <img src=x onerror=alert(1)>
   - Path traversal: ../../../etc/passwd, ..\..\windows\system32
   - Null bytes: value\u0000withnull
   - CRLF: value\r\nInjected-Header: true

5. PROTOCOL:
   - Wrong HTTP method (DELETE on GET-only endpoint)
   - Wrong Content-Type (text/plain when JSON expected)
   - Missing required headers
   - Duplicate headers

For each test case, verify:
- The system handles it gracefully (no crash, no 500)
- Error response is correct for the API contract (400 vs 422, correct error code)
- No data corruption in the database
- No PII/secrets leaked in error messages

File the report in: .coding-hermes/tests/negative/{category}/{operation_name}.md
```

### Visual/Render Testing Prompt

```
You are a visual testing agent for {project_name}.

Page/Component: {page_url_or_component}
Responsive breakpoints to test: 320px, 768px, 1024px, 1440px

For each breakpoint:
1. Navigate to {page_url}
2. Set viewport to {width}x{height}
3. Take screenshot with browser_vision
4. Verify:
   - No text overflow (text stays within container bounds)
   - No horizontal scrollbar at mobile widths (unless intentional)
   - All interactive elements visible and clickable (no z-index burial)
   - Color contrast meets WCAG AA (4.5:1 for normal text, 3:1 for large text)
   - Error states visible: empty state, loading state, error state ALL render
   - Forms: labels correctly associated with inputs, error messages visible
   - Dark mode: if supported, verify all elements readable in dark mode

Content verification:
- {content_check_1}
- {content_check_2}
- {content_check_3}

File the report in: .coding-hermes/tests/b2f/render/{component_name}.md
```

### Encryption/Key Verification Prompt

```
You are a cryptographic testing agent for {project_name}.

Target: {operation} which stores encrypted data at {storage_location}

Verify encryption correctness:
1. ENCRYPTION PRESENCE:
   - Is the data actually encrypted? (Not base64, not "encrypted": "plaintext")
   - Verify by inspecting the raw storage bytes. Encrypted data has:
     - High entropy (close to random)
     - No recognizable plaintext patterns
     - Correct format for the algorithm (e.g., GCM has auth tag appended)

2. KEY CORRECTNESS:
   - Decrypt with EXPECTED production key → get original plaintext ✅
   - Decrypt with STAGING key → get garbage or error ✅ (proves wrong key doesn't work)
   - Decrypt with RANDOM key → get garbage or error ✅
   - The key fingerprint/ID stored with the ciphertext must match the current active key

3. KEY STORAGE:
   - Is the key in a secure location? (HSM, vault, KMS) — NOT hardcoded, NOT config file
   - Does the key meet organization policy? (AES-256-GCM, not AES-128-ECB)
   - Is there a key rotation procedure?
   - Old data decryptable with old (rotated) key?

4. KEY ROTATION:
   - Insert data with KEY_V1 → verify it decrypts with KEY_V1
   - Rotate to KEY_V2
   - Insert new data → verify it encrypts with KEY_V2 and decrypts with KEY_V2
   - OLD data (KEY_V1) → must still decrypt with KEY_V1
   - NEW data (KEY_V2) → must NOT decrypt with KEY_V1

File the report in: .coding-hermes/tests/crypto/{operation_name}.md
```

## Integration with the Foreman Loop

When a foreman runs the never-done audit (coding-hermes-never-done), it includes this testing dimension as part of check #12 (Usability/End-to-End) and check #13 (E2E Testing Tick). The foreman should:

1. Check if `.coding-hermes/tests/_index.md` exists
2. If not, create it and inject a TEST-INFRA task: "Create testing infrastructure per coding-hermes-testing v1.0"
3. Check `test-state.toml` for coverage gaps (dimensions with 0 coverage)
4. Inject tasks for each untested dimension/operation
5. On E2E Testing Tick (#13): select one untested path and run the full F2B→B2F cycle

## Model Selection for Testing

Different testing dimensions benefit from different models:

| Dimension | Primary Model | Why |
|-----------|--------------|-----|
| F2B write path | DeepSeek V4 Pro | Structural reasoning, multi-hop tracing |
| B2F read path | GPT-5.6 Sol | Pattern matching, consistency verification |
| Visual/render | GPT-5.6 Luna | Vision, screenshot analysis |
| Negative testing | Kimi K3 | Exhaustive edge-case generation |
| Encryption/crypto | DeepSeek V4 Pro | Cryptographic reasoning |
| Structure/schema | DeepSeek V4 Flash | Fast schema validation |
| Cross-service wiring | DeepSeek V4 Pro | Multi-service dependency tracing |

## Task Matrix Format for Testing Tasks

When the foreman creates testing tasks, use this matrix format:

```
| ID | Task | Pri | Cpx | Deps | Tags | Model | Reasoning | Fallback |
| TEST-F2B-001 | F2B: {write path description} | Critical | 4 | {deps} | +f2b, +write, +{domain} | DeepSeek V4 Pro | Multi-hop tracing needed for {N} services | Kimi K3 |
| TEST-B2F-001 | B2F: {read path description} | High | 3 | {deps} | +b2f, +read, +render | GPT-5.6 Luna | Visual verification needed | DeepSeek V4 Flash |
| TEST-NEG-001 | NEG: {boundary description} | High | 2 | — | +negative, +boundary | Kimi K3 | Edge case generation | DeepSeek V4 Flash |
| TEST-VIS-001 | VIS: {visual check description} | Medium | 2 | {f2b_test} | +visual, +render, +browser | GPT-5.6 Luna | Screenshot analysis | — |
| TEST-CRYPTO-001 | CRYPTO: {encryption check} | Critical | 4 | — | +crypto, +security | DeepSeek V4 Pro | Cryptographic reasoning | — |
```

## Relationships

- **coding-hermes-never-done:** Check #13 (E2E Testing Tick) uses this skill's prompt templates to run comprehensive testing
- **coding-hermes-foreman:** Foreman injects testing tasks into the board using the matrix format above
- **coding-hermes-board:** Testing tasks follow the same model-router matrix format
- **hermes-dagger:** Future support for building these testing pipelines as Dagger workflows

## Version History

- **v1.0.0** (2026-07-24): Initial release — F2B/B2F dimensions, prompt templates, file structure, test-state.toml, model selection table
