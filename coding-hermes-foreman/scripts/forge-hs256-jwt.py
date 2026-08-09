#!/usr/bin/env python3
"""Forge an HS256 JWT for local E2E smoke tests. Stdlib only, cron-safe (no -c flag, no deps).

Usage:
    forge-hs256-jwt.py <secret> [tenant_id] [audience] [issuer]

Defaults (dexdat-memory service): tenant_id=tnt_tick73, audience=dexdat-memory-api,
issuer=dexdat-memory. For other services pass all args or edit the defaults.

Key lesson (tick #73): for services that resolve the actor from the JWT tenant/user
claim (e.g. dexdat-memory's sqlitePermissionsProvider), the claim MUST match a REAL
row in the DB — create the tenant/user via the API FIRST, then forge the token with
the returned id. Otherwise: FK constraint 787 on create, agent_lookup_failed on search.
"""
import base64, hashlib, hmac, json, sys, time

secret = sys.argv[1] if len(sys.argv) > 1 else "dev-secret"
tenant_id = sys.argv[2] if len(sys.argv) > 2 else "tnt_tick73"
audience = sys.argv[3] if len(sys.argv) > 3 else "dexdat-memory-api"
issuer = sys.argv[4] if len(sys.argv) > 4 else "dexdat-memory"
now = int(time.time())

header = {"alg": "HS256", "typ": "JWT"}
payload = {
    "sub": "e2e-smoke",
    "tenant_id": tenant_id,
    "iss": issuer,
    "aud": audience,
    "iat": now,
    "exp": now + 3600,
    "role": "admin",
}


def b64url(b: bytes) -> str:
    return base64.urlsafe_b64encode(b).rstrip(b"=").decode()


h = b64url(json.dumps(header, separators=(",", ":")).encode())
p = b64url(json.dumps(payload, separators=(",", ":")).encode())
sig = b64url(hmac.new(secret.encode(), f"{h}.{p}".encode(), hashlib.sha256).digest())
print(f"{h}.{p}.{sig}")
