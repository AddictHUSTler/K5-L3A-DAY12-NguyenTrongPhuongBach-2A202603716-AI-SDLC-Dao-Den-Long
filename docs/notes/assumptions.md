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
