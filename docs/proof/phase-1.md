# Phase 1 evidence
Reproduce at tag `phase-1`: `./scripts/test.sh` (8 tests). Manual: `python3 -m game.headless --seed 1 --ticks 200 --scenario scenarios/pick_and_light.json --inputs scenarios/pick_and_light.inputs.json --out /tmp/o.jsonl`.

| Requirement | Check | Result |
|---|---|---|
| Pick up motes, carry up to capacity | `test_pickup_deposit_light` | pass |
| Deposit and light a lantern | same test | pass |
| Win when all lit, win score | `test_win_when_all_lit` | pass |
| Pulse stuns, costs light | `test_pulse_stuns_shade_and_costs_light` | pass |
| Shade hit, drop, lose by no flames | `test_shade_hit_loses_game` | pass |
| Lose at dawn | `test_dawn_loss` | pass |
| Scenario setup gives no score | `test_scenario_setup_gives_no_score` | pass |
| Determinism (same seed/scenario/inputs) | `test_deterministic` | pass |
| Malformed inputs/scenario -> exit 2 | `test_bad_inputs_exit_2` | pass |
| Playable with 3D view | `python3 -m game.server`, open localhost:8000 | server endpoints checked with curl; browser rendering to be checked by hand |
| Test Contract details I may have misread | compare with the lab board | unverified against instructor scenarios |
