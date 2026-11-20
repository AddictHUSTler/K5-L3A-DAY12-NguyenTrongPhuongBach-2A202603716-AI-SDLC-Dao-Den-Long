# Retro (4 phases)

**What worked.** Pure, deterministic sim + a numbers-only contract file. Every phase changed rules in one place (`sim.py` stages, `game.contract.json`) and the same tests, `cmp` of headless runs and golden outputs caught regressions at once. Writing the verification plan before code (`docs/spec-phase*.md`) kept the agent honest. Reading each ticket once and keeping notes in `docs/notes/` saved tokens compared with re-explaining context.

**What did not.** Anything that needs a real browser: no browser was available to the agent, so rendering, FPS and the bench had to be written "blind" and are verified only by their pure parts. Hand-written expected numbers in tests were wrong twice (Phase 3 refuel, Phase 4 fps), always the test, not the code.

**Where the AI was wrong, how I found out.** Phase 2: a double-match string replace mangled `server.py` (syntax check + curl). Phase 3: tests assumed lanterns stay "full" and stunned Shades re-drain (tests failed, rule was right, tests fixed with the rule written down). Phase 4: render loop awaited the server and froze above 100 fps (found by reading the loop while designing the bench); a route ordered after a 404 check (curl). Details: `docs/notes/ai-log.md`.

**Harness that helped most.** `AGENTS.md` (numbers only in the contract, stage-numbered `step()`, never disable tests silently), then the `verify` skill (same checklist each phase), then `./scripts/test.sh`. Keeping `phaseN.md` tickets out of git avoided noise.

**Tokens.** Roughly 0.35M output tokens over four sessions; cache reads dominate (~22M) because context is re-read every turn (exact numbers per phase in `ai-log.md`). Saved by: stdlib-only code, one ticket read per phase, scripted patches instead of re-printing files, tests instead of manual replays.

**If I did it again.** Install a headless Chrome on day one so FPS, screenshots and the demo can be produced by the agent, vendor three.js from the start, and put the leaderboard and key bindings in at Phase 2 instead of retrofitting.
