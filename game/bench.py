"""Benchmark: python3 -m game.bench --seed 42 --duration 30 --out bench.json  (Ticket-04 section 1).
Opens the real browser game on the fixed bench scene, measures frame times, writes bench.json.
Needs Chrome/Chromium (or Edge/Brave) installed; override with env DDL_BROWSER=/path/to/browser."""
import argparse, json, math, os, platform, shutil, subprocess, sys, tempfile, threading, time
from http.server import ThreadingHTTPServer
from . import server
from .sim import load_tuning, mulberry32

BROWSERS = ("google-chrome", "google-chrome-stable", "chromium", "chromium-browser", "chrome", "brave-browser", "brave-origin-stable", "brave-origin", "microsoft-edge")
WARMUP_S = 3
MAC = ("/Applications/Google Chrome.app/Contents/MacOS/Google Chrome", "/Applications/Chromium.app/Contents/MacOS/Chromium")


def scene(seed):
    """Night 1, 200 Shades (wander) and 100 motes spread evenly over the island, L1-L3 lit at fuel 100. Seed only rotates the pattern."""
    rot = mulberry32(seed)() * math.tau
    def spread(n, r):   # sunflower spiral: even coverage of the disc, no rng needed
        return [[round(r * math.sqrt((i + .5) / n) * math.cos(i * 2.39996 + rot), 3), 0.0, round(r * math.sqrt((i + .5) / n) * math.sin(i * 2.39996 + rot), 3)] for i in range(n)]
    return {"time_left_s": 100000, "random_motes": False, "random_shades": False, "random_drifters": False, "wind_enabled": False,
            "motes": spread(100, 38), "shades": [{"pos": p, "state": "wander"} for p in spread(200, 38)],
            "lanterns": [{"id": f"L{i}", "lit": True, "fuel": 100} for i in (1, 2, 3)]}


def tuning():
    """No damage, no pickups, no fuel loss/drain, no chasing: Shades only wander. The Night cannot end (100000 s)."""
    return dict(load_tuning(), shade_hit_radius=0, shade_detect_m=0, pickup_radius=0, fuel_decay_per_s=0, drain_per_s=0)


def proc_rss_mb(root_pid):
    """Sum of RSS of root_pid and all its descendants (Linux /proc)."""
    kids, total = {}, 0
    try:
        for p in os.listdir("/proc"):
            if p.isdigit():
                with open(f"/proc/{p}/stat") as f:
                    kids.setdefault(int(f.read().rsplit(")", 1)[1].split()[1]), []).append(int(p))
    except OSError:
        return None
    todo = [root_pid]
    while todo:
        pid = todo.pop()
        todo += kids.get(pid, [])
        try:
            with open(f"/proc/{pid}/statm") as f:
                total += int(f.read().split()[1]) * 4096
        except OSError:
            pass
    return total / 1048576


def stats(dts, load_ms, peak, renderer):
    n, s = len(dts), sorted(dts)
    k = max(1, math.ceil(.01 * n))
    return {"contract_version": "1.3", "avg_fps": round(1000 * n / sum(dts), 1), "p1_low_fps": round(1000 / (sum(s[-k:]) / k), 1),
            "frame_ms_p95": round(s[min(n - 1, math.ceil(.95 * n) - 1)], 2), "frames": n, "load_ms": round(load_ms),
            "peak_mem_mb": None if peak is None else round(peak), "vsync_off": True, "renderer": renderer,
            "os": f"{platform.system()} {platform.release()} {platform.machine()}"}


def find_browser():
    env = os.environ.get("DDL_BROWSER")
    return env or next((p for p in (*(shutil.which(b) for b in BROWSERS), *MAC) if p and os.path.exists(p)), None)


def main(argv=None):
    t0 = time.time()
    ap = argparse.ArgumentParser()
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--duration", type=float, default=30)
    ap.add_argument("--out", required=True)
    a = ap.parse_args(argv)
    browser = find_browser()
    if not browser:
        print("error: no Chrome/Chromium found; install one or set DDL_BROWSER", file=sys.stderr)
        return 2
    server.BENCH = {"seed": a.seed, "duration": a.duration, "warmup": WARMUP_S, "result": None, "done": threading.Event()}
    httpd = ThreadingHTTPServer(("127.0.0.1", 0), server.H)
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    url = f"http://127.0.0.1:{httpd.server_port}/?bench=1"
    with tempfile.TemporaryDirectory() as prof:
        # --disable-gpu-vsync + --disable-frame-rate-limit: uncapped frames; fixed 1280x720 window, not fullscreen
        proc = subprocess.Popen([browser, f"--user-data-dir={prof}", "--no-first-run", "--no-default-browser-check", "--window-size=1280,720",
                                 "--window-position=0,0", "--disable-gpu-vsync", "--disable-frame-rate-limit", f"--app={url}"],
                                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        peak, t_end = 0.0, time.time() + WARMUP_S + a.duration + 60
        while not server.BENCH["done"].wait(.25) and time.time() < t_end and proc.poll() is None:
            if server.BENCH.get("measuring"):   # peak RSS only inside the measured window
                peak = max(peak, proc_rss_mb(proc.pid) or 0)
        proc.terminate()
        try:
            proc.wait(10)
        except subprocess.TimeoutExpired:
            proc.kill()
    r = server.BENCH["result"]
    if not r:
        print("error: browser did not report a result", file=sys.stderr)
        return 1
    ver = subprocess.run([browser, "--version"], capture_output=True, text=True).stdout.strip()
    res = stats(r["dts"], r["first_frame_ms"] - t0 * 1000, peak or None, f"{r['gpu']} via three.js r160 WebGL; {ver}")
    with open(a.out, "w") as f:
        json.dump(res, f, indent=1)
    print(json.dumps(res))
    return 0


if __name__ == "__main__":
    sys.exit(main())
