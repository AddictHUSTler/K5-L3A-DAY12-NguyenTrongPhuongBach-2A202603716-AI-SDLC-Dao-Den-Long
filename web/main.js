import * as THREE from "three";
import {cfg, save, chime, SFX, sfxEnd, music, resumeAudio, ACTIONS, DEFAULT_KEYS} from "./audio.js";
const C = {sky:0x0E1430, fog:0x1B2350, grass:0x2F5D50, sand:0xC9B48A, wood:0x6B4A2F, sea:0x12384A, lamp:0xFFB347, core:0xFFE9B0, off:0x5B5F6E,
  mote:0xFFF6C2, halo:0xFFE58A, shade:0x120A1A, rim:0x7A3CFF, stun:0x3A3450, shirt:0xE8E2D0, scarf:0xC8102E, gold:0xF2C14E, drifter:0x8FA3B8};
const NIGHTS = [null, {name:"Đảo Bến", say:"Ông Đăng: «Giữ ít nhất 3 trong 5 ngọn đèn sáng tới bình minh, cháu nhé. Đèn cạn dầu thì châm thêm.»"},
  {name:"Đảo Cau", say:"Ông Đăng: «Cầu tre không lan can. Dùng bục nhảy mà sang đảo kia. Giữ 4 trong 6 đèn sáng.»"},
  {name:"Đảo Chuông", say:"Ông Đăng: «Gió mạnh lắm. Lên tháp chuông, giữ 5 trong 7 đèn sáng tới sáng.»"}];
// ---- scene
const scene = new THREE.Scene(); scene.background = new THREE.Color(C.sky); scene.fog = new THREE.FogExp2(C.fog, 0.012);
const cam = new THREE.PerspectiveCamera(55, innerWidth/innerHeight, .1, 500);
const R = new THREE.WebGLRenderer({antialias:true}); R.setPixelRatio(Math.min(devicePixelRatio, 1.5)); R.setSize(innerWidth, innerHeight); document.body.prepend(R.domElement);
scene.add(new THREE.HemisphereLight(0x8aa4e0, 0x203020, .7));
const amb = new THREE.AmbientLight(0xffffff, .15); scene.add(amb);
const M = (c, o = {}) => new THREE.MeshStandardMaterial({color:c, ...o}), mesh = (g, m) => new THREE.Mesh(g, m);
const world = new THREE.Group(); scene.add(world);
const sea = mesh(new THREE.PlaneGeometry(600, 600), M(C.sea)); sea.rotation.x = -Math.PI/2; sea.position.y = -8; scene.add(sea);
const player = new THREE.Group();
player.add(mesh(new THREE.CylinderGeometry(.4,.4,1.4,12), M(C.shirt)).translateY(.7));
const scarf = mesh(new THREE.TorusGeometry(.42,.1,6,16), M(C.scarf)); scarf.rotation.x = Math.PI/2; scarf.position.y = 1.4; player.add(scarf);
player.add(mesh(new THREE.ConeGeometry(.9,.6,16), M(C.gold)).translateY(1.9));
const hl = new THREE.PointLight(C.lamp, 40, 14); hl.position.y = 1.2; player.add(hl); scene.add(player);
const leaves = Array.from({length:14}, () => { const l = mesh(new THREE.PlaneGeometry(.5,.3), new THREE.MeshBasicMaterial({color:0x7bb274, side:THREE.DoubleSide})); l.visible = false; scene.add(l); return l; });
let layout, pads = [];
function build(L) {
  world.clear(); layout = L;
  const cyl = (c, r, y0, y1, col) => world.add(mesh(new THREE.CylinderGeometry(r, r, y1 - y0, 48), M(col)).translateX(c[0]).translateZ(c[1]).translateY((y0 + y1) / 2));
  L.discs.forEach(d => cyl(d.c, d.r, d.y - 3, d.y, C.grass));
  (L.rects || []).forEach(r => world.add(mesh(new THREE.BoxGeometry(r.x1 - r.x0, .4, r.z1 - r.z0), M(C.wood)).translateX((r.x0 + r.x1) / 2).translateZ((r.z0 + r.z1) / 2).translateY(-.2)));
  (L.half_rings || []).forEach(h => { const s = new THREE.Shape(); s.absarc(0,0,h.r1,Math.PI,2*Math.PI,false); s.absarc(0,0,h.r0,2*Math.PI,Math.PI,true);
    const g = new THREE.ExtrudeGeometry(s, {depth:h.y + 2, bevelEnabled:false, curveSegments:32}); g.rotateX(-Math.PI/2); world.add(mesh(g, M(C.grass)).translateY(-2)); });
  (L.ramps || []).forEach(r => { const a = r.deg * Math.PI / 180, len = r.r1 - r.r0, g = new THREE.Group(), b = mesh(new THREE.BoxGeometry(len / Math.cos(Math.atan2(r.y1 - r.y0, len)), .3, r.w), M(C.sand));
    b.rotation.z = Math.atan2(r.y1 - r.y0, len); b.position.y = -.15; g.add(b); const m = (r.r0 + r.r1) / 2; g.position.set(m * Math.cos(a), (r.y0 + r.y1) / 2, m * Math.sin(a)); g.rotation.y = -a; world.add(g); });
  if (L.tower) world.add(mesh(new THREE.CylinderGeometry(L.tower.r, L.tower.r, L.tower.h, 16), M(C.wood)).translateY(L.tower.y + L.tower.h / 2));
  L.pads.forEach(p => world.add(mesh(new THREE.CylinderGeometry(p.r, p.r, .15, 24), M(C.gold, {emissive:C.gold, emissiveIntensity:.5})).translateX(p.pos[0]).translateZ(p.pos[2]).translateY(p.pos[1] + .08)));
}
const pools = {l:{}, d:{}, c:{}};
function sync(pool, items, make, dy = 0) {
  const ids = new Set(items.map(i => i.id));
  for (const id in pool) if (!ids.has(id)) { scene.remove(pool[id]); delete pool[id]; }
  for (const it of items) { if (!pool[it.id]) { pool[it.id] = make(it); scene.add(pool[it.id]); } pool[it.id].position.set(it.pos[0], it.pos[1] + dy, it.pos[2]); }
}
const moteGeo = new THREE.SphereGeometry(.22,8,8), haloGeo = new THREE.SphereGeometry(.5,8,8), shadeGeo = new THREE.SphereGeometry(.9,12,12);
const moteMat = new THREE.MeshBasicMaterial({color:C.mote}), haloMat = new THREE.MeshBasicMaterial({color:C.halo, transparent:true, opacity:.25});   // shared: no per-mote materials
// Motes and Shades are instanced: a few draw calls instead of one or two per entity
const dummy = new THREE.Object3D(), inst = (geo, mat) => { const m = new THREE.InstancedMesh(geo, mat, 256); m.count = 0; m.frustumCulled = false; scene.add(m); return m; };
function place(im, list, dy, scale = () => 1) {
  const n = Math.min(list.length, 256);
  for (let i = 0; i < n; i++) { const it = list[i]; dummy.position.set(it.pos[0], it.pos[1] + dy, it.pos[2]); dummy.scale.setScalar(scale(it)); dummy.updateMatrix(); im.setMatrixAt(i, dummy.matrix); }
  im.count = n; im.instanceMatrix.needsUpdate = true;
}
const shadeMat = M(C.shade, {emissive:cfg.cb ? 0x00B3FF : C.rim, emissiveIntensity:.5}), stunMat = M(C.stun);   // shared by all Shades
const moteIM = inst(moteGeo, moteMat), haloIM = inst(haloGeo, haloMat), shadeIM = inst(shadeGeo, shadeMat), stunIM = inst(shadeGeo, stunMat);
const mkLamp = () => { const g = new THREE.Group(); g.add(mesh(new THREE.CylinderGeometry(.2,.2,3,8), M(C.wood)).translateY(1.5));
  const b = mesh(new THREE.SphereGeometry(.7,12,12), M(C.off)); b.position.y = 3.2; b.name = "bulb"; g.add(b); const pl = new THREE.PointLight(C.lamp, 0, 30); pl.position.y = 3.2; pl.name = "pl"; g.add(pl);
  const tear = mesh(new THREE.BoxGeometry(.5, .08, .1), M(0x222222)); tear.position.set(0, 3.3, .66); tear.rotation.z = .5; tear.name = "tear"; g.add(tear);   // paper tear on a dark lantern
  const fb = mesh(new THREE.BoxGeometry(1.4, .12, .12), new THREE.MeshBasicMaterial({color:C.halo})); fb.position.y = 4.3; fb.name = "fuel"; g.add(fb); return g; };
const mkDrifter = () => mesh(new THREE.BoxGeometry(.2, .1, 2.2), new THREE.MeshBasicMaterial({color:C.drifter}));
const mkCharm = () => { const g = new THREE.Group(); g.add(mesh(new THREE.BoxGeometry(.7,.05,1), M(C.gold))); g.add(mesh(new THREE.BoxGeometry(.55,.08,.85), M(C.scarf))); return g; };
// ---- state
const $ = id => document.getElementById(id);
const keys = {}; let yaw = 0, last = performance.now(), mode = "menu", night = 1, total = 0, snap = null, busy = false, jumpPrev = false, lastSec = 99, flash = 0;
const shown = {}, put = (id, html) => { if (shown[id] !== html) { shown[id] = html; $(id).innerHTML = html; } };   // skip identical DOM writes
const post = (p, b) => fetch(p, {method:"POST", body:JSON.stringify(b)}).then(r => r.json());
async function send(inputs, steps) { const r = await post("/step", {inputs, steps}); r.events.forEach(e => handle(e)); draw(r.snap); return r.snap; }
function handle(e) {
  if (e.name === "lantern_lit") chime(snap.lanterns.filter(l => l.lit).length);   // snap is pre-event: count is one behind, so this is the n-th lit lantern's index
  else if (e.name === "game_over") { sfxEnd(e.data.result); } else { SFX[e.name]?.(); if (e.name === "shade_spawned") { cue.id = e.data.id; cue.until = performance.now() + 5000; } }
}
function overlay(html) { $("ovc").innerHTML = html; $("ov").style.display = html ? "grid" : "none"; }
const btn = (label, fn) => { const b = document.createElement("button"); b.textContent = label; b.onclick = fn; return b; };
function show(html, buttons = []) { overlay(html); buttons.forEach(b => $("ovc").append(btn(...b))); }
function menu() { mode = "menu"; music.on = false; total = 0; show("<h1>Đảo Đèn Lồng</h1><p>Ba Đêm, ba hòn đảo.</p>", [["Bắt đầu", () => intro(1)], ["Bảng xếp hạng", () => board(menu)], ["Cài đặt", () => settings(menu)]]); }
function intro(n) { night = n; mode = "intro"; show(`<h1>Đêm ${n}: ${NIGHTS[n].name}</h1><p>${NIGHTS[n].say}</p>`, [["Vào đêm", () => start(n)]]); }
async function start(n) { const r = await post("/reset", {night:n}); build(r.layout); draw(r.snap); mode = "play"; music.on = true; lastSec = 99; overlay(""); resumeAudio(); }
const keyName = c => c.replace(/^Key|^Digit/, "").replace("ShiftLeft", "Shift").replace("ShiftRight", "R-Shift").replace("Escape", "Esc");
let rebinding = null, rebindMsg = "";
function settings(back) {
  settings.back = back;
  const row = ([a, label]) => `<label>${label} <button class="key" data-a="${a}">${rebinding === a ? "bấm phím…" : keyName(cfg.keys[a])}</button></label>`;
  show(`<h1>Cài đặt</h1><label>Âm lượng <input id=v type=range min=0 max=1 step=.05 value=${cfg.vol}></label><label>Độ nhạy chuột <input id=s type=range min=.1 max=1.5 step=.05 value=${cfg.sens}></label>
    <label><input id=cb type=checkbox ${cfg.cb ? "checked" : ""}> Bảng màu dễ phân biệt</label><label><input id=rm type=checkbox ${cfg.rm ? "checked" : ""}> Giảm chuyển động (không chớp)</label>
    <label><input id=big type=checkbox ${cfg.big ? "checked" : ""}> Chữ lớn (×1.25)</label><h2>Phím</h2>${ACTIONS.map(row).join("")}<p class=err>${rebindMsg}</p>`,
    [["Khôi phục phím mặc định", () => { cfg.keys = {...DEFAULT_KEYS}; rebinding = null; rebindMsg = ""; save(); settings(back); }], ["Xong", () => { rebinding = null; rebindMsg = ""; back(); }]]);
  $("v").oninput = e => { cfg.vol = +e.target.value; save(); }; $("s").oninput = e => { cfg.sens = +e.target.value; save(); };
  $("cb").onchange = e => { cfg.cb = e.target.checked; save(); palette(); }; $("rm").onchange = e => { cfg.rm = e.target.checked; save(); palette(); };
  $("big").onchange = e => { cfg.big = e.target.checked; save(); palette(); };
  document.querySelectorAll("button.key").forEach(b => b.onclick = () => { rebinding = b.dataset.a; rebindMsg = ""; settings(back); });
}
function rebind(code) {   // true if this key press was used for rebinding
  if (!rebinding) return false;
  const clash = ACTIONS.find(([a]) => a !== rebinding && cfg.keys[a] === code);
  if (code === "ArrowLeft" || code === "ArrowRight") rebindMsg = "Mũi tên dùng để xoay camera.";
  else if (clash) rebindMsg = `Phím ${keyName(code)} đã dùng cho «${clash[1]}». Chọn phím khác.`;
  else { cfg.keys[rebinding] = code; save(); rebinding = null; rebindMsg = ""; }
  settings(settings.back); return true;
}
async function board(back) {
  const r = await (await fetch("/leaderboard")).json();
  show(`<h1>Bảng xếp hạng</h1>${r.entries.length ? "<table>" + r.entries.map((e, i) => `<tr><td>${i + 1}</td><td>${e.name}</td><td>${e.score}</td><td>${e.nights_won}/3</td></tr>`).join("") + "</table>" : "<p>Chưa có điểm nào.</p>"}`, [["Quay lại", back]]);
}
function saveScore(score, nights) {
  show(`<h1>Lưu điểm: ${score}</h1><label>Tên (3–12 ký tự: A-Z a-z 0-9 _) <input id=nm maxlength=12 autocomplete=off></label><p class=err id=err></p>`,
    [["Lưu", async () => { const r = await post("/score", {name:$("nm").value, score, nights_won:nights}); if (r.error) $("err").textContent = r.error; else board(menu); }], ["Bỏ qua", menu]]);
}
async function togglePause() { if (mode !== "play" && mode !== "pause") return; await send({pause:true}, 1); await send({pause:false}, 1); }
function pauseMenu() { show("<h1>Tạm dừng</h1>", [["Tiếp tục", togglePause], ["Chơi lại Đêm", () => start(night)], ["Cài đặt", () => settings(pauseMenu)], ["Về menu", menu]]); }
function finish(s) {
  mode = "end"; music.on = false;
  if (s.state === "won") { total += s.score; night < 3 ? show(`<h1>Đêm ${night} xong!</h1><p>Điểm đêm: ${s.score} · Tổng: ${total}</p>`, [["Đêm kế tiếp", () => intro(night + 1)]])
    : show(`<h1>Bình Minh</h1><p>Cả ba đảo còn sáng tới bình minh.</p><p>Tổng điểm: ${total}</p>`, [["Lưu điểm", () => saveScore(total, 3)], ["Về menu", menu]]); }
  else show(`<h1>Thất bại</h1><p>${s.player.flames <= 0 ? "Hết Ngọn Lửa" : "Trời sáng mà đảo chưa đủ đèn"}</p>`, [["Chơi lại Đêm", () => start(night)], ["Lưu điểm", () => saveScore(total, night - 1)], ["Về menu", menu]]);
}
// ---- draw
const warnCol = () => cfg.cb ? "#FFFFFF" : "#FF5A5F";
function palette() { document.documentElement.style.setProperty("--danger", warnCol()); document.documentElement.classList.toggle("cb", !!cfg.cb); document.documentElement.classList.toggle("rm", !!cfg.rm); document.documentElement.classList.toggle("big", !!cfg.big); }
palette();
const beams = {}, cue = {id:null, until:0};
function edgeArrow(el, v3) {   // points to a world position from the screen edge when it is off-screen
  el.style.display = "none"; if (!v3) return;
  const v = v3.project(cam), off = v.z > 1 || Math.abs(v.x) > .95 || Math.abs(v.y) > .95;
  if (!off) return;
  let x = v.x, y = v.y; if (v.z > 1) { x = -x; y = -y; } const k = Math.max(Math.abs(x), Math.abs(y)) || 1; x = x / k * .9; y = y / k * .85;
  el.style.display = "block"; el.style.left = `${(x + 1) / 2 * innerWidth - 14}px`; el.style.top = `${(1 - y) / 2 * innerHeight - 20}px`; el.style.transform = `rotate(${Math.atan2(x, y)}rad)`;
}
function draw(s) {
  snap = s; const p = s.player;
  player.position.set(...p.pos); player.rotation.y = Math.atan2(p.facing[0], p.facing[1]);
  player.children[0].material.color.set(p.invuln && !cfg.rm && (s.tick >> 2) % 2 ? 0xffffff : C.shirt);
  place(moteIM, s.motes, .8); place(haloIM, s.motes, .8); sync(pools.l, s.lanterns, mkLamp); sync(pools.d, s.drifters, mkDrifter); sync(pools.c, s.charms.filter(c => c.available), mkCharm, .8);
  place(shadeIM, s.shades.filter(h => h.state !== "stunned"), .9, h => h.state === "spawning" ? .4 : 1); place(stunIM, s.shades.filter(h => h.state === "stunned"), .9);
  const blink = cfg.rm || (performance.now() % 1000) < 500;   // low fuel: 1 Hz flicker
  s.lanterns.forEach(l => { const g = pools.l[l.id], b = g.getObjectByName("bulb"), low = l.lit && l.fuel < 30, on = l.lit && !(low && !blink);
    b.material.color.set(on ? C.core : C.off); b.material.emissive.set(on ? C.lamp : 0); b.scale.set(1, l.lit ? 1 : .8, 1);
    g.getObjectByName("pl").intensity = on ? 200 * (.4 + .6 * l.fuel / 100) : 0; g.getObjectByName("tear").visible = !l.lit;
    const fb = g.getObjectByName("fuel"); fb.visible = l.lit && !(low && !blink); fb.scale.x = Math.max(.01, l.fuel / 100); fb.material.color.set(low ? new THREE.Color(warnCol()) : C.halo); });
  shadeMat.emissive.set(cfg.cb ? 0x00B3FF : C.rim);
  for (const id in beams) if (!s.shades.some(h => h.id === id && h.state === "drain")) { scene.remove(beams[id]); delete beams[id]; }
  s.shades.filter(h => h.state === "drain").forEach(h => { const l = s.lanterns.find(q => q.id === h.target_lantern_id); if (!l) return;
    const pts = [new THREE.Vector3(...h.pos).setY(h.pos[1] + .9), new THREE.Vector3(...l.pos).setY(l.pos[1] + 3.2)];
    if (!beams[h.id]) { beams[h.id] = new THREE.Line(new THREE.BufferGeometry(), new THREE.LineBasicMaterial({color:cfg.cb ? 0x00B3FF : C.rim})); scene.add(beams[h.id]); }
    beams[h.id].geometry.setFromPoints(pts); });
  const lit = s.lanterns.filter(l => l.lit).length, n = s.lanterns.length, need = Math.ceil(.6 * n - 1e-9);
  amb.intensity = .15 + .55 * (lit / n);
  put("flames", "🔥".repeat(Math.max(0, p.flames)));
  const t = Math.ceil(s.time_left_s); $("clock").textContent = `${String(Math.floor(t/60)).padStart(2,"0")}:${String(t%60).padStart(2,"0")}`; $("clock").className = s.time_left_s <= 30 ? "low" : "";
  if (t <= 10 && t < lastSec && s.state === "playing") SFX.tick(); lastSec = t;
  put("score", `<span class="${lit < need ? "warn" : ""}">${lit < need ? "⚠ " : ""}Đèn ${lit}/${n} (cần ${need})</span><br>Điểm ${s.score}`);
  put("bar", `<span>${p.carried}/${p.capacity}</span>` + Array.from({length:p.capacity}, (_, i) => `<i class="${i < p.carried ? "on" : ""}"></i>`).join(""));
  put("cds", `<b class="${p.dash_cd_s > 0 ? "cd" : ""}">${keyName(cfg.keys.dash)} · Lướt${p.dash_cd_s > 0 ? " " + p.dash_cd_s.toFixed(1) : ""}</b><b class="${p.pulse_cd_s > 0 || p.carried < 3 ? "cd" : ""}">${keyName(cfg.keys.pulse)} · Tỏa Sáng ${p.pulse_cd_s > 0 ? p.pulse_cd_s.toFixed(1) : "(3)"}</b>`);
  const near = s.lanterns.filter(l => !l.lit || l.fuel < 100).map(l => ({l, d: Math.hypot(l.pos[0]-p.pos[0], l.pos[2]-p.pos[2])})).sort((a, b) => a.d - b.d)[0];
  $("prompt").textContent = near && near.d <= 2 ? (near.l.lit ? `${keyName(cfg.keys.interact)} — Châm dầu (${near.l.fuel.toFixed(0)}/100)` : `${keyName(cfg.keys.interact)} — Nạp ánh sáng (${near.l.deposited}/${near.l.ever_lit ? 5 : 10})`) : "";
  const weak = s.lanterns.filter(l => l.lit && l.fuel < 30).length; put("fuel", weak ? `<span class="warn">⚠ ${weak} đèn sắp cạn dầu</span>` : "");
  $("note").textContent = s.wind.warning ? "🍃 Gió sắp nổi!" : s.wind.active ? "🍃 Gió mạnh" : p.charm_s > 0 ? `Bùa Gió ${Math.ceil(p.charm_s)}s` : "";
  edgeArrow($("arrow"), near && new THREE.Vector3(...near.l.pos).setY(near.l.pos[1] + 3));
  const cueShade = performance.now() < cue.until && s.shades.find(h => h.id === cue.id);
  edgeArrow($("arrow2"), cueShade && new THREE.Vector3(...cueShade.pos).setY(cueShade.pos[1] + .9));
  $("cap").textContent = cueShade ? "Bóng Mực xuất hiện!" : t <= 10 && s.state === "playing" ? "10 giây cuối!" : "";
  cam.position.set(p.pos[0] - Math.sin(yaw)*12, p.pos[1] + 8, p.pos[2] - Math.cos(yaw)*12); cam.lookAt(p.pos[0], p.pos[1] + 1.5, p.pos[2]);
  if (s.state === "paused" && mode === "play") { mode = "pause"; pauseMenu(); } else if (s.state === "playing" && mode === "pause") { mode = "play"; overlay(""); }
  if ((s.state === "won" || s.state === "lost") && mode !== "end") finish(s);
}
// ---- input + loop
addEventListener("keydown", e => { if (e.repeat) return; if (rebind(e.code)) return e.preventDefault(); if (e.target.tagName === "INPUT" && e.target.type === "text") return; keys[e.code] = true; if (e.code === cfg.keys.pause) togglePause(); if (e.code === cfg.keys.jump) e.preventDefault(); });
addEventListener("keyup", e => keys[e.code] = false);
addEventListener("resize", () => { R.setSize(innerWidth, innerHeight); cam.aspect = innerWidth/innerHeight; cam.updateProjectionMatrix(); });
R.domElement.onclick = () => { if (mode === "play") R.domElement.requestPointerLock?.(); };
addEventListener("mousemove", e => { if (document.pointerLockElement && mode === "play") yaw -= e.movementX * .005 * cfg.sens * 2; });
let acc = 0, B = null;
function benchFrame(now) {   // fixed camera path; first 3 s are warm-up, then B.duration s are measured
  B.t0 ??= now; const t = (now - B.t0) / 1000, th = 2 * Math.PI * t / 15;
  cam.position.set(30 * Math.cos(th), 15, -30 * Math.sin(th)); cam.lookAt(0, 0, 0);
  if (t >= B.warmup && !B.on) { B.on = true; post("/bench-measuring", {on:true}); }
  if (B.on && B.prev !== undefined) B.dts.push(now - B.prev);
  B.prev = now;
  if (t >= B.warmup + B.duration && mode === "bench") { mode = "done"; post("/bench-measuring", {on:false});
    const gl = R.getContext(), x = gl.getExtension("WEBGL_debug_renderer_info");
    post("/bench-result", {dts:B.dts, first_frame_ms:B.first, gpu:x ? gl.getParameter(x.UNMASKED_RENDERER_WEBGL) : "unknown"}).then(() => window.close()); }
}
function loop(now) {
  acc += (now - last) * 0.06; last = now;       // 60 ticks/s, kept across frames (works above 100 fps)
  const steps = Math.min(Math.floor(acc), 6); acc -= Math.floor(acc);
  if (keys.ArrowLeft) yaw += .03; if (keys.ArrowRight) yaw -= .03;
  leaves.forEach((l, i) => { const on = snap && (snap.wind.warning || snap.wind.active); l.visible = !!on; if (on) { const a = snap.wind.dir_deg * Math.PI / 180, k = (now / 1000 * 6 + i * 3.1) % 30 - 15;
    l.position.set(player.position.x + Math.cos(a) * k + Math.sin(a) * (i - 7) * 2, player.position.y + 2 + Math.sin(now / 300 + i), player.position.z + Math.sin(a) * k - Math.cos(a) * (i - 7) * 2); l.rotation.y += .1; } });
  if (!busy && (mode === "play" || mode === "bench") && steps > 0) {
    busy = true;
    const K = cfg.keys, x = (keys[K.right]?1:0) - (keys[K.left]?1:0), z = (keys[K.up]?1:0) - (keys[K.down]?1:0);
    if (keys[K.jump] && !jumpPrev) SFX.jump(); jumpPrev = !!keys[K.jump];
    const inputs = mode === "bench" ? {} : {move:[x,z], cam_yaw_deg: yaw*180/Math.PI, jump: !!keys[K.jump], interact: !!keys[K.interact], pulse: !!keys[K.pulse], dash: !!keys[K.dash]};
    send(inputs, steps).catch(() => {}).finally(() => busy = false);   // not awaited: drawing never waits for the server
  }
  if (mode === "bench" || mode === "done") benchFrame(now);
  R.render(scene, cam);
  if (B) R.getContext().finish();   // bench: wait for the GPU so uncapped frames do not pile up in its queue and stall
  if (B && B.first === undefined) B.first = Date.now();   // first rendered frame of the bench scene
  requestAnimationFrame(loop);
}
async function startBench(cfgB) {
  B = {...cfgB, dts:[]}; const r = await post("/bench-reset", {}); build(r.layout); draw(r.snap); mode = "bench"; last = performance.now();
  delete B.first;
}
fetch("/bench").then(r => r.json()).catch(() => null).then(b => { if (b && location.search.includes("bench")) startBench(b); else menu(); });
requestAnimationFrame(loop);
