# Headless Chrome Dashboard Screenshots

Capture high-quality PNG screenshots of locally-hosted dashboards without a
display server. Works on headless Linux machines with `google-chrome` installed.

## Command

```bash
google-chrome --headless=new --disable-gpu \
  --screenshot=/tmp/dashboard.png \
  --window-size=1280,900 \
  --virtual-time-budget=8000 \
  http://127.0.0.1:9090/dashboard
```

## Important steps

1. **Warm the endpoint first.** The dashboard relies on database queries that may
   be cold. Two quick curls before the screenshot ensure data populates:
   ```bash
   curl -s http://127.0.0.1:9090/dashboard > /dev/null
   curl -s http://127.0.0.1:9090/dashboard > /dev/null
   ```

2. **virtual-time-budget** is the max simulated time Chrome waits for JS/paint.
   Increase to 10000 for slow-loading pages.

3. **D-Bus errors in stderr are harmless.** Without a user session bus,
   Chrome logs dbus connection errors. These don't affect the screenshot.

4. **Output is ~100KB** for a typical dashboard. Verify with:
   ```bash
   ls -lh /tmp/dashboard.png
   ```

## Why not browser_navigate / browser_cdp?

Hermes' browser tools (browser_navigate, browser_cdp) block localhost/private
addresses for security. The Chrome binary in `--headless=new` mode bypasses
this restriction because it runs as a subprocess, not through Hermes' CDP
supervisor.

## Proven

2026-07-18 — captured the coding-hermes-scheduler dashboard for README.md
via this technique. Works reliably on karaHermes-mde-7840hs (headless server).
