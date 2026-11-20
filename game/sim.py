"""Pure game logic for Đảo Đèn Lồng, Test Contract v1.3. No I/O, no rendering, no wall-clock.
Deterministic per seed. All numbers and maps come from game.contract.json."""
import json, math, os
from .world import Terrain, ring_points, unit

DT = 1.0 / 60.0
CONTRACT_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "game.contract.json")
SHADE_STATES = ("spawning", "wander", "chase", "recoil", "stunned", "drain")
DRIFTER_STATES = ("idle", "chase", "flee")
BUTTONS = ("jump", "interact", "pulse", "dash", "pause")
FUEL_UNIT = 60      # fuel is stored as integer 1/60 units so per-tick decay has no float error


class ScenarioError(ValueError):
    pass


def load_contract(path=CONTRACT_PATH):
    with open(path) as f:
        return json.load(f)


def load_tuning(path=CONTRACT_PATH):
    return load_contract(path)["tuning"]


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


def ticks(s):
    return round(s * 60)


def num(v):
    return isinstance(v, (int, float)) and not isinstance(v, bool)


def vec(v, name):
    if not (isinstance(v, list) and len(v) == 3 and all(num(x) for x in v)):
        raise ScenarioError(f"{name} must be [x, y, z]")
    return [float(x) for x in v]


class Sim:
    def __init__(self, seed=0, scenario=None, tuning=None, night=1, contract=None):
        con = contract or load_contract()
        self.T = tuning or con["tuning"]
        if night not in (1, 2, 3):
            raise ScenarioError("night must be 1, 2 or 3")
        sc = scenario or {}
        if not isinstance(sc, dict):
            raise ScenarioError("scenario must be an object")
        self.night, self.M = night, con["maps"][str(night)]
        self.rnd = mulberry32(seed)
        self.terrain = Terrain(self.M, self.T["step_up_m"])
        self.mote_pts, self.shade_pts = ring_points(self.M["mote_rings"]), ring_points(self.M["shade_rings"])
        self.tick = self.sim_tick = 0                       # tick counts while paused, sim_tick does not
        self.state, self.paused, self.started, self.score = "playing", False, False, 0
        self.base_ticks = ticks(float(sc.get("time_left_s", self.T[self.M["duration_key"]])))
        self.random_motes = sc.get("random_motes", True)
        self.random_shades = sc.get("random_shades", True)
        self.random_drifters = sc.get("random_drifters", night >= 2)
        self.wind_on = sc.get("wind_enabled", bool(self.M.get("wind")))
        self.wind = {"active": False, "warn": False, "dir": 0.0, "next": ticks(self.T["wind_every_s"]), "end": 0}
        self.in_ = {"move": [0.0, 0.0], "cam_yaw_deg": 0.0, **{k: False for k in BUTTONS}}
        self.prev = {k: False for k in BUTTONS}
        self._init_player(sc.get("player", {}))
        self._init_lanterns(sc.get("lanterns", []))
        self.motes, self.mote_n, self.shades, self.shade_n, self.drifters, self.drifter_n = [], 0, [], 0, [], 0
        self._init_motes(sc)
        self._init_mobs(sc)
        self._init_charms(sc)

    def _init_player(self, p):
        T = self.T
        self.start = list(map(float, self.M["start"]))
        self.pos = vec(p["pos"], "player.pos") if "pos" in p else list(self.start)
        self.vx, self.vy, self.vz = vec(p["vel"], "player.vel") if "vel" in p else (0.0, 0.0, 0.0)
        h = self.terrain.height(self.pos[0], self.pos[2])
        self.grounded = h is not None and abs(self.pos[1] - h) < 1e-6
        self.face = (0.0, 1.0)
        self.flames, self.carried = int(p.get("flames", T["flames"])), int(p.get("carried", 0))
        self.invuln, self.dash_cd = int(p.get("invuln_ticks", 0)), int(p.get("dash_cd_ticks", 0))
        self.pulse_cd, self.charm = int(p.get("pulse_cd_ticks", 0)), int(p.get("charm_ticks", 0))
        self.dash_left, self.dash_dir = 0, (0.0, 1.0)
        self.launched, self.launch_v = False, (0.0, 0.0)    # launched = flying from a pad; keys do not steer
        self.successful_lights = int(p.get("successful_lights", 0))
        self.fall_wait = 0                                  # ticks left frozen after falling off the island

    def _init_lanterns(self, updates):
        self.lanterns = [{"id": f"L{i+1}", "pos": list(map(float, q)), "lit": False, "deposited": 0, "fuel": 0, "ever_lit": False, "relit": 0} for i, q in enumerate(self.M["lanterns"])]
        for u in updates:
            self._apply_lantern(u)

    def _init_motes(self, sc):
        if "motes" in sc:   # scenario list replaces the defaults; entries are [x,y,z] or {pos, kind, ttl_ticks}
            for m in sc["motes"]:
                if isinstance(m, dict):
                    self._add_mote(vec(m.get("pos"), "motes[].pos"), m.get("kind", "random"), m.get("ttl_ticks"), None)
                else:
                    self._add_mote(vec(m, "motes[]"), "random", None, None)
        elif self.random_motes:
            free = list(range(len(self.mote_pts)))
            for _ in range(self.T["mote_initial"]):
                i = free.pop(int(self.rnd() * len(free)))
                self._add_mote(list(self.mote_pts[i]), "random", None, i)

    def _init_mobs(self, sc):
        T = self.T
        for s in sc.get("shades", []):
            st = s.get("state", "chase")
            if st not in SHADE_STATES:
                raise ScenarioError(f"bad shade state {st}")
            sh = self._new_shade(s.get("id"), vec(s.get("pos"), "shades[].pos"), st)
            default_left = {"stunned": T["pulse_stun_ticks"], "recoil": T["recoil_ticks"]}.get(st, 0)
            sh["left"] = int(s.get("state_ticks_left", default_left))
            sh["target"] = s.get("target_lantern_id")
            self.shades.append(sh)
        for d in sc.get("drifters", []):
            st = d.get("state", "idle")
            if st not in DRIFTER_STATES:
                raise ScenarioError(f"bad drifter state {st}")
            self.drifters.append(self._new_drifter(d.get("id"), vec(d.get("pos"), "drifters[].pos"), st,
                                                   int(d.get("stolen", 0)), int(d.get("state_ticks_left", T["drifter_flee_ticks"]))))

    def _init_charms(self, sc):
        if "charms" in sc:
            self.charms = [{"id": c.get("id") or f"C{i+1}", "pos": vec(c.get("pos"), "charms[].pos"),
                            "available": bool(c.get("available", True)), "respawn": int(c.get("respawn_ticks", 0))} for i, c in enumerate(sc["charms"])]
        else:
            self.charms = [{"id": f"C{i+1}", "pos": list(map(float, q)), "available": True, "respawn": 0} for i, q in enumerate(self.M["charms"])]

    def layout(self):
        return json.loads(json.dumps(self.M))

    # ---- helpers
    def _add_mote(self, pos, kind, ttl, idx):
        self.mote_n += 1
        self.motes.append({"id": f"M{self.mote_n}", "pos": pos, "kind": kind, "ttl": ttl, "idx": idx})

    def _new_shade(self, sid, pos, state):
        if not sid:
            self.shade_n += 1
            sid = f"S{self.shade_n}"
            while any(s["id"] == sid for s in self.shades):
                self.shade_n += 1
                sid = f"S{self.shade_n}"
        return {"id": sid, "pos": pos, "state": state, "left": 0, "dir": (1.0, 0.0), "push": 0, "eject": 0, "ec": None, "turn": 0, "target": None, "drain_t": 0}

    def _new_drifter(self, did, pos, state, stolen, left):
        if not did:
            self.drifter_n += 1
            did = f"D{self.drifter_n}"
        return {"id": did, "pos": pos, "state": state, "stolen": stolen, "left": left, "dir": (1.0, 0.0), "turn": 0}

    def _apply_lantern(self, u):
        if not isinstance(u, dict) or "id" not in u:
            raise ScenarioError("lantern update needs id")
        L = next((l for l in self.lanterns if l["id"] == u["id"]), None)
        if L is None:
            if "pos" not in u:
                raise ScenarioError(f"unknown lantern {u['id']}")
            L = {"id": u["id"], "pos": [0, 0, 0], "lit": False, "deposited": 0, "fuel": 0, "ever_lit": False, "relit": 0}
            self.lanterns.append(L)
        if "pos" in u:
            L["pos"] = vec(u["pos"], "lantern.pos")
        if "deposited" in u:
            L["deposited"] = int(u["deposited"])
        L["ever_lit"] = bool(u.get("ever_lit", L["ever_lit"]))
        if u.get("lit"):
            L["lit"], L["ever_lit"], L["deposited"] = True, True, max(L["deposited"], self.T["lantern_cost"])
            L["fuel"] = round(float(u.get("fuel", self.T["fuel_max"])) * FUEL_UNIT)

    def left_ticks(self):
        return max(0, self.base_ticks - self.sim_tick)

    def xz(self, a, b):
        return math.hypot(a[0] - b[0], a[2] - b[2])

    # ---- input
    def set_inputs(self, ch):
        for k, v in ch.items():
            if k == "tick":
                continue
            if k == "move":
                if not (isinstance(v, list) and len(v) == 2 and all(num(x) and -1 <= x <= 1 for x in v)):
                    raise ScenarioError("move must be [x, z] within [-1, 1]")
                self.in_["move"] = [float(v[0]), float(v[1])]
            elif k == "cam_yaw_deg":
                if not num(v):
                    raise ScenarioError("cam_yaw_deg must be a number")
                self.in_["cam_yaw_deg"] = float(v)
            elif k in BUTTONS:
                if not isinstance(v, bool):
                    raise ScenarioError(f"{k} must be boolean")
                self.in_[k] = v

    # ---- step: stages follow the ticket's mandatory order
    def step(self):
        """Advance one tick; return list of (name, data) events."""
        evs = []
        if self.state != "playing":
            return evs
        ev = lambda n, d: evs.append((n, d))
        T = self.T
        self.tick += 1
        # 1. input / pause
        if self.in_["pause"] and not self.prev["pause"]:
            self.paused = not self.paused
            ev("paused" if self.paused else "resumed", {})
        self.prev["pause"] = self.in_["pause"]
        if self.paused:
            return evs
        edge = {k: self.in_[k] and not self.prev[k] for k in self.prev}
        for k in self.prev:
            self.prev[k] = self.in_[k]
        self.sim_tick += 1
        if not self.started:
            self.started = True
            ev("night_start", {"night": self.night})
        # 2. counters
        respawn = self._tick_counters()
        self._burn_fuel(ev)
        # 3. move player
        if respawn:
            self.pos, self.vx, self.vy, self.vz = list(self.start), 0.0, 0.0, 0.0
            self.grounded, self.launched, self.dash_left, self.invuln = True, False, 0, T["invuln_ticks"]
        if self.fall_wait == 0:
            self._move_player(ev, edge)
        # 4. pickups
        if self.fall_wait == 0:
            self._pickups(ev)
        # 5. lanterns
        if edge["interact"] and self.fall_wait == 0:
            self._interact(ev)
        # 6. safe zones (ejection)
        self._eject()
        # 7. pulse
        if edge["pulse"] and self.fall_wait == 0 and self.pulse_cd <= 0 and self.carried >= T["pulse_cost"]:
            self._pulse(ev)
        # 8. shades and drifters move
        self._move_shades()
        self._move_drifters()
        # 9. contact: drifters first, then shades by id
        if self.fall_wait == 0:
            self._contact(ev)
        # 10. scheduled spawns
        self._spawns(ev)
        # 11. win / lose
        if self.flames <= 0:
            self._end(ev, "lost", "no_flames")
        elif self.left_ticks() <= 0:
            lit = sum(l["lit"] for l in self.lanterns)
            if lit >= math.ceil(round(T["win_ratio"] * len(self.lanterns), 9)):
                self._end(ev, "won", "dawn_survived")
            else:
                self._end(ev, "lost", "dawn")
        return evs

    def _tick_counters(self):
        """Stage 2. Returns True when the post-fall wait just ended and the player should respawn."""
        self.invuln, self.dash_cd = max(0, self.invuln - 1), max(0, self.dash_cd - 1)
        self.pulse_cd, self.charm = max(0, self.pulse_cd - 1), max(0, self.charm - 1)
        respawn = False
        if self.fall_wait > 0:
            self.fall_wait -= 1
            respawn = self.fall_wait == 0 and self.flames > 0
        for m in self.motes:
            if m["ttl"] is not None:
                m["ttl"] -= 1
        self.motes = [m for m in self.motes if m["ttl"] is None or m["ttl"] > 0]
        for c in self.charms:
            if not c["available"]:
                c["respawn"] -= 1
                if c["respawn"] <= 0:
                    c["available"], c["respawn"] = True, 0
        for s in self.shades:
            if s["state"] == "stunned":
                s["left"] -= 1
                if s["left"] <= 0:
                    s["state"], s["left"], s["push"] = "wander", 0, 0
        return respawn

    def _lantern(self, lid):
        return next((l for l in self.lanterns if l["id"] == lid), None)

    def _burn_fuel(self, ev):
        """Stage 2 (fuel): lit lanterns lose decay + 5/s per draining shade; then any lantern at <= 0 goes out."""
        T = self.T
        for l in self.lanterns:
            if l["lit"]:
                l["fuel"] -= round(T["fuel_decay_per_s"])
        for s in self.shades:
            l = self._lantern(s["target"])
            if s["state"] == "drain" and l and l["lit"]:
                l["fuel"] -= round(T["drain_per_s"])
                s["drain_t"] += 1
                if s["drain_t"] % 60 == 0:
                    ev("fuel_drain", {"lantern_id": l["id"], "shade_id": s["id"], "fuel": self._fuel(l)})
        for l in self.lanterns:
            if l["lit"] and l["fuel"] <= 0:
                l["lit"], l["fuel"], l["deposited"] = False, 0, 0
                ev("lantern_out", {"lantern_id": l["id"]})

    def _fuel(self, l):
        return round(l["fuel"] / FUEL_UNIT, 1) + 0.0

    def _safe(self, l):
        """A lantern repels shades only while lit and fuel >= low_fuel_threshold."""
        return l["lit"] and l["fuel"] >= self.T["low_fuel_threshold"] * FUEL_UNIT

    def capacity(self):
        T = self.T
        return min(T["capacity_max"], T["carry_capacity"] + T["capacity_per_light"] * self.successful_lights)

    # ---- stage 3: move the player
    def _move_player(self, ev, edge):
        dashing = self._steer(ev, edge)
        self._walk()
        self._use_pads()
        self._blow_wind()
        if not dashing:
            self._vertical()
        self._check_fall(ev)

    def _steer(self, ev, edge):
        """Set horizontal velocity from keys, dash or pad launch; handle jump/dash presses. Returns True while dashing."""
        T = self.T
        mx, mz = self.in_["move"]
        n = math.hypot(mx, mz)
        if n > 1:
            mx, mz, n = mx / n, mz / n, 1.0
        th = math.radians(self.in_["cam_yaw_deg"])
        wx, wz = mx * math.cos(th) + mz * math.sin(th), -mx * math.sin(th) + mz * math.cos(th)
        speed = T["charm_speed"] if self.charm > 0 else T["player_speed"]
        if n > 1e-9:
            self.face = (wx / n, wz / n)
        if edge["jump"] and self.grounded:
            self.vy, self.grounded = T["jump_speed"], False
        if edge["dash"] and self.dash_cd <= 0 and self.dash_left <= 0:
            self.dash_dir = (wx / n, wz / n) if n > 1e-9 else self.face
            self.dash_left = ticks(T["dash_duration_s"])
            self.dash_cd = 0 if self.charm > 0 else ticks(T["dash_cooldown_s"])
            ev("dash", {})
        if self.dash_left > 0:
            self.vx, self.vz, self.vy = self.dash_dir[0] * T["dash_speed"], self.dash_dir[1] * T["dash_speed"], 0.0
            self.dash_left -= 1
            return True
        if self.launched:
            self.vx, self.vz = self.launch_v
        else:   # reach the target velocity within accel_s
            a = speed * DT / T["accel_s"]
            self.vx += max(-a, min(a, wx * speed - self.vx))
            self.vz += max(-a, min(a, wz * speed - self.vz))
        return False

    def _walk(self):
        """Apply horizontal velocity; walls and the tower block it (slide along one axis if possible)."""
        x, y, z = self.pos
        nx, nz = x + self.vx * DT, z + self.vz * DT
        if not self.terrain.walk_ok(nx, nz, y):
            if self.terrain.walk_ok(nx, z, y):
                nz, self.vz = z, 0.0
            elif self.terrain.walk_ok(x, nz, y):
                nx, self.vx = x, 0.0
            else:
                nx, nz, self.vx, self.vz = x, z, 0.0, 0.0
        self.pos[0], self.pos[2] = nx, nz

    def _use_pads(self):
        if self.launched:
            return
        x, y, z = self.pos
        for p in self.M["pads"]:
            if math.hypot(x - p["pos"][0], z - p["pos"][2]) <= p["r"] and abs(y - p["pos"][1]) <= 0.5:
                ux, uz = p["dir"] if "dir" in p else (p["to"][0] - p["pos"][0], p["to"][1] - p["pos"][2])
                ux, uz = unit(ux, uz)
                self.launch_v = (ux * p["vh"], uz * p["vh"])
                self.vx, self.vz = self.launch_v
                self.vy, self.grounded, self.launched = float(p["vy"]), False, True
                return

    def _blow_wind(self):
        if not self.wind_on:
            return
        self._wind_tick()
        if self.wind["active"]:
            a, k = math.radians(self.wind["dir"]), self.T["wind_speed"] * DT
            x, z = self.pos[0] + math.cos(a) * k, self.pos[2] + math.sin(a) * k
            if self.terrain.walk_ok(x, z, self.pos[1]):
                self.pos[0], self.pos[2] = x, z

    def _vertical(self):
        """Stay on the ground (snapping up/down small steps) or fall under gravity and land."""
        T, x, z = self.T, self.pos[0], self.pos[2]
        if self.grounded:
            h = self.terrain.height(x, z)
            if h is not None and self.pos[1] - h <= T["step_up_m"]:
                self.pos[1] = h
            else:
                self.grounded = False
        if not self.grounded:
            self.vy -= T["gravity"] * DT
            self.pos[1] += self.vy * DT
            h = self.terrain.height(x, z)
            if h is not None and self.pos[1] <= h and self.vy <= 0:
                self.pos[1], self.vy, self.grounded, self.launched = h, 0.0, True, False

    def _check_fall(self, ev):
        T = self.T
        if self.pos[1] < T["fall_y"] and self.fall_wait == 0:
            lost, self.carried = self.carried, 0
            self.flames -= 1
            self.fall_wait = T["fall_wait_ticks"]
            self.vx = self.vy = self.vz = 0.0
            self.launched, self.dash_left = False, 0
            ev("player_hit", {"by": "fall", "flames": self.flames, "dropped": 0, "lost": lost})

    def _wind_tick(self):
        T, w, t = self.T, self.wind, self.sim_tick
        if not w["active"] and t == w["next"] - ticks(T["wind_warn_s"]):
            w["dir"], w["warn"] = r3(self.rnd() * 360.0), True
        if not w["active"] and t == w["next"]:
            w["active"], w["warn"], w["end"] = True, False, t + ticks(T["wind_duration_s"])
        elif w["active"] and t >= w["end"]:
            w["active"] = False
            w["next"] += ticks(T["wind_every_s"])

    # ---- stage 4
    def _pickups(self, ev):
        T = self.T
        keep = []
        for m in self.motes:
            if self.carried < self.capacity() and self.xz(m["pos"], self.pos) <= T["pickup_radius"] and abs(m["pos"][1] - self.pos[1]) <= T["pickup_dy"]:
                self.carried += 1
                ev("mote_picked", {"carried": self.carried})
            else:
                keep.append(m)
        self.motes = keep
        for c in self.charms:
            if c["available"] and self.xz(c["pos"], self.pos) <= T["pickup_radius"] and abs(c["pos"][1] - self.pos[1]) <= T["pickup_dy"]:
                c["available"], c["respawn"] = False, T["charm_respawn_ticks"]
                self.charm = T["charm_ticks"]
                ev("charm_picked", {"charm_id": c["id"], "charm_ticks": self.charm})

    # ---- stage 5
    def _interact(self, ev):
        T = self.T
        fmax = T["fuel_max"] * FUEL_UNIT
        cands = [l for l in self.lanterns if (not l["lit"] or l["fuel"] < fmax) and self.xz(l["pos"], self.pos) <= T["interact_radius"]]
        if not cands or self.carried <= 0:
            return
        best = min(cands, key=lambda l: (self.xz(l["pos"], self.pos), l["id"]))
        if best["lit"]:
            self._refuel(ev, best)
        else:
            self._deposit(ev, best)

    def _deposit(self, ev, l):
        T = self.T
        cost = T["relight_cost"] if l["ever_lit"] else T["lantern_cost"]
        amt = min(self.carried, cost - l["deposited"])
        if amt <= 0:
            return
        self.carried -= amt
        l["deposited"] += amt
        self.score += T["score"]["per_mote"] * amt
        ev("deposit", {"lantern_id": l["id"], "amount": amt, "deposited": l["deposited"]})
        if l["deposited"] >= cost:
            relight = l["ever_lit"]
            l["lit"], l["ever_lit"], l["fuel"] = True, True, T["fuel_max"] * FUEL_UNIT
            l["relit"] += relight
            self.successful_lights += 1
            self.score += T["score"]["relight" if relight else "per_lantern"]
            ev("lantern_lit", {"lantern_id": l["id"], "relight": relight})
            self._push_out_shades(l)

    def _refuel(self, ev, l):
        T = self.T
        fmax = T["fuel_max"] * FUEL_UNIT
        per = T["fuel_per_mote"] * FUEL_UNIT
        used = min(self.carried, -(-(fmax - l["fuel"]) // per))
        if used <= 0:
            return
        was_weak = not self._safe(l)
        l["fuel"] = min(fmax, l["fuel"] + per * used)
        self.carried -= used
        self.score += T["score"]["per_mote"] * used
        ev("refuel", {"lantern_id": l["id"], "amount": used, "fuel": self._fuel(l)})
        if was_weak and self._safe(l):
            self._push_out_shades(l)

    def _push_out_shades(self, l):
        for s in self.shades:
            if self.xz(s["pos"], l["pos"]) < self.T["safe_radius"]:
                s["eject"], s["ec"] = self.T["eject_ticks"], l["pos"]

    # ---- stage 6
    def _eject(self):
        r = self.T["safe_radius"]
        for s in self.shades:
            if s["eject"] > 0:
                c = s["ec"]
                dx, dz = s["pos"][0] - c[0], s["pos"][2] - c[2]
                d = math.hypot(dx, dz)
                ux, uz = unit(dx, dz)
                step = max(0.0, r - d) / s["eject"]
                s["pos"][0] += ux * step
                s["pos"][2] += uz * step
                s["eject"] -= 1

    # ---- stage 7
    def _pulse(self, ev):
        T = self.T
        self.carried -= T["pulse_cost"]
        self.pulse_cd = ticks(T["pulse_cooldown_s"])
        cx, cy, cz = self.pos[0], self.pos[1] + T["pulse_center_dy"], self.pos[2]
        hit = []
        for s in self.shades:
            dx, dz = s["pos"][0] - cx, s["pos"][2] - cz
            if math.sqrt(dx * dx + dz * dz + (s["pos"][1] - cy) ** 2) <= T["pulse_radius"]:
                self.score += T["score"]["stun_drain" if s["state"] == "drain" else "per_stun"]
                s["state"], s["left"], s["push"] = "stunned", T["pulse_stun_ticks"], T["pulse_push_ticks"]
                s["dir"] = unit(dx, dz)
                hit.append(s["id"])
        for d in self.drifters:
            if math.dist(d["pos"], (cx, cy, cz)) <= T["pulse_radius"]:
                if d["state"] == "chase":
                    d["state"], d["left"] = "flee", T["drifter_flee_ticks"]
                elif d["state"] == "flee" and d["stolen"] > 0:
                    for i in range(d["stolen"]):
                        self._add_mote([d["pos"][0] + 0.3 * i, self.terrain.height(d["pos"][0], d["pos"][2]) or 0.0, d["pos"][2]], "dropped", T["mote_drop_ttl_ticks"], None)
                    ev("drifter_drop", {"drifter_id": d["id"], "amount": d["stolen"]})
                    d["stolen"], d["left"] = 0, min(d["left"], T["drifter_drop_vanish_ticks"])
        ev("pulse", {"stunned_ids": hit})

    # ---- stage 8
    def _shade_move(self, s, dx, dz):
        """Move a shade by (dx, dz) if the target has ground; slide along axes; return True if moved."""
        x, z = s["pos"][0], s["pos"][2]
        ok = lambda a, b: self.terrain.height(a, b) is not None and not self.terrain.in_tower(a, b, 0.0)
        for ax, az in ((dx, dz), (dx, 0.0), (0.0, dz)):
            if (ax or az) and ok(x + ax, z + az):
                s["pos"][0], s["pos"][2] = x + ax, z + az
                return True
        return False

    def _move_shades(self):
        speed = self.T["shade_speed_night3"] if self.night == 3 else self.T["shade_speed"]
        lit = [l for l in self.lanterns if self._safe(l)]
        for s in self.shades:
            self._shade_ai(s, speed)
            if s["eject"] <= 0:
                self._keep_out_of_safe_zones(s, lit)
            h = self.terrain.height(s["pos"][0], s["pos"][2])
            if h is not None:
                s["pos"][1] = h

    def _shade_ai(self, s, speed):
        """One tick of shade behaviour by state. States: spawning -> wander <-> chase; recoil/stunned from hits and pulses."""
        T = self.T
        px, pz = self.pos[0] - s["pos"][0], self.pos[2] - s["pos"][2]
        d = math.hypot(px, pz)
        if s["state"] == "spawning":
            s["state"] = "chase" if d <= T["shade_detect_m"] else "wander"
        if s["state"] == "drain":
            self._drain_check(s, d)
        if s["eject"] > 0:          # being pushed out of a fresh safe zone (see _eject)
            return
        st = s["state"]
        if st == "drain":
            pass                    # stands still; the drain itself happens in stage 2
        elif st == "stunned":
            if s["push"] > 0:
                k = T["pulse_push_m"] / T["pulse_push_ticks"]
                s["push"] = s["push"] - 1 if self._shade_move(s, s["dir"][0] * k, s["dir"][1] * k) else 0
        elif st == "recoil":
            k = T["recoil_m"] / T["recoil_ticks"]
            self._shade_move(s, s["dir"][0] * k, s["dir"][1] * k)
            s["left"] -= 1
            if s["left"] <= 0:
                s["state"] = "chase"
        else:
            if st == "wander" and d <= T["shade_detect_m"]:
                st = s["state"] = "chase"
            elif st == "chase" and d > T["shade_lose_m"]:
                st = s["state"] = "wander"
            if st == "chase" and d > 1e-9:
                k = min(speed * DT, d)
                self._shade_move(s, px / d * k, pz / d * k)
            elif st == "wander" and self._seek_lantern(s):
                pass
            elif st == "wander":
                if s["turn"] <= 0:
                    a = self.rnd() * math.tau
                    s["dir"], s["turn"] = (math.cos(a), math.sin(a)), T["shade_wander_turn_ticks"]
                s["turn"] -= 1
                k = T["shade_wander_speed"] * DT
                if not self._shade_move(s, s["dir"][0] * k, s["dir"][1] * k):
                    s["turn"] = 0

    def _drain_check(self, s, d):
        """Drain exits: lantern out or refuelled to >= threshold or shade > 2 m away -> wander; player within 6 m -> chase."""
        T, l = self.T, self._lantern(s["target"])
        if l is None or not l["lit"] or self._safe(l) or self.xz(s["pos"], l["pos"]) > T["drain_reach_m"]:
            s["state"], s["target"], s["drain_t"] = "wander", None, 0
        elif d <= T["drain_detect_m"]:
            s["state"], s["drain_t"] = "chase", 0

    def _seek_lantern(self, s):
        """Wander goal: nearest lit lantern with fuel < threshold (ties: smaller id), else the nearest unlit one. Starts draining within reach."""
        T, w = self.T, self.lanterns
        weak = [l for l in w if l["lit"] and not self._safe(l)]
        pool = weak or [l for l in w if not l["lit"]]
        if not pool:
            return False
        l = min(pool, key=lambda q: (self.xz(q["pos"], s["pos"]), q["id"]))
        d = self.xz(l["pos"], s["pos"])
        if weak and d <= T["drain_reach_m"]:
            s["state"], s["target"], s["drain_t"] = "drain", l["id"], 0
        elif d > T["drain_reach_m"]:
            k = T["shade_wander_speed"] * DT
            self._shade_move(s, (l["pos"][0] - s["pos"][0]) / d * k, (l["pos"][2] - s["pos"][2]) / d * k)
        return True

    def _keep_out_of_safe_zones(self, s, lit):
        r = self.T["safe_radius"]
        for l in lit:
            dx, dz = s["pos"][0] - l["pos"][0], s["pos"][2] - l["pos"][2]
            if math.hypot(dx, dz) < r:
                ux, uz = unit(dx, dz)
                s["pos"][0], s["pos"][2] = l["pos"][0] + ux * r, l["pos"][2] + uz * r

    def _move_drifters(self):
        T = self.T
        keep = []
        for d in self.drifters:
            dx, dy, dz = self.pos[0] - d["pos"][0], self.pos[1] - d["pos"][1], self.pos[2] - d["pos"][2]
            dxz = math.hypot(dx, dz)
            near = self.carried >= T["drifter_need_carried"] and dxz <= T["drifter_chase_m"]
            if d["state"] == "idle" and near:
                d["state"] = "chase"
            elif d["state"] == "chase" and not near:
                d["state"] = "idle"
            k = T["drifter_speed"] * DT
            if d["state"] == "chase":
                n3 = math.sqrt(dx * dx + dy * dy + dz * dz) or 1.0
                step = min(k, n3)
                d["pos"][0] += dx / n3 * step; d["pos"][1] += dy / n3 * step; d["pos"][2] += dz / n3 * step
            elif d["state"] == "flee":
                if dxz > 1e-9:
                    d["pos"][0] -= dx / dxz * k
                    d["pos"][2] -= dz / dxz * k
                else:
                    d["pos"][0] += k
                d["left"] -= 1
                if d["left"] <= 0:
                    continue   # removed, taking what it stole
            else:
                if d["turn"] <= 0:
                    a = self.rnd() * math.tau
                    d["dir"], d["turn"] = (math.cos(a), math.sin(a)), T["shade_wander_turn_ticks"]
                d["turn"] -= 1
                if self.terrain.height(d["pos"][0], d["pos"][2]) is None:   # drifted over the sea: turn back to the island
                    cx, cz = self.M["center"][0] - d["pos"][0], self.M["center"][1] - d["pos"][2]
                    cn = math.hypot(cx, cz) or 1.0
                    d["dir"] = (cx / cn, cz / cn)
                d["pos"][0] += d["dir"][0] * T["drifter_idle_speed"] * DT
                d["pos"][2] += d["dir"][1] * T["drifter_idle_speed"] * DT
            keep.append(d)
        self.drifters = keep

    # ---- stage 9
    def _contact(self, ev):
        T = self.T
        for d in self.drifters:
            if d["state"] == "chase" and d["stolen"] == 0 and self.carried > 0 and self.xz(d["pos"], self.pos) <= T["drifter_steal_radius"]:
                amt = min(T["drifter_steal"], self.carried)
                self.carried -= amt
                d["stolen"], d["state"], d["left"] = amt, "flee", T["drifter_flee_ticks"]
                ev("drifter_steal", {"drifter_id": d["id"], "amount": amt, "carried": self.carried})
        if self.invuln > 0:
            return
        for s in self.shades:
            if s["state"] in ("chase", "wander") and s["eject"] <= 0 and self.xz(s["pos"], self.pos) <= T["shade_hit_radius"] \
                    and abs(s["pos"][1] - self.pos[1]) <= T["shade_hit_dy"]:
                n = int(self.carried * T["hit_drop_ratio"])
                self.carried -= n
                for i in range(n):
                    a = (i + self.rnd() * 0.8) / max(n, 1) * math.tau
                    r = T["drop_ring_min"] + self.rnd() * (T["drop_ring_max"] - T["drop_ring_min"])
                    x, z = self.pos[0] + r * math.cos(a), self.pos[2] + r * math.sin(a)
                    h = self.terrain.height(x, z)
                    self._add_mote([x, self.pos[1] if h is None else h, z], "dropped", T["mote_drop_ttl_ticks"], None)
                self.flames -= 1
                self.invuln = T["invuln_ticks"]
                s["state"], s["left"] = "recoil", T["recoil_ticks"]
                s["dir"] = unit(s["pos"][0] - self.pos[0], s["pos"][2] - self.pos[2])
                ev("player_hit", {"by": "shade", "flames": self.flames, "dropped": n})
                break

    # ---- stage 10
    def _spawns(self, ev):
        T, M, t = self.T, self.M, self.sim_tick
        if self.random_motes and t % T["mote_spawn_every_ticks"] == 0 and len(self.motes) < T["mote_max"]:
            used = {m["idx"] for m in self.motes}
            free = [i for i in range(len(self.mote_pts)) if i not in used]
            if free:
                i = free[int(self.rnd() * len(free))]
                self._add_mote(list(self.mote_pts[i]), "random", None, i)
        if self.random_shades:
            first = T["shade_first_tick"]
            count = T["shade_first_count"] if t == first else 1 if t > first and (t - first) % M["shade_every_ticks"] == 0 else 0
            for _ in range(count):
                if len(self.shades) >= M["shade_max"]:
                    break
                valid = [p for p in self.shade_pts if self.xz(p, self.pos) >= T["shade_spawn_min_dist"]
                         and all(self.xz(p, s["pos"]) > 1.0 for s in self.shades)]
                if not valid:
                    break
                s = self._new_shade(None, list(valid[int(self.rnd() * len(valid))]), "spawning")
                self.shades.append(s)
                ev("shade_spawned", {"id": s["id"]})
        if self.random_drifters and t % T["drifter_every_ticks"] == 0 and len(self.drifters) < T["drifter_max"]:
            p = self.shade_pts[int(self.rnd() * len(self.shade_pts))]
            self.drifters.append(self._new_drifter(None, [p[0], p[1] + 1.0, p[2]], "idle", 0, 0))

    def _end(self, ev, result, reason):
        if result == "won":
            sc = self.T["score"]
            self.score += sum(sc["dawn_lantern"] + int(l["fuel"] // FUEL_UNIT) for l in self.lanterns if l["lit"]) + sc["dawn_flame"] * self.flames
        self.state = result
        ev("game_over", {"result": result, "reason": reason})

    # ---- output
    def snapshot(self):
        T = self.T
        state = "paused" if self.paused and self.state == "playing" else self.state
        w = self.wind
        return {"type": "snapshot", "tick": self.tick, "sim_tick": self.sim_tick, "state": state, "night": self.night,
                "time_left_s": r3(self.left_ticks() / 60), "score": self.score,
                "wind": {"active": w["active"], "dir_deg": w["dir"], "warning": w["warn"]},
                "player": {"pos": [r3(v) for v in self.pos], "vel": [r3(self.vx), r3(self.vy), r3(self.vz)],
                           "flames": self.flames, "carried": self.carried, "capacity": self.capacity(), "grounded": self.grounded, "invuln": self.invuln > 0,
                           "dash_cd_s": r3(self.dash_cd / 60), "pulse_cd_s": r3(self.pulse_cd / 60), "charm_s": r3(self.charm / 60),
                           "facing": [r3(self.face[0]), r3(self.face[1])]},
                "lanterns": [{"id": l["id"], "pos": [r3(v) for v in l["pos"]], "lit": l["lit"], "deposited": l["deposited"],
                               "fuel": self._fuel(l), "ever_lit": l["ever_lit"], "relit_count": l["relit"]} for l in self.lanterns],
                "shades": [{"id": s["id"], "pos": [r3(v) for v in s["pos"]], "state": s["state"], "state_ticks_left": s["left"], "target_lantern_id": s["target"]} for s in self.shades],
                "motes_active": len(self.motes),
                "motes": [{"id": m["id"], "pos": [r3(v) for v in m["pos"]], "kind": m["kind"],
                           "ttl_s": None if m["ttl"] is None else r3(m["ttl"] / 60)} for m in self.motes],
                "drifters": [{"id": d["id"], "pos": [r3(v) for v in d["pos"]], "state": d["state"], "stolen": d["stolen"]} for d in self.drifters],
                "charms": [{"id": c["id"], "pos": [r3(v) for v in c["pos"]], "available": c["available"], "respawn_s": r3(c["respawn"] / 60)} for c in self.charms]}
