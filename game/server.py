"""Play locally: python3 -m game.server  ->  http://localhost:8000  (sim runs here, browser only draws)."""
import json, os, random, sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from .sim import Sim

WEB = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "web")
sim = Sim(random.randrange(1 << 30))


class H(BaseHTTPRequestHandler):
    def log_message(self, *a): pass

    def send(self, body, ctype="application/json"):
        self.send_response(200); self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body))); self.end_headers(); self.wfile.write(body)

    def do_GET(self):
        with open(os.path.join(WEB, "index.html"), "rb") as f:
            self.send(f.read(), "text/html; charset=utf-8")

    def do_POST(self):
        global sim
        body = json.loads(self.rfile.read(int(self.headers.get("Content-Length", 0))) or b"{}")
        if self.path == "/reset":
            sim = Sim(random.randrange(1 << 30))
            ev = []
        else:   # /step: {inputs, steps}
            sim.set_inputs(body.get("inputs", {}))
            ev = [{"name": n, "data": d} for _ in range(min(int(body.get("steps", 1)), 10)) for n, d in sim.step()]
        self.send(json.dumps({"snap": sim.snapshot(), "events": ev}).encode())


if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8000
    print(f"Open http://localhost:{port}")
    ThreadingHTTPServer(("127.0.0.1", port), H).serve_forever()
