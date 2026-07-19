#!/usr/bin/env node
/* ============================================================================
 * record-tool-videos.mjs — автозапись роликов-подсказок для карточек инструментов
 * планировщика (мини-Revit). Playwright «руками робота» рисует в редакторе и
 * пишет экран → assets/tool-videos/<id>.webm.
 *
 *   node scripts/record-tool-videos.mjs            # записать все
 *   node scripts/record-tool-videos.mjs draw poly  # только выбранные
 *
 * Требуется Playwright + браузер chromium. Если модуль не установлен локально,
 * скрипт пытается найти его в кэше npx; иначе подскажет `npm i -D playwright`.
 * Системный ffmpeg НЕ обязателен: без него сохраняется исходный webm от Playwright
 * (крупнее, но рабочий). С ffmpeg — кроп/сжатие до ~640px, цель ≤500 КБ/ролик.
 *
 * Пейвол НЕ трогаем в бою: скрипт подменяет window.AQ_CONFIG.PAYWALL=false ТОЛЬКО
 * в записывающем браузере (init-script + геттер, устойчивый к переприсвоению в index.html).
 * ========================================================================== */
import http from 'node:http';
import fs from 'node:fs';
import fsp from 'node:fs/promises';
import path from 'node:path';
import os from 'node:os';
import { fileURLToPath, pathToFileURL } from 'node:url';
import { spawnSync } from 'node:child_process';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const ROOT = path.resolve(__dirname, '..');
const OUT_DIR = path.join(ROOT, 'assets', 'tool-videos');
const TMP_DIR = path.join(os.tmpdir(), 'aq-tool-rec');
const VW = 1280, VH = 800;
const PORT = 8123;

/* ── Разрешение Playwright: локально или из кэша npx ─────────────────────── */
function pickChromium(mod) {          // named export (ESM) или .default (CJS через ESM)
  if (mod && mod.chromium) return mod;
  if (mod && mod.default && mod.default.chromium) return mod.default;
  return null;
}
async function loadPlaywright() {
  let mod = null;
  try { mod = await import('playwright'); } catch { /* ищем в кэше npx */ }
  if (!pickChromium(mod)) {
    const npx = path.join(os.homedir(), '.npm', '_npx');
    try {
      for (const h of await fsp.readdir(npx)) {
        const p = path.join(npx, h, 'node_modules', 'playwright', 'index.js');
        if (fs.existsSync(p)) { mod = await import(pathToFileURL(p).href); if (pickChromium(mod)) break; }
      }
    } catch { /* нет кэша */ }
  }
  const pw = pickChromium(mod);
  if (!pw) throw new Error('Playwright не найден. Установите: npm i -D playwright && npx playwright install chromium');
  return pw;
}

/* ── Простой статический сервер корня проекта ────────────────────────────── */
function startServer() {
  const types = { '.html':'text/html', '.js':'text/javascript', '.css':'text/css',
    '.json':'application/json', '.svg':'image/svg+xml', '.png':'image/png',
    '.jpg':'image/jpeg', '.webp':'image/webp', '.woff2':'font/woff2', '.webm':'video/webm' };
  const srv = http.createServer((req, res) => {
    let rel = decodeURIComponent(req.url.split('?')[0]);
    if (rel === '/' || rel === '') rel = '/index.html';
    const file = path.join(ROOT, path.normalize(rel));
    if (!file.startsWith(ROOT)) { res.writeHead(403).end(); return; }
    fs.readFile(file, (err, buf) => {
      if (err) { res.writeHead(404).end('not found'); return; }
      res.writeHead(200, { 'Content-Type': types[path.extname(file)] || 'application/octet-stream' });
      res.end(buf);
    });
  });
  return new Promise(r => srv.listen(PORT, () => r(srv)));
}

/* ── Init-script: гасим пейвол и внешние сети только в браузере записи ────── */
const INIT = `
Object.defineProperty(window,'AQ_CONFIG',{configurable:true,
  get(){return window.__AQ;},
  set(v){window.__AQ=Object.assign({},v||{},{PAYWALL:false,SUPABASE_URL:'',SUPABASE_ANON_KEY:''});}});
try{ localStorage.setItem('aq_lang','ru'); localStorage.setItem('aq_ribbon_v2','1');
  localStorage.removeItem('mr_cats'); localStorage.setItem('aq_ribbon_more','0'); }catch(e){}
/* Маска: пока не открыт редактор — сплошной тёмный экран вместо лендинга.
   Вешаем fixed-div в <body>, как только он появится (MutationObserver), снимаем из скрипта после openEditor. */
document.documentElement.style.background='#0B0F1A';
(function(){
  function mount(){ if(document.getElementById('__recmask')) return;
    var m=document.createElement('div'); m.id='__recmask';
    m.style.cssText='position:fixed;inset:0;background:#0B0F1A;z-index:2147483647;pointer-events:none';
    (document.body||document.documentElement).appendChild(m); }
  if(document.body) mount();
  else new MutationObserver(function(_,obs){ if(document.body){ mount(); obs.disconnect(); } }).observe(document.documentElement,{childList:true,subtree:true});
})();
`;

/* ── Фейковый курсор (реальный курсор Playwright в записи не виден) ───────── */
const CURSOR = `(()=>{ if(document.getElementById('__fc'))return;
  const c=document.createElement('div'); c.id='__fc';
  c.style.cssText='position:fixed;z-index:2147483647;left:-40px;top:-40px;width:26px;height:26px;pointer-events:none;transition:transform .06s ease';
  c.innerHTML='<svg width="26" height="26" viewBox="0 0 24 24"><path d="M4 2l6 16 2.4-6.4L19 9z" fill="#fff" stroke="#111" stroke-width="1.3" stroke-linejoin="round"/></svg>';
  document.body.appendChild(c);
})()`;

let cur = { x: VW / 2, y: VH / 2 };
let dialogAnswer = '2';            // ответ на prompt() (scale/offset задают своё значение)
const sleep = ms => new Promise(r => setTimeout(r, ms));

async function moveCursor(page, x, y, steps = 26) {
  const sx = cur.x, sy = cur.y;
  for (let i = 1; i <= steps; i++) {
    const t = i / steps, e = t < .5 ? 2*t*t : 1-Math.pow(-2*t+2,2)/2; // easeInOut
    const nx = sx + (x - sx) * e, ny = sy + (y - sy) * e;
    await page.mouse.move(nx, ny);
    await page.evaluate(([px,py]) => { const c=document.getElementById('__fc'); if(c){c.style.left=(px-3)+'px';c.style.top=(py-2)+'px';} }, [nx,ny]);
    await sleep(11);
  }
  cur = { x, y };
}
async function press(page){ await page.evaluate(()=>{const c=document.getElementById('__fc');if(c)c.style.transform='scale(.78)';}); await page.mouse.down(); await sleep(90); }
async function release(page){ await page.mouse.up(); await page.evaluate(()=>{const c=document.getElementById('__fc');if(c)c.style.transform='scale(1)';}); await sleep(120); }
async function clickAt(page, x, y){ await moveCursor(page, x, y); await press(page); await release(page); }
async function dragTo(page, x1, y1, x2, y2){ await moveCursor(page, x1, y1); await press(page); await moveCursor(page, x2, y2, 34); await release(page); }

async function toolPt(page, id){
  const loc = page.locator(`.er-ico[data-tool-id="${id}"]`).first();
  // Инструмент может быть в свёрнутой папке/категории — раскрываем, чтобы кнопка стала видимой
  await page.evaluate((tid) => {
    const btn = document.querySelector(`.er-ico[data-tool-id="${tid}"]`); if (!btn) return;
    const mb = document.getElementById('er-more-body'); if (mb) mb.classList.remove('hidden');
    const mh = document.getElementById('er-more-head'); if (mh) mh.classList.add('open');
    const body = btn.closest('.er-body'); if (body) { body.classList.remove('hidden');
      const cat = body.closest('.er-cat'); const head = cat && cat.querySelector('.er-head'); if (head) head.classList.add('open'); }
  }, id);
  await loc.scrollIntoViewIfNeeded().catch(() => {});
  const box = await loc.boundingBox();
  if (!box) throw new Error('кнопка не найдена: ' + id);
  return { x: box.x + box.width/2, y: box.y + box.height/2 };
}
async function clickTool(page, id){ const p = await toolPt(page, id); await clickAt(page, p.x, p.y); await sleep(350); }
async function canvasRect(page){ return page.locator('#ed-canvas').boundingBox(); }

/* Нарисовать образцовую комнату — база для многих сцен */
async function drawSampleRoom(page){
  const c = await canvasRect(page); const cx = c.x + c.width/2, cy = c.y + c.height/2;
  await clickTool(page, 'draw');
  await dragTo(page, cx - 170, cy - 110, cx + 130, cy + 100);
  await sleep(500);
}
/* Нарисовать комнату и выбрать её — база для сцен «изменение выбранной комнаты» */
async function selectRoom(page){
  await drawSampleRoom(page);
  const c = await canvasRect(page); const cx = c.x + c.width/2, cy = c.y + c.height/2;
  await clickTool(page, 'select');
  await clickAt(page, cx - 10, cy - 10); await sleep(500);
  return { cx, cy };
}
const cc = c => ({ cx: c.x + c.width/2, cy: c.y + c.height/2 });

/* ── Сценарии (4–7 с плавных движений) ───────────────────────────────────── */
const SCENARIOS = {
  async draw(page){
    const c = await canvasRect(page); const cx = c.x + c.width/2, cy = c.y + c.height/2;
    await clickTool(page, 'draw');
    await dragTo(page, cx - 180, cy - 110, cx + 150, cy + 110);
    await sleep(1200);
  },
  async poly(page){
    const c = await canvasRect(page); const cx = c.x + c.width/2, cy = c.y + c.height/2;
    await clickTool(page, 'poly');
    for (const [dx,dy] of [[-150,-110],[160,-90],[130,110],[-90,130]]) { await clickAt(page, cx+dx, cy+dy); await sleep(320); }
    await page.keyboard.press('Enter'); await sleep(1200);
  },
  async select(page){
    await drawSampleRoom(page);
    const c = await canvasRect(page); const cx = c.x + c.width/2, cy = c.y + c.height/2;
    await clickTool(page, 'select');
    await clickAt(page, cx - 10, cy - 10); await sleep(500);
    await dragTo(page, cx + 130, cy + 100, cx + 190, cy + 150);   // тянем ручку — размер
    await sleep(500);
    await dragTo(page, cx, cy, cx - 90, cy - 40);                 // тянем комнату — перемещение
    await sleep(900);
  },
  async delete(page){
    await drawSampleRoom(page);
    const c = await canvasRect(page); const cx = c.x + c.width/2, cy = c.y + c.height/2;
    await clickTool(page, 'select');
    await clickAt(page, cx - 10, cy - 5); await sleep(650);
    await clickTool(page, 'delete'); await sleep(1100);
  },
  async 'zoom-in'(page){
    await drawSampleRoom(page);
    for (let i = 0; i < 3; i++) { await clickTool(page, 'zoom-in'); await sleep(650); }
    await sleep(700);
  },
  async 'zoom-out'(page){
    await drawSampleRoom(page);
    for (let i = 0; i < 3; i++) { await clickTool(page, 'zoom-out'); await sleep(650); }
    await sleep(700);
  },
  async fit(page){
    await drawSampleRoom(page);
    for (let i = 0; i < 3; i++) { await clickTool(page, 'zoom-in'); await sleep(400); }
    const c = await canvasRect(page); const cx = c.x + c.width/2, cy = c.y + c.height/2;
    await page.keyboard.down('Space');
    await dragTo(page, cx, cy, cx - 220, cy - 140);               // «уводим» план
    await page.keyboard.up('Space');
    await sleep(600);
    await clickTool(page, 'fit'); await sleep(1200);              // возвращаем в экран
  },
  async view3d(page){
    await drawSampleRoom(page);
    await clickTool(page, 'view3d');
    await page.waitForFunction(() => window.VIEW3D && VIEW3D.active && VIEW3D.renderer, null, { timeout: 15000 });
    await sleep(900);
    const c = await canvasRect(page); const cx = c.x + c.width/2, cy = c.y + c.height/2;
    await moveCursor(page, cx - 120, cy); await press(page);       // орбита вращением
    for (const dx of [-60, 40, 120, 60]) { await moveCursor(page, cx + dx, cy - 20, 18); }
    await release(page); await sleep(1000);
    await clickTool(page, 'view3d'); await sleep(600);             // назад в план
  },
  // ── Черчение ──
  async line(page){ const {cx,cy}=cc(await canvasRect(page)); await clickTool(page,'line'); await clickAt(page,cx-160,cy+80); await sleep(300); await clickAt(page,cx+160,cy-70); await sleep(1200); },
  async arc(page){ const {cx,cy}=cc(await canvasRect(page)); await clickTool(page,'arc'); await clickAt(page,cx-150,cy+40); await sleep(280); await clickAt(page,cx+150,cy+40); await sleep(280); await clickAt(page,cx,cy-110); await sleep(1200); },
  async circle(page){ const {cx,cy}=cc(await canvasRect(page)); await clickTool(page,'circle'); await dragTo(page,cx,cy,cx+130,cy+90); await sleep(1300); },
  // ── Редактирование (над выбранной комнатой) ──
  async duplicate(page){ await selectRoom(page); await clickTool(page,'duplicate'); await sleep(1300); },
  async rotate(page){ await selectRoom(page); await clickTool(page,'rotate'); await sleep(600); await clickTool(page,'rotate'); await sleep(1000); },
  async mirror(page){ await selectRoom(page); await clickTool(page,'mirror'); await sleep(1300); },
  async 'bring-front'(page){ await selectRoom(page); await clickTool(page,'bring-front'); await sleep(1200); },
  async pin(page){ await selectRoom(page); await clickTool(page,'pin'); await sleep(1400); },
  async scale(page){ dialogAnswer='1.4'; await selectRoom(page); await clickTool(page,'scale'); await sleep(1400); },
  async offset(page){ dialogAnswer='0.4'; await selectRoom(page); await clickTool(page,'offset'); await sleep(1400); },
  // ── Отопление ──
  async radiator(page){ await drawSampleRoom(page); const {cx,cy}=cc(await canvasRect(page)); await clickTool(page,'radiator'); await clickAt(page,cx-170,cy); await sleep(1300); },
  async 'warm-floor'(page){ await selectRoom(page); await clickTool(page,'warm-floor'); await sleep(1400); },
  async boiler(page){ await drawSampleRoom(page); const {cx,cy}=cc(await canvasRect(page)); await clickTool(page,'boiler'); await clickAt(page,cx+180,cy-90); await sleep(1300); },
  async pipe(page){ await drawSampleRoom(page); const {cx,cy}=cc(await canvasRect(page)); await clickTool(page,'pipe'); for(const [dx,dy] of [[-150,60],[-40,60],[-40,-60],[120,-60]]){ await clickAt(page,cx+dx,cy+dy); await sleep(300);} await page.keyboard.press('Enter'); await sleep(1200); },
  async collector(page){ await drawSampleRoom(page); const {cx,cy}=cc(await canvasRect(page)); await clickTool(page,'collector'); await clickAt(page,cx+180,cy+90); await sleep(1300); },
  async thermostat(page){ await drawSampleRoom(page); const {cx,cy}=cc(await canvasRect(page)); await clickTool(page,'thermostat'); await clickAt(page,cx,cy); await sleep(1300); },
  // ── Помещения ──
  async 'area-tag'(page){ await drawSampleRoom(page); await clickTool(page,'area-tag'); await sleep(1500); },
  async perimeter(page){ await selectRoom(page); await clickTool(page,'perimeter'); await sleep(1400); },
  // ── Аннотации ──
  async dim(page){ const {cx,cy}=cc(await canvasRect(page)); await clickTool(page,'dim'); await clickAt(page,cx-150,cy+90); await sleep(280); await clickAt(page,cx+150,cy+90); await sleep(1300); },
  async text(page){ const {cx,cy}=cc(await canvasRect(page)); await clickTool(page,'text'); await clickAt(page,cx-80,cy); await sleep(400); await page.keyboard.type('Кухня',{delay:90}); await sleep(400); await page.keyboard.press('Enter'); await sleep(1200); },
  async leader(page){ await drawSampleRoom(page); const {cx,cy}=cc(await canvasRect(page)); await clickTool(page,'leader'); await clickAt(page,cx,cy); await sleep(280); await clickAt(page,cx+170,cy-110); await sleep(1300); },
  async 'heat-label'(page){ await drawSampleRoom(page); await clickTool(page,'heat-label'); await sleep(1500); },
  async 'level-marker'(page){ const {cx,cy}=cc(await canvasRect(page)); await clickTool(page,'level-marker'); await clickAt(page,cx-120,cy-90); await sleep(280); await clickAt(page,cx+120,cy-90); await sleep(1300); },
  async 'section-line'(page){ const {cx,cy}=cc(await canvasRect(page)); await clickTool(page,'section-line'); await clickAt(page,cx-150,cy); await sleep(280); await clickAt(page,cx+150,cy); await sleep(1300); },
  async 'grid-line'(page){ const {cx,cy}=cc(await canvasRect(page)); await clickTool(page,'grid-line'); await clickAt(page,cx,cy-120); await sleep(280); await clickAt(page,cx,cy+120); await sleep(1300); },
  async 'spot-elevation'(page){ await drawSampleRoom(page); const {cx,cy}=cc(await canvasRect(page)); await clickTool(page,'spot-elevation'); await clickAt(page,cx,cy); await sleep(1300); },
  async 'tag-room'(page){ await drawSampleRoom(page); const {cx,cy}=cc(await canvasRect(page)); await clickTool(page,'tag-room'); await clickAt(page,cx,cy); await sleep(1300); },
  async 'north-arrow'(page){ const {cx,cy}=cc(await canvasRect(page)); await clickTool(page,'north-arrow'); await clickAt(page,cx+180,cy-120); await sleep(1300); },
  // ── Измерения ──
  async distance(page){ await drawSampleRoom(page); const {cx,cy}=cc(await canvasRect(page)); await clickTool(page,'distance'); await clickAt(page,cx-140,cy-80); await sleep(280); await clickAt(page,cx+140,cy+80); await sleep(1300); },
  async 'area-measure'(page){ const {cx,cy}=cc(await canvasRect(page)); await clickTool(page,'area-measure'); for(const [dx,dy] of [[-140,-90],[150,-80],[120,100],[-100,110]]){ await clickAt(page,cx+dx,cy+dy); await sleep(300);} await page.keyboard.press('Enter'); await sleep(1300); },
  // ── Вид ──
  async hand(page){ await drawSampleRoom(page); const {cx,cy}=cc(await canvasRect(page)); await clickTool(page,'hand'); await dragTo(page,cx,cy,cx-140,cy+90); await sleep(400); await dragTo(page,cx-140,cy+90,cx+60,cy-40); await sleep(1000); },
  async snap(page){ await drawSampleRoom(page); await clickTool(page,'snap'); await sleep(700); await clickTool(page,'snap'); await sleep(900); },
  async grid(page){ await drawSampleRoom(page); await clickTool(page,'grid'); await sleep(800); await clickTool(page,'grid'); await sleep(900); },
  async dims(page){ await drawSampleRoom(page); await clickTool(page,'dims'); await sleep(700); await clickTool(page,'dims'); await sleep(900); },
  async schedule(page){ await drawSampleRoom(page); await clickTool(page,'schedule'); await sleep(1700); },
};

/* ── Поиск установленного chromium (на случай рассинхрона версии Playwright) ─ */
function findChromium(){
  if (process.env.PW_CHROMIUM && fs.existsSync(process.env.PW_CHROMIUM)) return process.env.PW_CHROMIUM;
  const base = path.join(os.homedir(), 'Library', 'Caches', 'ms-playwright');
  const cands = [];
  try {
    const dirs = fs.readdirSync(base);
    for (const d of dirs) if (d.startsWith('chromium_headless_shell')) {   // headless-shell пишет видео и без GUI
      for (const sub of fs.readdirSync(path.join(base, d))) {
        const bin = path.join(base, d, sub, 'chrome-headless-shell');
        if (fs.existsSync(bin)) cands.push(bin);
      }
    }
    for (const d of dirs) if (d.startsWith('chromium-')) {                  // полный chromium (fallback)
      for (const rel of [['chrome-mac','Chromium.app','Contents','MacOS','Chromium'], ['chrome-linux','chrome']]) {
        const bin = path.join(base, d, ...rel);
        if (fs.existsSync(bin)) cands.push(bin);
      }
    }
  } catch { /* нет кэша — вернём null, Playwright возьмёт свой браузер */ }
  return cands[0] || null;
}

/* ── Постобработка: системный ffmpeg или тот, что идёт в комплекте с Playwright ─ */
function findFfmpeg(){
  try { if (spawnSync('ffmpeg', ['-version'], { stdio: 'ignore' }).status === 0) return 'ffmpeg'; } catch { /* нет системного */ }
  const base = path.join(os.homedir(), 'Library', 'Caches', 'ms-playwright');
  try {
    for (const d of fs.readdirSync(base)) if (d.startsWith('ffmpeg-'))
      for (const n of ['ffmpeg-mac', 'ffmpeg-linux', 'ffmpeg-win.exe']) {
        const p = path.join(base, d, n); if (fs.existsSync(p)) return p;
      }
  } catch { /* нет кэша */ }
  return null;
}
/* trimStart — сколько секунд отрезать с начала (загрузка сайта до открытия редактора).
   Два прохода: (1) убрать заставку + масштаб; (2) оставить последние ~8с —
   действие инструмента у нас в конце сценария (сначала рисуем комнату, потом жмём). */
const CLIP_TAIL = 8;
async function finalize(rawPath, id, ff, trimStart){
  const out = path.join(OUT_DIR, id + '.webm');
  if (ff) {
    const tmp = path.join(TMP_DIR, id + '_t.webm');
    const a1 = [];
    if (trimStart > 0.05) a1.push('-ss', trimStart.toFixed(2));
    a1.push('-i', rawPath, '-vf', 'scale=640:-2', '-c:v', 'libvpx', '-b:v', '480k', '-an', '-y', tmp);
    const r1 = spawnSync(ff, a1, { stdio: 'ignore' });
    if (r1.status === 0) {
      const r2 = spawnSync(ff, ['-sseof', '-' + CLIP_TAIL, '-i', tmp, '-c:v', 'libvpx', '-b:v', '480k', '-an', '-y', out], { stdio: 'ignore' });
      if (r2.status === 0) { try { await fsp.rm(tmp, { force: true }); } catch {} return out; }
      await fsp.copyFile(tmp, out); return out;   // 2-й проход не удался — отдаём результат 1-го
    }
    console.warn('  ⚠ ffmpeg упал — кладу исходный webm');
  }
  await fsp.copyFile(rawPath, out);
  return out;
}

/* ── Манифест TOOL_VIDEOS = все .webm, реально лежащие в assets/tool-videos ── */
async function updateManifest(){
  const f = path.join(ROOT, 'assets', 'app.js');
  let src = await fsp.readFile(f, 'utf8');
  let files = [];
  try { files = (await fsp.readdir(OUT_DIR)).filter(n => n.endsWith('.webm')).map(n => n.replace(/\.webm$/, '')).sort(); } catch { /* пусто */ }
  const body = files.map(id => JSON.stringify(id) + ':1').join(',');
  const next = 'const TOOL_VIDEOS = {' + body + '};';
  const re = /const TOOL_VIDEOS = \{[^}]*\};/;
  if (!re.test(src)) { console.warn('⚠ не нашёл TOOL_VIDEOS в app.js — манифест не обновлён'); return; }
  await fsp.writeFile(f, src.replace(re, next));
  console.log('✓ манифест TOOL_VIDEOS (' + files.length + '):', files.join(', ') || '(пусто)');
}

/* ── main ────────────────────────────────────────────────────────────────── */
const want = process.argv.slice(2);
const ids = (want.length ? want : Object.keys(SCENARIOS)).filter(id => {
  if (!SCENARIOS[id]) { console.warn('нет сценария для', id, '— пропуск'); return false; }
  return true;
});

const { chromium } = await loadPlaywright();
await fsp.mkdir(OUT_DIR, { recursive: true });
await fsp.mkdir(TMP_DIR, { recursive: true });
const server = await startServer();
const ff = findFfmpeg();
console.log(`Playwright ✓  ffmpeg ${ff ? '✓' : '✗ (исходный webm)'}  инструментов: ${ids.length}`);

const exe = findChromium();
if (exe) console.log('chromium:', exe.replace(os.homedir(), '~'));
const browser = await chromium.launch(exe ? { executablePath: exe } : {});
const done = [];
for (const id of ids) {
  process.stdout.write(`● ${id} … `);
  cur = { x: VW / 2, y: VH / 2 };
  const ctx = await browser.newContext({ viewport: { width: VW, height: VH }, recordVideo: { dir: TMP_DIR, size: { width: VW, height: VH } } });
  await ctx.addInitScript(INIT);
  const page = await ctx.newPage();
  page.on('dialog', d => { try { d.accept(d.type() === 'prompt' ? dialogAnswer : undefined); } catch (e) {} }); // авто-ответ scale/offset
  dialogAnswer = '2';
  let ok = false, readyMs = 0;
  try {
    const tGoto = Date.now();
    await page.goto(`http://localhost:${PORT}/index.html`, { waitUntil: 'domcontentloaded' });
    await page.waitForFunction(() => typeof window.openEditor === 'function', null, { timeout: 15000 });
    await page.evaluate(() => window.openEditor());
    await page.waitForSelector('#ed-canvas', { timeout: 8000 });
    await sleep(450);                                                              // дать редактору отрисоваться
    await page.evaluate(() => { const m = document.getElementById('__recmask'); if (m) m.remove(); }); // снять тёмную маску
    readyMs = Date.now() - tGoto;                                                  // столько длилась загрузка (её отрежем)
    await page.addStyleTag({ content: '.et-tip-wrap{display:none!important}' });   // не показывать hover-карточки в ролике
    await page.evaluate(CURSOR);
    await sleep(400);
    await SCENARIOS[id](page);
    await sleep(300);
    ok = true;
  } catch (e) {
    console.log('✗', (e.message || e).split('\n')[0]);
  }
  const video = page.video();
  await ctx.close();                       // видео дописывается только после close()
  if (ok && video) {
    try {
      const raw = await video.path();
      const trim = Math.max(0, readyMs / 1000 - 0.1);   // отрезаем загрузку сайта до открытия редактора
      await finalize(raw, id, ff, trim);
      done.push(id); console.log('✓');
    } catch (e) { console.log('✗ финализация:', e.message); }
  }
}
await browser.close();
server.close();
await updateManifest();
try { await fsp.rm(TMP_DIR, { recursive: true, force: true }); } catch {}
console.log(`\nГотово. Записано: ${done.length}/${ids.length}${done.length ? ' → assets/tool-videos/' : ''}`);
process.exit(0);
