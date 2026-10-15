// Renders PNG frames of ngisa-demo.html through one headless Chrome (DevTools protocol).
// Usage: node render-demo-frames.mjs <html> <lang> <fps> <out-dir>
// Needs Node 22 (global WebSocket) and Google Chrome. Set CHROME to override the binary.
import { spawn } from "node:child_process";
import { mkdirSync, mkdtempSync, writeFileSync, readFileSync, rmSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";

const [html, lang, fpsArg, outDir] = process.argv.slice(2);
const fps = Number(fpsArg);
const chrome = process.env.CHROME || "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome";
const port = 9300 + Math.floor(Math.random() * 500);
const profile = mkdtempSync(join(tmpdir(), "ngisa-chrome-"));
mkdirSync(outDir, { recursive: true });

const proc = spawn(chrome, [
  "--headless=new", "--disable-gpu", "--hide-scrollbars", "--no-first-run",
  `--remote-debugging-port=${port}`, `--user-data-dir=${profile}`, "about:blank",
], { stdio: "ignore" });
const cleanup = () => { try { proc.kill(); } catch {} try { rmSync(profile, { recursive: true, force: true }); } catch {} };
process.on("exit", cleanup);

const sleep = ms => new Promise(r => setTimeout(r, ms));
async function wsUrl() {
  for (let i = 0; i < 100; i++) {
    try {
      const pages = await (await fetch(`http://127.0.0.1:${port}/json`)).json();
      const p = pages.find(x => x.type === "page");
      if (p) return p.webSocketDebuggerUrl;
    } catch {}
    await sleep(100);
  }
  throw new Error("Chrome did not start");
}

const ws = new WebSocket(await wsUrl());
await new Promise((res, rej) => { ws.onopen = res; ws.onerror = rej; });
let id = 0; const pending = new Map();
ws.onmessage = ev => { const m = JSON.parse(ev.data); if (m.id && pending.has(m.id)) { pending.get(m.id)(m); pending.delete(m.id); } };
const send = (method, params = {}) => new Promise((res, rej) => {
  const i = ++id; pending.set(i, m => (m.error ? rej(new Error(m.error.message)) : res(m.result)));
  ws.send(JSON.stringify({ id: i, method, params }));
});

await send("Page.enable");
await send("Emulation.setDeviceMetricsOverride", { width: 960, height: 540, deviceScaleFactor: 1, mobile: false });
await send("Page.navigate", { url: `file://${html}?t=0&lang=${lang}` });
for (let i = 0; i < 100; i++) {
  const r = await send("Runtime.evaluate", { expression: "typeof draw === 'function' && typeof TOTAL === 'number' && document.readyState" });
  if (r.result.value === "complete") break;
  await sleep(100);
}
const total = (await send("Runtime.evaluate", { expression: "TOTAL" })).result.value;
const frames = Math.floor(total * fps / 1000);

for (let f = 0; f < frames; f++) {
  const t = Math.round(f * 1000 / fps);
  let ok = false;
  for (let attempt = 0; attempt < 3 && !ok; attempt++) {
    try {
      await send("Runtime.evaluate", { expression: `draw(${t}, ${JSON.stringify(lang)})` });
      const shot = await send("Page.captureScreenshot", { format: "png" });
      writeFileSync(join(outDir, String(f).padStart(4, "0") + ".png"), Buffer.from(shot.data, "base64"));
      ok = true;
    } catch (e) { await sleep(200); }
  }
  if (!ok) throw new Error(`frame ${f} failed`);
}
console.log(`${lang}: ${frames} frames`);
ws.close(); cleanup(); process.exit(0);
