# AI usage log
| Phase | Tool | Est. tokens | Notes |
|---|---|---|---|
| 1 (incl. reading docs + prep) | Claude Code (Sonnet 5.5) | MEASURED from session transcript: output ~45k, cache write ~113k, fresh input ~120, cache reads ~4.5M (context re-read each turn) | Wrote sim, headless CLI, tests, web client in one pass. Kept context small: spec read once, pure-stdlib code. |
| 2 | Claude Code (Sonnet 5.5) | MEASURED from session transcript (this session only): output ~102k, cache write ~174k, fresh input ~140, cache reads ~7.4M (context re-read each turn) | Read ticket once, rewrote sim to v1.1, tests per feature, client rewrite, then a refactor guarded by a before/after golden-output diff (byte-identical). Lab board unreadable by the agent: ticket was pasted in as `phase2.md` (kept uncommitted). |

## AI mistakes caught
- (fill in as they happen) e.g. first draft of `Sim.__init__` had tangled mote-list handling; simplified after review.
- Phase 2: a string replace in `server.py` matched twice and mangled the file; caught by a syntax check and a curl run, fixed.
- Phase 2: first draft of the fall test put the player above ground, so it landed instead of falling; fixed the test setup, not the sim.

| 3 | Claude Code (Sonnet 5.5) | MEASURED from session transcript: output ~38k, cache write ~134k, fresh input ~72, cache reads ~3.1M | Read ticket + prep notes, changed sim in place (fuel/drain/dawn rules, ~170 lines), tests per rule, ADR + changelog. |
- Phase 3: first draft of the refuel test assumed a lantern stays "full" after a tick; stage-2 decay makes it 99.98. Fixed the test with the rule written down in assumptions.
- Phase 3: a stunned Shade next to a weak lantern re-entered drain at once; the test expected wander. Rule is right; test fixed.

| 4 | Claude Code (Sonnet 5.5) | MEASURED from session transcript up to the last doc edit (this session only): output ~41k, cache write ~107k, fresh input ~54, cache reads ~2.6M | Read ticket once, new modules (`bench`, `soak`, `leaderboard`) + client edits via scripted patches, 5 new tests. No browser available, so the bench was written but not run end to end. |
- Phase 4: the browser loop awaited the server before drawing, so FPS would have measured server latency and the tick accumulator rounded to 0 above 100 fps (game froze on fast monitors). Found by reading the loop while designing the bench; fixed (accumulator, no await).
- Phase 4: my first bench-stats test had a wrong hand-computed expectation (90.9 vs 94.3 fps); the code was right, the arithmetic in the test was wrong.
- Phase 4: first server patch put the leaderboard route after the file-extension check, so `/leaderboard` returned 404; caught by a curl run.
- Prompts of note: "KEEP IT SIMPLE, CONCISE, AND NON ENSHITTIFIED" (kept each module small, no new dependency); "no co-authored by" (plain commit messages; see memory feedback).
