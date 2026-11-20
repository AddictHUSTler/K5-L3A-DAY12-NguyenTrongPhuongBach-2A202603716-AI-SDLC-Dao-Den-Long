"""Map geometry: ground height, walls, tower, spawn rings. Pure functions of the map data in game.contract.json."""
import math


def ring_points(rings):
    out = []
    for g in rings:
        for i in range(g["n"]):
            a = math.radians(g["start"] + g["step"] * i)
            out.append([g["c"][0] + g["r"] * math.cos(a), float(g["y"]), g["c"][1] + g["r"] * math.sin(a)])
    return out


def unit(dx, dz, default=(1.0, 0.0)):
    """Unit vector of (dx, dz); `default` when the length is ~0."""
    d = math.hypot(dx, dz)
    return (dx / d, dz / d) if d > 1e-9 else default


class Terrain:
    def __init__(self, map_data, step_up):
        self.M, self.step_up = map_data, step_up

    def height(self, x, z):
        """Ground height at (x, z), or None over the cloud sea."""
        M, h = self.M, None
        def up(v):
            nonlocal h
            h = v if h is None else max(h, v)
        for d in M["discs"]:
            if math.hypot(x - d["c"][0], z - d["c"][1]) <= d["r"]:
                up(d["y"])
        for r in M.get("rects", []):
            if r["x0"] <= x <= r["x1"] and r["z0"] <= z <= r["z1"]:
                up(r["y"])
        for r in M.get("half_rings", []):
            if z > 0 and r["r0"] <= math.hypot(x, z) <= r["r1"]:
                up(r["y"])
        for r in M.get("ramps", []):
            a = math.radians(r["deg"])
            s, lat = x * math.cos(a) + z * math.sin(a), -x * math.sin(a) + z * math.cos(a)
            if r["r0"] <= s <= r["r1"] and abs(lat) <= r["w"] / 2:
                up(r["y0"] + (r["y1"] - r["y0"]) * (s - r["r0"]) / (r["r1"] - r["r0"]))
        return h

    def in_tower(self, x, z, y):
        t = self.M.get("tower")
        return bool(t) and math.hypot(x, z) <= t["r"] and y < t["y"] + t["h"]

    def walk_ok(self, x, z, feet):
        if self.in_tower(x, z, feet):
            return False
        h = self.height(x, z)
        return h is None or h <= feet + self.step_up
