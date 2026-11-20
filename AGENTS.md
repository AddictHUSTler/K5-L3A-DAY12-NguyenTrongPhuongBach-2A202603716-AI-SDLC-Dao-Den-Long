# AGENTS.md
Đảo Đèn Lồng: Python 3.12 stdlib only, no deps.
- Logic: `game/sim.py` (pure, deterministic, no I/O). Headless: `game/headless.py`. Play: `python3 -m game.server`. Browser only draws.
- All numbers live in `game.contract.json` `tuning`. Never hardcode them in code.
- Test everything: `./scripts/test.sh`. Run it before finishing; do not finish red.
- Never disable/delete a test silently. If a new rule invalidates one, change it and write why in `docs/notes/assumptions.md`.
- Output must stay deterministic per seed (no wall-clock, no `random`, no set/dict-order dependence).
- Contract spec lives on the lab board; keep `docs/notes/assumptions.md` in sync.
- Map data (islands, lanterns, spawn rings, pads) is in `game.contract.json` `maps`; geometry helpers are in `game/world.py`, rules in `game/sim.py`.
- `sim.step()` stages are numbered in the ticket's mandatory order (comments `# 1.` to `# 11.`); put a new rule in the method for its stage, one rule per method.
- Anything that is only for looks/sound stays in `web/index.html` and must not change headless output.
- Verify with the `verify` skill (`.claude/skills/verify/SKILL.md`). Never `git add -A`: `phase2.md` is a local copy of the ticket and stays uncommitted.
