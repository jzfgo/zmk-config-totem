#!/usr/bin/env python3
"""Generate an SVG cheatsheet of the TOTEM Spanish-QWERTY keymap (layers laid out in a grid)."""

K = 58          # key side
G = 8           # gap between keys
U = K + G
HALF_GAP = 56   # gap between the two halves
# column stagger per finger (pinky → inner), in px
STAG = [30, 10, 0, 12, 24]

# --- data: (tap, shifted/note, hold) ---
_ = None
def key(tap, sec=None, hold=None): return (tap, sec, hold)
# &trans: resolved against the layers below and drawn faded.
# key("") is &none: an empty slot that does nothing.
TR = ("__trans__", None, None)

BASE = {
  "rows": [
    [key("Q"), key("W"), key("E"), key("R"), key("T"),   key("Y"), key("U"), key("I"), key("O"), key("P")],
    [key("A",_, "⌘"), key("S",_, "⌥"), key("D",_, "⌃"), key("F",_, "⇧"), key("G"),
     key("H"), key("J",_, "⇧"), key("K",_, "⌃"), key("L",_, "⌥"), key("Ñ",_, "⌘")],
    [key("<", ">"), key("Z"), key("X"), key("C"), key("V"), key("B"),
     key("N"), key("M"), key(",", ";"), key(".", ":"), key("-", "_"), key("´", "¨")],
  ],
  "thumbs": [key("DEL"), key("TAB",_, "NAV"), key("SPC"),   key("RET"), key("ESC",_, "SYM"), key("⌫")],
}
NAV = {
  "rows": [
    [key("ESC"), key(""), key("↑"), key("="), key("{"),   key("}"), key("7"), key("8"), key("9"), key("+")],
    [key("⇧"), key("←"), key("↓"), key("→"), key("["),   key("]"), key("4"), key("5"), key("6"), key("−")],
    [TR, key("DEL"), key("Pg↑"), key("Caps"), key("Pg↓"), key("("),
     key(")"), key("1"), key("2"), key("3"), key("*"), key("/")],
  ],
  "thumbs": [TR, key("●",_, "NAV"), TR,   key("0"), TR, TR],
}
SYM = {
  "rows": [
    [key("º"), key("ª"), key("~"), key("{"), key("¡"),   key("!"), key("}"), key("'"), key("\""), key("`")],
    [key("|"), key("@"), key("("), key("["), key("¿"),   key("?"), key("]"), key(")"), key("&"), key("$")],
    [key("<"), key("€"), key("#"), key("%"), key("^"), key("\\"),
     key("/"), key("*"), key("+"), key("-"), key("="), key(">")],
  ],
  "thumbs": [key("Emoji", "⌃⌘␣"), TR, TR,   TR, key("●",_, "SYM"), TR],
}
ADJ = {
  "rows": [
    [key("BT ▶"), key(""), key("Capt", "⌘⇧3"), key("⏯"), key("⏮"),   key("⏭"), key("F7"), key("F8"), key("F9"), key("F12")],
    [key("BT ◀"), key("Lock", "⌃⌘Q"), key("Area", "⌘⇧4"), key("Mute"), key("Vol−"),   key("Vol+"), key("F4"), key("F5"), key("F6"), key("F11")],
    [key("BT", "CLR"), key("OUT", "USB/BT"), key(""), key("Rec", "⌘⇧5"), key("MCtl", "⌃↑"), key("☀−"),
     key("☀+"), key("F1"), key("F2"), key("F3"), key("F10"), key("Spot", "⌘␣")],
  ],
  "thumbs": [key("BOOT"), key("●",_, "NAV"), key("RST"),   key("RST"), key("●",_, "SYM"), key("BOOT")],
}

LEARN = {
  "rows": [
    [TR, TR, TR, TR, TR,   TR, TR, TR, TR, TR],
    [key("A"), key("S"), key("D"), key("F"), TR,
     TR, key("J"), key("K"), key("L"), key("Ñ")],
    [TR, TR, TR, TR, TR, TR,
     TR, TR, TR, TR, TR, TR],
  ],
  "thumbs": [TR, TR, TR,   TR, TR, TR],
}

def resolve(layer, below):
    """Replace each TR with the first non-transparent key in the layers below
    (in priority order) and mark it as inherited."""
    def at(l, part, r, i):
        return l["thumbs"][i] if part == "thumbs" else l["rows"][r][i]
    def fix(part, r, i, k):
        if k is not TR:
            return k
        for b in below:
            kb = at(b, part, r, i)
            if kb is not TR:
                return (kb[0], kb[1], kb[2], True)
        return key("")
    return {
        "rows": [[fix("rows", r, i, k) for i, k in enumerate(row)] for r, row in enumerate(layer["rows"])],
        "thumbs": [fix("thumbs", 0, i, k) for i, k in enumerate(layer["thumbs"])],
    }

# ADJ is NAV+SYM held together: its &trans fall through to SYM (layer 3) first, then NAV, then BASE.
ADJ_R   = resolve(ADJ,   [SYM, NAV, BASE])
NAV_R   = resolve(NAV,   [BASE])
SYM_R   = resolve(SYM,   [BASE])
LEARN_R = resolve(LEARN, [BASE])

# Colours by CSS class: the SVG follows the system light/dark mode (prefers-color-scheme).
ACCENT      = {"BASE": "#4A6FA5", "NAVI": "#5B8C5A", "SYM": "#B0713C", "ADJ": "#8A5A9E", "LEARN": "#3E8E8B"}
ACCENT_DARK = {"BASE": "#86A9DE", "NAVI": "#8CC08A", "SYM": "#E0A46E", "ADJ": "#C094D2", "LEARN": "#6FC4BF"}
LIGHT = {"bg": "#faf8f4", "ink": "#2b2925", "muted": "#6d675e", "sec": "#8a8378",
         "key": "#ffffff", "off": "#f2f0ec", "ostroke": "#c8c2b8", "none": "#f2f0ec", "nstroke": "#c8c2b8", "stroke": "#c8c2b8", "inh": "#b4ada2", "inh2": "#c4beb4"}
DARK  = {"bg": "#1b1a18", "ink": "#ece8e1", "muted": "#a8a196", "sec": "#9a9387",
         "key": "#2b2926", "off": "#24221f", "ostroke": "#58534b", "none": "#25231f", "nstroke": "#615b52", "stroke": "#4a463f", "inh": "#7a7469", "inh2": "#6e685e"}

def css(pal, acc):
    rules = [
        f".bg{{fill:{pal['bg']}}}", f".ink{{fill:{pal['ink']}}}", f".muted{{fill:{pal['muted']}}}",
        f".sec{{fill:{pal['sec']}}}", f".inh{{fill:{pal['inh']}}}", f".inh2{{fill:{pal['inh2']}}}",
        f".k{{fill:{pal['key']};stroke:{pal['stroke']}}}", f".off{{fill:{pal['off']};stroke:{pal['ostroke']}}}",
        f".none{{fill:{pal['none']};stroke:{pal['nstroke']}}}",
    ]
    rules += [f".a-{n}{{fill:{c}}}" for n, c in acc.items()]
    return "".join(rules)

STYLE = ("<style>" + css(LIGHT, ACCENT)
         + "@media (prefers-color-scheme: dark){" + css(DARK, ACCENT_DARK) + "}</style>")

def esc(s):
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

def draw_key(x, y, k, name):
    tap, sec, hold = k[:3]
    inherited = len(k) > 3 and k[3]
    out = []
    cls = "off" if inherited else ("k" if tap else "none")   # none = &none (disabled slot)
    dash = ' stroke-dasharray="4 3"' if inherited else ""
    out.append(f'<rect class="{cls}" x="{x}" y="{y}" width="{K}" height="{K}" rx="9" stroke-width="1.2"{dash}/>')
    c_tap, c_sec, c_hold = ("inh", "inh2", "inh") if inherited else ("ink", "sec", f"a-{name}")
    weight = "500" if inherited else "600"
    if tap:
        big = len(tap) <= 2
        size = 21 if big else (13 if len(tap) <= 4 else 11)
        dy = 6 if not hold else 3
        out.append(f'<text x="{x+K/2}" y="{y+K/2+dy}" text-anchor="middle" font-size="{size}" font-weight="{weight}" class="{c_tap}">{esc(tap)}</text>')
    if sec:
        out.append(f'<text x="{x+K-7}" y="{y+15}" text-anchor="end" font-size="10.5" class="{c_sec}">{esc(sec)}</text>')
    if hold:
        out.append(f'<text x="{x+K/2}" y="{y+K-8}" text-anchor="middle" font-size="10.5" font-weight="700" class="{c_hold}">{esc(hold)}</text>')
    return "\n".join(out)

def draw_layer(ox, oy, name, subtitle, data):
    accent = name
    out = [f'<text x="{ox}" y="{oy+4}" font-size="19" font-weight="800" class="a-{name}">{name}</text>',
           f'<text x="{ox+96}" y="{oy+3}" font-size="12.5" class="muted">{esc(subtitle)}</text>']
    top = oy + 18
    xs_left  = [ox + U * (i + 1) for i in range(5)]
    xs_right = [ox + U * 6 + HALF_GAP + U * i for i in range(5)]
    stag_r = list(reversed(STAG))
    # rows 0-1 (5+5), row 2 (6+6)
    for r, row in enumerate(data["rows"]):
        if r < 2:
            for i in range(5):
                out.append(draw_key(xs_left[i],  top + STAG[i]   + U * r, row[i],   accent))
                out.append(draw_key(xs_right[i], top + stag_r[i] + U * r, row[5+i], accent))
        else:
            out.append(draw_key(ox, top + STAG[0] + U * 2, row[0], accent))                     # left outer pinky
            for i in range(5):
                out.append(draw_key(xs_left[i],  top + STAG[i]   + U * 2, row[1+i], accent))
                out.append(draw_key(xs_right[i], top + stag_r[i] + U * 2, row[6+i], accent))
            out.append(draw_key(ox + U * 6 + HALF_GAP + U * 5, top + stag_r[4] + U * 2, row[11], accent))  # right outer pinky
    # thumbs: left under cols 2-4, right under cols 0-2
    ty = top + U * 3 + 34
    for i in range(3):
        out.append(draw_key(xs_left[2] + U * i, ty + 4 * i, data["thumbs"][i], accent))
        out.append(draw_key(xs_right[0] + U * i, ty + 8 - 4 * i, data["thumbs"][3+i], accent))
    return "\n".join(out)

BLOCK_W = U * 12 + HALF_GAP + 10   # width of one layer block
BLOCK_H = 18 + STAG[0] + U * 3 + 34 + K + 14 + 40
M = 34                             # margin
W = M * 2 + BLOCK_W * 2 + 50
H = 118 + BLOCK_H * 3 + 30

svg = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" font-family="Helvetica Neue, Helvetica, Arial, sans-serif">',
  STYLE,
  f'<rect class="bg" width="{W}" height="{H}"/>',
  f'<text x="{M}" y="52" font-size="30" font-weight="800" class="ink">TOTEM · Spanish QWERTY (macOS)</text>',
  f'<text x="{M}" y="76" font-size="13.5" class="muted">NAV layer: hold TAB · SYM layer: hold ESC · ADJ layer: hold TAB + ESC · Home row: tap = letter, hold = modifier</text>',
]
y0 = 108
svg.append(draw_layer(M, y0, "BASE", "top corner = with Shift · bottom edge = on hold", BASE))
svg.append(draw_layer(M + BLOCK_W + 50, y0, "NAVI", "hold TAB (left thumb)", NAV_R))
svg.append(draw_layer(M, y0 + BLOCK_H, "SYM", "hold ESC (right thumb)", SYM_R))
svg.append(draw_layer(M + BLOCK_W + 50, y0 + BLOCK_H, "ADJ", "hold TAB + ESC (tri-layer) · BOOT = flashing mode", ADJ_R))
svg.append(draw_layer(M, y0 + BLOCK_H * 2, "LEARN", "combo S+D+F toggles it · for touch-typing practice", LEARN_R))

# notes block, right of LEARN
nx = M + BLOCK_W + 50
ny = y0 + BLOCK_H * 2
NOTES = [
    "´ ¨ (BASE) are dead keys: press, then the vowel (´+a = á)",
    "In SYM, ` ^ ~ come out as is (macro: dead key + space)",
    "Combo Q+W = ESC · Combo C+V = ç (with ⇧: Ç)",
    "Combo S+D+F = LEARN layer: the home row loses its hold",
    "modifiers (letters only).",
    "Light grey, dashed border = transparent: does what the layer",
    "below does (in ADJ: SYM first, then NAV, then BASE).",
    "Empty grey slot = disabled key, does nothing.",
    "Requires macOS with the “Spanish – ISO” input source",
    "and the keyboard identified as ISO (KeyboardSetupAssistant).",
]
svg.append(f'<text x="{nx}" y="{ny+4}" font-size="19" font-weight="800" class="muted">NOTES</text>')
for i, line in enumerate(NOTES):
    svg.append(f'<text x="{nx}" y="{ny + 34 + i * 24}" font-size="13.5" class="muted">{esc(line)}</text>')
svg.append('</svg>')

import os
path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "totem-keymap-cheatsheet.svg")
with open(path, "w") as f:
    f.write("\n".join(svg))
print(f"OK → {path}")
