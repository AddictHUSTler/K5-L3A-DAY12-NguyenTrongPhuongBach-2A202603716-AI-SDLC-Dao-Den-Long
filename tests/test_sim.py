import io, json, math, os, subprocess, sys, tempfile, time, unittest
from game.sim import Sim
from game import headless

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
def load(n):
    with open(os.path.join(ROOT, "scenarios", n)) as f: return json.load(f)

def run(scn, inp=None, ticks=300, seed=1, night=1):
    out = io.StringIO()
    headless.run(seed, ticks, load(scn), headless.load_frames(os.path.join(ROOT, "scenarios", inp)) if inp else [], 10, out, night)
    return [json.loads(l) for l in out.getvalue().splitlines()]

def events(lines): return [(l["name"], l["data"]) for l in lines if l["type"] == "event"]

def sim(night=1, **kw):
    sc = {"random_motes": False, "random_shades": False, "random_drifters": False, "wind_enabled": False, "motes": [], "shades": []}
    sc.update(kw)
    return Sim(1, sc, night=night)

def go(s, n, **inp):
    s.set_inputs(inp); out = []
    for _ in range(n): out += s.step()
    return out

class T(unittest.TestCase):
    # ---- Phase 1 rules, re-checked under v1.1 numbers
    def test_pickup_deposit_light(self):
        ev = events(run("pick_and_light.json", "pick_and_light.inputs.json", ticks=200))
        self.assertEqual([e for e in ev if e[0] == "mote_picked"][-1][1]["carried"], 10)
        self.assertIn(("lantern_lit", {"lantern_id": "L1"}), ev)

    def test_pulse_stuns_shade_and_costs_light(self):
        lines = run("pulse.json", "pulse.inputs.json", ticks=5)
        self.assertIn(("pulse", {"stunned_ids": ["S1"]}), events(lines))
        snap = [l for l in lines if l["type"] == "snapshot"][-1]
        self.assertEqual(snap["player"]["carried"], 0)
        self.assertEqual(snap["shades"][0]["state"], "stunned")
        self.assertEqual(snap["score"], 5)

    def test_shade_hit_loses_game(self):
        lines = run("shade_hit.json", ticks=600)
        self.assertEqual([e[0] for e in events(lines)][-2:], ["player_hit", "game_over"])
        self.assertEqual(lines[-1]["state"], "lost")
        self.assertEqual(events(lines)[-2][1], {"by": "shade", "flames": 0, "dropped": 2})

    def test_dawn_loss(self):
        s = sim(time_left_s=1); go(s, 60)
        self.assertEqual(s.state, "lost")

    def test_win_when_all_lit(self):
        s = sim(player={"carried": 10}, lanterns=[{"id": f"L{i}", "lit": True} for i in (2, 3, 4, 5)] + [{"id": "L1", "pos": [0, 0, 1]}])
        ev = go(s, 1, interact=True)
        self.assertEqual(ev[-1], ("game_over", {"result": "won", "reason": "all_lit"}))
        self.assertEqual(s.score, 100 + 100 + 299 * 2 + 50 * 3)   # 10 motes + lantern + floor(299 s) * 2 + 3 flames * 50

    def test_scenario_setup_gives_no_score(self):
        self.assertEqual(Sim(1, {"lanterns": [{"id": "L1", "lit": True}]}).score, 0)

    def test_deterministic(self):
        for n in (1, 2, 3):
            a, b = io.StringIO(), io.StringIO()
            headless.run(3, 3000, None, [], 10, a, n); headless.run(3, 3000, None, [], 10, b, n)
            self.assertEqual(a.getvalue(), b.getvalue())

    def test_bad_inputs_exit_2(self):
        with tempfile.TemporaryDirectory() as d:
            bad = os.path.join(d, "bad.json"); json.dump({"frames": [{"tick": 5}, {"tick": 5}]}, open(bad, "w"))
            for args in (["--inputs", bad], ["--scenario", os.path.join(d, "missing.json")], ["--night", "4"]):
                r = subprocess.run([sys.executable, "-m", "game.headless", "--seed", "1", "--ticks", "5", "--out", os.path.join(d, "o")] + args, cwd=ROOT, capture_output=True)
                self.assertEqual(r.returncode, 2)

    # ---- Phase 2
    def test_standard_numbers(self):
        from game.sim import load_tuning
        T_ = load_tuning()
        for k, v in dict(player_speed=6.0, jump_speed=7.0, gravity=20.0, dash_speed=14.0, dash_duration_s=0.2, dash_cooldown_s=1.5,
                         carry_capacity=10, lantern_cost=10, pulse_cost=3, pulse_radius=5.0, safe_radius=6.0,
                         night1_duration_s=300, night2_duration_s=330, night3_duration_s=360).items():
            self.assertEqual(T_[k], v, k)

    def test_run_speed_and_stop(self):
        s = sim(); go(s, 6, move=[0, 1]); self.assertAlmostEqual(s.vz, 6.0)
        go(s, 6, move=[0, 0]); self.assertAlmostEqual(s.vz, 0.0)

    def test_jump_only_on_ground(self):
        s = sim(); go(s, 1, jump=True); self.assertGreater(s.pos[1], 0)
        go(s, 1, jump=False); go(s, 1, jump=True); self.assertLess(s.vy, 7.0)   # no double jump
        go(s, 60); self.assertEqual(s.pos[1], 0.0)

    def test_dash(self):
        lines = run("dash.json", "dash.inputs.json", ticks=40, night=2)
        self.assertIn(("dash", {}), events(lines))
        p = [l for l in lines if l["type"] == "snapshot"][-1]["player"]
        self.assertAlmostEqual(p["dash_cd_s"], 1.5 - 19 / 60, places=2)
        s = sim(night=2); go(s, 1, move=[0, 1], dash=True)
        self.assertAlmostEqual(s.vz, 14.0)
        go(s, 1, dash=False); go(s, 1, dash=True)   # pressed again mid-dash/cooldown: ignored
        self.assertEqual(s.dash_cd, 88)

    def test_dash_keeps_height_in_air(self):
        s = sim(); go(s, 1, jump=True); go(s, 3); y = s.pos[1]; go(s, 1, dash=True)
        self.assertEqual(s.pos[1], y)

    def test_pad_launch_night2(self):
        s = sim(2, player={"pos": [19.5, 0, 17.5]}); go(s, 1)
        self.assertEqual((s.vy > 0, s.launched), (True, True))
        go(s, 100, move=[-1, 0])   # keys do not override launch
        self.assertTrue(s.grounded and 35 < s.pos[0] < 70, s.pos)

    def test_fall_once_then_respawn(self):
        lines = run("fall.json", "fall.inputs.json", ticks=300, night=2)
        hits = [e for e in events(lines) if e[0] == "player_hit"]
        self.assertEqual(hits, [("player_hit", {"by": "fall", "flames": 2, "dropped": 0, "lost": 4})])
        p = [l for l in lines if l["type"] == "snapshot"][-1]["player"]
        self.assertTrue(p["invuln"] or p["flames"] == 2)

    def test_fall_wait_60_ticks_then_start(self):
        s = sim(2, player={"pos": [0, -10.5, 60], "carried": 3}); go(s, 1)
        self.assertEqual((s.flames, s.carried, s.fall_wait), (2, 0, 60))
        go(s, 59); self.assertLess(s.pos[1], 0)
        go(s, 1); self.assertEqual((s.pos, s.invuln), ([0.0, 0.0, 0.0], 90))

    def test_night_maps(self):
        self.assertEqual([len(sim(n).lanterns) for n in (1, 2, 3)], [5, 6, 7])
        self.assertEqual([sim(n).left_ticks() for n in (1, 2, 3)], [18000, 19800, 21600])
        self.assertEqual(len(Sim(1, night=3).motes), 20)

    def test_night3_wall_blocks_tier1_and_ramp_climbs(self):
        s = sim(3, player={"pos": [0, 0, 10.5]}); go(s, 30, move=[0, 1]); self.assertEqual(s.pos[1], 0.0)   # wall at r=12 (inner edge of tier 1 is a drop, not a wall)
        s = sim(3, player={"pos": [27.0, 0, 15.6]}); go(s, 40, move=[-1, -0.6])  # onto the ramp at 30 deg
        self.assertGreater(s.pos[1], 0.0)
        s = sim(3, player={"pos": [30.0, 0, 8.0]}); go(s, 60, move=[-1, 0])   # straight into tier-1 wall, no ramp
        self.assertEqual(s.pos[1], 0.0)

    def test_night3_pad_reaches_tier2(self):
        s = sim(3, player={"pos": [0, 3, 13.5]}); go(s, 1); go(s, 70)
        self.assertEqual((s.grounded, s.pos[1]), (True, 6.0)); self.assertLess(math.hypot(s.pos[0], s.pos[2]), 8)

    def test_wind_schedule(self):
        s = Sim(1, {"random_motes": False, "random_shades": False, "random_drifters": False, "motes": []}, night=3)
        go(s, 1679); self.assertFalse(s.wind["warn"]); go(s, 1); self.assertTrue(s.wind["warn"])
        go(s, 120); self.assertTrue(s.wind["active"]); go(s, 300); self.assertFalse(s.wind["active"])

    def test_drifter_steals_then_pulse_returns(self):
        s = sim(2, player={"carried": 6}, drifters=[{"id": "D1", "pos": [3, 1, 0], "state": "idle"}])
        ev = go(s, 40)
        steal = [e for e in ev if e[0] == "drifter_steal"]
        self.assertEqual(steal, [("drifter_steal", {"drifter_id": "D1", "amount": 3, "carried": 3})])
        self.assertEqual(s.drifters[0]["state"], "flee")
        s.drifters[0]["pos"] = [1.0, 1.0, 0.0]; s.pos = [0.0, 0.0, 0.0]
        ev = go(s, 1, pulse=True)
        self.assertIn(("drifter_drop", {"drifter_id": "D1", "amount": 3}), ev)
        self.assertEqual(len([m for m in s.motes if m["kind"] == "dropped"]), 3)

    def test_pulse_turns_chasing_drifter_to_flee_without_theft(self):
        s = sim(2, player={"carried": 6}, drifters=[{"id": "D1", "pos": [3, 1, 0], "state": "chase"}])
        go(s, 1, pulse=True); self.assertEqual((s.drifters[0]["state"], s.drifters[0]["stolen"], s.carried), ("flee", 0, 3))

    def test_drifter_needs_5_carried_and_15m(self):
        s = sim(2, player={"carried": 4}, drifters=[{"pos": [5, 1, 0], "state": "idle"}]); go(s, 2)
        self.assertEqual(s.drifters[0]["state"], "idle")
        s = sim(2, player={"carried": 5}, drifters=[{"pos": [14, 1, 0], "state": "idle"}]); go(s, 1)
        self.assertEqual(s.drifters[0]["state"], "chase")

    def test_charm_effects(self):
        lines = run("charm.json", None, ticks=2, night=2)
        self.assertIn(("charm_picked", {"charm_id": "C1", "charm_ticks": 600}), events(lines))
        s = sim(2, charms=[{"id": "C1", "pos": [0, 0, 0.5]}]); go(s, 1)
        go(s, 12, move=[0, 1]); self.assertAlmostEqual(s.vz, 7.2)
        go(s, 1, dash=True); self.assertEqual(s.dash_cd, 0)
        self.assertFalse(s.charms[0]["available"])
        go(s, 600); self.assertEqual(s.charm, 0)
        s.charms[0]["respawn"] = 1; go(s, 1); self.assertTrue(s.charms[0]["available"])

    def test_pause_freezes_sim(self):
        lines = run("pause.json", "pause.inputs.json", ticks=30, night=2)
        self.assertEqual([e[0] for e in events(lines)], ["night_start", "paused", "resumed"])
        self.assertEqual(lines[-1]["ticks"], 30)
        s = sim(2); go(s, 5); go(s, 1, pause=True); st = s.sim_tick; go(s, 1, pause=False); go(s, 10)
        self.assertEqual(s.snapshot()["state"], "paused"); self.assertEqual(s.sim_tick, st)

    def test_hit_recoil_drops_motes_and_grants_invuln(self):
        s = sim(player={"carried": 7}, shades=[{"id": "S1", "pos": [0.5, 0, 0]}]); ev = go(s, 1)
        self.assertIn(("player_hit", {"by": "shade", "flames": 2, "dropped": 3}), ev)
        self.assertEqual((s.flames, s.carried, s.invuln, s.shades[0]["state"]), (2, 4, 90, "recoil"))
        self.assertEqual([m["ttl"] for m in s.motes], [480] * 3)
        p0 = list(s.shades[0]["pos"]); go(s, 60)
        self.assertAlmostEqual(math.hypot(s.shades[0]["pos"][0] - p0[0], s.shades[0]["pos"][2] - p0[2]), 2.0, places=2)

    def test_shade_spawn_schedule(self):
        s = Sim(1, {"random_motes": False, "motes": []}); ev = go(s, 300)
        self.assertEqual([e[0] for e in ev].count("shade_spawned"), 2)
        self.assertEqual(s.shades[0]["state"], "spawning"); go(s, 480); self.assertEqual(len(s.shades), 3)

    def test_mote_spawn_cap_and_schedule(self):
        s = Sim(1, {"random_shades": False}, night=3); self.assertEqual(len(s.motes), 20)
        go(s, 240); self.assertEqual(len(s.motes), 21)
        for _ in range(12): go(s, 240)
        self.assertEqual(len(s.motes), 30)   # cap 30 (night 3 has exactly 30 points)
        s = Sim(1, {"random_shades": False}); go(s, 240 * 12); self.assertEqual(len(s.motes), 24)   # night 1: out of free points, skip

    def test_safe_zone_blocks_and_ejects(self):
        s = sim(player={"pos": [0, 0, 20], "carried": 10}, lanterns=[{"id": "L1", "pos": [0, 0, 19]}],
                shades=[{"id": "S1", "pos": [0, 0, 17]}]); go(s, 1, interact=True)
        for _ in range(30): s.step()
        self.assertAlmostEqual(s.xz(s.shades[0]["pos"], [0, 0, 19]), 6.0, places=2)

    def test_night_runs_fast(self):
        t = time.time(); headless.run(1, 21600, None, [], 10, io.StringIO(), 3)
        self.assertLess(time.time() - t, 30)

if __name__ == "__main__":
    unittest.main()
