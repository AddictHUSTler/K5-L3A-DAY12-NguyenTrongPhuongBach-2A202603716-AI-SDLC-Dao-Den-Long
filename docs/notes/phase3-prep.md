# Phase 3 prep (before reading Ticket-03)
Phase 3 may replace rules. How the code is ready:
- Numbers and maps are data (`game.contract.json`), so a changed number or map is a JSON edit plus its test.
- Each rule lives in one method of `game/sim.py`, in ticket order (`_move_player`, `_pickups`, `_interact`, `_eject`, `_pulse`, `_move_shades`, `_move_drifters`, `_contact`, `_spawns`, `_end`).
- Rules most likely to be replaced, and the tests that would then change: scoring (`test_win_when_all_lit`, `test_pulse_*`), pulse/dash numbers (`test_dash`, `test_charm_effects`), hit/fall consequences (`test_hit_recoil_*`, `test_fall_*`), spawn schedules (`test_shade_spawn_schedule`), drifter/charm rules.
- On a replaced rule: edit the test, write the old vs new rule and why in `docs/notes/assumptions.md` (never disable silently), update `docs/spec-phase2.md` -> new spec file, re-run `./scripts/test.sh`.
- Open risks to re-check first: the assumptions list in `assumptions.md` (night 3 start, drifter spawn point, pause edge handling), and the unverified browser client.
