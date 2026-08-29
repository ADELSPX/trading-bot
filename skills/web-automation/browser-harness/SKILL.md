---
name: browser-harness
description: "Use when driving a real browser via CDP — automation, scraping, site interaction, or app work. Prefer over browser-use for protected/bot-walled sites. Requires Chrome running with remote debugging on 127.0.0.1:9222 (or set BU_CDP_URL)."
---

# browser-harness (teknium1/browser-use)

Direct browser control via CDP. Better than `browser-use` skill for bot-protected or JS-heavy pages because it attaches to a real running Chrome and writes reusable helpers as it works.

## Prerequisites (IMPORTANT — verified working setup on Fazza server)
1. Chrome must be running with remote debugging enabled:
   ```
   google-chrome --remote-debugging-port=9222 --user-data-dir=/root/hermes-browser-profile --no-sandbox --disable-gpu --headless=new
   ```
   (already configured; if not running, start it — a systemd unit or background process should keep it alive)
2. The harness needs `BU_CDP_URL` pointed at it. Either export it once:
   ```
   export BU_CDP_URL="http://127.0.0.1:9222"
   ```
   or prefix every call:
   ```
   BU_CDP_URL="http://127.0.0.1:9222" browser-harness <<'PY'
   ...
   PY
   ```

## Quick start
```bash
BU_CDP_URL="http://127.0.0.1:9222" browser-harness <<'PY'
print(page_info())
PY
```
- Invoke as `browser-harness`. Use heredocs for multi-line commands.
- Helpers are pre-imported: `page_info()`, `js(expr)`, `new_tab(url)`, `goto_url(url)`, `fill_input(sel, txt)`, `click_at_xy(x,y)`, `capture_screenshot()`, `cdp("Domain.method", ...)`, `ensure_real_tab()`, `wait_for_load()`.
- First navigation is `new_tab(url)`, not `goto_url(url)`.

## When NOT to use
A plain HTTP fetch (`curl`/web tools) reads public pages fine — no browser needed. Escalate to browser-harness only when the task needs clicks, typing, logged-in sessions, JS rendering, or a bot-protected page.

## Page workflow (verified)
- Prefer the accessibility tree: `cdp("Accessibility.getFullAXTree")["nodes"]` → filter by role/name → get box center → `click_at_xy(x,y)` → verify with `js(...)`.
- Coordinates: `q = cdp("DOM.getBoxModel", backendNodeId=n)["model"]["content"]; x,y = sum(q[0::2])/4, sum(q[1::2])/4`.
- After navigation call `wait_for_load()`.
- `js("document.body.innerText")` extracts page text (use `js`, NOT `import js`).
- Login walls: stop and ask. Use available SSO only if Chrome is already signed in.
- Raw CDP available: `cdp("Domain.method", **kwargs)`.

## Gotchas (Fazza-specific)
- browser-harness does NOT auto-discover Chrome — you MUST pass `BU_CDP_URL`.
- `js` is a pre-imported function, not an importable module.
- Chrome CDP runs headless on the server; keep it alive via background process or systemd.
- For protected sites (Payhip/Cloudflare), use the mac's real Chrome profile via SSH CDP instead (see real-profile-browsing notes in memory).

## Local Chrome management
- Diagnostics: `browser-harness --doctor`
- Stop Chrome: `pkill -f "remote-debugging-port=9222"` (then restart if needed)
- Update: `browser-harness --update -y`

## Cloud browsers (optional, paid)
`browser-harness auth login` then `start_remote_daemon("name")` for isolated/parallel/stealth browsers. Not needed for local server work.
