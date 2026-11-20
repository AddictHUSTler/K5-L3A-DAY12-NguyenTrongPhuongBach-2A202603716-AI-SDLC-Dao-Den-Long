# AGENTS.md
Đảo Đèn Lồng: Python 3.12 stdlib only, no deps.
- Logic: `game/sim.py` (pure, deterministic, no I/O). Headless: `game/headless.py`. Play: `python3 -m game.server`. Browser only draws.
- All numbers live in `game.contract.json` `tuning`. Never hardcode them in code.
- Test everything: `./scripts/test.sh`. Run it before finishing; do not finish red.
- Never disable/delete a test silently. If a new rule invalidates one, change it and write why in `docs/notes/assumptions.md`.
- Output must stay deterministic per seed (no wall-clock, no `random`, no set/dict-order dependence).
- Contract spec lives on the lab board; keep `docs/notes/assumptions.md` in sync.
