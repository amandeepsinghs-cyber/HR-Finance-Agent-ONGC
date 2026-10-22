# Yukti AI UI — Audit (2026-10-20, before fixes)

**Verdict: the UI could not work for the user's setup, and voice was broken by design.** The browser called the backend on a second port (`http://<host>:8095`, `ws://<host>:8095`), so with only the UI port forwarded from the laptop, every live call failed and the app silently fell back to mock fixtures. On top of that, Space was bound to "advance mock briefing", voice transcripts never reached the thread, and placeholder/developer labels leaked onto the canvas.

Evidence: Playwright + Chrome screenshots at 1440×900, 1920×1080, 2560×1440 (`scratch/audit_before/*.png`), console capture, and a fake-mic voice attempt.

## 1. Blocking

| # | Problem | Where | Effect for the user |
|---|---|---|---|
| B1 | Client hard-codes `http://${hostname}:8095` and `ws://${hostname}:8095/ws/live`; export also calls `:8095` directly | `services/websocketClient.ts`, `CanvasView.tsx` | Laptop → Cloudtop via port forward of 3200 only: `/health` fails → red "Backend offline" banner → mock answers. "It's not working." |
| B2 | **Space** = "advance to next mock scenario" (keydown handler). No push-to-talk at all. Placeholder copy says "Tap orb or press Space to ask". | `app/page.tsx` | Pressing Space to talk loads a canned fixture instead of listening. |
| B3 | Spoken questions never appear: backend only emits `user_transcript` for typed text; ADK `input_transcription` / `output_transcription` are not forwarded; frontend has no handling for `status_event`, `interrupted`, `error.message`. | `backend/app/live_session.py`, `websocketClient.ts` | "Voice is not even listening or responding": no transcript, no feedback, no error. (Backend change requested.) |
| B4 | AudioWorklet posts every 128-frame render quantum (≈42 samples) → ~375 WebSocket JSON messages/s; nearest-sample decimation (aliasing, drifts at 44.1 kHz); worklet not connected to a sink. | `public/audio-processor.js`, `audioAnalyser.ts` | Choppy/garbled input to Gemini Live; high CPU; flaky on some devices. |
| B5 | Playback `AudioContext` created lazily on first audio chunk (no user gesture) → Chrome autoplay policy keeps it `suspended`. | `audioAnalyser.ts` | Agent audio may never be heard. |
| B6 | WS connected at page load, never reconnected; persona switch only sent as `config` (not honoured by the running live agent); errors swallowed. | `page.tsx`, `websocketClient.ts` | Dead socket after idle/restart with no UI indication. |

## 2. Important (looks broken)

- Offline banner and mic-denied banner push content down, but the floating panel is `fixed top-16` — it **covers the banner's Retry / Switch to Mock buttons** and the canvas bottom is clipped (`h-[calc(100vh-4rem)]` ignores banner height; `body{overflow:hidden}`).
- Greeting contract from `/ws/live` overwrites the canvas with **insights "Yukti AI connected / Role: CMD"** and **"Sources (1) ONGC Enterprise Data Bank"**.
- Developer labels in live mode: **"PRIMARY CANVAS VISUAL" + "REPLACE"** badge, **"1/12" mock pager**, "Press Spacebar to advance executive briefing", "Hands-free voice active" (when it is not).
- Insight card shows telemetry ("Voice turn completed on gemini-…", "Grounding: …"); chat bubbles show `[1]` markers stripped only partially.
- Mic button shows a **crossed-out mic** when idle (reads as "muted/broken"); no level meter, no permission guidance beyond "denied".
- History index bug: `setCurrentHistoryIndex(history.length)` uses a stale closure → wrong active thumbnail.
- `GET /favicon.ico` → **404** on every load (the "404 resource").
- Big screens: 2560×1440 is a sea of white — fixed px text (`text-[10px]`, `text-[11px]`), fixed 160 px orb, ECharts fonts 12–13 px → unreadable at 5 m.
- Laptop 1440×900: panel 420 px + canvas padding → donut labels truncated ("E2:…", "E…"), KPI row + chart overflow below the fold.

## 3. Visuals ("too basic")

- Plain ECharts defaults: one flat blue, 4 px radii, no gradients, no annotations, raw numbers (`5631` not `5,631`), axis labels rotated 10–15°, unit strings like `executives` repeated on every tick.
- Chart kind trusted blindly from backend (`donut` with 12 slices; `bar` with long labels; `hbar` for time series).
- No reference/average lines, no callouts for the key insight, no centre total on donut, waterfall without connectors or total emphasis, bullet chart without target ticks or qualitative bands.
- Map: generic grey India with uniform `effectScatter` ripples on every point; sizes not proportional (`10 + count/200` clamped 12–26).
- Table: raw column names (`grade_id`, `wc_id`), raw codes (`DISC-FIN`, `WC-DEL`), left-aligned numbers, no sticky header.

## 4. Console / network (1440×900, backend down)

```
[http 404] /favicon.ico
[reqfailed] http://localhost:8095/health net::ERR_CONNECTION_REFUSED   (x2 per load)
```

## 5. Fix plan (executed — see README "Run" and the after-screenshots)

1. Single origin: `server.js` (Next custom server) proxies `/api/*`, `/health`, `/ws/live` (WebSocket upgrade) to `YUKTI_BACKEND_URL` (default `http://127.0.0.1:8095`); client uses relative URLs. `npm run dev` / `npm run start` both use it. **Forward only port 3200.**
2. Voice: new worklet (100 ms frames, proper resampling, RMS level), gesture-unlocked 24 kHz playback with byte counters, Space = push-to-talk (hold) / toggle (tap), click orb/mic = hands-free toggle, live level meter, permission/error states, barge-in (local + server `interrupted`), incremental transcripts, auto-reconnect.
3. Layout: CSS-grid shell (top bar / banners / canvas + panel), fluid root font-size for big screens, panel width `clamp()`, no fixed px text; placeholder junk removed; mock controls only in mock mode.
4. Chart system: themed palette from the deck, auto chart-form selection from data shape + units, rounded/gradient bars, Indian-format labels, average/target reference lines, maroon callouts for losses, donut with centre total, waterfall with connectors, bullet with bands/targets, small multiples, India bubble map, human-labelled table.
