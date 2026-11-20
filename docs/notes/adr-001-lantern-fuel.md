# ADR-001: lanterns have fuel; the goal is dawn, not "all lit"
Status: accepted (Ticket-03, contract v1.2).

**Before:** lantern = `lit` + `deposited`. Lit was final; winning = all lit.
**Now:** lantern = `lit`, `fuel` (int, 1/60 units), `ever_lit`, `relit`, `deposited` (only while unlit). Lit lanterns lose fuel each tick (stage 2), drain-state Shades subtract more, and `fuel <= 0` turns the lantern off (`lantern_out`, `deposited = 0`, `ever_lit` kept). One `_lantern`/`_safe` pair answers "is it lit" and "does it repel Shades" (lit and fuel >= 30), so weak lanterns need no extra flag.
**Win rule:** all outcome logic moved to stage 11 and only fires on flames <= 0 (no_flames first) or time out (dawn_survived / dawn). No early win exists any more.
**Why integers:** 1/60 per tick summed in floats drifts; integers keep per-seed output exact.
**Why a Shade `drain` state:** the ticket's pressure source needs a stationary, visible, stoppable Shade. Exits are checked before the eject early-return so a refuelled lantern stops draining the same tick.
**Consequence:** old tests tied to `all_lit`, 300/330/360 s and the old score were replaced, with reasons in `assumptions.md`.
