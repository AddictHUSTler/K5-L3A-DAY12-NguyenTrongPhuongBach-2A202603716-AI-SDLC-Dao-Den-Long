# Phase 2 evidence
Reproduce at tag `phase-2`: `./scripts/test.sh` (30 tests, all pass). Machine: x86_64 Linux, 16 cores, Python 3.12.3.

| Requirement | How checked | Result |
|---|---|---|
| Standard numbers (Part 1) | `test_standard_numbers` + all gameplay tests use them | pass |
| Movement, jump, dash | `test_run_speed_and_stop`, `test_jump_only_on_ground`, `test_dash`, `test_dash_keeps_height_in_air`; scenario `dash.json` | pass |
| Pickup / deposit / light / win score | `test_pickup_deposit_light`, `test_win_when_all_lit` | pass |
| Pulse, shade hit, recoil, drop | `test_pulse_stuns_shade_and_costs_light`, `test_hit_recoil_drops_motes_and_grants_invuln`, `test_shade_hit_loses_game` | pass |
| Safe zone | `test_safe_zone_blocks_and_ejects` | pass |
| Fall and respawn | `test_fall_once_then_respawn`, `test_fall_wait_60_ticks_then_start` | pass |
| Maps, pads, walls, ramp (nights 2, 3) | `test_night_maps`, `test_pad_launch_night2`, `test_night3_wall_blocks_tier1_and_ramp_climbs`, `test_night3_pad_reaches_tier2` | pass |
| Wind | `test_wind_schedule` | pass |
| Drifters | `test_drifter_*`, `test_pulse_turns_chasing_*`; scenario `drifter.json` | pass |
| Wind Charm | `test_charm_effects`; scenario `charm.json` | pass |
| Pause | `test_pause_freezes_sim`; scenario `pause.json` | pass |
| Spawn schedules | `test_shade_spawn_schedule`, `test_mote_spawn_cap_and_schedule` | pass |
| Determinism, bad input -> exit 2 | `test_deterministic` (all 3 nights), `test_bad_inputs_exit_2` | pass |
| Full night headless <= 30 s | measured 0.29 s / 0.41 s / 0.37 s for nights 1/2/3 (21,600 ticks) | pass |
| Phase 1 regression | Phase 1 tests kept and updated to v1.1 numbers (see `assumptions.md`); none removed | pass |
| Browser play: night 1, night 2 (full), night 3 (partly) | played by hand by the author, no problems reported | pass (manual) |
| Menu chain, settings, audio, palette, rest of night 3 | `web/main.js` written to the ticket | **not verified** individually |
| >= 30 FPS at 1280x720 | not measured | **not achieved / unmeasured** |
| Instructor hidden scenarios | cannot run them | unverified |
