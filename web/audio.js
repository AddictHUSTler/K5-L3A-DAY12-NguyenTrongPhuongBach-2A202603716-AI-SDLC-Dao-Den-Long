// Settings (saved in localStorage) and synthesized audio. Client only: never touches the sim.
export const ACTIONS = [["up","Đi lên"],["down","Đi xuống"],["left","Sang trái"],["right","Sang phải"],["jump","Nhảy"],["dash","Lướt"],["interact","Tương tác"],["pulse","Tỏa Sáng"],["pause","Tạm dừng"]];
export const DEFAULT_KEYS = {up:"KeyW", down:"KeyS", left:"KeyA", right:"KeyD", jump:"Space", dash:"ShiftLeft", interact:"KeyE", pulse:"KeyQ", pause:"Escape"};
export const cfg = {vol:.6, sens:.5, cb:false, rm:false, big:false, keys:{...DEFAULT_KEYS}};
try { Object.assign(cfg, JSON.parse(localStorage.getItem("ddl") || "{}")); cfg.keys = {...DEFAULT_KEYS, ...cfg.keys}; } catch(e) {}
export const save = () => { try { localStorage.setItem("ddl", JSON.stringify(cfg)); } catch(e) {} };
// ---- audio (WebAudio synth; client only)
let ac;
export const music = {on: false};
function tone(f, d = .25, type = "sine", v = .2, to = 0) { try { ac ??= new AudioContext(); const o = ac.createOscillator(), g = ac.createGain(), t = ac.currentTime;
  o.type = type; o.frequency.setValueAtTime(f, t); if (to) o.frequency.exponentialRampToValueAtTime(to, t + d);
  g.gain.setValueAtTime(v * cfg.vol, t); g.gain.exponentialRampToValueAtTime(.0005, t + d); o.connect(g).connect(ac.destination); o.start(); o.stop(t + d); } catch(e) {} }
const PENT = [0,2,4,7,9];
export const chime = n => tone(392 * 2 ** (PENT[n % 5] / 12 + Math.floor(n / 5)), 1.2, "sine", .3);   // creative: each lit lantern rings one step higher
export const SFX = {mote_picked:()=>tone(880,.1,"triangle",.15,1320), pulse:()=>tone(300,.5,"sine",.3,900), player_hit:()=>tone(160,.4,"sawtooth",.25,60),
  dash:()=>tone(500,.15,"square",.08,200), shade_spawned:()=>tone(90,.6,"sawtooth",.12,60), jump:()=>tone(330,.15,"triangle",.12,520),
  charm_picked:()=>tone(660,.3,"triangle",.2,1320), drifter_steal:()=>tone(240,.3,"square",.12,120), tick:()=>tone(1000,.06,"square",.08),
  lantern_out:()=>tone(392,1.4,"sine",.3,196), refuel:()=>tone(660,.2,"triangle",.15,880)}   // creative: a dying lantern rings the chime backwards;
setInterval(() => { if (music.on) tone(130.8 * 2 ** (PENT[Math.floor(Math.random()*5)] / 12), 3, "sine", .09); }, 2200);

export const sfxEnd = res => res === "won"
  ? [523,659,784,1047].forEach((f,i) => setTimeout(() => tone(f,.5,"triangle",.25), i*140))
  : [330,262,196].forEach((f,i) => setTimeout(() => tone(f,.6,"sawtooth",.15), i*200));
export const resumeAudio = () => { try { ac?.resume(); } catch(e) {} };
