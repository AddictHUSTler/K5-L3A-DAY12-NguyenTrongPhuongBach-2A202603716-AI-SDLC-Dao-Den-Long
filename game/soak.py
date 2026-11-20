"""Soak test: python3 -m game.soak --seed 7 --nights 10 --out soak.json  (headless, Ticket-04 section 2)."""
import argparse, gc, json, math, sys, time
from .sim import Sim, mulberry32


def rss_mb():
    with open("/proc/self/statm") as f:
        return int(f.read().split()[1]) * 4096 / 1048576


DIRS = [[0, 0]] + [[round(math.cos(a * math.pi / 4), 3), round(math.sin(a * math.pi / 4), 3)] for a in range(8)]


def play_night(seed, night):
    """Random input from the seed until the Night ends (win, loss or standard duration)."""
    sim, rnd, mv = Sim(seed, night=night), mulberry32(seed ^ 0xA5A5), DIRS[0]
    while sim.state == "playing":
        if sim.tick % 30 == 0:
            mv = DIRS[int(rnd() * len(DIRS))]
        sim.set_inputs({"move": mv, "jump": rnd() < .05, "dash": rnd() < .03, "pulse": rnd() < .02, "interact": rnd() < .10})
        sim.step()
    return sim.state


def run(seed, nights):
    t0, results, crashes = time.perf_counter(), [], 0
    first = Sim(seed, night=1)      # Night 1 loaded
    mem_start = rss_mb()
    del first
    for i in range(nights):
        try:
            results.append(play_night(seed + i, i % 3 + 1))
        except Exception as e:      # a crash must not stop the soak; it is counted
            crashes += 1
            results.append("crash")
            print(f"night {i + 1} crashed: {e!r}", file=sys.stderr)
        gc.collect()
    Sim(seed + nights - 1, night=(nights - 1) % 3 + 1)   # reset of the last Night
    gc.collect()
    return {"nights": nights, "crashes": crashes, "results": results, "mem_start_mb": round(mem_start, 1),
            "mem_end_mb": round(rss_mb(), 1), "duration_s": round(time.perf_counter() - t0, 1)}


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--seed", type=int, default=7)
    ap.add_argument("--nights", type=int, default=10)
    ap.add_argument("--out", required=True)
    a = ap.parse_args(argv)
    res = run(a.seed, a.nights)
    with open(a.out, "w") as f:
        json.dump(res, f)
    print(json.dumps(res))
    return 0


if __name__ == "__main__":
    sys.exit(main())
