# Review: `U3` redo — "Aurora wave" voice orb (D-29)

**Reviewer:** independent reviewer agent (Opus, fresh, read-only) · **Date:** 2026-10-22 · **Branch:** `upgrade/U5-visuals` · **Decision:** D-29 (sponsor chose concept C of three; infinity ribbon retired) · **Executor:** O

## Verdict
**APPROVE WITH NITS (round 2 of 3).** Round 1: changes required — (H) phase scrubbed on state changes and worsened with uptime (phase was t × eased speed); thinking snapped between formulas; dark bands washed to white; per-frame gradient allocation. Round 2: all fixed (integrated phase, eased thinking blend, lower dark alphas + level-independent thinking highlight, cached gradients, dt-based easing, 3-band small orb); the three optional nits were also applied (highlight rides the wave and fades at the ends; small orb keeps blue/red/yellow).

## What the sponsor sees
Borderless, feathered bands of AI-aura light. Idle: calm low ripples. Listening: bands rise and fall with the real mic level. Thinking: a soft highlight travels along the wave. Speaking: bands follow Yukti's voice. Greeting ≈ 208 px at 1440p (scales on 4K), ask bar 48 px, minimised corner 96 px. The selection page with the three concepts is preserved as evidence (`assets/U3-aurora/orbs_all_*.png`).

## Evidence
- [`assets/U3-aurora/`](assets/U3-aurora/): `orb_states_{light,dark}`, `home_{light,dark}`, `home_listening_light`, `home_light_4k`, `askbar_*`, `minimised_*`, `orbs_all_*`.
- Production build: 60 fps at 1440p and 4K; reduced motion = static frame (identical screenshots 800 ms apart); orb double-click → getUserMedia 1×, listening; stop → 0 live tracks; aria-pressed; 0 page errors.
- Long-uptime test (Playwright clock, +12 min): steady per-frame change 0.55–1.09; no spike at the idle → listening transition (spikes only with the fake mic's periodic beep, i.e. level-driven).
- tsc, lint:tokens clean.

## Open (sponsor-side)
4K smoothness on the demo laptop; blind identification of the 4 states. Known deviation: `white()` neutral is not a token.
