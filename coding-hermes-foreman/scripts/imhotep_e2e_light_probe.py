#!/usr/bin/env python3
"""Imhotep E2E light smoke probe — API endpoints + SPA assets on the local demo (:8095).

Usage: python3 scripts/imhotep_e2e_light_probe.py [base_url]
Default base: http://localhost:8095. Env var BASE overrides.
Prints PASS/FAIL per endpoint + hashed-asset check; exit 0 iff all expected codes match.
Route table source: cmd/demo/main.go (verified T77):
  - GET /api/v1/materials/categories is the ONLY categories route; bare /api/v1/categories
    is NOT a route (404) — never probe it (T77 false-regression scare).
  - bare /health returns SPA fallback HTML 200 (457B) — the real probe is /api/v1/health
    (spec API-ENDPOINT-002, corrected T76).
  - /pipeline is fully inline (zero external src/href) — probe assets from root index.html only.
"""
import json
import os
import re
import sys
import urllib.error
import urllib.request

BASE = sys.argv[1] if len(sys.argv) > 1 else os.environ.get("BASE", "http://localhost:8095")

# (path, expected_status, kind) — kind: json|html|None (no body parse)
PATHS = [
    ("/api/v1/health", 200, "json"),
    ("/api/v1/projects", 200, "json"),
    ("/api/v1/materials", 200, "json"),
    ("/api/v1/agencies", 200, "json"),
    ("/api/v1/materials/categories", 200, "json"),
    ("/api/v1/boq/generate", 404, None),
    ("/api/v1/placement/approve", 404, None),
    ("/pipeline", 200, "html"),
]


def fetch(path):
    try:
        with urllib.request.urlopen(urllib.request.Request(BASE + path, method="GET"), timeout=15) as r:
            return r.status, r.read(), r.headers.get("Content-Type", "")
    except urllib.error.HTTPError as e:
        return e.code, b"", e.headers.get("Content-Type", "")


ok = 0
for path, expect, kind in PATHS:
    code, body, ctype = fetch(path)
    good = code == expect
    ok += good
    extra = ""
    if path == "/api/v1/health" and code == 200:
        d = json.loads(body)
        extra = f"status={d.get('status')} v={d.get('version')} checks={','.join(d.get('checks', {}).keys())}"
    if path == "/api/v1/materials" and code == 200:
        extra = f"envelope keys={sorted(json.loads(body).keys())}"
    if path == "/pipeline" and code == 200:
        txt = body.decode(errors="ignore")
        extra = f"{len(body)}B inline={'src=' not in txt and 'href=' not in txt}"
    print(f"{'PASS' if good else 'FAIL'} {code} (expect {expect}) {path} [{ctype[:25]}] {extra}")
print(f"E2E_SMOKE={ok}/{len(PATHS)}")

# Hashed assets referenced ONLY from root index.html
try:
    with urllib.request.urlopen(BASE + "/", timeout=15) as r:
        root = r.read().decode(errors="ignore")
    m = re.search(r"<title>(.*?)</title>", root)
    print(f"root: {r.status} {len(root)}B title={m.group(1) if m else '?'}")
    assets = re.findall(r'(?:src|href)="(/assets/[^"]+)"', root)
    aok = 0
    for a in assets:
        with urllib.request.urlopen(BASE + a, timeout=15) as ar:
            b = ar.read()
            good = ar.status == 200 and len(b) > 0
            aok += good
            print(f"{'PASS' if good else 'FAIL'} {a} {len(b)}B")
    print(f"ASSETS={aok}/{len(assets)}")
except Exception as e:
    print("ASSET_PROBE_ERR", e)

sys.exit(0 if ok == len(PATHS) else 1)
