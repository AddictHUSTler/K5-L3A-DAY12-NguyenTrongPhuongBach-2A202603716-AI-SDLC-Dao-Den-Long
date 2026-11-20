# Phase 2 spec: acceptance criteria (Ticket-02, contract v1.1)
Format: do A, see B. Test names are in `tests/test_sim.py`; "manual" = checked by hand in the browser.

| Item (Part 3) | Acceptance criterion | Check |
|---|---|---|
| Drifter (Gió Lạc) | Night 2/3 only, max 2, spawn at tick 1200, 2400, ... Carrying >= 5 and within 15 m: idle -> chase. Contact (<= 1.2 m) steals min(3, carried) and it flees 240 ticks. Once per drifter. | `test_drifter_needs_5_carried_and_15m`, `test_drifter_steals_then_pulse_returns` |
| Drifter vs Pulse | Pulse on a chasing drifter: it flees, steals nothing. Pulse on a fleeing drifter with loot: loot drops as motes, `drifter_drop` event. | `test_pulse_turns_chasing_drifter_to_flee_without_theft`, `test_drifter_steals_then_pulse_returns` |
| Wind Charm | Pick up: 600 ticks, speed 7.2, Dash cooldown 0 (still needs a new press). Respawns 2700 ticks later. | `test_charm_effects` |
| Three-night chain | Menu -> intro -> play -> result -> next night. Win night 3 -> Dawn screen with total of won nights. Lose -> retry that night. | manual (`web/index.html`) |
| Pause | Press pause: `paused` event, `sim_tick`/timers/spawns frozen, snapshot `state: "paused"`, `tick` still counts. Press again: `resumed`. | `test_pause_freezes_sim` |
| Settings | Volume and mouse sensitivity sliders persist after reload (localStorage). | manual |
| Audio | Music + SFX for pickup, light, pulse, hit, jump, dash, win, lose, shade spawn, last-10 s countdown. | manual |
| HUD | Flames top-left, mm:ss top-centre (red + blink at <= 30 s), lanterns + score top-right, 10-cell mote bar bottom-centre, Dash/Pulse cooldowns bottom-right, "E - Nạp ánh sáng (x/10)" prompt near a lantern, arrow to nearest unlit lantern when off-screen. | manual |
| Palette | Colours in `web/index.html` constant `C` use the ticket's hex values. Ambient light = 0.15 + 0.55 x lit/total. | manual / code |
| Standard numbers | `tuning` matches Part 1 table. | `test_standard_numbers` |
| Maps | Night lantern counts 5/6/7, durations 300/330/360 s. Pads, walls, ramps, tower on night 3. | `test_night_maps`, `test_pad_launch_night2`, `test_night3_*` |
| Falling | Y < -10 once: -1 flame, lose motes, 60 ticks frozen, respawn at start with 90 ticks invulnerable. | `test_fall_*` |
| Night 3 wind | Warning 2 s before a 5 s gust every 30 s, 2 m/s push. | `test_wind_schedule` |
| Speed | One full night headless <= 30 s. | `test_night_runs_fast` (0.4 s measured) |
