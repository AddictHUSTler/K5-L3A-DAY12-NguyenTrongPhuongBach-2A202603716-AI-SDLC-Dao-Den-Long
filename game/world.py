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
        self.discs = [(d["c"][0], d["c"][1], d["r"], d["y"]) for d in map_data["discs"]]
        self.rects = [(r["x0"], r["x1"], r["z0"], r["z1"], r["y"]) for r in map_data.get("rects", [])]
        self.rings = [(r["r0"], r["r1"], r["y"]) for r in map_data.get("half_rings", [])]
        self.ramps = [(math.cos(math.radians(r["deg"])), math.sin(math.radians(r["deg"])), r["r0"], r["r1"], r["w"], r["y0"], r["y1"]) for r in map_data.get("ramps", [])]

    def height(self, x, z):
        """Ground height at (x, z), or None over the cloud sea. The highest matching surface wins."""
        h = None
        for cx, cz, r, y in self.discs:
            if math.hypot(x - cx, z - cz) <= r and (h is None or y > h):
                h = y
        for x0, x1, z0, z1, y in self.rects:
            if x0 <= x <= x1 and z0 <= z <= z1 and (h is None or y > h):
                h = y
        if self.rings and z > 0:
            d = math.hypot(x, z)
            for r0, r1, y in self.rings:
                if r0 <= d <= r1 and (h is None or y > h):
                    h = y
        for c, sn, r0, r1, w, y0, y1 in self.ramps:
            s, lat = x * c + z * sn, -x * sn + z * c
            if r0 <= s <= r1 and abs(lat) <= w / 2:
                y = y0 + (y1 - y0) * (s - r0) / (r1 - r0)
                if h is None or y > h:
                    h = y
        return h

    def in_tower(self, x, z, y):
        t = self.M.get("tower")
        return bool(t) and math.hypot(x, z) <= t["r"] and y < t["y"] + t["h"]

    def walk_ok(self, x, z, feet):
        if self.in_tower(x, z, feet):
            return False
        h = self.height(x, z)
        return h is None or h <= feet + self.step_up
