# AI usage log
| Phase | Tool | Est. tokens | Notes |
|---|---|---|---|
| 1 (incl. reading docs + prep) | Claude Code (Sonnet 5.5) | MEASURED from session transcript: output ~45k, cache write ~113k, fresh input ~120, cache reads ~4.5M (context re-read each turn) | Wrote sim, headless CLI, tests, web client in one pass. Kept context small: spec read once, pure-stdlib code. |

## AI mistakes caught
- (fill in as they happen) e.g. first draft of `Sim.__init__` had tangled mote-list handling; simplified after review.
