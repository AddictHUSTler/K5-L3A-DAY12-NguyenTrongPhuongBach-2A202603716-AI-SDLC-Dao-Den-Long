# Changelog
## Phase 3 (contract v1.2) - breaking changes
- Win: only at dawn with >= ceil(0.6 x lanterns) lit; `game_over.reason` `all_lit` removed, `dawn_survived` added. Lighting everything no longer ends the night.
- Nights are 240 / 270 / 300 s (were 300 / 330 / 360).
- Lit lanterns decay, can go out (`lantern_out`) and be refuelled (`refuel`); relight costs 5.
- Lanterns below 30 fuel lose their safe zone; new Shade state `drain` (+ `fuel_drain` event); stunned Shades return to wander, not chase.
- Carry capacity 10 -> up to 20 (`player.capacity`).
- Score formula replaced; no time bonus.
- Snapshot adds `fuel`, `ever_lit`, `relit_count` (lanterns), `capacity` (player), `target_lantern_id` (shades). `lantern_lit` adds `relight`. Scenarios add `fuel`, `ever_lit`, `successful_lights`, `target_lantern_id`.
- Browser: fuel bars, low-fuel flicker, colour-blind palette, easy mode, lantern-out sound.
