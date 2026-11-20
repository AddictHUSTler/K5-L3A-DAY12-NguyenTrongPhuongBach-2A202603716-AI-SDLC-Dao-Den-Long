# Changelog
## Phase 4 / v1.0.0 (contract v1.3) - no rule or number changes, headless output unchanged
- `contract_version` 1.3; `bench_cmd` and `soak_cmd` added.
- `python3 -m game.bench` (real browser, fixed 200-Shade scene) and `python3 -m game.soak` (10 headless Nights).
- Local leaderboard (top 10, `leaderboard.json`), menu screen, name entry after a win or loss, `python3 -m game.server --export-leaderboard out.json`.
- Accessibility: rebindable keys (conflict warning, reset, saved), shade-appears arrow + captions (last 10 s), reduce-motion option, UI text >= 18 px with a x1.25 option.
- three.js is now served from `web/three.module.js` (works offline). Frame timing no longer depends on the server round-trip, and 60 ticks/s holds above 100 fps.
- Browser keys: one key per action; the old second keys (P for pause, Right Shift for dash) are gone, rebind instead.

## Phase 3 (contract v1.2) - breaking changes
- Win: only at dawn with >= ceil(0.6 x lanterns) lit; `game_over.reason` `all_lit` removed, `dawn_survived` added. Lighting everything no longer ends the night.
- Nights are 240 / 270 / 300 s (were 300 / 330 / 360).
- Lit lanterns decay, can go out (`lantern_out`) and be refuelled (`refuel`); relight costs 5.
- Lanterns below 30 fuel lose their safe zone; new Shade state `drain` (+ `fuel_drain` event); stunned Shades return to wander, not chase.
- Carry capacity 10 -> up to 20 (`player.capacity`).
- Score formula replaced; no time bonus.
- Snapshot adds `fuel`, `ever_lit`, `relit_count` (lanterns), `capacity` (player), `target_lantern_id` (shades). `lantern_lit` adds `relight`. Scenarios add `fuel`, `ever_lit`, `successful_lights`, `target_lantern_id`.
- Browser: fuel bars, low-fuel flicker, colour-blind palette, easier/faster browser tuning, lantern-out sound.

## Phase 2 (contract v1.1)
Nights 2 and 3 (maps, jump pads, wind, tiers), Gió Lạc drifters, Wind Charm, pause, dash, Mây's pulse costs 3 light. See `docs/spec-phase2.md`.

## Phase 1 (contract v1.0)
Night 1: motes, lanterns, Shades, pulse, headless runner and scenarios.
