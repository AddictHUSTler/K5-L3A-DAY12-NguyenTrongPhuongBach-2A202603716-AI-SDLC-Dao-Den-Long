import io, json, os, subprocess, sys, tempfile, unittest
from game.sim import Sim
from game import headless

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
def load(n):
    with open(os.path.join(ROOT, "scenarios", n)) as f: return json.load(f)

def run(scn, inp=None, ticks=300, seed=1):
    out = io.StringIO()
    headless.run(seed, ticks, load(scn), headless.load_frames(os.path.join(ROOT, "scenarios", inp)) if inp else [], 10, out)
    return [json.loads(l) for l in out.getvalue().splitlines()]

def events(lines): return [(l["name"], l["data"]) for l in lines if l["type"] == "event"]

class T(unittest.TestCase):
    def test_pickup_deposit_light(self):
        ev = events(run("pick_and_light.json", "pick_and_light.inputs.json"))
        self.assertEqual([e for e in ev if e[0] == "mote_picked"][-1][1]["carried"], 6)
        self.assertIn(("lantern_lit", {"lantern_id": "L1"}), ev)

    def test_pulse_stuns_shade_and_costs_light(self):
        lines = run("pulse.json", "pulse.inputs.json", ticks=5)
        self.assertIn(("pulse", {"stunned_ids": ["S1"]}), events(lines))
        snap = [l for l in lines if l["type"] == "snapshot"][-1]
        self.assertEqual(snap["player"]["carried"], 1)
        self.assertEqual(snap["shades"][0]["state"], "stunned")

    def test_shade_hit_loses_game(self):
        lines = run("shade_hit.json", ticks=600)
        names = [e[0] for e in events(lines)]
        self.assertEqual(names, ["player_hit", "game_over"])
        self.assertEqual(lines[-1]["state"], "lost")
        self.assertEqual(events(lines)[0][1], {"by": "shade", "flames": 0, "dropped": 2})

    def test_dawn_loss(self):
        s = load("pulse.json"); s["time_left_s"] = 1; s["shades"] = []
        sim = Sim(1, s)
        for _ in range(60): sim.step()
        self.assertEqual(sim.state, "lost")

    def test_win_when_all_lit(self):
        s = {"random_motes": False, "random_shades": False, "motes": [], "shades": [], "player": {"carried": 6},
             "lanterns": [{"id": f"L{i}", "lit": True} for i in (2, 3, 4, 5)] + [{"id": "L1", "pos": [0, 0, 1]}]}
        sim = Sim(1, s); sim.set_inputs({"interact": True}); ev = sim.step()
        self.assertEqual(ev[-1], ("game_over", {"result": "won", "reason": "all_lit"}))
        self.assertGreater(sim.score, 0)

    def test_scenario_setup_gives_no_score(self):
        self.assertEqual(Sim(1, {"lanterns": [{"id": "L1", "lit": True}]}).score, 0)

    def test_deterministic(self):
        a = run("pick_and_light.json", ticks=2000, seed=7)
        b = run("pick_and_light.json", ticks=2000, seed=7)
        self.assertEqual(a, b)
        full = io.StringIO(); headless.run(3, 3000, None, [], 10, full)
        full2 = io.StringIO(); headless.run(3, 3000, None, [], 10, full2)
        self.assertEqual(full.getvalue(), full2.getvalue())

    def test_bad_inputs_exit_2(self):
        with tempfile.TemporaryDirectory() as d:
            bad = os.path.join(d, "bad.json"); json.dump({"frames": [{"tick": 5}, {"tick": 5}]}, open(bad, "w"))
            for args in (["--inputs", bad], ["--scenario", os.path.join(d, "missing.json")]):
                r = subprocess.run([sys.executable, "-m", "game.headless", "--seed", "1", "--ticks", "5", "--out", os.path.join(d, "o")] + args, cwd=ROOT, capture_output=True)
                self.assertEqual(r.returncode, 2)

if __name__ == "__main__":
    unittest.main()
