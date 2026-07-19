# Go: `http.NewRequest` Panics on Typed-Nil Body

## The Bug

```go
var bodyReader *bytes.Buffer  // typed nil — *bytes.Buffer is nil
if body != nil {
    // …body is nil, so this block never executes…
    bodyReader = bytes.NewBuffer(b)
}
// bodyReader is still nil (*bytes.Buffer)
req, err := http.NewRequest(method, url, bodyReader)
// PANIC: runtime error: invalid memory address or nil pointer dereference
// at bytes.(*Buffer).Len() — called inside http.NewRequest
```

`http.NewRequest` calls `.Len()` on the body reader to determine Content-Length. When a typed nil `*bytes.Buffer` is passed, Go's method dispatch still resolves `(*bytes.Buffer).Len()` which dereferences the nil pointer → segfault.

## The Fix

Use `io.Reader` (interface type) instead of `*bytes.Buffer` (concrete type):

```go
var bodyReader io.Reader  // interface nil — not a typed nil
if body != nil {
    bodyReader = bytes.NewBuffer(b)
}
// bodyReader is nil (interface nil — no dynamic type)
req, err := http.NewRequest(method, url, bodyReader)
// Works! http.NewRequest checks if body == nil at the interface level.
```

`http.NewRequest` does an interface-nil check (`body == nil`) BEFORE calling any methods, so an interface-nil `io.Reader` behaves correctly — no body → no Content-Length header.

## Detection

- Stack trace shows: `panic: runtime error: invalid memory address or nil pointer dereference`
- Trace points to: `bytes.(*Buffer).Len` called from `net/http.NewRequestWithContext`
- The caller is a test helper like `doJSON` that delegates to `http.NewRequest`

## Proven

Rabbit-Hole 2026-07-12 — `doJSON` helper in `server_test.go` used `var bodyReader *bytes.Buffer`; test `TestListSessions_Empty` passed `nil` body → panic during `http.NewRequest`. Fix: change to `var bodyReader io.Reader`. All 22 express tests passed immediately after.
