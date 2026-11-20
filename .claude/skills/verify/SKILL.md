---
name: verify
description: Run the test suite and the headless checks for a phase and record evidence in docs/proof/.
---
1. `./scripts/test.sh` must be green.
2. Determinism: run `python3 -m game.headless --seed 1 --night N --ticks 21600 --out a.jsonl` twice per night, `cmp` the files.
3. Speed: `time` one full-night run, must stay under 30 s.
4. For each new rule add one scenario in `scenarios/` and one test in `tests/test_sim.py`.
5. Write results (pass / not achieved + reason) in `docs/proof/phase-N.md`.
