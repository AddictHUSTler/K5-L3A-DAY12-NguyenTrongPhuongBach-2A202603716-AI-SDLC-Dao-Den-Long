"""Play locally: python3 -m game.server  ->  http://localhost:8000  (sim runs here, browser only draws)."""
import argparse, json, os, random, sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from . import leaderboard
from .sim import Sim, load_tuning

WEB = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "web")
sim = Sim(random.randrange(1 << 30))
seed = 0
BENCH = None   # set by game.bench: {"seed", "duration", "warmup", "result", "done"}


# Browser play is tuned easier and faster than the contract numbers (headless/contract are untouched).
PLAY_S = {1: 150, 2: 170, 3: 190}
PLAY_T = dict(load_tuning(), flames=5, drain_per_s=2, fuel_decay_per_s=0, mote_spawn_every_ticks=120, shade_first_tick=900)


def new(night):
    global seed
    night = night if night in (1, 2, 3) else 1
    seed = random.randrange(1 << 30)
    return Sim(seed, {"time_left_s": PLAY_S[night]}, tuning=PLAY_T, night=night)


class H(BaseHTTPRequestHandler):
    def log_message(self, *a): pass

    def send(self, body, ctype="application/json"):
        self.send_response(200); self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body))); self.end_headers(); self.wfile.write(body)

    TYPES = {".html": "text/html; charset=utf-8", ".js": "text/javascript", ".css": "text/css"}

    def do_GET(self):
        url = self.path.split("?")[0]
        if url == "/leaderboard":
            return self.send(json.dumps({"entries": leaderboard.load()}).encode())
        if url == "/bench":
            return self.send(json.dumps({k: BENCH[k] for k in ("seed", "duration", "warmup")} if BENCH else None).encode())
        path = os.path.join(WEB, os.path.basename("index.html" if url == "/" else url))   # flat folder: basename blocks path tricks
        ext = os.path.splitext(path)[1]
        if ext not in self.TYPES or not os.path.isfile(path):
            return self.send_error(404)
        with open(path, "rb") as f:
            self.send(f.read(), self.TYPES[ext])

    def do_POST(self):
        global sim
        body = json.loads(self.rfile.read(int(self.headers.get("Content-Length", 0))) or b"{}")
        if self.path == "/score":
            try:
                return self.send(json.dumps({"entries": leaderboard.add(body.get("name"), body.get("score"), body.get("nights_won"), seed)}).encode())
            except ValueError as e:
                return self.send(json.dumps({"error": str(e)}).encode())
        if BENCH and self.path == "/bench-reset":
            from .bench import scene, tuning
            sim = Sim(BENCH["seed"], scene(BENCH["seed"]), tuning=tuning(), night=1)
            return self.send(json.dumps({"snap": sim.snapshot(), "layout": sim.layout()}).encode())
        if BENCH and self.path == "/bench-measuring":
            BENCH["measuring"] = bool(body.get("on"))
            return self.send(b"{}")
        if BENCH and self.path == "/bench-result":
            BENCH["result"] = body
            BENCH["done"].set()
            return self.send(b"{}")
        if self.path == "/reset":
            sim = new(int(body.get("night", 1)))
            return self.send(json.dumps({"snap": sim.snapshot(), "events": [], "layout": sim.layout()}).encode())
        # /step: {inputs, steps}
        sim.set_inputs(body.get("inputs", {}))
        ev = [{"name": n, "data": d} for _ in range(min(int(body.get("steps", 1)), 10)) for n, d in sim.step()]
        self.send(json.dumps({"snap": sim.snapshot(), "events": ev}).encode())


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("port", type=int, nargs="?", default=8000)
    ap.add_argument("--export-leaderboard", metavar="OUT.json")
    a = ap.parse_args()
    if a.export_leaderboard:
        leaderboard.export(a.export_leaderboard)
        sys.exit(0)
    port = a.port
    print(f"Open http://localhost:{port}")
    ThreadingHTTPServer(("127.0.0.1", port), H).serve_forever()
