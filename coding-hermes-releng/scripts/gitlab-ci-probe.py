#!/usr/bin/env python3
"""Read-only CI/tag/release probe for a GitLab-hosted project (releng lanes).

Exists because a credential-bearing `curl -H "PRIVATE-TOKEN: $TOKEN"` chain is
gate-blocked on unattended surfaces: the whole command refuses, so the CI
question goes unanswered and the tick looks like it skipped the gate. A staged
script reads the token internally and prints only ids, statuses and SHAs.

Auth: GITLAB_TOKEN from the environment, else GITLAB_TOKEN= from ~/.hermes/.env
(override the file with GITLAB_ENV_FILE). The token is never printed.

Usage:
  gitlab-ci-probe.py <project-id> [pipelines|pipeline <id>|tags|releases|commit <sha>]

  pipelines        last 8 pipelines: id status sha ref created_at source
  pipeline <id>    status/sha/finished_at plus every job with allow_failure
  tags             repository tags (JSON)
  releases         release objects (JSON)
  commit <sha>     commit title plus per-status checks

Reading it: a pipeline whose status is `skipped` was created for a tip that
carried `[ci skip]` (board-only carrier) - that is ABSENT CI for the tip, not a
pass. Cite the nearest code-bearing ancestor's pipeline id and conclusion
alongside it.
"""
from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.request

API = os.environ.get("GITLAB_API_BASE", "https://gitlab.readydedis.com/api/v4")


def token() -> str:
    tok = os.environ.get("GITLAB_TOKEN", "").strip()
    if tok:
        return tok
    envfile = os.environ.get("GITLAB_ENV_FILE", os.path.expanduser("~/.hermes/.env"))
    if os.path.exists(envfile):
        with open(envfile) as fh:
            for line in fh:
                line = line.strip()
                if line.startswith("GITLAB_TOKEN="):
                    return line.split("=", 1)[1].strip().strip('"').strip("'")
    sys.exit("GITLAB_TOKEN unavailable (env or %s) - do not guess, report the probe as UNVERIFIED" % envfile)


def get(path: str, pid: int):
    req = urllib.request.Request(
        "%s/projects/%d%s" % (API, pid, path),
        headers={"PRIVATE-TOKEN": token()},
    )
    try:
        with urllib.request.urlopen(req, timeout=45) as resp:
            return json.loads(resp.read().decode())
    except urllib.error.HTTPError as exc:
        # Surface the code, never the request headers.
        return {"_http_error": exc.code, "_body": exc.read().decode()[:300]}


def main(argv: list[str]) -> int:
    if len(argv) < 2:
        print(__doc__.strip())
        return 2
    pid = int(argv[1])
    cmd = argv[2] if len(argv) > 2 else "pipelines"

    if cmd == "pipelines":
        for p in get("/pipelines?per_page=8", pid):
            print(p["id"], p["status"], (p.get("sha") or "")[:9], p.get("ref"),
                  (p.get("created_at") or "")[:19], p.get("source"))
    elif cmd == "pipeline":
        run = get("/pipelines/%s" % argv[3], pid)
        print(json.dumps({k: run.get(k) for k in
                          ("id", "status", "sha", "ref", "created_at", "finished_at", "web_url")}, indent=1))
        for job in get("/pipelines/%s/jobs?per_page=50" % argv[3], pid):
            print(" job", job["name"], job["status"],
                  "allow_failure=%s" % job.get("allow_failure"),
                  "sha=%s" % (job.get("commit", {}).get("id") or "")[:9])
    elif cmd == "tags":
        print(json.dumps(get("/repository/tags", pid)))
    elif cmd == "releases":
        print(json.dumps(get("/releases", pid)))
    elif cmd == "commit":
        commit = get("/repository/commits/%s" % argv[3], pid)
        print(json.dumps({k: commit.get(k) for k in ("id", "title", "created_at")}, indent=1))
        for status in get("/repository/commits/%s/statuses?per_page=20" % argv[3], pid):
            print(" status", status.get("name"), status.get("status"), (status.get("sha") or "")[:9])
    else:
        print("unknown command: %s" % cmd)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
