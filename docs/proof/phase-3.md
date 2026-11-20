# Phase 3 evidence
`./scripts/test.sh`: 45 tests, all pass. Machine: x86_64 Linux, Python 3.12.3.

| Requirement | Result |
|---|---|
| Fuel, refuel, relight, lantern_out | pass (tests in `docs/spec-phase3.md`) |
| Weak lantern + drain state + events | pass |
| Dawn win rule (3/5, 4/6, 5/7), no_flames first, new scores | pass |
| Capacity 10 -> 20 | pass |
| Phase 1-2 regression | pass; replaced tests listed in `assumptions.md` |
| Determinism (3 nights, seed 1, run twice, `cmp`) | pass |
| Speed (21,600 ticks) | 1.1 s / 1.7 s / 1.0 s on nights 1/2/3 (idle player; Python, 1 run each) |
| Browser: fuel bar, flicker, colour-blind palette, easy mode, capacity HUD | written, **not verified in a browser** |
| Instructor hidden scenarios | cannot run |
Ambiguity chosen by me: wander goal when no weak lantern exists (see `assumptions.md`).
