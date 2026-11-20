"""Play locally: python3 -m game.server  ->  http://localhost:8000  (sim runs here, browser only draws)."""
import json, os, random, sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from .sim import Sim, load_tuning

WEB = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "web")
sim = Sim(random.randrange(1 << 30))


EASY_S = {1: 150, 2: 170, 3: 190}   # browser-only assist: shorter night, 5 flames, weaker drain, faster motes, later first Shade. Headless/contract numbers are untouched.


def new(night, easy=False):
    night = night if night in (1, 2, 3) else 1
    if not easy:
        return Sim(random.randrange(1 << 30), night=night)
    T = dict(load_tuning(), flames=5, drain_per_s=2, mote_spawn_every_ticks=120, shade_first_tick=900)
    return Sim(random.randrange(1 << 30), {"time_left_s": EASY_S[night]}, tuning=T, night=night)


class H(BaseHTTPRequestHandler):
    def log_message(self, *a): pass

    def send(self, body, ctype="application/json"):
        self.send_response(200); self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body))); self.end_headers(); self.wfile.write(body)

    TYPES = {".html": "text/html; charset=utf-8", ".js": "text/javascript", ".css": "text/css"}

    def do_GET(self):
        name = "index.html" if self.path == "/" else self.path.lstrip("/")
        path = os.path.join(WEB, os.path.basename(name))   # flat folder: basename blocks path tricks
        ext = os.path.splitext(path)[1]
        if ext not in self.TYPES or not os.path.isfile(path):
            self.send_error(404)
            return
        with open(path, "rb") as f:
            self.send(f.read(), self.TYPES[ext])

    def do_POST(self):
        global sim
        body = json.loads(self.rfile.read(int(self.headers.get("Content-Length", 0))) or b"{}")
        if self.path == "/reset":
            sim = new(int(body.get("night", 1)), bool(body.get("easy")))
            return self.send(json.dumps({"snap": sim.snapshot(), "events": [], "layout": sim.layout()}).encode())
        # /step: {inputs, steps}
        sim.set_inputs(body.get("inputs", {}))
        ev = [{"name": n, "data": d} for _ in range(min(int(body.get("steps", 1)), 10)) for n, d in sim.step()]
        self.send(json.dumps({"snap": sim.snapshot(), "events": ev}).encode())


if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8000
    print(f"Open http://localhost:{port}")
    ThreadingHTTPServer(("127.0.0.1", port), H).serve_forever()
