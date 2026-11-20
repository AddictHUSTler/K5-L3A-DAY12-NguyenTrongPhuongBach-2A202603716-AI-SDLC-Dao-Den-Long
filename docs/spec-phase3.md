# Phase 3 spec: acceptance criteria (Ticket-03, contract v1.2)
| Item | Criterion | Check |
|---|---|---|
| Numbers | v1.2 tuning keys and 240/270/300 s | `test_v12_numbers`, `test_standard_numbers` |
| Fuel | lit = 100, -1/s, out at <= 0 with `lantern_out`, `deposited` 0, `ever_lit` kept | `test_fuel_decay_and_lit_default`, `test_out_at_zero_then_relight_costs_5` |
| Refuel | used = min(carried, ceil((100-fuel)/10)); full lantern not chosen; +5/mote | `test_refuel_amounts_and_full_lantern_ignored`, `test_interact_picks_nearest_receivable_lantern` |
| Relight | 5 motes if `ever_lit`, +40, `relight: true` | `test_out_at_zero_then_relight_costs_5` |
| Weak lantern | fuel < 30 loses safe zone; exactly 30 keeps it | `test_weak_lantern_has_no_safe_zone` |
| Drain | wander Shade goes to weak lantern, drains 5/s stacking, `fuel_drain` per 60 ticks, exits, +15 stun | `test_wander_shade_*`, `test_drain_*`, `test_refuel_to_30_*` |
| Win/lose | dawn: >= ceil(0.6n) lit; no_flames first; scores | `test_win_at_dawn_*`, `test_no_flames_beats_dawn` |
| Capacity | 10 + 2 per light, max 20 | `test_capacity_grows_and_caps` |
| Determinism | same seed, same output | `test_phase3_deterministic_full_night`, `test_deterministic` |
| Colour-blind, fuel bar, flicker, HUD capacity | manual in browser | not verified (no browser here) |
