"""Pure game logic for Đảo Đèn Lồng. No I/O, no rendering, no wall-clock. Deterministic per seed."""
import json, math, os

DT = 1.0 / 60.0
CONTRACT_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "game.contract.json")
ISLAND_R = 100.0
JUMP_V, GRAVITY = 7.0, 20.0
LANTERN_POS = [[30, 0, -18], [52, 0, 40], [-8, 0, 64], [-58, 0, -26], [-14, 0, -56]]
MOTE_INIT, MOTE_MAX, MOTE_EVERY_TICKS = 28, 40, 144       # 2.4 s
SHADE_FIRST_S, SHADE_EVERY_S, SHADE_MAX, SHADE_SPAWN_R = 22, 20, 4, 70.0


class ScenarioError(ValueError):
    pass


def load_tuning(path=CONTRACT_PATH):
    with open(path) as f:
        return json.load(f)["tuning"]


def mulberry32(seed):
    a = seed & 0xFFFFFFFF
    def rnd():
        nonlocal a
        a = (a + 0x6D2B79F5) & 0xFFFFFFFF
        t = ((a ^ (a >> 15)) * (1 | a)) & 0xFFFFFFFF
        t = ((t + (((t ^ (t >> 7)) * (61 | t)) & 0xFFFFFFFF)) & 0xFFFFFFFF) ^ t
        return ((t ^ (t >> 14)) & 0xFFFFFFFF) / 4294967296.0
    return rnd


def r3(v):
    return round(v, 3) + 0.0


def vec(v, name):
    if not (isinstance(v, list) and len(v) == 3 and all(isinstance(x, (int, float)) and not isinstance(x, bool) for x in v)):
        raise ScenarioError(f"{name} must be [x, y, z]")
    return [float(x) for x in v]


class Sim:
    def __init__(self, seed=0, scenario=None, tuning=None):
        self.T = tuning or load_tuning()
        self.rnd = mulberry32(seed)
        sc = scenario or {}
        if not isinstance(sc, dict):
            raise ScenarioError("scenario must be an object")
        T = self.T
        self.steps = 0
        self.state = "playing"
        self.score = 0
        self.base_time = float(sc.get("time_left_s", T["night1_duration_s"]))
        p = sc.get("player", {})
        self.pos = vec(p.get("pos", [0, 0, 0]), "player.pos")
        self.vy = 0.0
        self.flames = int(p.get("flames", T["flames"]))
        self.carried = int(p.get("carried", 0))
        self.invuln = 0.0
        self.pulse_cd = 0.0
        self.lanterns = [{"id": f"L{i+1}", "pos": list(map(float, q)), "lit": False, "deposited": 0}
                         for i, q in enumerate(LANTERN_POS[:T["lantern_count_night1"]])]
        for u in sc.get("lanterns", []):
            self._apply_lantern(u)
        self.motes, self.shades = [], []
        self.mote_n = self.shade_n = 0
        self.random_shades = sc.get("random_shades", True)
        self.random_motes = sc.get("random_motes", True)
        if "motes" in sc:
            for m in sc["motes"]:
                self.motes.append({"id": f"M{self._next('mote_n')}", "pos": vec(m, "motes[]")})
        elif self.random_motes:
            for _ in range(MOTE_INIT):
                self._spawn_mote()
        if "shades" in sc:
            self.shades = []
            for s in sc["shades"]:
                sid = s.get("id") or f"S{self._next('shade_n')}"
                self.shades.append({"id": sid, "pos": vec(s.get("pos"), "shades[].pos"), "state": "chase", "stun": 0.0})
            self.shade_n = len(self.shades)
        self.in_ = {"move": [0.0, 0.0], "cam_yaw_deg": 0.0, "jump": False, "interact": False, "pulse": False}
        self.prev = {"jump": False, "interact": False, "pulse": False}

    # ---- helpers
    def _next(self, attr):
        setattr(self, attr, getattr(self, attr) + 1)
        return getattr(self, attr)

    def _apply_lantern(self, u):
        if not isinstance(u, dict) or "id" not in u:
            raise ScenarioError("lantern update needs id")
        L = next((l for l in self.lanterns if l["id"] == u["id"]), None)
        if L is None:
            if "pos" not in u:
                raise ScenarioError(f"unknown lantern {u['id']}")
            L = {"id": u["id"], "pos": [0, 0, 0], "lit": False, "deposited": 0}
            self.lanterns.append(L)
        if "pos" in u:
            L["pos"] = vec(u["pos"], "lantern.pos")
        if "deposited" in u:
            L["deposited"] = int(u["deposited"])
        if u.get("lit"):
            L["lit"], L["deposited"] = True, max(L["deposited"], self.T["lantern_cost"])

    def _spawn_mote(self):
        for _ in range(20):
            a, r = self.rnd() * math.tau, math.sqrt(self.rnd()) * (ISLAND_R - 12)
            x, z = r * math.cos(a), r * math.sin(a)
            if all(math.hypot(x - l["pos"][0], z - l["pos"][2]) > 3 for l in self.lanterns):
                break
        self.motes.append({"id": f"M{self._next('mote_n')}", "pos": [x, 0.0, z]})

    def _spawn_shade(self, ev):
        a = self.rnd() * math.tau
        sid = f"S{self._next('shade_n')}"
        while any(s["id"] == sid for s in self.shades):
            sid = f"S{self._next('shade_n')}"
        self.shades.append({"id": sid, "pos": [SHADE_SPAWN_R * math.cos(a), 1.0, SHADE_SPAWN_R * math.sin(a)], "state": "chase", "stun": 0.0})
        ev("shade_spawned", {"id": sid})

    def time_left(self):
        return max(0.0, self.base_time - self.steps / 60.0)

    # ---- input
    def set_inputs(self, ch):
        for k, v in ch.items():
            if k in ("tick",):
                continue
            if k == "move":
                if not (isinstance(v, list) and len(v) == 2 and all(isinstance(x, (int, float)) and not isinstance(x, bool) and -1 <= x <= 1 for x in v)):
                    raise ScenarioError("move must be [x, z] within [-1, 1]")
                self.in_["move"] = [float(v[0]), float(v[1])]
            elif k == "cam_yaw_deg":
                if not isinstance(v, (int, float)) or isinstance(v, bool):
                    raise ScenarioError("cam_yaw_deg must be a number")
                self.in_["cam_yaw_deg"] = float(v)
            elif k in ("jump", "interact", "pulse", "dash"):
                if not isinstance(v, bool):
                    raise ScenarioError(f"{k} must be boolean")
                if k != "dash":
                    self.in_[k] = v

    # ---- step
    def step(self):
        """Advance one tick; return list of (name, data) events."""
        evs = []
        if self.state != "playing":
            return evs
        ev = lambda n, d: evs.append((n, d))
        T = self.T
        self.steps += 1
        # move
        mx, mz = self.in_["move"]
        n = math.hypot(mx, mz)
        if n > 1:
            mx, mz = mx / n, mz / n
        th = math.radians(self.in_["cam_yaw_deg"])
        wx, wz = mx * math.cos(th) + mz * math.sin(th), -mx * math.sin(th) + mz * math.cos(th)
        self.pos[0] += wx * T["player_speed"] * DT
        self.pos[2] += wz * T["player_speed"] * DT
        d = math.hypot(self.pos[0], self.pos[2])
        if d > ISLAND_R:
            self.pos[0] *= ISLAND_R / d
            self.pos[2] *= ISLAND_R / d
        # jump / gravity
        edge = {k: self.in_[k] and not self.prev[k] for k in self.prev}
        self.prev = {k: self.in_[k] for k in self.prev}
        if edge["jump"] and self.pos[1] <= 0:
            self.vy = JUMP_V
        if self.pos[1] > 0 or self.vy > 0:
            self.vy -= GRAVITY * DT
            self.pos[1] = max(0.0, self.pos[1] + self.vy * DT)
            if self.pos[1] == 0:
                self.vy = 0.0
        # timers
        self.invuln = max(0.0, self.invuln - DT)
        self.pulse_cd = max(0.0, self.pulse_cd - DT)
        for s in self.shades:
            if s["state"] == "stunned":
                s["stun"] -= DT
                if s["stun"] <= 0:
                    s["state"], s["stun"] = "chase", 0.0
        # interact
        if edge["interact"]:
            self._interact(ev)
            if self.state != "playing":
                return evs
        # pulse
        if edge["pulse"] and self.pulse_cd <= 0 and self.carried >= T["pulse_cost"]:
            self.carried -= T["pulse_cost"]
            self.pulse_cd = T["pulse_cooldown_s"]
            hit = []
            for s in self.shades:
                dx, dz = s["pos"][0] - self.pos[0], s["pos"][2] - self.pos[2]
                dd = math.hypot(dx, dz)
                if dd <= T["pulse_radius"]:
                    if s["state"] != "stunned":
                        self.score += T["score"]["per_stun"]
                    s["state"], s["stun"] = "stunned", T["pulse_stun_s"]
                    ux, uz = (dx / dd, dz / dd) if dd > 1e-9 else (1.0, 0.0)
                    s["pos"][0] += ux * T["pulse_push_m"]
                    s["pos"][2] += uz * T["pulse_push_m"]
                    hit.append(s["id"])
            ev("pulse", {"stunned_ids": hit})
        # pickup
        keep = []
        for m in self.motes:
            if self.carried < T["carry_capacity"] and math.hypot(m["pos"][0] - self.pos[0], m["pos"][2] - self.pos[2]) <= T["pickup_radius"]:
                self.carried += 1
                self.score += T["score"]["per_mote"]
                ev("mote_picked", {"carried": self.carried})
            else:
                keep.append(m)
        self.motes = keep
        # spawns
        if self.steps % MOTE_EVERY_TICKS == 0 and len(self.motes) < MOTE_MAX and self.random_motes:
            self._spawn_mote()
        t = self.steps / 60.0
        if self.random_shades and len(self.shades) < SHADE_MAX and t >= SHADE_FIRST_S and \
                (self.steps - round(SHADE_FIRST_S * 60)) % round(SHADE_EVERY_S * 60) == 0:
            self._spawn_shade(ev)
        # shades
        lit = [l for l in self.lanterns if l["lit"]]
        for s in self.shades:
            if s["state"] == "stunned":
                continue
            dx, dz = self.pos[0] - s["pos"][0], self.pos[2] - s["pos"][2]
            dd = math.hypot(dx, dz)
            if dd > 1e-9:
                st = min(T["shade_speed"] * DT, dd)
                s["pos"][0] += dx / dd * st
                s["pos"][2] += dz / dd * st
        for s in self.shades:
            for l in lit:
                ox, oz = s["pos"][0] - l["pos"][0], s["pos"][2] - l["pos"][2]
                od = math.hypot(ox, oz)
                if od < T["safe_radius"]:
                    ux, uz = (ox / od, oz / od) if od > 1e-9 else (1.0, 0.0)
                    s["pos"][0], s["pos"][2] = l["pos"][0] + ux * T["safe_radius"], l["pos"][2] + uz * T["safe_radius"]
        # hit
        if self.invuln <= 0:
            for s in self.shades:
                if s["state"] != "stunned" and math.hypot(s["pos"][0] - self.pos[0], s["pos"][2] - self.pos[2]) <= T["shade_hit_radius"]:
                    drop = int(self.carried * T["hit_drop_ratio"])
                    self.carried -= drop
                    self.flames -= 1
                    self.invuln = T["invuln_s"]
                    ev("player_hit", {"by": "shade", "flames": self.flames, "dropped": drop})
                    if self.flames <= 0:
                        self._end(ev, "lost", "no_flames")
                        return evs
                    break
        # dawn
        if self.time_left() <= 0:
            self._end(ev, "lost", "dawn")
        return evs

    def _interact(self, ev):
        T = self.T
        best, bd = None, 1e18
        for l in self.lanterns:
            if l["lit"]:
                continue
            dd = math.hypot(l["pos"][0] - self.pos[0], l["pos"][2] - self.pos[2])
            if dd <= T["interact_radius"] and dd < bd:
                best, bd = l, dd
        if not best or self.carried <= 0:
            return
        amt = min(self.carried, T["lantern_cost"] - best["deposited"])
        if amt <= 0:
            return
        self.carried -= amt
        best["deposited"] += amt
        ev("deposit", {"lantern_id": best["id"], "amount": amt, "deposited": best["deposited"]})
        if best["deposited"] >= T["lantern_cost"]:
            best["lit"] = True
            self.score += T["score"]["per_lantern"]
            ev("lantern_lit", {"lantern_id": best["id"]})
            if all(l["lit"] for l in self.lanterns):
                self._end(ev, "won", "all_lit")

    def _end(self, ev, result, reason):
        if result == "won":
            self.score += self.T["score"]["per_second_left"] * int(self.time_left()) + self.T["score"]["per_flame_left"] * self.flames
        self.state = result
        ev("game_over", {"result": result, "reason": reason})

    # ---- output
    def snapshot(self):
        return {"type": "snapshot", "tick": self.steps, "sim_tick": self.steps, "state": self.state,
                "time_left_s": r3(self.time_left()), "score": self.score,
                "player": {"pos": [r3(v) for v in self.pos], "flames": self.flames, "carried": self.carried},
                "lanterns": [{"id": l["id"], "pos": [r3(v) for v in l["pos"]], "lit": l["lit"], "deposited": l["deposited"]} for l in self.lanterns],
                "shades": [{"id": s["id"], "pos": [r3(v) for v in s["pos"]], "state": s["state"]} for s in self.shades],
                "motes_active": len(self.motes),
                "motes": [{"id": m["id"], "pos": [r3(v) for v in m["pos"]]} for m in self.motes]}

