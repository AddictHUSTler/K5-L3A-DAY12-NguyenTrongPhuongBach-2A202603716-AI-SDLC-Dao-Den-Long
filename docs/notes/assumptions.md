# Assumptions

## Phase 1
- Tech: Python 3.12 stdlib; the sim runs in Python, the browser (three.js) only draws via `game/server.py`.
- Numbers: all in `game.contract.json`. Pulse costs carried light (`pulse_cost`), needs cooldown 0.
- Shades: always chase; stunned shades freeze. Only **lit** lanterns repel them (`safe_radius`); they are pushed to the edge.
- Hit: needs XZ distance <= `shade_hit_radius`, not invulnerable, shade not stunned. Drops `floor(carried * 0.5)`.
- Jump is cosmetic (hits/pickups use XZ only, per contract).
- Deposit: `interact` on nearest unlit lantern within radius moves `min(carried, cost - deposited)`.
- Win bonus (added once on win): `per_second_left * floor(time_left)` + `per_flame_left * flames`.
- Scenario `motes`/`shades` replace the lists; `lanterns` updates by id; setup gives no score or events.
- Shades spawn at 22 s then every 20 s (max 4) on a ring of radius 70. Motes: 28 at start, +1 every 2.4 s up to 40.
- Out-of-range `move`, non-increasing frame ticks, or unreadable files -> exit 2.
- `dash` is accepted and ignored (no dash mechanic).
- Island is a circle of radius 100; edge clamps, no falling (`fall_enabled: false`).

## Phase 2 (contract v1.1)
Ticket numbers replace every Phase 1 number (all in `game.contract.json`; maps too, under `maps`). Phase 1 rules that changed: score is +10 per mote *deposited* (was per pick), carry 10, lantern cost 10, safe zone 6 m, hits knock the shade back (recoil), shades wander/chase by distance (12 / 18 m), start/lantern/spawn positions come from the night maps. Old Phase 1 tests/scenarios were updated to the new numbers (e.g. 10 motes instead of 6); none were disabled.
- Angles: x = r cos a, z = r sin a (matches the ticket's Night 1 lanterns).
- Start: night 1 and 2 at (0,0,0). Night 3 start was not given; (0,0,-15) on tier 0 (the centre is the tower). Respawn goes to the same start.
- Pause is a toggle on the false->true edge; other buttons pressed while paused are not consumed. `tick` counts while paused, `sim_tick` does not. `night_start` is emitted on the first running tick.
- Accel/stop: velocity moves toward the target by speed/6 per tick (0.1 s). Dash end snaps to the held-key velocity.
- Walls (night 3): you may not walk to ground higher than your feet + 0.5 m; stepping to lower ground = fall. Tower (r 2, up to y 14) blocks. Shades ignore tier walls but stay on ground and out of the tower.
- Shade wander: 2 m/s, new random heading every 120 ticks. After stun/recoil the shade resumes chase. `spawning` lasts one tick, then wander/chase by distance. Valid spawn point = >= 15 m (XZ) from the player and no shade within 1 m. At the max count the spawn is skipped.
- Safe zone: shades inside a lantern's radius at the moment it lights are moved out over 30 ticks (harmless meanwhile); afterwards shades are clamped to the 6 m edge.
- Pulse: centre = feet + 0.8 m; shade/drifter position is its `pos` (shade y = ground height). Push direction is horizontal from the centre.
- Motes: `mote_max` 30 counts all motes (including dropped). "Free point" = spawn point with no random mote on it; night 1 has only 24 points so it tops out at 24. Dropped motes: ring 1.5-2.5 m, TTL 480. Random motes' `ttl_s` is `null`.
- Drifter spawn point: a random shade-ring point (the ticket says "random mist point"), 1 m above ground. Idle drift 2 m/s; turns back to the island centre over the sea. Flee drift is horizontal. A drifter that drops its loot vanishes after <= 120 ticks.
- Snapshot `player.invuln` is a boolean; extra fields (`facing`, shade `state_ticks_left`, `wind.warning`) are additions only.
- Wind direction is picked when the warning starts. `wind_enabled` defaults to true on night 3 only; `random_drifters` to true on nights 2-3.
- Totals across nights are kept by the browser client (a headless run is one night).
- Not verified: browser rendering/FPS (no browser available in this session) and the hidden instructor scenarios.

## Phase 3 (contract v1.2): replaced rules, old -> new, why
| Old (Phase 1-2) | New (Ticket-03) | Test changed |
|---|---|---|
| Lit lantern takes no more motes; stays lit | Lit lantern has fuel (0-100), decays 1/s, can be refuelled, goes out at 0 | new `test_fuel_*`, `test_refuel_*` |
| Light cost 10 always | 10 first time, 5 relight (`ever_lit`) | `test_out_at_zero_then_relight_costs_5` |
| Win when all lit (`all_lit`) | Win at dawn with >= ceil(0.6 x lanterns) lit (`dawn_survived`) | `test_win_when_all_lit` replaced by `test_lighting_all_does_not_end_night` + `test_win_at_dawn_*` (old rule is gone, not skipped) |
| Nights 300/330/360 s | 240/270/300 s | `test_standard_numbers`, `test_night_maps` updated |
| Carry 10 | 10 + 2 per successful light, max 20 | `test_capacity_grows_and_caps` |
| Score: 10/mote, 100/lantern, time + flame bonus | 5/mote, 100 first light, 40 relight, 5 stun (15 if draining), dawn 50 + fuel per lit lantern, 50 per flame | none asserted score before; new tests assert the new numbers |
| Lit lanterns always repel Shades | Only lit with fuel >= 30 repel | `test_weak_lantern_has_no_safe_zone` |
| Stun end -> chase | Stun end -> wander (then chase if Mây within 12 m) | none |
Kept as is: all other Phase 1-2 tests pass unchanged except `lantern_lit` now carries `relight`.

Assumptions made in Phase 3:
- Fuel is stored as integer 1/60 units (`FUEL_UNIT`); decay = `round(fuel_decay_per_s)` units per tick, drain = `round(drain_per_s)`. Fractional per-second values are not supported (rounded). Output fuel is rounded to 1 decimal.
- Fuel decay/drain runs in stage 2 and a lantern lit in stage 5 of a tick first loses fuel on the next tick. So a lantern you just topped up to 100 reads 99.98 next tick and can take 1 more mote; "full" means fuel = 100 exactly at interaction time.
- Unlit lantern scenarios: `fuel` is ignored (0). `lit: true` without `fuel` -> 100. `lit` also sets `ever_lit`.
- Wander goal: nearest weak lit lantern (fuel < 30) else the nearest unlit lantern (ticket: "như trước"; Phase 2 only had random wander, so this is new), walking at `shade_wander_speed`. With no unlit and no weak lanterns: random wander as before. Drain starts only for weak lanterns, within 2 m. A shade next to an unlit lantern just waits there.
- Drain shades never hit Mây (Phase 2 hit rule only lists chase/wander). Drain -> chase has priority over nothing but the wander exits (lantern out / fuel >= 30 / > 2 m) which are checked first.
- `fuel_drain` is emitted every 60 ticks of continuous draining per shade (counter resets on leaving drain).
- Extra tuning keys (not in the ticket): `capacity_per_light` 2, `drain_reach_m` 2, `drain_detect_m` 6, score keys `relight`, `stun_drain`, `dawn_lantern`, `dawn_flame`. Removed: `per_second_left`, `per_flame_left`.
- Total lanterns for the 60% rule = lanterns in the sim (scenario-added ones count).
- Browser "Chế độ dễ" (saved setting) is an assist applied only in `game/server.py` (150/170/190 s, 5 flames, drain 2/s). Headless and contract numbers are untouched.
