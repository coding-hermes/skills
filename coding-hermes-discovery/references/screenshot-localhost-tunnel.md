# Screenshot Localhost Services via Cloudflare Tunnel + CDP

When you need browser screenshots of a localhost service (Forgejo, web UI, dashboard) and both `browser_navigate` and CDP `Page.captureScreenshot` are blocked for private/internal addresses, use this tunnel + cookie-injection pattern.

## The Problem

- `browser_navigate("http://localhost:3030")` → blocked (private address)
- `browser_cdp(Page.captureScreenshot, target_id=...)` → blocked (private content)
- `curl` can access localhost but can't produce browser screenshots
- Need a public URL the browser tool can access that routes to localhost

## The Solution: Cloudflare Tunnel + ROOT_URL Fix + CDP Cookie Injection

### Step 1: Create a Cloudflare tunnel

```bash
cloudflared tunnel --url http://localhost:<port> &
# Wait for the URL to appear in output:
# https://<subdomain>.trycloudflare.com
```

### Step 2: Fix the service's ROOT_URL to match the tunnel

If the service issues session cookies tied to its configured domain (Forgejo, Gitea, any web app with login), the cookies won't work through the tunnel unless the ROOT_URL matches:

```bash
# For Forgejo/Gitea — update the env var and restart
docker rm -f <container>
docker run -d --name <container> --network host \
  -e GITEA__server__ROOT_URL=https://<tunnel>.trycloudflare.com/ \
  -e GITEA__server__DOMAIN=<tunnel>.trycloudflare.com \
  ... <image>
```

### Step 3: Authenticate via curl to get a session cookie

```bash
curl -s -c /tmp/cookies.txt -X POST \
  "https://<tunnel>.trycloudflare.com/user/login" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "user_name=<user>&password=<pass>" \
  -o /dev/null -w "%{http_code}"
# Should return 303 (redirect = success)

# Extract the session cookie value
grep i_like_gitea /tmp/cookies.txt | awk '{print $NF}'
```

### Step 4: Inject the session cookie via CDP Storage.setCookies

The session cookie from curl is HttpOnly — JavaScript's `document.cookie` can't set it. Use CDP's `Storage.setCookies`:

```json
{
  "method": "Storage.setCookies",
  "params": {
    "cookies": [{
      "domain": "<tunnel>.trycloudflare.com",
      "httpOnly": true,
      "name": "i_like_gitea",
      "path": "/",
      "sameSite": "Lax",
      "secure": true,
      "session": true,
      "value": "<cookie-value-from-curl>"
    }]
  },
  "target_id": "<active-browser-tab-target-id>"
}
```

**Critical:** Use the EXACT domain without a leading dot (`.trycloudflare.com` vs `trycloudflare.com`). Check with `Storage.getCookies` after injection to verify the cookie was set with the correct domain.

### Step 5: Clear stale cookies first

If a previous login attempt left stale cookies, clear them before injecting:

```json
{"method": "Storage.clearCookies", "params": {}, "target_id": "<target>"}
```

Then re-inject the correct cookie and navigate to the authenticated page.

### Step 6: Navigate and screenshot

Now `browser_navigate` to the authenticated URL through the tunnel — cookies will carry the session:

```
browser_navigate("https://<tunnel>.trycloudflare.com/admin/users")
browser_vision(question="Screenshot of the admin page")
```

## Pitfalls

1. **Domain mismatch:** Cookie domain must match EXACTLY — `domain.com` ≠ `.domain.com`. Check with `Storage.getCookies` after injection.

2. **ROOT_URL mismatch:** If the service's configured ROOT_URL doesn't match the tunnel URL, session cookies won't be accepted. Fix the ROOT_URL before capturing cookies.

3. **Tunnel expiration:** Cloudflare quick tunnels are temporary. If the session drops, recreate the tunnel and re-inject cookies.

4. **Stale cookies:** Failed login attempts leave invalid session cookies. Always `Storage.clearCookies` before injecting a fresh one.

5. **Tab hijacking:** The CDP target may switch to a different tab if another automation is using the same browser. Create a fresh `Target.createTarget({"url":"about:blank"})` before injecting cookies.

## Alternative: serveo.net (if cloudflare is blocked)

```bash
ssh -o StrictHostKeyChecking=no -R 80:localhost:<port> serveo.net
# URL: https://<hash>.serveousercontent.com
# NOTE: serveo has a warning interstitial — click "Continue to Site" first
```

## Proven

Helix 2026-07-30 — Used this pattern to capture Forgejo admin panel + PR page screenshots for client verification report. Cloudflare tunnel + ROOT_URL fix + CDP Storage.setCookies injection + browser_vision.
