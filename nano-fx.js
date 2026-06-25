/* ============================================================================
   NanoFX — nano-tech "materialization" animation system
   ----------------------------------------------------------------------------
   A wave-front of nanites sweeps across an element: behind the front the element
   is revealed (clip-path mask), panels snap into place (canvas tessellation),
   particles settle along bezier paths, and a specular blip seals the finish.

   • One shared <canvas>, one rAF loop (paused when idle / document.hidden).
   • Object-pooled particles, zero per-frame allocation.
   • Colour entirely from CSS vars  --nano-core/-gold/-accent/-deep/-edge.
   • 3 quality tiers + reduced-motion fallback, live FPS watchdog.
   • Animates only transform / opacity / clip-path → no layout, no CLS.

   Public API:  window.NanoFX
     .assemble(el, opts) -> Promise
     .disassemble(el, opts) -> Promise
     .reveal(el, opts)            // assemble when scrolled into view (IO)
     .text(el, opts)              // per-glyph materialization
     .init()                      // scan DOM, wire data-attrs + triggers
     .config(globalOpts)          // set global defaults
     .refresh()                   // re-scan after dynamic DOM
   ========================================================================== */
(function (w, d) {
  'use strict';
  if (w.NanoFX) return;

  /* ------------------------------------------------------------------ utils */
  var clamp = function (v, a, b) { return v < a ? a : v > b ? b : v; };
  var rand  = function (a, b) { return a + Math.random() * (b - a); };
  var lerp  = function (a, b, t) { return a + (b - a) * t; };
  var easeOutCubic = function (t) { return 1 - Math.pow(1 - t, 3); };
  var expoOut = function (t) { return t >= 1 ? 1 : 1 - Math.pow(2, -10 * t); };
  var qbez = function (s, c, e, t) { var u = 1 - t; return u * u * s + 2 * u * t * c + t * t * e; };
  var now = function () { return performance.now(); };

  /* --------------------------------------------------------------- defaults */
  var DEFAULTS = {
    preset: 'standard',
    dir: 'up',
    origin: '50% 50%',
    duration: 880,
    stagger: 60,
    particles: { count: 'auto', size: [1, 3], speed: 1, curve: 0.55, trail: 0.8 },
    tessellation: { shape: 'hex', cell: 26, wave: 1 },
    glow: { edge: 2, intensity: 1 },
    easing: 'expo.out'
  };

  var PRESETS = {
    subtle:    { duration: 460, density: 0.35, trail: false, tess: false, blip: false },
    standard:  { duration: 880, density: 1.0,  trail: true,  tess: true,  blip: true  },
    cinematic: { duration: 1250, density: 1.7, trail: true,  tess: true,  blip: true  }
  };

  var GLOBAL = JSON.parse(JSON.stringify(DEFAULTS));

  /* --------------------------------------------------------------- palette  */
  var COLORS = ['#fff6e9', '#ffd27a', '#f59e0b', '#ff6b35'];
  function readPalette() {
    try {
      var cs = getComputedStyle(d.documentElement);
      var pick = function (name, fb) { var v = cs.getPropertyValue(name).trim(); return v || fb; };
      COLORS = [
        pick('--nano-core', '#fff6e9'),
        pick('--nano-gold', '#ffd27a'),
        pick('--nano-accent', '#f59e0b'),
        pick('--nano-deep', '#ff6b35')
      ];
      EDGE_COL = pick('--nano-edge', '#ffe3a6');
    } catch (e) {}
  }
  var EDGE_COL = '#ffe3a6';

  /* ----------------------------------------------------------------- tiers  */
  var reduceMotion = w.matchMedia && w.matchMedia('(prefers-reduced-motion: reduce)').matches;
  var coarse = w.matchMedia && w.matchMedia('(pointer: coarse)').matches;
  var TIERS = {
    high:    { cap: 1500, emit: 1.0 },
    mid:     { cap: 900,  emit: 0.6 },
    low:     { cap: 400,  emit: 0.3 },
    reduced: { cap: 0,    emit: 0 }
  };
  function detectTier() {
    if (reduceMotion) return 'reduced';
    var cores = navigator.hardwareConcurrency || 4;
    var mem = navigator.deviceMemory || 4;
    var mobile = coarse || /Mobi|Android|iPhone|iPad/i.test(navigator.userAgent);
    if (mobile || cores <= 4 || mem <= 3) return 'low';
    if (cores <= 6 || mem <= 4) return 'mid';
    return 'high';
  }
  var TIER = detectTier();

  /* --------------------------------------------------------- shared canvas  */
  var canvas, ctx, DPR = 1, VW = 0, VH = 0, sprites = [], edgeSprite = null;
  function dpr() { return Math.min(2, w.devicePixelRatio || 1); }

  function makeSprite(color) {
    var s = d.createElement('canvas'); s.width = s.height = 32;
    var c = s.getContext('2d');
    var g = c.createRadialGradient(16, 16, 0, 16, 16, 16);
    g.addColorStop(0, color);
    g.addColorStop(0.35, color);
    g.addColorStop(1, 'rgba(255,255,255,0)');
    c.fillStyle = g; c.beginPath(); c.arc(16, 16, 16, 0, 7); c.fill();
    return s;
  }
  function buildSprites() {
    sprites = COLORS.map(function (col) {
      // recolour via temp fill using the hex directly in gradient
      var s = d.createElement('canvas'); s.width = s.height = 32;
      var c = s.getContext('2d');
      var g = c.createRadialGradient(16, 16, 0, 16, 16, 16);
      g.addColorStop(0, '#ffffff');
      g.addColorStop(0.25, col);
      g.addColorStop(1, hexA(col, 0));
      c.fillStyle = g; c.beginPath(); c.arc(16, 16, 16, 0, 7); c.fill();
      return s;
    });
    edgeSprite = makeSprite(EDGE_COL);
  }
  function hexA(hex, a) {
    hex = hex.replace('#', '');
    if (hex.length === 3) hex = hex.replace(/(.)/g, '$1$1');
    var n = parseInt(hex, 16);
    return 'rgba(' + ((n >> 16) & 255) + ',' + ((n >> 8) & 255) + ',' + (n & 255) + ',' + a + ')';
  }

  function ensureCanvas() {
    if (canvas || TIER === 'reduced') return;
    canvas = d.createElement('canvas');
    canvas.id = 'nano-canvas';
    canvas.setAttribute('aria-hidden', 'true');
    (d.body || d.documentElement).appendChild(canvas);
    ctx = canvas.getContext('2d', { alpha: true });
    readPalette(); buildSprites();
    resize();
    w.addEventListener('resize', resize, { passive: true });
  }
  function resize() {
    if (!canvas) return;
    DPR = dpr(); VW = w.innerWidth; VH = w.innerHeight;
    canvas.width = Math.floor(VW * DPR); canvas.height = Math.floor(VH * DPR);
    canvas.style.width = VW + 'px'; canvas.style.height = VH + 'px';
  }

  /* ------------------------------------------------------------ particle pool */
  var POOL = [], poolCap = 0, activeCount = 0;
  function initPool() {
    poolCap = TIERS[TIER].cap;
    POOL = new Array(poolCap);
    for (var i = 0; i < poolCap; i++) {
      POOL[i] = { on: false, sx: 0, sy: 0, cx: 0, cy: 0, tx: 0, ty: 0,
                  px: 0, py: 0, t: 0, dur: 1, size: 1, col: 0, trail: 0, scout: 0 };
    }
  }
  function spawn(sx, sy, tx, ty, opt) {
    if (activeCount >= poolCap) return null;
    var p = null, i;
    for (i = 0; i < poolCap; i++) { if (!POOL[i].on) { p = POOL[i]; break; } }
    if (!p) return null;
    var dist = Math.hypot(tx - sx, ty - sy);
    var nx = -(ty - sy) / (dist || 1), ny = (tx - sx) / (dist || 1); // perpendicular
    var curve = opt.curve * dist * rand(-1, 1);
    p.on = true; p.sx = sx; p.sy = sy; p.tx = tx; p.ty = ty;
    p.cx = (sx + tx) / 2 + nx * curve; p.cy = (sy + ty) / 2 + ny * curve;
    p.px = sx; p.py = sy;
    p.t = 0; p.dur = rand(0.55, 1) * opt.life;
    p.size = rand(opt.size[0], opt.size[1]);
    p.col = opt.scout ? 0 : (Math.random() < 0.5 ? 2 : (Math.random() < 0.6 ? 1 : 3));
    p.trail = opt.trail; p.scout = opt.scout ? 1 : 0;
    activeCount++;
    return p;
  }
  function stepParticle(p, dt) {
    p.t += dt / p.dur;
    if (p.t >= 1) { p.on = false; activeCount--; return; }
    var e = easeOutCubic(p.t);
    p.px = qbez(p.sx, p.cx, p.tx, e);
    p.py = qbez(p.sy, p.cy, p.ty, e);
  }
  function drawParticle(p) {
    var a = Math.sin(Math.PI * p.t) * (p.scout ? 0.5 : 1);
    if (a <= 0.01) return;
    var spr = sprites[p.col] || sprites[2];
    var s = p.size * 3.2;
    ctx.globalAlpha = a;
    if (p.trail > 0) {
      ctx.globalAlpha = a * 0.4 * p.trail;
      ctx.drawImage(spr, lerp(p.px, p.sx, 0.18) - s / 2, lerp(p.py, p.sy, 0.18) - s / 2, s, s);
      ctx.globalAlpha = a;
    }
    ctx.drawImage(spr, p.px - s / 2, p.py - s / 2, s, s);
  }

  /* --------------------------------------------------------------- effects  */
  var effects = [], running = false, lastT = 0;
  var fpsBuf = [], fpsIdx = 0, watchT = 0;

  function startLoop() {
    if (running || TIER === 'reduced') return;
    running = true; lastT = now();
    requestAnimationFrame(frame);
  }
  function frame(ts) {
    var dt = Math.min(50, ts - lastT); lastT = ts;
    if (d.hidden) { running = false; return; }   // pause when tab hidden

    // FPS watchdog
    fpsBuf[fpsIdx = (fpsIdx + 1) % 30] = dt;
    if (ts - watchT > 1000) { watchT = ts; watchdog(); }

    ctx.clearRect(0, 0, canvas.width, canvas.height);
    ctx.save();
    ctx.scale(DPR, DPR);
    ctx.globalCompositeOperation = 'lighter';

    var i;
    // advance + draw effects (front, tessellation, edge, blip)
    for (i = effects.length - 1; i >= 0; i--) {
      var done = effects[i].update(dt, ts);
      if (done) effects.splice(i, 1);
    }
    // advance + draw particles
    for (i = 0; i < poolCap; i++) {
      var p = POOL[i];
      if (p.on) { stepParticle(p, dt); if (p.on) drawParticle(p); }
    }
    ctx.restore();

    if (effects.length === 0 && activeCount === 0) { running = false; return; }
    requestAnimationFrame(frame);
  }
  function watchdog() {
    var sum = 0, n = 0;
    for (var i = 0; i < fpsBuf.length; i++) { if (fpsBuf[i]) { sum += fpsBuf[i]; n++; } }
    if (n < 10) return;
    var avg = sum / n; // ms/frame
    if (avg > 26 && TIER === 'high') downgrade('mid');
    else if (avg > 30 && TIER === 'mid') downgrade('low');
  }
  function downgrade(to) {
    TIER = to; var cap = TIERS[to].cap;
    if (cap < poolCap) { // shrink: deactivate overflow
      for (var i = cap; i < poolCap; i++) { if (POOL[i] && POOL[i].on) { POOL[i].on = false; activeCount--; } }
    }
    poolCap = cap;
  }

  /* ------------------------------------------------------- geometry helpers */
  function rectOf(el) {
    var r = el.getBoundingClientRect();
    return { x: r.left, y: r.top, w: r.width, h: r.height, sc: w.scrollY };
  }
  // live rect that follows scroll without re-measuring (no layout read per frame)
  function liveRect(r0) {
    var dy = r0.sc - w.scrollY;
    return { x: r0.x, y: r0.y + dy, w: r0.w, h: r0.h };
  }
  function parseOrigin(str, r) {
    var m = (str || '50% 50%').trim().split(/\s+/);
    var ox = parseFloat(m[0]) / 100, oy = parseFloat(m[1] != null ? m[1] : m[0]) / 100;
    return { x: r.x + ox * r.w, y: r.y + oy * r.h, ox: ox, oy: oy };
  }
  // clip-path string for visible fraction f (0=hidden .. 1=full)
  function clipFor(dir, f, originPct) {
    var inv = (100 * (1 - f)).toFixed(2) + '%';
    switch (dir) {
      case 'left':   return 'inset(0% ' + inv + ' 0% 0%)';
      case 'right':  return 'inset(0% 0% 0% ' + inv + ')';
      case 'up':     return 'inset(' + inv + ' 0% 0% 0%)';
      case 'down':   return 'inset(0% 0% ' + inv + ' 0%)';
      case 'center': var h = (50 * (1 - f)).toFixed(2) + '%'; return 'inset(' + h + ' ' + h + ' ' + h + ' ' + h + ')';
      case 'radial': return 'circle(' + (f * 75).toFixed(2) + '% at ' + originPct + ')';
      default:       return 'inset(' + inv + ' 0% 0% 0%)';
    }
  }
  // front line / circle in screen coords for visible fraction f
  function frontGeom(dir, r, f, origin) {
    switch (dir) {
      case 'left':   return { type: 'v', x: r.x + f * r.w, y0: r.y, y1: r.y + r.h };
      case 'right':  return { type: 'v', x: r.x + (1 - f) * r.w, y0: r.y, y1: r.y + r.h };
      case 'up':     return { type: 'h', y: r.y + (1 - f) * r.h, x0: r.x, x1: r.x + r.w };
      case 'down':   return { type: 'h', y: r.y + f * r.h, x0: r.x, x1: r.x + r.w };
      case 'center':
      case 'radial': return { type: 'r', cx: origin.x, cy: origin.y, rad: f * Math.hypot(r.w, r.h) * 0.75 };
      default:       return { type: 'h', y: r.y + (1 - f) * r.h, x0: r.x, x1: r.x + r.w };
    }
  }
  // a settle target behind the front (already-revealed region)
  function settleTarget(dir, r, f, origin) {
    var pad = 6;
    switch (dir) {
      case 'left':   return { x: r.x + rand(0, f) * r.w, y: rand(r.y + pad, r.y + r.h - pad) };
      case 'right':  return { x: r.x + (1 - rand(0, f)) * r.w, y: rand(r.y + pad, r.y + r.h - pad) };
      case 'up':     return { x: rand(r.x + pad, r.x + r.w - pad), y: r.y + (1 - rand(0, f)) * r.h };
      case 'down':   return { x: rand(r.x + pad, r.x + r.w - pad), y: r.y + rand(0, f) * r.h };
      default:
        var ang = rand(0, 6.28318), rr = rand(0, f) * Math.hypot(r.w, r.h) * 0.7;
        return { x: clamp(origin.x + Math.cos(ang) * rr, r.x, r.x + r.w),
                 y: clamp(origin.y + Math.sin(ang) * rr, r.y, r.y + r.h) };
    }
  }

  /* ------------------------------------------------- tessellation cell grid */
  function buildCells(dir, r, cell, origin) {
    var cells = [], maxD = Math.hypot(r.w, r.h);
    var cols = Math.min(40, Math.ceil(r.w / cell)), rows = Math.min(40, Math.ceil(r.h / cell));
    cols = Math.max(1, cols); rows = Math.max(1, rows);
    var cw = r.w / cols, ch = r.h / rows;
    for (var yi = 0; yi < rows; yi++) {
      for (var xi = 0; xi < cols; xi++) {
        var cx = r.x + (xi + 0.5) * cw, cy = r.y + (yi + 0.5) * ch, thr;
        switch (dir) {
          case 'left':  thr = (cx - r.x) / r.w; break;
          case 'right': thr = (r.x + r.w - cx) / r.w; break;
          case 'up':    thr = (r.y + r.h - cy) / r.h; break;
          case 'down':  thr = (cy - r.y) / r.h; break;
          default:      thr = Math.hypot(cx - origin.x, cy - origin.y) / (maxD * 0.75);
        }
        cells.push({ cx: cx - r.x, cy: cy - r.y, w: cw, h: ch, thr: clamp(thr, 0, 1), snap: -1 });
        if (cells.length >= 220) return cells;
      }
    }
    return cells;
  }

  /* ----------------------------------------------------------- Effect class */
  function Effect(el, opts, reverse) {
    this.el = el; this.reverse = !!reverse;
    var preset = PRESETS[opts.preset] || PRESETS.standard;
    this.dir = opts.dir; this.dur = (opts.duration || preset.duration) * (reverse ? 0.65 : 1);
    this.preset = preset; this.intensity = (opts.glow && opts.glow.intensity) || 1;
    this.pp = opts.particles || GLOBAL.particles;
    this.r0 = rectOf(el);
    this.origin = parseOrigin(opts.origin, this.r0);
    this.originPct = (this.origin.ox * 100).toFixed(0) + '% ' + (this.origin.oy * 100).toFixed(0) + '%';
    this.cell = (opts.tessellation && opts.tessellation.cell) || 26;
    this.cells = preset.tess ? buildCells(this.dir, this.r0, this.cell, this.origin) : [];
    this.start = now(); this.done = false; this.blip = 0;
    this.emitAcc = 0;
    el.classList.add('nano-running');
    el.style.willChange = 'opacity, clip-path, transform';
  }
  Effect.prototype.update = function (dt, ts) {
    var raw = clamp((ts - this.start) / this.dur, 0, 1);
    var p = expoOut(raw);                       // eased front progress
    var f = this.reverse ? 1 - p : p;           // visible fraction
    var r = liveRect(this.r0);
    var el = this.el;

    // --- mask + opacity (write only; no layout read) ---
    var clip = clipFor(this.dir, f, this.originPct);
    el.style.clipPath = clip; el.style.webkitClipPath = clip;
    el.style.opacity = this.reverse ? (0.15 + 0.85 * f) : clamp(0.12 + 1.15 * f, 0, 1);

    // --- tessellation snaps ---
    var fg = frontGeom(this.dir, r, f, this.origin), i, c;
    if (this.cells.length) {
      ctx.save();
      for (i = 0; i < this.cells.length; i++) {
        c = this.cells[i];
        var lit = this.reverse ? (f <= c.thr) : (f >= c.thr);
        if (lit && c.snap < 0) c.snap = ts;
        if (c.snap > 0) {
          var sp = clamp((ts - c.snap) / 200, 0, 1);
          var ca = (1 - sp) * 0.5 * this.intensity;
          if (ca > 0.01) {
            var sc = lerp(0.85, 1, easeOutCubic(sp));
            var x = r.x + c.cx, y = r.y + c.cy, ww = c.w * sc, hh = c.h * sc;
            ctx.globalAlpha = ca;
            ctx.strokeStyle = EDGE_COL; ctx.lineWidth = 1;
            ctx.strokeRect(x - ww / 2, y - hh / 2, ww, hh);
          }
        }
      }
      ctx.restore();
    }

    // --- particle emission along the front ---
    var emit = TIERS[TIER].emit * this.preset.density * this.intensity;
    if (raw < 1 && emit > 0) {
      this.emitAcc += emit * (dt / 16) * 6;
      var n = this.emitAcc | 0; this.emitAcc -= n;
      for (i = 0; i < n; i++) {
        var s = frontPoint(fg);
        var t = settleTarget(this.dir, r, f, this.origin);
        spawn(s.x, s.y, t.x, t.y, {
          size: this.pp.size, curve: this.pp.curve, life: rand(380, 620),
          trail: this.preset.trail ? this.pp.trail : 0, scout: false
        });
        if (Math.random() < 0.12) { // scout running ahead
          var sc2 = frontPoint(fg), ahead = aheadPoint(this.dir, r, f, this.origin);
          spawn(sc2.x, sc2.y, ahead.x, ahead.y, { size: this.pp.size, curve: this.pp.curve * 1.6,
            life: rand(260, 420), trail: this.preset.trail ? this.pp.trail : 0, scout: true });
        }
      }
    }

    // --- bright leading edge glow ---
    if (raw > 0 && raw < 1) drawEdge(fg, this.intensity);

    // --- finish specular blip ---
    if (raw >= 1 && !this.reverse) {
      if (this.preset.blip && this.blip === 0) this.blip = ts;
      if (this.blip > 0) {
        var bp = clamp((ts - this.blip) / 220, 0, 1);
        if (bp < 1) drawBlip(this.dir, r, bp, this.intensity);
        else return this.finish();
      } else { return this.finish(); }
    }
    if (raw >= 1 && this.reverse) return this.finish();
    return false;
  };
  Effect.prototype.finish = function () {
    var el = this.el;
    el.style.clipPath = ''; el.style.webkitClipPath = '';
    el.style.willChange = ''; el.classList.remove('nano-running', 'nano-armed');
    if (this.reverse) { el.style.opacity = ''; }
    else { el.style.opacity = ''; }
    this.done = true;
    if (this._res) this._res();
    return true;
  };

  function frontPoint(fg) {
    if (fg.type === 'v') return { x: fg.x, y: rand(fg.y0, fg.y1) };
    if (fg.type === 'h') return { x: rand(fg.x0, fg.x1), y: fg.y };
    var a = rand(0, 6.28318); return { x: fg.cx + Math.cos(a) * fg.rad, y: fg.cy + Math.sin(a) * fg.rad };
  }
  function aheadPoint(dir, r, f, origin) {
    var d2 = 26;
    switch (dir) {
      case 'left':  return { x: r.x + Math.min(1, f + 0.12) * r.w + d2, y: rand(r.y, r.y + r.h) };
      case 'right': return { x: r.x + Math.max(0, 1 - f - 0.12) * r.w - d2, y: rand(r.y, r.y + r.h) };
      case 'up':    return { x: rand(r.x, r.x + r.w), y: r.y + Math.max(0, 1 - f - 0.12) * r.h - d2 };
      case 'down':  return { x: rand(r.x, r.x + r.w), y: r.y + Math.min(1, f + 0.12) * r.h + d2 };
      default:      var a = rand(0, 6.28318), rr = (f + 0.12) * Math.hypot(r.w, r.h) * 0.75;
                    return { x: origin.x + Math.cos(a) * rr, y: origin.y + Math.sin(a) * rr };
    }
  }
  function drawEdge(fg, inten) {
    ctx.save(); ctx.globalAlpha = clamp(0.55 * inten, 0, 1);
    var s = edgeSprite, sz = 18;
    if (fg.type === 'v') {
      for (var y = fg.y0; y <= fg.y1; y += 10) ctx.drawImage(s, fg.x - sz / 2, y - sz / 2, sz, sz);
      ctx.globalAlpha = clamp(0.9 * inten, 0, 1);
      ctx.fillStyle = EDGE_COL; ctx.fillRect(fg.x - 0.75, fg.y0, 1.5, fg.y1 - fg.y0);
    } else if (fg.type === 'h') {
      for (var x = fg.x0; x <= fg.x1; x += 10) ctx.drawImage(s, x - sz / 2, fg.y - sz / 2, sz, sz);
      ctx.globalAlpha = clamp(0.9 * inten, 0, 1);
      ctx.fillStyle = EDGE_COL; ctx.fillRect(fg.x0, fg.y - 0.75, fg.x1 - fg.x0, 1.5);
    } else {
      ctx.globalAlpha = clamp(0.7 * inten, 0, 1);
      ctx.strokeStyle = EDGE_COL; ctx.lineWidth = 2;
      ctx.beginPath(); ctx.arc(fg.cx, fg.cy, fg.rad, 0, 6.28318); ctx.stroke();
    }
    ctx.restore();
  }
  function drawBlip(dir, r, bp, inten) {
    ctx.save();
    var a = Math.sin(Math.PI * bp) * 0.4 * inten; ctx.globalAlpha = a;
    var g, pos;
    if (dir === 'left' || dir === 'right') {
      pos = r.x + bp * r.w; g = ctx.createLinearGradient(pos - 60, 0, pos + 60, 0);
      g.addColorStop(0, hexA(EDGE_COL, 0)); g.addColorStop(0.5, EDGE_COL); g.addColorStop(1, hexA(EDGE_COL, 0));
      ctx.fillStyle = g; ctx.fillRect(r.x, r.y, r.w, r.h);
    } else {
      pos = r.y + bp * r.h; g = ctx.createLinearGradient(0, pos - 60, 0, pos + 60);
      g.addColorStop(0, hexA(EDGE_COL, 0)); g.addColorStop(0.5, EDGE_COL); g.addColorStop(1, hexA(EDGE_COL, 0));
      ctx.fillStyle = g; ctx.fillRect(r.x, r.y, r.w, r.h);
    }
    ctx.restore();
  }

  /* ---------------------------------------------------------- normalize opts */
  function norm(el, o) {
    o = o || {};
    var ds = el.dataset || {};
    var out = {
      preset: o.preset || ds.nanoPreset || GLOBAL.preset,
      dir: o.dir || ds.nanoDir || GLOBAL.dir,
      origin: o.origin || ds.nanoOrigin || GLOBAL.origin,
      duration: o.duration || (ds.nanoDuration ? +ds.nanoDuration : 0) || 0,
      stagger: o.stagger != null ? o.stagger : (ds.nanoStagger ? +ds.nanoStagger : GLOBAL.stagger),
      delay: o.delay != null ? o.delay : (ds.nanoDelay ? +ds.nanoDelay : 0),
      particles: o.particles || GLOBAL.particles,
      tessellation: o.tessellation || GLOBAL.tessellation,
      glow: o.glow || GLOBAL.glow,
      color: o.color || ds.nanoColor || null
    };
    if (!out.duration) out.duration = (PRESETS[out.preset] || PRESETS.standard).duration;
    return out;
  }

  /* ------------------------------------------------------------- public ops */
  function fadeFallback(el, dir) {
    return new Promise(function (res) {
      el.classList.remove('nano-armed');
      el.style.transition = 'opacity .26s ease-out';
      el.style.opacity = '0';
      requestAnimationFrame(function () { el.style.opacity = '1';
        setTimeout(function () { el.style.transition = ''; el.style.opacity = ''; res(); }, 280); });
    });
  }

  function assemble(el, opts) {
    if (!el) return Promise.resolve();
    var o = norm(el, opts);
    if (TIER === 'reduced') return fadeFallback(el, o.dir);
    ensureCanvas();
    return new Promise(function (res) {
      var run = function () {
        var ef = new Effect(el, o, false);
        ef._res = res; effects.push(ef); startLoop();
      };
      if (o.delay) setTimeout(run, o.delay); else run();
    });
  }
  function disassemble(el, opts) {
    if (!el) return Promise.resolve();
    var o = norm(el, opts);
    if (TIER === 'reduced') { el.style.opacity = '0'; return new Promise(function (r) { setTimeout(function () { el.style.opacity = ''; r(); }, 200); }); }
    ensureCanvas();
    return new Promise(function (res) {
      var ef = new Effect(el, o, true); ef._res = res; effects.push(ef); startLoop();
    });
  }

  /* ---------------------------------------------------- IntersectionObserver */
  var io = null, ioMap = new WeakMap();
  function getIO() {
    if (io) return io;
    io = new IntersectionObserver(function (ents) {
      ents.forEach(function (e) {
        if (!e.isIntersecting) return;
        var cfg = ioMap.get(e.target); if (!cfg) return;
        if (cfg.fired && !cfg.repeat) return;
        cfg.fired = true;
        revealNow(e.target, cfg);
        if (!cfg.repeat) { io.unobserve(e.target); ioMap.delete(e.target); }
      });
    }, { rootMargin: '0px 0px 0px 0px', threshold: 0.12 });
    return io;
  }
  function revealNow(el, cfg) {
    if (cfg.group && cfg.idx) cfg.opts = Object.assign({}, cfg.opts, { delay: (cfg.opts.delay || 0) + cfg.idx * cfg.stagger });
    if (el.dataset.nano === 'text') return textOf(el, cfg.opts);
    // staggered children?
    var stag = cfg.opts.stagger;
    if (el.hasAttribute('data-nano-children')) {
      el.classList.remove('nano-armed'); // container stays visible; children assemble
      var kids = el.children, k;
      for (k = 0; k < kids.length; k++) {
        (function (kid, i) { kid.classList.add('nano-armed');
          assemble(kid, Object.assign({}, cfg.opts, { delay: (cfg.opts.delay || 0) + i * stag })); })(kids[k], k);
      }
      return;
    }
    assemble(el, cfg.opts);
  }
  function reveal(el, opts) {
    if (!el) return;
    var o = norm(el, opts);
    if (TIER === 'reduced') { return; } // never hide under reduced motion
    if (el.hasAttribute('data-nano-children')) {
      // children-stagger: keep the container visible, hide+assemble its children
      for (var i = 0; i < el.children.length; i++) el.children[i].classList.add('nano-armed');
    } else {
      el.classList.add('nano-armed');
    }
    ioMap.set(el, { opts: o, repeat: (el.dataset.nanoRepeat === 'true' || opts && opts.repeat) || false,
                    stagger: o.stagger, fired: false });
    getIO().observe(el);
  }

  /* -------------------------------------------------------------- text split */
  function textOf(el, opts) {
    if (el._nanoSplit) return Promise.resolve();
    el._nanoSplit = true;
    var o = norm(el, opts);
    var text = el.textContent;
    el.setAttribute('aria-label', text);
    el.classList.add('nano-text-wrap');
    el.textContent = '';
    var frag = d.createDocumentFragment(), glyphs = [];
    for (var i = 0; i < text.length; i++) {
      var ch = text[i];
      if (ch === ' ' || ch === '\n') { frag.appendChild(d.createTextNode(ch)); continue; }
      var sp = d.createElement('span'); sp.className = 'nano-glyph'; sp.textContent = ch;
      sp.setAttribute('aria-hidden', 'true'); frag.appendChild(sp); glyphs.push(sp);
    }
    el.appendChild(frag);
    if (TIER === 'reduced') { glyphs.forEach(function (g) { g.style.opacity = '1'; }); return Promise.resolve(); }
    ensureCanvas();
    var stag = o.stagger * 0.5 || 28;
    glyphs.forEach(function (g, i) {
      var dx = rand(-14, 14), dy = rand(8, 22);
      g.style.transform = 'translate(' + dx + 'px,' + dy + 'px) scale(.7)';
      g.style.filter = 'blur(6px)'; g.style.opacity = '0';
      setTimeout(function () {
        g.style.transition = 'transform .5s cubic-bezier(.2,.8,.2,1), opacity .4s ease, filter .4s ease';
        g.style.transform = 'translate(0,0) scale(1)'; g.style.filter = 'blur(0)'; g.style.opacity = '1';
        // particle convergence to glyph centre
        var rg = g.getBoundingClientRect(), gx = rg.left + rg.width / 2, gy = rg.top + rg.height / 2;
        for (var k = 0; k < (TIER === 'high' ? 5 : TIER === 'mid' ? 3 : 1); k++) {
          var a = rand(0, 6.28318), rr = rand(14, 40);
          spawn(gx + Math.cos(a) * rr, gy + Math.sin(a) * rr, gx, gy,
            { size: [1, 2], curve: 0.4, life: rand(320, 480), trail: 0.6, scout: false });
        }
        startLoop();
      }, i * stag);
    });
    return new Promise(function (r) { setTimeout(r, glyphs.length * stag + 600); });
  }

  /* ---------------------------------------------- CTA hover shimmer tracking */
  function wireHover(el) {
    if (el._nanoHover || TIER === 'reduced') return; el._nanoHover = true;
    el.addEventListener('mouseenter', function () {
      ensureCanvas();
      var r = el.getBoundingClientRect();
      var n = TIER === 'high' ? 18 : TIER === 'mid' ? 10 : 5;
      for (var i = 0; i < n; i++) {
        var sx = rand(r.left, r.right), sy = r.top + r.height;
        spawn(sx, sy, rand(r.left, r.right), rand(r.top, r.top + r.height),
          { size: [1, 2.2], curve: 0.3, life: rand(300, 520), trail: 0.7, scout: false });
      }
      startLoop();
    });
  }

  /* ------------------------------------------------- monkey-patch triggers   */
  function patch(name, opener, card, exitDir) {
    var orig = w[name];
    if (typeof orig !== 'function' || orig.__nano) return;
    var wrapped;
    if (opener) {
      wrapped = function () {
        var rv = orig.apply(this, arguments);
        if (TIER !== 'reduced') {
          var el = typeof card === 'function' ? card() : d.getElementById(card);
          if (el) requestAnimationFrame(function () { requestAnimationFrame(function () {
            assemble(el, { dir: 'radial', origin: '50% 42%', preset: 'cinematic', duration: 760 }); }); });
        }
        return rv;
      };
    } else {
      wrapped = function () {
        var el = typeof card === 'function' ? card() : d.getElementById(card);
        var args = arguments, self = this;
        if (TIER !== 'reduced' && el && el.offsetParent !== null) {
          return disassemble(el, { dir: exitDir || 'down', preset: 'standard', duration: 420 })
            .then(function () { return orig.apply(self, args); });
        }
        return orig.apply(self, args);
      };
    }
    wrapped.__nano = true; w[name] = wrapped;
  }
  function patchRenderStep() {
    var orig = w.renderStep;
    if (typeof orig !== 'function' || orig.__nano) return;
    var wrapped = function () {
      var rv = orig.apply(this, arguments);
      if (TIER !== 'reduced') {
        var panel = d.getElementById('step-panel');
        if (panel) {
          var r = panel.getBoundingClientRect();
          if (r.top < w.innerHeight && r.bottom > 0)   // only if visible
            requestAnimationFrame(function () { assemble(panel, { dir: 'up', preset: 'standard', duration: 720 }); });
        }
      }
      return rv;
    };
    wrapped.__nano = true; w.renderStep = wrapped;
  }
  // Generic shared-overlay opener/closer (_openSec / _closeSec drive the
  // profile, my-calcs and settings panels). One patch covers them all: the
  // animated target is the "<name>-content" node holding the rendered cards.
  function patchSec() {
    var oOpen = w._openSec;
    if (typeof oOpen === 'function' && !oOpen.__nano) {
      var wo = function (id) {
        var rv = oOpen.apply(this, arguments);
        if (TIER !== 'reduced') {
          var el = d.getElementById(String(id).replace('-overlay', '-content'));
          if (el) requestAnimationFrame(function () { requestAnimationFrame(function () {
            assemble(el, { dir: 'radial', origin: '50% 28%', preset: 'cinematic', duration: 740 }); }); });
        }
        return rv;
      };
      wo.__nano = true; w._openSec = wo;
    }
    var oClose = w._closeSec;
    if (typeof oClose === 'function' && !oClose.__nano) {
      var wc = function (id) {
        var el = d.getElementById(String(id).replace('-overlay', '-content'));
        var self = this, args = arguments;
        if (TIER !== 'reduced' && el && el.offsetParent !== null) {
          return disassemble(el, { dir: 'down', preset: 'standard', duration: 380 })
            .then(function () { return oClose.apply(self, args); });
        }
        return oClose.apply(self, args);
      };
      wc.__nano = true; w._closeSec = wc;
    }
  }
  // Editor floor tabs: the room-properties panel re-assembles on tab switch.
  function patchSwitchFloor() {
    var orig = w.switchFloor;
    if (typeof orig !== 'function' || orig.__nano) return;
    var wrapped = function () {
      var rv = orig.apply(this, arguments);
      if (TIER !== 'reduced') {
        var panel = d.getElementById('ed-props');
        if (panel && panel.offsetParent !== null)
          requestAnimationFrame(function () { assemble(panel, { dir: 'left', preset: 'subtle', duration: 520 }); });
      }
      return rv;
    };
    wrapped.__nano = true; w.switchFloor = wrapped;
  }
  function wirePatches() {
    patch('openModal', true, 'modal-card');
    patch('openWorkshop', true, 'modal-card');
    patch('openAuth', true, 'auth-card');
    patch('openAdmin', true, 'admin-overlay');
    patch('openEditor', true, 'ed-root');
    patch('closeModal', false, 'modal-card', 'down');
    patch('closeAuth', false, 'auth-card', 'down');
    patch('closeAdmin', false, 'admin-overlay', 'center');
    patch('closeEditor', false, 'ed-root', 'center');
    patchRenderStep();
    patchSec();
    patchSwitchFloor();
  }

  /* ------------------------------------------------------------------ init   */
  var inited = false;
  function init() {
    if (TIER !== 'reduced') ensureCanvas();
    scan();
    wirePatches();
    wireHero();
    if (!inited) {
      inited = true;
      d.addEventListener('visibilitychange', function () { if (!d.hidden) startLoop(); });
    }
  }
  function scan() {
    var nodes = d.querySelectorAll('[data-nano]');
    nodes.forEach(function (el) {
      if (el._nanoWired) return; el._nanoWired = true;
      var type = el.dataset.nano, on = el.dataset.nanoOn || 'view';
      if (type === 'text') { if (on === 'view') reveal(el, {}); else if (on === 'load') textOf(el, {}); return; }
      if (on === 'hover') { el.classList.add('nano-cta'); wireHover(el); return; }
      if (on === 'load') { el.classList.add('nano-armed'); assemble(el, {}); return; }
      reveal(el, {}); // default: in-view
    });
    // CTA shimmer by class (config selector)
    if (GLOBAL.ctaSelector) d.querySelectorAll(GLOBAL.ctaSelector).forEach(wireHover);
    // optional auto-reveal selectors (broad coverage without markup edits)
    if (GLOBAL.autoReveal) d.querySelectorAll(GLOBAL.autoReveal).forEach(function (el) {
      if (el._nanoWired || el.closest('[data-nano]')) return; el._nanoWired = true; reveal(el, {});
    });
  }
  function wireHero() {
    var hero = d.getElementById('hero');
    if (hero && !hero._nanoHero && TIER !== 'reduced') {
      hero._nanoHero = true;
      // hero already painted by the site; do a light overlay sweep, don't hide it
      var target = hero.querySelector('h1, .hero-title') || null;
    }
  }

  /* ---------------------------------------------------------------- config   */
  function config(opts) {
    opts = opts || {};
    Object.keys(opts).forEach(function (k) {
      if (k === 'particles' || k === 'tessellation' || k === 'glow')
        GLOBAL[k] = Object.assign({}, GLOBAL[k], opts[k]);
      else GLOBAL[k] = opts[k];
    });
    return GLOBAL;
  }

  /* ----------------------------------------------------------------- export  */
  w.NanoFX = {
    assemble: assemble,
    disassemble: disassemble,
    reveal: reveal,
    text: textOf,
    init: init,
    config: config,
    refresh: function () { scan(); },
    _tier: function () { return TIER; },
    _state: function () { return { tier: TIER, cap: poolCap, active: activeCount, effects: effects.length, running: running }; }
  };

  /* defaults for this project: warm CTA shimmer + broad section auto-reveal   */
  config({
    ctaSelector: '.lg-btn, .lg-btn-sec, .ed-launch, [data-nano-on="hover"]',
    autoReveal: null   // explicit data-nano attrs drive reveals (set a selector to auto-cover)
  });

  initPool();
  if (!reduceMotion) readPalette();

  /* auto-init after DOM + inline scripts are ready (script is deferred) */
  if (d.readyState === 'loading') d.addEventListener('DOMContentLoaded', init);
  else init();

})(window, document);
