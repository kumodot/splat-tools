// Tests for the take filter chain.
//
//   node test/chain.mjs [path-to-build.html]
//
// It pulls the chain straight out of the shipped HTML rather than keeping a
// copy, so these can never drift from the code that actually runs. Everything
// between "const sources" and the Take list UI banner is either pure or only
// touches the page when called, so it evaluates with no DOM in sight.
import fs from "fs";
import path from "path";
import { fileURLToPath } from "url";

const HERE = path.dirname(fileURLToPath(import.meta.url));
const SW = path.dirname(HERE);
const file = process.argv[2] || fs.readdirSync(SW).filter(f => /^SplatWalk_v.*\.html$/.test(f)).sort().pop();
const html = fs.readFileSync(path.isAbsolute(file) ? file : path.join(SW, file), "utf8");
console.log("testing " + path.basename(file));

const a = html.indexOf("const sources = [];");
const b = html.indexOf("// Take list UI");
if (a < 0 || b < 0) throw new Error("chain markers not found in the build");
const code = html.slice(a, html.lastIndexOf("// ---", b));

const round4 = (v) => Math.round(v * 1e4) / 1e4;
const uuid = () => "id" + Math.random().toString(36).slice(2);
const mod = eval(code + "\n;({ sources, takes, edits, procOf, sampleTake, evalCR, newFx, takeDuration, despike, newEdit, addBlock, editLayout, editDuration, sampleEdit })");
const { sources, takes, edits, procOf, sampleTake, evalCR, newFx, takeDuration } = mod;
const { newEdit, addBlock, editLayout, editDuration, sampleEdit } = mod;

let pass = 0, fail = 0;
const ok = (name, cond, extra) => {
  if (cond) { pass++; console.log("  ok   " + name); }
  else { fail++; console.log("  FAIL " + name + (extra !== undefined ? "   " + extra : "")); }
};
const near = (x, y, tol) => Math.abs(x - y) <= tol;
const touch = (c) => { c._rev = (c._rev || 0) + 1; };
const dist = (p, q) => Math.hypot(p[0] - q[0], p[1] - q[1], p[2] - q[2]);

function setSource(samples) {
  sources.length = 0;
  sources.push({ id: "s", name: "s", samples });
}
function clip(fx) {
  const c = { id: "c" + Math.random(), srcId: "s", name: "c", enabled: true, fx: { ...newFx(), ...fx } };
  touch(c);
  return c;
}

// Parked 2s, 3s of travel, parked 1.5s. The shape auto-trim is meant to find.
function flight(opts = {}) {
  const fps = 60, s = [];
  let t = 0;
  const push = (x, y, z, yaw, pitch) =>
    s.push({ t: round4(t), p: [round4(x), round4(y), round4(z)], yaw: round4(yaw), pitch: round4(pitch), fov: 60 });
  for (let i = 0; i < 2 * fps; i++, t += 1 / fps) push(0, 1.6, 0, 0, 0);
  for (let i = 0; i < 3 * fps; i++, t += 1 / fps) {
    const u = i / (3 * fps);
    const n = opts.noise ? (Math.sin(i * 7.3) * 0.5 + Math.sin(i * 2.1)) * opts.noise : 0;
    push(u * 6 + n, 1.6 + Math.sin(u * 6) * 0.1, u * 2, u * 1.2, Math.sin(u * 3) * 0.2);
  }
  for (let i = 0; i < 1.5 * fps; i++, t += 1 / fps) push(6, 1.6, 2, 1.2, round4(Math.sin(3) * 0.2));
  setSource(s);
  return s;
}

console.log("\n1. pass-through reproduces the recording");
{
  const s = flight();
  const c = clip({ trimAuto: false });
  const pr = procOf(c);
  ok("duration matches", near(pr.outDur, s[s.length - 1].t, 1e-6), pr.outDur);
  ok("point count matches", pr.pts.length === s.length, pr.pts.length + " vs " + s.length);
  let worst = 0;
  for (let i = 0; i < s.length; i += 7) worst = Math.max(worst, dist(sampleTake(c, s[i].t).pos, s[i].p));
  ok("worst position error under 1mm", worst < 0.001, worst.toExponential(2));
}

console.log("\n2. auto-trim finds the still head and tail");
{
  flight();
  const pr = procOf(clip({}));
  ok("in near 2.0s", near(pr.tIn, 2.0, 0.2), pr.tIn.toFixed(3));
  ok("out near 5.0s", near(pr.tOut, 5.0, 0.2), pr.tOut.toFixed(3));
  ok("raw duration still reported", near(pr.rawDur, 6.5, 0.05), pr.rawDur.toFixed(3));
}

console.log("\n3. a take that never stops is left alone");
{
  const s = flight().slice(120, 300).map((q, i) => ({ ...q, t: round4(i / 60) }));
  setSource(s);
  const pr = procOf(clip({}));
  ok("keeps the whole thing", near(pr.srcDur, pr.rawDur, 0.02), pr.srcDur.toFixed(2) + " of " + pr.rawDur.toFixed(2));
}

console.log("\n4. detail drops points without losing the move");
{
  flight({ noise: 0.01 });
  const full = procOf(clip({ trimAuto: false }));
  const counts = [], devs = [];
  for (const d of [1, 0.8, 0.6, 0.4, 0.2, 0]) {
    const pr = procOf(clip({ trimAuto: false, detail: d }));
    counts.push(pr.pts.length);
    let worst = 0;
    for (let i = 0; i < full.pts.length; i += 5) worst = Math.max(worst, dist(evalCR(pr.pts, full.pts[i].t).pos, full.pts[i].p));
    devs.push(worst);
  }
  console.log("     points   : " + counts.join("  ->  "));
  console.log("     deviation: " + devs.map(v => v.toFixed(3)).join("  ->  "));
  ok("count never rises as detail falls", counts.every((v, i) => i === 0 || v <= counts[i - 1]));
  ok("full detail keeps everything", counts[0] === full.pts.length);
  ok("zero detail is a handful", counts[counts.length - 1] < full.pts.length / 20, counts[counts.length - 1]);
  ok("deviation bounded even at zero", devs[devs.length - 1] < 1.0, devs[devs.length - 1].toFixed(3));
}

console.log("\n5. smoothing reaches the curve early in the slider");
{
  flight({ noise: 0.02 });
  const jerk = (c) => {
    const dt = 1 / 60, N = Math.floor(procOf(c).outDur / dt) - 2;
    let acc = 0;
    for (let i = 2; i < N; i++) {
      acc += Math.abs(sampleTake(c, i * dt).pos[0] - 2 * sampleTake(c, (i - 1) * dt).pos[0] + sampleTake(c, (i - 2) * dt).pos[0]);
    }
    return acc / Math.max(1, N);
  };
  const raw = jerk(clip({ trimAuto: false, detail: 1 }));
  const at9 = jerk(clip({ trimAuto: false, detail: 0.9 }));
  const at5 = jerk(clip({ trimAuto: false, detail: 0.5 }));
  console.log(`     jerk: 1.00 ${raw.toExponential(2)}   0.90 ${at9.toExponential(2)}   0.50 ${at5.toExponential(2)}`);
  // The bug this pins: smoothing used to be a no-op until well down the slider,
  // because the window shared the decimator's squared curve.
  ok("0.90 already does something", at9 < raw * 0.9, at9.toExponential(2));
  ok("0.50 does a lot", at5 < raw * 0.5, at5.toExponential(2));
}

console.log("\n6. a hand slip is removed, a real corner is not");
{
  // One bad frame at t=1.5, a genuine direction change at t=3.
  const fps = 60, s = [];
  for (let i = 0; i <= 6 * fps; i++) {
    const t = i / fps;
    let yaw = t < 3 ? t * 0.35 : 1.05 - (t - 3) * 0.35;
    let x = t * 0.8;
    if (i === 90) { yaw += 0.09; x += 0.07; }
    yaw += Math.sin(i * 5.1) * 0.004;
    s.push({ t: round4(t), p: [round4(x), 1.6, 0], yaw: round4(yaw), pitch: 0, fov: 60 });
  }
  setSource(s);
  const c = clip({ trimAuto: false, detail: 1 });
  const peak = (t0, t1) => {
    const dt = 1 / 60;
    let worst = 0;
    for (let t = t0; t < t1; t += dt) {
      worst = Math.max(worst, Math.abs(sampleTake(c, t + dt).yaw - 2 * sampleTake(c, t).yaw + sampleTake(c, t - dt).yaw));
    }
    return worst;
  };
  const jolt = peak(1.2, 1.8), corner = peak(2.7, 3.3);
  console.log(`     jolt ${jolt.toExponential(2)}   corner ${corner.toExponential(2)}   ratio ${(jolt / corner).toFixed(2)}`);
  ok("the slip is smaller than the real corner", jolt < corner, (jolt / corner).toFixed(2) + "x");
  ok("the corner survives at full detail", corner > 5e-3, corner.toExponential(2));
  ok("it was flagged", procOf(c).spikes > 0, procOf(c).spikes + " samples");
}

console.log("\n7. despiking leaves clean motion alone");
{
  const fps = 60, s = [];
  for (let i = 0; i <= 4 * fps; i++) {
    const t = i / fps;
    s.push({ t: round4(t), p: [round4(t * 0.9), 1.6, round4(Math.sin(t) * 2)], yaw: round4(t * 0.4), pitch: 0, fov: 60 });
  }
  setSource(s);
  const pr = procOf(clip({ trimAuto: false, detail: 1 }));
  ok("nothing flagged on a clean path", pr.spikes === 0, pr.spikes + " flagged");
  let worst = 0;
  for (let i = 0; i < s.length; i++) worst = Math.max(worst, dist(pr.pts[i].p, s[i].p));
  ok("samples come through untouched", worst < 1e-9, worst.toExponential(2));
}

console.log("\n8. endpoints are never moved");
{
  flight({ noise: 0.02 });
  const full = procOf(clip({ trimAuto: false, detail: 1 })).pts;
  const first = full[0], last = full[full.length - 1];
  let wa = 0, wb = 0;
  for (const d of [0.8, 0.5, 0.2, 0]) {
    const pts = procOf(clip({ trimAuto: false, detail: d })).pts;
    wa = Math.max(wa, dist(pts[0].p, first.p));
    wb = Math.max(wb, dist(pts[pts.length - 1].p, last.p));
  }
  ok("first pose untouched", wa < 1e-9, wa);
  ok("last pose untouched", wb < 1e-9, wb);
}

console.log("\n9. yaw crossing the seam turns the short way");
{
  const s = [];
  for (let i = 0; i <= 60; i++) {
    const yaw = Math.PI - 0.3 + (i / 60) * 0.6;
    s.push({ t: i / 60, p: [0, 1.6, 0], yaw: round4(yaw > Math.PI ? yaw - 2 * Math.PI : yaw), pitch: 0, fov: 60 });
  }
  setSource(s);
  const c = clip({ trimAuto: false });
  const pr = procOf(c);
  let maxStep = 0, prev = sampleTake(c, 0).yaw;
  const start = prev;
  for (let t = 0; t <= pr.outDur; t += 0.01) {
    const y = sampleTake(c, t).yaw;
    maxStep = Math.max(maxStep, Math.abs(y - prev));
    prev = y;
  }
  ok("no jump across the seam", maxStep < 0.1, maxStep.toFixed(4));
  ok("total travel about 0.6 rad", near(Math.abs(prev - start), 0.6, 0.05));
}

console.log("\n10. speed retimes without changing the path");
{
  flight();
  const base = procOf(clip({ trimAuto: false })).outDur;
  let worst = 0;
  for (const sp of [0.25, 0.5, 2, 4]) {
    const c1 = clip({ trimAuto: false, speed: 1 });
    const c2 = clip({ trimAuto: false, speed: sp });
    const pr = procOf(c2);
    if (!near(pr.outDur, base / sp, 1e-6)) ok("duration at " + sp + "x", false, pr.outDur);
    for (let u = 0; u <= 1; u += 0.05) worst = Math.max(worst, dist(sampleTake(c1, u * base).pos, sampleTake(c2, u * pr.outDur).pos));
  }
  ok("same path at every speed", worst < 1e-9, worst.toExponential(2));
}

console.log("\n11. ease keeps the ends and only redistributes time");
{
  flight();
  const c1 = clip({ ease: 1 }), c0 = clip({ ease: 0 });
  const dur = procOf(c1).outDur;
  ok("start pose unchanged", dist(sampleTake(c1, 0).pos, sampleTake(c0, 0).pos) < 1e-9);
  ok("end pose unchanged", dist(sampleTake(c1, dur).pos, sampleTake(c0, dur).pos) < 1e-9);
  let mono = true, prev = -Infinity;
  for (let t = 0; t <= dur; t += 0.02) { const x = sampleTake(c1, t).pos[0]; if (x < prev - 1e-6) mono = false; prev = x; }
  ok("no backtrack", mono);
  ok("eased start is slower", sampleTake(c1, dur * 0.2).pos[0] < sampleTake(c0, dur * 0.2).pos[0] - 1e-4);
  ok("eased end is slower", sampleTake(c1, dur * 0.8).pos[0] > sampleTake(c0, dur * 0.8).pos[0] + 1e-4);
}

console.log("\n12. the curve never overshoots a hard stop");
{
  const s = [];
  let t = 0;
  const push = (x) => { s.push({ t: round4(t), p: [x, 1.6, 0], yaw: 0, pitch: 0, fov: 60 }); t += 1 / 60; };
  for (let i = 0; i < 60; i++) push(0);
  for (let i = 1; i <= 60; i++) push(i / 60 * 4);
  for (let i = 0; i < 60; i++) push(4);
  setSource(s);
  for (const d of [1, 0.6, 0.3]) {
    const c = clip({ trimAuto: false, detail: d });
    const pr = procOf(c);
    let lo = Infinity, hi = -Infinity, back = 0, prev = -Infinity;
    for (let u = 0; u <= pr.outDur; u += 0.005) {
      const x = sampleTake(c, u).pos[0];
      lo = Math.min(lo, x); hi = Math.max(hi, x);
      if (x < prev - 1e-9) back = Math.max(back, prev - x);
      prev = x;
    }
    ok(`detail ${d}: never dips below the start`, lo > -1e-6, lo.toExponential(2));
    ok(`detail ${d}: never sails past the end`, hi < 4 + 1e-6, (hi - 4).toExponential(2));
    ok(`detail ${d}: never travels backwards`, back < 1e-6, back.toExponential(2));
  }
}

console.log("\n13. handheld is deterministic and opt-in");
{
  flight();
  const c0 = clip({ trimAuto: false, shake: 0 });
  const cs = clip({ trimAuto: false, shake: 0.5 });
  const clean = [], a = [], b = [];
  for (let t = 0; t < 3; t += 0.1) { clean.push(sampleTake(c0, t).yaw); a.push(sampleTake(cs, t).yaw); }
  for (let t = 0; t < 3; t += 0.1) b.push(sampleTake(cs, t).yaw);
  ok("same every time", a.every((v, i) => v === b[i]));
  ok("it moves something", a.some((v, i) => Math.abs(v - clean[i]) > 1e-4));
  ok("within a couple of degrees", Math.max(...a.map((v, i) => Math.abs(v - clean[i]))) < 0.05);
  const off = [];
  for (let t = 0; t < 3; t += 0.1) off.push(sampleTake(clip({ trimAuto: false, shake: 0 }), t).yaw);
  ok("zero means truly off", off.every((v, i) => v === clean[i]));
}

console.log("\n13b. cutting points by hand");
{
  flight({ noise: 0.01 });
  const base = procOf(clip({ trimAuto: false, detail: 0.7 }));
  const n0 = base.pts.length;
  ok("something to work with", n0 > 6, n0);

  const victim = base.pts[Math.floor(n0 / 2)].t;
  const c = clip({ trimAuto: false, detail: 0.7, cut: [victim] });
  const pr = procOf(c);
  ok("the point leaves the curve", pr.pts.length === n0 - 1, `${pr.pts.length} vs ${n0}`);
  ok("and is kept as a ghost", pr.ghosts.length === 1 && Math.abs(pr.ghosts[0].t - victim) < 1e-9);
  ok("the curve still spans the same time", Math.abs(pr.srcDur - base.srcDur) < 1e-9);

  // The ends anchor the shot; losing one would move where it starts or stops.
  const ends = clip({ trimAuto: false, detail: 0.7, cut: [base.pts[0].t, base.pts[n0 - 1].t] });
  const pe = procOf(ends);
  ok("the first and last cannot be cut", pe.pts.length === n0 && pe.ghosts.length === 0, pe.pts.length);

  // Stored as times, so a nudge of Detail does not throw the edit away, and a
  // big move simply leaves it with nothing to apply to.
  const moved = clip({ trimAuto: false, detail: 0.69, cut: [victim] });
  ok("survives a nudge of Detail", procOf(moved).ghosts.length === 1, procOf(moved).ghosts.length);
  const far = clip({ trimAuto: false, detail: 0, cut: [victim] });
  const pf = procOf(far);
  ok("goes inert rather than breaking", pf.pts.length >= 2 && pf.ghosts.length <= 1,
     `${pf.pts.length} pts, ${pf.ghosts.length} ghosts`);

  // A cut take must still be renderable from end to end.
  let bad = 0;
  for (let i = 0; i <= 40; i++) {
    const p = sampleTake(c, (i / 40) * pr.outDur);
    if (!p || [p.pos[0], p.pos[1], p.pos[2], p.yaw].some(v => !isFinite(v))) bad++;
  }
  ok("still samples cleanly end to end", bad === 0, bad + " bad");
}

console.log("\n13c. reverse");
{
  flight();
  const fwd = clip({ trimAuto: false });
  const rev = clip({ trimAuto: false, reverse: true });
  const dur = procOf(fwd).outDur;
  ok("same length", Math.abs(procOf(rev).outDur - dur) < 1e-9);
  ok("starts where the other ends", dist(sampleTake(rev, 0).pos, sampleTake(fwd, dur).pos) < 1e-9);
  ok("ends where the other starts", dist(sampleTake(rev, dur).pos, sampleTake(fwd, 0).pos) < 1e-9);
  let worst = 0;
  for (let u = 0; u <= 1; u += 0.05) {
    worst = Math.max(worst, dist(sampleTake(rev, u * dur).pos, sampleTake(fwd, (1 - u) * dur).pos));
  }
  ok("mirrors the whole path", worst < 1e-9, worst.toExponential(2));

  // It is a read direction, not an edit: turning it off restores the original
  // exactly, and it composes with the rest of the chain rather than fighting it.
  const back = clip({ trimAuto: false, reverse: false });
  ok("toggling off is lossless", dist(sampleTake(back, 0).pos, sampleTake(fwd, 0).pos) < 1e-9);
  const both = clip({ trimAuto: false, reverse: true, detail: 0.4, speed: 2, ease: 1 });
  const pr = procOf(both);
  let bad = 0;
  for (let i = 0; i <= 40; i++) {
    const p = sampleTake(both, (i / 40) * pr.outDur);
    if (!p || [p.pos[0], p.pos[1], p.pos[2], p.yaw].some(v => !isFinite(v))) bad++;
  }
  ok("composes with detail, speed and ease", bad === 0, bad + " bad");
}

console.log("\n13d. timing: as recorded vs linear");
{
  // A straight dash: the first half of the recording crawls through one metre,
  // the second half bolts through nine. Same path, wildly uneven pacing.
  const fps = 60, s = [];
  for (let i = 0; i < 120; i++) {
    const x = i < 60 ? (i / 60) * 1 : 1 + ((i - 60) / 60) * 9;
    s.push({ t: round4(i / fps), p: [round4(x), 1.6, 0], yaw: 0, pitch: 0, fov: 60 });
  }
  setSource(s);

  const rec = clip({ trimAuto: false, timing: "recorded" });
  const lin = clip({ trimAuto: false, timing: "linear" });
  const base = clip({ trimAuto: false });
  const dur = procOf(rec).outDur;

  ok("linear keeps the clip length", near(procOf(lin).outDur, dur, 1e-9));

  // "As recorded" is the default and has to be a true no-op.
  let drift = 0;
  for (let i = 0; i <= 40; i++) {
    const u = (i / 40) * dur;
    drift = Math.max(drift, dist(sampleTake(rec, u).pos, sampleTake(base, u).pos));
  }
  ok("as recorded changes nothing", drift < 1e-9, drift.toExponential(2));

  const spread = (c) => {
    // sampleTake hands back a reused pose object, so hold on to a copy.
    let lo = Infinity, hi = 0, prev = sampleTake(c, 0).pos.slice();
    for (let i = 1; i <= 60; i++) {
      const p = sampleTake(c, (i / 60) * dur).pos.slice();
      const d = dist(p, prev);
      prev = p;
      if (d < lo) lo = d;
      if (d > hi) hi = d;
    }
    return hi / Math.max(lo, 1e-9);
  };
  const rRec = spread(rec), rLin = spread(lin);
  console.log("     speed spread: recorded " + rRec.toFixed(2) + "x   linear " + rLin.toFixed(2) + "x");
  ok("the recording really is uneven", rRec > 4, rRec.toFixed(2));
  ok("linear covers equal ground per second", rLin < 1.5, rLin.toFixed(2));
  ok("and it is an improvement", rLin < rRec / 3);

  // Endpoints are the one thing retiming must not touch.
  ok("starts in the same place", dist(sampleTake(lin, 0).pos, s[0].p) < 1e-6);
  ok("ends in the same place", dist(sampleTake(lin, dur).pos, s[s.length - 1].p) < 1e-6);

  // A take that only turns on the spot covers no ground at all, so a retime by
  // position alone would divide by zero.
  const pan = [];
  for (let i = 0; i < 120; i++) {
    const u = i < 60 ? (i / 60) * 0.1 : 0.1 + ((i - 60) / 60) * 0.9;
    pan.push({ t: round4(i / fps), p: [0, 1.6, 0], yaw: round4(u), pitch: 0, fov: 60 });
  }
  setSource(pan);
  const panLin = clip({ trimAuto: false, timing: "linear" });
  const pd = procOf(panLin).outDur;
  let bad = 0;
  for (let i = 0; i <= 40; i++) {
    const p = sampleTake(panLin, (i / 40) * pd);
    if (!p || !isFinite(p.yaw) || !isFinite(p.pos[0])) bad++;
  }
  ok("a pan-only take still retimes", bad === 0, bad + " bad");
  ok("and spreads the turn evenly", near(sampleTake(panLin, pd / 2).yaw, 0.5, 0.08),
     sampleTake(panLin, pd / 2).yaw);

  // Nothing moved at all: fall back to even spacing rather than NaN.
  setSource(Array.from({ length: 30 }, (_, i) => ({ t: round4(i / fps), p: [0, 1.6, 0], yaw: 0, pitch: 0, fov: 60 })));
  const still = clip({ trimAuto: false, timing: "linear" });
  const sp = sampleTake(still, procOf(still).outDur / 2);
  ok("a frozen take does not divide by zero", sp && isFinite(sp.pos[0]) && isFinite(sp.yaw));
}

console.log("\n13e. edits: blocks of takes on one timeline");
{
  // Two takes that are easy to tell apart: one runs along X, the other along Z.
  const fps = 60;
  const line = (ax) => Array.from({ length: 121 }, (_, i) => ({
    t: round4(i / fps), p: ax === 0 ? [round4(i / 12), 1.6, 0] : [0, 1.6, round4(i / 12)],
    yaw: 0, pitch: 0, fov: 60,
  }));
  sources.length = 0; takes.length = 0; edits.length = 0;
  sources.push({ id: "sx", name: "sx", samples: line(0) });
  sources.push({ id: "sz", name: "sz", samples: line(2) });
  const mk = (srcId, name) => {
    const c = { id: "c" + name, srcId, name, enabled: true, fx: { ...newFx(), trimAuto: false } };
    c._rev = 1; takes.push(c); return c;
  };
  const A = mk("sx", "A"), B = mk("sz", "B");
  const dA = takeDuration(A), dB = takeDuration(B);

  const ed = newEdit("Opening");
  addBlock(ed, A); addBlock(ed, B);
  ok("the edit is as long as its parts", near(editDuration(ed), dA + dB, 1e-6), editDuration(ed));

  // Butted together, so the second block starts exactly where the first ends.
  const l = editLayout(ed);
  ok("blocks are butted", near(l[1].t0, dA, 1e-9), l[1].t0);

  ok("plays the first take first", dist(sampleEdit(ed, 0).pos, sampleTake(A, 0).pos) < 1e-9);
  ok("and the second take second",
     dist(sampleEdit(ed, dA + dB / 2).pos, sampleTake(B, dB / 2).pos) < 1e-9);
  ok("the end is the end of the last block",
     dist(sampleEdit(ed, dA + dB).pos, sampleTake(B, dB).pos) < 1e-6);
  ok("past the end holds the last frame",
     dist(sampleEdit(ed, 999).pos, sampleTake(B, dB).pos) < 1e-6);

  // The cut itself: a frame either side must come from different takes, and
  // neither may be NaN.
  const before = sampleEdit(ed, dA - 1 / fps), after = sampleEdit(ed, dA + 1 / fps);
  ok("a hard cut, not a blend", before.pos[0] > 1 && after.pos[0] < 1e-6, `${before.pos[0]} / ${after.pos[0]}`);

  // Trimming a block shortens the edit and shifts everything after it. The
  // take is untouched, which is the whole point of the split.
  l[0].b.tIn = 0.5; l[0].b.tOut = 1.5;
  ok("trim changes the block", near(editLayout(ed)[0].dur, 1, 1e-6), editLayout(ed)[0].dur);
  ok("and the edit with it", near(editDuration(ed), 1 + dB, 1e-6));
  ok("but never the take", near(takeDuration(A), dA, 1e-9));
  ok("the block plays from its in point",
     dist(sampleEdit(ed, 0).pos, sampleTake(A, 0.5).pos) < 1e-9);
  ok("the next block follows the trim",
     dist(sampleEdit(ed, 1 + dB / 2).pos, sampleTake(B, dB / 2).pos) < 1e-9);

  // Duration is a property of the TAKE, so changing it reflows every edit.
  A.fx.speed = 2; A._rev++;
  ok("a take's speed reflows the edit", near(editLayout(ed)[1].t0, editLayout(ed)[0].dur, 1e-9));

  // The same take twice, showing different stretches, with nothing duplicated.
  const ed2 = newEdit("Twice");
  const b1 = addBlock(ed2, B), b2 = addBlock(ed2, B);
  b1.tOut = 1; b2.tIn = dB - 1;
  ok("one take can appear twice", editLayout(ed2).length === 2);
  ok("each instance keeps its own trim",
     near(editLayout(ed2)[0].dur, 1, 1e-6) && near(editLayout(ed2)[1].dur, 1, 1e-6));
  ok("and they play different stretches",
     dist(sampleEdit(ed2, 0).pos, sampleEdit(ed2, 1.0001).pos) > 0.5);

  // A block whose take went away is skipped, not a crash and not a hole.
  takes.splice(takes.indexOf(B), 1);
  ok("a dead block is skipped", editLayout(ed).length === 1);
  ok("the edit is still playable", !!sampleEdit(ed, 0));
  ok("an empty edit has no length and no pose",
     editDuration(newEdit("Empty")) === 0 && sampleEdit(newEdit("Empty2"), 0) === null);

  sources.length = 0; takes.length = 0; edits.length = 0;
}

console.log("\n14. nothing produces NaN, anywhere");
{
  flight({ noise: 0.03 });
  let bad = 0, n = 0;
  for (const d of [1, 0.73, 0.4, 0]) for (const sp of [0.3, 1, 3]) for (const e of [0, 0.5, 1]) for (const sh of [0, 0.7]) {
    const c = clip({ detail: d, speed: sp, ease: e, shake: sh });
    const pr = procOf(c);
    for (let i = 0; i <= 40; i++) {
      const p = sampleTake(c, (i / 40) * pr.outDur);
      n++;
      if (!p || [p.pos[0], p.pos[1], p.pos[2], p.yaw, p.pitch, p.fov].some(v => !isFinite(v))) bad++;
    }
  }
  ok(n + " poses over 72 parameter combinations, all finite", bad === 0, bad + " bad");
}

console.log("\n15. degenerate takes do not explode");
{
  setSource([{ t: 0, p: [1, 2, 3], yaw: 0.5, pitch: 0.1, fov: 60 }]);
  const c = clip({});
  ok("single sample returns its pose", sampleTake(c, 0).pos[0] === 1 && sampleTake(c, 99).pos[0] === 1);
  const orphan = { id: "x", srcId: "nope", name: "x", enabled: true, fx: newFx() };
  ok("missing recording returns null, not a throw", sampleTake(orphan, 0) === null);
  ok("and reports zero duration", takeDuration(orphan) === 0);
}

console.log("\n" + (fail ? "FAILED" : "PASSED") + ": " + pass + " passed, " + fail + " failed\n");
process.exit(fail ? 1 : 0);
