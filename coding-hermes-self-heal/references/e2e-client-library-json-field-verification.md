# E2E Client Library JSON Field Verification

When a worker builds an API client library + E2E test that fails against the live
service despite unit tests passing (mocks match the struct tags but not the real API),
the cause is often a JSON field name mismatch between the Go struct tags and the
actual API response. Unit tests pass because the mocks use the same wrong field
names as the struct. Only the live service reveals the gap.

## Detection

1. E2E test fails with an empty or wrong value extracted from the API response
2. Unit tests (mock-based) pass — the mocks return the same wrong format
3. The API call itself succeeds (HTTP 200/201) but the parsed result is wrong

**Smell:** "branch should have a commit SHA" assertion fails, but the API returned
201 Created. The struct parsed the response but the field was never populated.

## Diagnosis Flow

```
1. Run E2E test against live service → observe failure
2. curl the live API endpoint with the same parameters → capture raw JSON
3. Compare the actual JSON keys against the Go struct's json:"" tags
4. If they differ, the struct tags are wrong — the mock tests are self-consistent
   but wrong against reality
5. Fix the struct tags to match the actual API response
6. Update all mock responses in unit tests to use the correct structure
7. Re-run unit tests → should pass (now using the correct field names)
8. Re-run E2E test against live service → should pass
```

## Canonical Example: Forgejo Branch Creation Response

**The bug:** Go struct used `json:"commit_sha,omitempty"` expecting a flat field.
Forgejo v1.21+ returns the SHA nested inside a `commit` object:

```json
{
    "name": "feature/xyz",
    "ref": "refs/heads/feature/xyz",
    "commit": {
        "id": "812c6dd28a36324cdb7ea3303eca68ecd9d208fa",
        "message": "Initial commit\n",
        ...
    },
    ...
}
```

**The fix:** Replace the flat field with a nested struct:

```go
// Before (wrong — doesn't match Forgejo v1.21 API)
type CreateBranchResponse struct {
    Name      string `json:"name"`
    Ref       string `json:"ref"`
    CommitSHA string `json:"commit_sha,omitempty"`
}

// After (correct — matches actual API)
type CreateBranchResponse struct {
    Name   string `json:"name"`
    Ref    string `json:"ref"`
    Commit struct {
        ID      string `json:"id"`
        Message string `json:"message"`
    } `json:"commit"`
    CommitSHA string `json:"-"` // populated from Commit.ID after unmarshal
}
```

Then in the method, extract `CommitSHA` from `Commit.ID` after unmarshaling:

```go
if branch.CommitSHA == "" {
    switch {
    case branch.Commit.ID != "":
        branch.CommitSHA = branch.Commit.ID
    case branch.Ref != "":
        branch.CommitSHA = branch.Ref // fallback: older API versions
    }
}
```

## Why Mock Tests Don't Catch This

Mock-based unit tests define their own response bodies. When the mock writes
`"commit_sha": "abc123"` and the struct reads `json:"commit_sha"`, the test
passes — but the real API never returns that key. The mock and the struct are
self-consistent but both wrong against reality.

Only an E2E test against the live service catches the mismatch. Always run at
least one E2E test against the live API after building a client library, even
if all mock-based unit tests pass.

## Proven

Helix Tick #46 (2026-07-29) — TestForgejoE2E failed because `CreateBranchResponse.CommitSHA`
used `json:"commit_sha"` but Forgejo v1.21 returned `commit.id` (nested). The branch
created successfully (HTTP 201) but the SHA was empty because the flat field didn't
match the nested structure. Mock tests in `branch_test.go` passed because they used
`"commit_sha": "abc123def456"` — the mock matched the (wrong) struct. Fixed by
querying the live API with curl, discovering the nested `commit.id` structure, and
updating the struct tags + all mock responses.
