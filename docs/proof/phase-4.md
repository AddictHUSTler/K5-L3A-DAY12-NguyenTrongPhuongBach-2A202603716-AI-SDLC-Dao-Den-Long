# Phase 4 evidence (Ticket-04, contract v1.3)
Machine: Linux 7.0 x86_64, Intel i7-12650H (16 threads), 62 GB RAM, Python 3.12.3. Agent had **no browser**, so everything that needs rendering is marked.

| Requirement | Check | Result |
|---|---|---|
| Tests (Phases 1-4) | `./scripts/test.sh`: 50 tests | pass |
| Headless unchanged | `headless --seed 1 --night 2 --ticks 21600` byte-identical to the Phase 3 code (`git stash` run + `cmp`) | pass |
| Determinism, nights 1-3 | each run twice, `cmp` | pass |
| Speed, full night | 1.0 s (night 3) | pass |
| Soak | `python3 -m game.soak --seed 7 --nights 10`: crashes 0, RSS 12.7 -> 12.7 MB, 2.0 s. File: `docs/proof/soak.json`. Results all "lost" (random input, see assumptions) | pass (<= 1.2x, 0 crashes) |
| Bench scene (200 wander Shades, 100 motes, L1-L3 lit 100, nothing changes for 600 ticks) | `test_bench_scene` | pass |
| Bench stats formulas (avg, p1 low, p95) | `test_bench_stats_formulas` | pass |
| Bench in a real browser (`docs/proof/bench.json`, Brave Origin 158, Intel ADL GT2, Mesa, vsync flags off) | avg_fps 223.5 (>= 60 pass), load_ms 2838 (<= 10000 pass), **p1_low_fps 5.9 (>= 30 FAIL)**, p95 8.9 ms, peak 1133 MB | partial. Frame times show a ~70 ms hitch every ~32 frames (about 270 of 8800 frames) between bursts of ~3 ms frames, with or without the RSS poller; this looks like GPU/driver back-pressure from uncapped frames, not game logic (Python cost is 1.5 ms/tick). Not fixed; a vsync-on run was not completed |
| Leaderboard: name rule, top 10, order, tie, file, export | `test_leaderboard_rules`, `test_leaderboard_missing_file_is_empty`; `--export-leaderboard` run by hand; HTTP `/score` rejects bad names | pass (UI screen not seen in a browser) |
| Accessibility: rebinding + conflict + reset + saved; cues; reduce motion; fonts >= 18 px, x1.25 | written in `web/` | **not verified in a browser** |
| Install in <= 3 commands | README: clone, `python3 -m game.server`, open URL; no dependencies, three.js vendored | by reading; clean-clone run: see below |
| README/CHANGELOG (4 phases)/CREDITS/LICENSE | present | pass |
| Release v1.0.0, demo video, screenshot | not done by the agent | open |
