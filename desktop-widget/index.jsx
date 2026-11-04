// TOTEM keymap cheatsheet drawn on the desktop, above the wallpaper and below every window,
// with frosted-glass keys.
//
// Übersicht's window can't backdrop-blur the wallpaper (it lives in another window), so
// `wallsnap` (built from wallsnap.swift) snapshots the on-screen wallpaper window of this
// display (works with rotating wallpapers), and the SVG draws it blurred, clipped to the
// shape of the keys.

const DIR = "$HOME/Library/Application Support/Übersicht/widgets/totem-cheatsheet.widget";
const SVG = "$HOME/Developer/zmk-config-totem/totem-keymap-cheatsheet.svg";

export const command = `
  D="${DIR}"
  # Wallpaper snapshot stamp (unchanged while the wallpaper is); "0" = no glass available.
  "$D/wallsnap" 2>/dev/null || echo 0
  # keyglow's per-run token (empty line if keyglow isn't running)
  printf '%s\\n' "$(cat "$D/keyglow.token" 2>/dev/null)"
  cat "${SVG}"
  exit 0
`;

// Poll often so the glass follows a wallpaper change within seconds. Cheap: wallsnap takes
// ~0.3 s, and while the wallpaper is unchanged the output is identical, so nothing re-renders.
export const refreshFrequency = 5 * 1000;

const BLUR = 22; // blur radius, in SVG units (~14 screen px on the laptop)
const MARGIN = 8; // SVG units around the whole grid
const GAP_X = 70, GAP_Y = 36; // minimum gaps between layers; spare room is added on top
const DROP_LAYERS = new Set(["LEARN"]);
// Layer-name pills: font size, height, side padding, and how far the pill's top sits above
// the text baseline (baseline − cap-height/2 − PILL_H/2).
const PILL_FONT = 16, PILL_H = 28, PILL_PAD = 14, PILL_TOP = 20;

// ── Re-layout ─────────────────────────────────────────────────────────────────────────
// The repo SVG is a 2×3 sheet (BASE NAVI / SYM ADJ / LEARN NOTES) with a title and
// captions. On the desktop only the four working layers and their names are wanted, so:
// drop the captions/titles/notes and LEARN, then lay the layers out as a 2×2 grid whose
// spacing makes the whole grid match the screen's proportions.

// Proportions of the box the SVG is drawn into (the widget's padding is 1vw/side, 3.5vh).
const boxAspect = () => (innerWidth * 0.98) / (innerHeight * 0.965);

let layoutCache = { key: null, svg: null };

const relayout = (src) => {
  const aspect = boxAspect();
  const key = `${aspect.toFixed(3)}|${src.length}|${src.slice(-64)}`;
  if (layoutCache.key === key) return layoutCache.svg;

  const doc = new DOMParser().parseFromString(src, "image/svg+xml");
  const root = doc.documentElement;
  const num = (el, a) => parseFloat(el.getAttribute(a));
  const cls = (el) => el.getAttribute("class") || "";

  // Layer names: the 19px coloured titles (BASE, NAVI, SYM, ADJ, LEARN).
  const titles = [...root.children]
    .filter((e) => e.tagName === "text" && num(e, "font-size") === 19 && cls(e).startsWith("a-"))
    .map((e) => ({ el: e, name: e.textContent.trim(), x: num(e, "x"), y: num(e, "y") }));
  const colSplit = Math.max(...titles.map((t) => t.x)) - 40; // left/right column boundary
  const right = (x) => x >= colSplit;
  const layerAt = (x, y) =>
    titles.filter((t) => t.y <= y + 5 && right(t.x) === right(x)).sort((a, b) => b.y - a.y)[0];

  const layers = new Map(); // name → { title, els, minX, minY, maxX, maxY }
  for (const el of [...root.children]) {
    if (el.tagName !== "rect" && el.tagName !== "text") continue;
    if (cls(el) === "bg") continue;
    const x = num(el, "x"), y = num(el, "y");
    const isCaption = el.tagName === "text" && (cls(el) === "muted" || num(el, "font-size") >= 30);
    const layer = layerAt(x, y);
    if (isCaption || !layer || DROP_LAYERS.has(layer.name)) { el.remove(); continue; }
    if (!layers.has(layer.name)) {
      layers.set(layer.name, { title: layer, els: [], minX: layer.x, minY: layer.y - PILL_TOP,
                               maxX: layer.x, maxY: layer.y });
    }
    const L = layers.get(layer.name);
    L.els.push(el);
    if (el.tagName === "rect") {
      L.minX = Math.min(L.minX, x);
      L.maxX = Math.max(L.maxX, x + num(el, "width"));
      L.maxY = Math.max(L.maxY, y + num(el, "height"));
    }
  }

  // Keep the sheet's reading order: rows by title height, then left before right.
  const order = [...layers.values()].sort(
    (a, b) => a.title.y - b.title.y || a.title.x - b.title.x);
  const W = Math.max(...order.map((L) => L.maxX - L.minX));
  const H = Math.max(...order.map((L) => L.maxY - L.minY));
  const cols = 2, rows = Math.ceil(order.length / cols);

  // Grow whichever gaps are needed so the grid has the screen's proportions; the spare
  // room is shared between the gaps and the outer margins so it reads as evenly spaced.
  let gx = GAP_X, gy = GAP_Y, mx = MARGIN, my = MARGIN;
  const tw = cols * W + (cols - 1) * gx + 2 * mx;
  const th = rows * H + (rows - 1) * gy + 2 * my;
  if (tw / th > aspect) {
    const extra = (tw / aspect - th) / (rows + 1);
    gy += extra; my += extra;
  } else {
    const extra = (th * aspect - tw) / (cols + 1);
    gx += extra; mx += extra;
  }

  const r2 = (v) => Math.round(v * 100) / 100;
  order.forEach((L, i) => {
    const dx = mx + (i % cols) * (W + gx) - L.minX;
    const dy = my + Math.floor(i / cols) * (H + gy) - L.minY;
    for (const el of L.els) {
      el.setAttribute("x", r2(num(el, "x") + dx));
      el.setAttribute("y", r2(num(el, "y") + dy));
    }

    // Layer name: centred over its layer, on a pill (drawn before the text, so behind it).
    const t = L.title.el;
    const cx = r2((L.minX + L.maxX) / 2 + dx);
    const ty = num(t, "y");
    t.setAttribute("x", cx);
    t.setAttribute("text-anchor", "middle");
    t.setAttribute("data-layer", L.title.name);
    t.setAttribute("font-size", PILL_FONT);
    t.setAttribute("letter-spacing", "0.06em");
    const w = L.title.name.length * PILL_FONT * 0.78 + 2 * PILL_PAD; // bold caps ≈ 0.72em + spacing
    const pill = doc.createElementNS("http://www.w3.org/2000/svg", "rect");
    pill.setAttribute("class", "pill");
    for (const [a, v] of [["x", cx - w / 2], ["y", ty - PILL_TOP], ["width", w],
                          ["height", PILL_H], ["rx", PILL_H / 2]]) pill.setAttribute(a, r2(v));
    root.insertBefore(pill, t);
  });

  const vw = cols * W + (cols - 1) * gx + 2 * mx;
  const vh = rows * H + (rows - 1) * gy + 2 * my;
  root.setAttribute("viewBox", `0 0 ${r2(vw)} ${r2(vh)}`);
  const svg = new XMLSerializer().serializeToString(root);
  layoutCache = { key, svg };
  return svg;
};

// Where the whole display falls in SVG units, measured from the live DOM (needed to line
// the wallpaper snapshot up with the real wallpaper). geo = { screen: {x, y, w, h}, aspect }
let geo = null;

const KEY = /<rect class="(?:k|off|none|pill)" ([^>]*?)\/>/g; // shapes that get the glass

// Rewrites the SVG string: re-layout + blurred wallpaper clipped to the keys.
const transform = (src, stamp) => {
  const svg = relayout(src);
  // Halo for lit keys (CSS drop-shadow doesn't render on SVG shapes in Übersicht's WebKit).
  const glow = `
    <defs>
      <filter id="keyglow" x="-60%" y="-60%" width="220%" height="220%">
        <feGaussianBlur in="SourceGraphic" stdDeviation="9" result="halo"/>
        <feMerge><feMergeNode in="halo"/><feMergeNode in="halo"/><feMergeNode in="SourceGraphic"/></feMerge>
      </filter>
    </defs>`;
  const out = svg.replace(/(<rect class="bg"[^>]*\/>)/, `$1${glow}`);
  // No wallpaper snapshot, or screen mapping not measured yet: plain translucent keys.
  if (stamp === "0" || !geo || geo.aspect !== boxAspect()) return out;

  const clips = [];
  for (const m of svg.matchAll(KEY)) {
    const attrs = m[1].replace(/\s*stroke-[a-z]+="[^"]*"/g, "");
    clips.push(`<rect ${attrs}/>`);
  }
  const { x, y, w, h } = geo.screen;
  const glass = `
    <defs>
      <filter id="frost" x="${x}" y="${y}" width="${w}" height="${h}" filterUnits="userSpaceOnUse">
        <feGaussianBlur stdDeviation="${BLUR}" edgeMode="duplicate"/>
        <feColorMatrix type="saturate" values="1.35"/>
      </filter>
      <clipPath id="keys">${clips.join("")}</clipPath>
    </defs>
    <image class="frost" href="totem-cheatsheet.widget/wall.jpg?t=${stamp}"
      x="${x}" y="${y}" width="${w}" height="${h}" preserveAspectRatio="none"
      filter="url(#frost)" clip-path="url(#keys)"/>`;
  // Right after the (hidden) background rect, so the glass sits under every key.
  return out.replace(/(<rect class="bg"[^>]*\/>)/, `$1${glass}`);
};

// Command output: line 1 = wallpaper stamp, line 2 = keyglow token, rest = the SVG.
const split = (output) => {
  const [stamp, token] = output.split("\n", 2);
  const start = stamp.length + token.length + 2;
  return { stamp: stamp.trim(), token: token.trim(), svg: output.slice(start) };
};

// After a render: measure where the screen falls in SVG units, then redraw with the glass.
const measure = (el, output, tries = 20) => {
  if (!el || (geo && geo.aspect === boxAspect())) return;
  const svg = el.querySelector("svg");
  const m = svg && svg.getScreenCTM(); // user units -> window px (window == whole display)
  if (!m || svg.getBoundingClientRect().width === 0) {
    if (tries > 0) requestAnimationFrame(() => measure(el, output, tries - 1));
    return;
  }
  geo = {
    aspect: boxAspect(),
    screen: { x: -m.e / m.a, y: -m.f / m.d, w: innerWidth / m.a, h: innerHeight / m.d },
  };
  const { stamp, svg: src } = split(output);
  el.innerHTML = transform(src, stamp);
};

// ── Live key glow ─────────────────────────────────────────────────────────────────────
// keyglow (see keyglow.swift, run by a LaunchAgent) streams key presses as labels drawn on
// the cheatsheet ("Q", "{", "RET", "⌘⇧3"...). The host only sees characters, not layers,
// so a label lights every key that carries it, each in its layer's colour.

const KEYGLOW = "http://127.0.0.1:41427/";
const MOD_DELAY = 150; // ms a home-row modifier must stay held before it lights
const STUCK_MS = 4000; // safety: unlight a key whose key-up never arrived

const norm = (s) => s.trim().replace(/−/g, "-"); // − (U+2212) → -
const MODS = new Set(["⌘", "⌥", "⌃", "⇧"]);

// Index of the current SVG: label → keys, home-row modifier → [left key, right key].
let index = null;

const buildIndex = (svg) => {
  const num = (el, a) => parseFloat(el.getAttribute(a));
  const titles = [...svg.querySelectorAll("text")]
    .filter((t) => t.hasAttribute("data-layer"))
    .map((t) => ({ x: num(t, "x"), y: num(t, "y"), layer: t.getAttribute("class").slice(2),
                   color: getComputedStyle(t).fill }));
  const keys = [...svg.querySelectorAll("rect.k")].map((r) => {
    const x = num(r, "x"), y = num(r, "y");
    // Section = in the nearest row of titles above, the title closest horizontally
    // (titles are centred over their layer).
    const above = titles.filter((t) => t.y <= y);
    const rowY = Math.max(...above.map((t) => t.y));
    const sec = above.filter((t) => t.y === rowY)
      .sort((a, b) => Math.abs(a.x - x) - Math.abs(b.x - x))[0];
    return { r, x, y, w: num(r, "width"), h: num(r, "height"), sec, labels: [], hold: null };
  });
  for (const t of svg.querySelectorAll("text")) {
    const x = num(t, "x"), y = num(t, "y");
    const k = keys.find((k) => x >= k.x && x <= k.x + k.w && y >= k.y && y <= k.y + k.h);
    if (!k) continue;
    const cls = t.getAttribute("class"), txt = norm(t.textContent);
    if (cls === "ink" || cls === "sec") k.labels.push(txt);
    else if (cls === "a-BASE" && MODS.has(txt)) k.hold = txt;
  }
  const byLabel = new Map(), holds = new Map();
  for (const k of keys) {
    if (!k.sec || k.sec.layer === "LEARN") continue; // LEARN only mirrors BASE
    k.r.style.setProperty("--glow", k.sec.color);
    for (const l of k.labels) byLabel.set(l, [...(byLabel.get(l) || []), k.r]);
    if (k.hold) holds.set(k.hold, [...(holds.get(k.hold) || []), k]);
  }
  const sides = new Map();
  for (const [mod, ks] of holds) {
    ks.sort((a, b) => a.x - b.x);
    sides.set(`L${mod}`, [ks[0].r]);
    sides.set(`R${mod}`, [ks[ks.length - 1].r]);
  }
  return { svg, byLabel, sides };
};

const getIndex = () => {
  const svg = document.querySelector("svg .bg")?.ownerSVGElement;
  if (!svg) return null;
  if (!index || index.svg !== svg || !svg.isConnected) index = buildIndex(svg);
  return index;
};

// Several presses may light the same rect (e.g. two layers sharing "{"): count them.
const litCount = new WeakMap();
const light = (rects, on) => {
  for (const r of rects) {
    const n = Math.max(0, (litCount.get(r) || 0) + (on ? 1 : -1));
    litCount.set(r, n);
    r.classList.toggle("lit", n > 0);
  }
};

const pressed = new Map(); // id → { rects, timer }
const release = (id) => {
  const p = pressed.get(id);
  if (!p) return;
  clearTimeout(p.timer);
  pressed.delete(id);
  if (p.rects) light(p.rects, false);
};
const press = (id, rects, delay = 0) => {
  release(id);
  const p = { rects: null, timer: null };
  pressed.set(id, p);
  const on = () => {
    p.rects = rects;
    light(rects, true);
    if (!id.startsWith("mod")) p.timer = setTimeout(() => release(id), STUCK_MS);
  };
  if (delay) p.timer = setTimeout(on, delay); else on();
};

const onKeyEvent = (e) => {
  const ix = getIndex();
  if (!ix) return;
  const ev = JSON.parse(e.data);
  if (ev.t === "down") {
    const rects = [...new Set(ev.labels.flatMap((l) => ix.byLabel.get(norm(l)) || []))];
    press(ev.id, rects);
  } else if (ev.t === "up") {
    release(ev.id);
  } else if (ev.t === "mod") {
    const id = `mod${ev.side}${ev.mod}`;
    if (ev.down) press(id, ix.sides.get(`${ev.side}${ev.mod}`) || [], MOD_DELAY);
    else release(id);
  }
};

// One connection per page, surviving Übersicht's hot reloads of this module. keyglow mints
// a new token each time it starts, so reconnect whenever the token changes.
const connect = (token) => {
  const prev = window.__keyglow;
  if (prev?.es && prev.token === token && prev.es.readyState !== EventSource.CLOSED) return;
  (prev?.es || prev)?.close?.();
  window.__keyglow = null;
  if (!token) return;
  const es = new EventSource(`${KEYGLOW}?t=${encodeURIComponent(token)}`);
  es.onmessage = onKeyEvent;
  es.onerror = () => [...pressed.keys()].forEach(release); // reconnects on its own
  window.__keyglow = { es, token };
};

export const className = `
  top: 0; left: 0;
  width: 100vw; height: 100vh;
  box-sizing: border-box;
  padding: 2.5vh 1vw 1vh;
  display: flex; align-items: center; justify-content: center;
  pointer-events: none;

  > div, svg { width: 100%; height: 100%; }

  /* Drop the SVG's opaque background (also keeps it out of getBBox for the crop). */
  svg .bg { display: none; }

  /* Glass: a translucent tint over the blurred wallpaper, with a light rim. */
  svg .k    { fill: rgba(255, 255, 255, 0.10); stroke: rgba(255, 255, 255, 0.65); }
  svg .off  { fill: rgba(255, 255, 255, 0.05); stroke: rgba(255, 255, 255, 0.55); }
  svg .none { fill: rgba(255, 255, 255, 0.03); stroke: rgba(255, 255, 255, 0.40); }

  /* Layer-name pills: glass like the keys, but with more tint so the coloured name reads. */
  svg rect.pill { fill: rgba(255, 255, 255, 0.55); stroke: rgba(255, 255, 255, 0.7); stroke-width: 1; }
  /* Layer names: more saturated than the sheet's print-friendly palette. */
  svg text[data-layer="BASE"] { fill: #1F6BFF; }
  svg text[data-layer="NAVI"] { fill: #1E9E3C; }
  svg text[data-layer="SYM"]  { fill: #E8650A; }
  svg text[data-layer="ADJ"]  { fill: #9A2FE0; }
  @media (prefers-color-scheme: dark) {
    svg rect.pill { fill: rgba(22, 21, 19, 0.5); stroke: rgba(255, 255, 255, 0.24); }
    svg text[data-layer="BASE"] { fill: #5C9DFF; }
    svg text[data-layer="NAVI"] { fill: #4BE07A; }
    svg text[data-layer="SYM"]  { fill: #FF9A3D; }
    svg text[data-layer="ADJ"]  { fill: #C76BFF; }
  }

  /* Softer key legends so they blend with the glass (layer names, 19px, stay as they are;
     .inh/.inh2 on transparent keys are already faint). */
  svg text.ink, svg text.sec,
  svg text[class^="a-"]:not([data-layer]) { fill-opacity: 0.8; }

  /* Live glow: the key lights in its layer's colour and fades out on release. */
  svg rect.k { transition: fill 0.4s ease-out, fill-opacity 0.4s ease-out, stroke 0.4s ease-out; }
  svg rect.k.lit {
    fill: var(--glow); fill-opacity: 0.9;
    stroke: rgba(255, 255, 255, 0.9); stroke-width: 2;
    filter: url(#keyglow);
    transition: none;
  }

  @media (prefers-color-scheme: dark) {
    svg .k    { fill: rgba(22, 21, 19, 0.10); stroke: rgba(255, 255, 255, 0.24); }
    svg .off  { fill: rgba(22, 21, 19, 0.05); stroke: rgba(255, 255, 255, 0.22); }
    svg .none { fill: rgba(22, 21, 19, 0.03); stroke: rgba(255, 255, 255, 0.18); }  }
`;

export const render = ({ output, error }) => {
  if (error) return <div>{String(error)}</div>;
  if (!output) return <div />;
  const { stamp, token, svg } = split(output);
  connect(token);
  return (
    <div
      ref={(el) => requestAnimationFrame(() => measure(el, output))}
      dangerouslySetInnerHTML={{ __html: transform(svg, stamp) }}
    />
  );
};
