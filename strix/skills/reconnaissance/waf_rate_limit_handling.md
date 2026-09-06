---
name: waf-rate-limit-handling
description: Detect Cloudflare/WAF rate-limiting and challenge responses, throttle proactively before triggering them, and back off correctly when one is hit
---

# WAF / Rate-Limit Handling

Load this before any high-volume fuzzing, crawling, or spraying against a
target — and immediately once you suspect a block, even mid-task. Getting
rate-limited or WAF-challenged mid-scan is not just noise: it silently
degrades every subsequent tool run against that host (fuzzers "complete"
against a challenge page and report false negatives), and one agent's burst
can burn the rate budget every other agent sharing this scan's sandbox
needs.

## Why this matters more here than in a normal single-client tool

All agents in one scan share the sandbox container's single egress IP.
Cloudflare (and most WAFs/CDNs) rate-limit by source IP, so the limit is a
**scan-wide budget**, not a per-agent or per-tool one. Five agents each
independently sending a "reasonable" 10 req/s to the same host can trigger a
block that none of them would have caused alone. Individual throttling is
necessary but not sufficient — coordination across agents matters just as
much (see "Cross-agent coordination" below).

## Detection signals

Treat any of these as a hit, not just an explicit `429`:

- **Headers**: `Server: cloudflare`, `cf-ray`, `cf-mitigated`, `cf-cache-status`
  suddenly appearing where it wasn't before, `Retry-After`.
- **Status codes**: `429` (explicit); `403`/`503` where the body also matches
  below (WAF/CDN block, not the app's own auth logic).
- **Body markers**: "Just a moment...", "Checking your browser before
  accessing", "Attention Required! | Cloudflare", "cf_chl_opt",
  "cf-browser-verification", a Turnstile/hCaptcha/reCAPTCHA widget appearing
  on an endpoint that previously returned normal content.
- **Behavioral**: a previously-200 endpoint starts returning the same
  challenge page for every request regardless of parameters; a sudden latency
  spike (JS challenge computation) across an entire run; a fuzzer's hit rate
  drops to near-zero with all responses looking identical.

A tool run that "completes successfully" while every response is actually a
challenge page is a false negative, not a clean result — check a sample of
raw responses, not just exit codes/counts, when a target is known or
suspected to sit behind a WAF/CDN.

## Proactive: throttle before you get blocked

1. Fingerprint the WAF/CDN early in recon, before any high-volume tool run:
   `wafw00f <url>`, or a single lightweight probe checking the headers above.
2. If Cloudflare (or any WAF) is present, do not start at a tool's default
   rate. Start conservative and only ramp up gradually while watching for
   the signals above:
   - `ffuf`: `-rate 2` with a randomized delay (`-p 1.5-3.0`), `-t 5`
   - `nuclei`: `-rl 5 -c 5 -bs 5`
   - `katana`: `-rl 5 -c 2 -p 5`
   - `httpx`: `-rl 5 -t 5`
   - `sqlmap`: `--delay=1 --randomize --safe-freq=5 --threads=1`
   - Custom `asyncio`/`aiohttp` sprays: bound concurrency with a
     `asyncio.Semaphore`, add a fixed-or-jittered delay between requests
     (start ~2-3 req/s total), and check every response against the
     detection signals inline rather than only at the end.
3. Record the fingerprint and starting ceiling via `create_note` so every
   other agent that touches this host starts conservative too, instead of
   each independently rediscovering the limit.

## Reactive: what to do the moment you hit one

This is the part that matters most and is easy to get wrong — do not just
let the current tool run finish at the same rate and call it done.

1. **Stop immediately.** Kill the running tool/script rather than letting it
   keep sending at the triggering rate; every request sent while blocked
   both wastes budget and risks escalating a temporary rate-limit into a
   longer/harder block.
2. **Cool down before probing again.** Wait before sending anything else to
   that host. Start at ~60s. If a single lightweight follow-up probe still
   shows a block/challenge, double the wait (60s → 120s → 240s → ..., cap
   around 15 minutes) with ±20% random jitter. Never busy-poll the target to
   check if the block cleared.
3. **Resume materially below the rate that triggered it — never at the same
   rate.** Concrete rule: halve whatever rate/concurrency was active when
   the block hit, with a hard floor around 1 request per 2-3 seconds,
   single-threaded. Treat this reduced ceiling as the new default for this
   host for the rest of the scan, not a temporary dip you creep back up
   from.
4. **Record it.** `create_note` the host, the rate that triggered the block,
   the new ceiling, and when — so other agents inherit the lesson instead of
   re-triggering the same block independently.
5. If you hit a hard, persistent block that backoff doesn't clear after a
   couple of cycles (a real ban, not a transient rate-limit), stop testing
   that host/asset, note it clearly, and redirect effort to other in-scope
   surface rather than looping retries indefinitely.

## Cross-agent coordination

- Before starting any high-volume tool against a host, check `list_notes`
  for an existing throttle/WAF record on it and start from that ceiling, not
  a tool's default.
- Once a host is confirmed rate-limited, avoid running multiple fuzzers or
  multiple testing agents concurrently against it — serialize testing
  against that specific host until you have evidence the limit window has
  reset, even if each individual agent's own rate looks conservative.

## What NOT to do

Slowing down is the fix — evading the control is not. Do not rotate/spoof
source IPs, forge headers, or otherwise disguise traffic specifically to get
around a legitimate rate-limit/WAF block during an authorized engagement;
that is circumventing a control the target operator deliberately put in
place, not vulnerability testing, unless WAF-bypass is an explicit in-scope
objective of this engagement. If throttling still can't get useful signal
from a host, that is itself worth noting (the control is working), not a
problem to route around.
