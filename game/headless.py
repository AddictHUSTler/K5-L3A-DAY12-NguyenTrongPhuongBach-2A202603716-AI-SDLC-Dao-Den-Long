"""Headless runner per Test Contract v1.3. Usage: python3 -m game.headless --seed 1 --night 1 --ticks 600 --out out.jsonl"""
import argparse, json, sys
from .sim import Sim, ScenarioError


def load_json(path):
    try:
        with open(path) as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError) as e:
        raise ScenarioError(f"{path}: {e}")


def load_frames(path):
    frames = load_json(path).get("frames") if path else []
    if not isinstance(frames, list):
        raise ScenarioError("frames must be a list")
    last = -1
    for fr in frames:
        if not isinstance(fr, dict) or not isinstance(fr.get("tick"), int) or fr["tick"] <= last:
            raise ScenarioError("frame ticks must be integers, strictly increasing")
        last = fr["tick"]
    return frames


def run(seed, ticks, scenario, frames, every, out, night=1):
    sim = Sim(seed, scenario, night=night)
    w = lambda o: out.write(json.dumps(o, separators=(",", ":")) + "\n")
    w(sim.snapshot())
    fi = 0
    for k in range(ticks):
        while fi < len(frames) and frames[fi]["tick"] <= k:
            sim.set_inputs(frames[fi])
            fi += 1
        for name, data in sim.step():
            w({"type": "event", "tick": sim.tick, "name": name, "data": data})
        if sim.state != "playing":
            break
        if sim.tick % every == 0:
            w(sim.snapshot())
    if sim.tick % every != 0 or sim.state != "playing":
        w(sim.snapshot())
    w({"type": "end", "ticks": sim.tick, "state": sim.state, "score": sim.score})


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--seed", type=int, required=True)
    ap.add_argument("--night", type=int, default=1)
    ap.add_argument("--scenario")
    ap.add_argument("--inputs")
    ap.add_argument("--ticks", type=int, required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--snapshot-every", type=int, default=10)
    a = ap.parse_args(argv)   # bad args -> exit 2
    try:
        scenario = load_json(a.scenario) if a.scenario else None
        frames = load_frames(a.inputs) if a.inputs else []
        with open(a.out, "w") as out:
            run(a.seed, a.ticks, scenario, frames, max(1, a.snapshot_every), out, a.night)
    except ScenarioError as e:
        print(f"error: {e}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
