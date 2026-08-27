#!/usr/bin/env python3
"""Genera una chuleta SVG del keymap TOTEM QWERTY-ES (4 capas en cuadrícula 2x2)."""

K = 58          # lado de tecla
G = 8           # separación
U = K + G
HALF_GAP = 56   # hueco entre mitades
# stagger columnar por dedo (meñique→interior), en px
STAG = [30, 10, 0, 12, 24]

# --- datos: (tap, shift/nota, hold) ---
_ = None
def key(tap, sec=None, hold=None): return (tap, sec, hold)

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
    [key("ESC"), key("BT", "CLR"), key("↑"), key("="), key("{"),   key("}"), key("7"), key("8"), key("9"), key("+")],
    [key("⇧"), key("←"), key("↓"), key("→"), key("["),   key("]"), key("4"), key("5"), key("6"), key("−")],
    [key(""), key("DEL"), key("Pg↑"), key("Caps"), key("Pg↓"), key("("),
     key(")"), key("1"), key("2"), key("3"), key("*"), key("")],
  ],
  "thumbs": [key(""), key("●",_, "NAV"), key(""),   key("ADJ"), key("0"), key("")],
}
SYM = {
  "rows": [
    [key("!"), key("@"), key("#"), key("$"), key("%"),   key("&"), key("/"), key("("), key(")"), key("=")],
    [key("€"), key("|"), key("~"), key("¡"), key("¿"),   key("?"), key("'"), key("\""), key("ç"), key("¨")],
    [key(""), key("º"), key("ª"), key("\\"), key("`"), key("^"),
     key("Vol−"), key("Vol+"), key("⏮"), key("⏭"), key("⏯"), key("")],
  ],
  "thumbs": [key(""), key("GIF"), key("ADJ"),   key(""), key("●",_, "SYM"), key("")],
}
ADJ = {
  "rows": [
    [key("RST"), key("BT", "CLR"), key("OUT", "USB/BT"), key(""), key(""),   key(""), key("F7"), key("F8"), key("F9"), key("F12")],
    [key("BOOT"), key("BT ▶"), key(""), key(""), key(""),   key(""), key("F4"), key("F5"), key("F6"), key("F11")],
    [key(""), key(""), key("BT ◀"), key(""), key(""), key(""),
     key(""), key("F1"), key("F2"), key("F3"), key("F10"), key("")],
  ],
  "thumbs": [key(""), key(""), key(""),   key(""), key(""), key("")],
}

LEARN = {
  "rows": [
    [key(""), key(""), key(""), key(""), key(""),   key(""), key(""), key(""), key(""), key("")],
    [key("A"), key("S"), key("D"), key("F"), key(""),
     key(""), key("J"), key("K"), key("L"), key("Ñ")],
    [key(""), key(""), key(""), key(""), key(""), key(""),
     key(""), key(""), key(""), key(""), key(""), key("")],
  ],
  "thumbs": [key(""), key(""), key(""),   key(""), key(""), key("")],
}

ACCENT = {"BASE": "#4A6FA5", "NAVI": "#5B8C5A", "SYM": "#B0713C", "ADJ": "#8A5A9E", "LEARN": "#3E8E8B"}

def esc(s):
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

def draw_key(x, y, k, accent):
    tap, sec, hold = k
    out = []
    fill = "#ffffff" if tap else "#f2f0ec"
    out.append(f'<rect x="{x}" y="{y}" width="{K}" height="{K}" rx="9" fill="{fill}" stroke="#c8c2b8" stroke-width="1.2"/>')
    if tap:
        big = len(tap) <= 2
        size = 21 if big else (13 if len(tap) <= 4 else 11)
        dy = 6 if not hold else 3
        out.append(f'<text x="{x+K/2}" y="{y+K/2+dy}" text-anchor="middle" font-size="{size}" font-weight="600" fill="#2b2925">{esc(tap)}</text>')
    if sec:
        out.append(f'<text x="{x+K-7}" y="{y+15}" text-anchor="end" font-size="10.5" fill="#8a8378">{esc(sec)}</text>')
    if hold:
        out.append(f'<text x="{x+K/2}" y="{y+K-8}" text-anchor="middle" font-size="10.5" font-weight="700" fill="{accent}">{esc(hold)}</text>')
    return "\n".join(out)

def draw_layer(ox, oy, name, subtitle, data):
    accent = ACCENT[name]
    out = [f'<text x="{ox}" y="{oy+4}" font-size="19" font-weight="800" fill="{accent}">{name}</text>',
           f'<text x="{ox+96}" y="{oy+3}" font-size="12.5" fill="#6d675e">{esc(subtitle)}</text>']
    top = oy + 18
    xs_left  = [ox + U * (i + 1) for i in range(5)]
    xs_right = [ox + U * 6 + HALF_GAP + U * i for i in range(5)]
    stag_r = list(reversed(STAG))
    # filas 0-1 (5+5), fila 2 (6+6)
    for r, row in enumerate(data["rows"]):
        if r < 2:
            for i in range(5):
                out.append(draw_key(xs_left[i],  top + STAG[i]   + U * r, row[i],   accent))
                out.append(draw_key(xs_right[i], top + stag_r[i] + U * r, row[5+i], accent))
        else:
            out.append(draw_key(ox, top + STAG[0] + U * 2, row[0], accent))                     # meñique ext. izq
            for i in range(5):
                out.append(draw_key(xs_left[i],  top + STAG[i]   + U * 2, row[1+i], accent))
                out.append(draw_key(xs_right[i], top + stag_r[i] + U * 2, row[6+i], accent))
            out.append(draw_key(ox + U * 6 + HALF_GAP + U * 5, top + stag_r[4] + U * 2, row[11], accent))  # meñique ext. der
    # pulgares: izq bajo cols 2-4, der bajo cols 0-2
    ty = top + U * 3 + 34
    for i in range(3):
        out.append(draw_key(xs_left[2] + U * i, ty + 4 * i, data["thumbs"][i], accent))
        out.append(draw_key(xs_right[0] + U * i, ty + 8 - 4 * i, data["thumbs"][3+i], accent))
    return "\n".join(out)

BLOCK_W = U * 12 + HALF_GAP + 10   # ancho de un bloque de capa
BLOCK_H = 18 + STAG[0] + U * 3 + 34 + K + 14 + 40
M = 34                             # margen
W = M * 2 + BLOCK_W * 2 + 50
H = 118 + BLOCK_H * 3 + 30

svg = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" font-family="Helvetica Neue, Helvetica, Arial, sans-serif">',
  f'<rect width="{W}" height="{H}" fill="#faf8f4"/>',
  f'<text x="{M}" y="52" font-size="30" font-weight="800" fill="#2b2925">TOTEM · QWERTY español (macOS)</text>',
  f'<text x="{M}" y="76" font-size="13.5" fill="#6d675e">Capa NAV: mantener TAB · Capa SYM: mantener ESC · Capa ADJ: desde NAV o SYM, tecla ADJ · Fila central: toque = letra, mantener = modificador</text>',
]
y0 = 108
svg.append(draw_layer(M, y0, "BASE", "esquina sup. = con Mayús · borde inf. = al mantener", BASE))
svg.append(draw_layer(M + BLOCK_W + 50, y0, "NAVI", "mantener TAB (pulgar izq.)", NAV))
svg.append(draw_layer(M, y0 + BLOCK_H, "SYM", "mantener ESC (pulgar der.)", SYM))
svg.append(draw_layer(M + BLOCK_W + 50, y0 + BLOCK_H, "ADJ", "NAV+RET o SYM+SPC · BOOT = modo flasheo", ADJ))
svg.append(draw_layer(M, y0 + BLOCK_H * 2, "LEARN", "combo S+D+F activa/desactiva · para practicar mecanografía", LEARN))

# bloque de notas a la derecha de LEARN
nx = M + BLOCK_W + 50
ny = y0 + BLOCK_H * 2
NOTAS = [
    "´ ` ^ ¨ son teclas muertas: pulsa y luego la vocal (´+a = á)",
    "Combo Q+W = ESC",
    "Combo S+D+F = capa LEARN: la fila central pierde los modificadores",
    "al mantener (solo letras). En LEARN, las teclas grises funcionan",
    "igual que en BASE (NAV, SYM y símbolos siguen disponibles).",
    "Requiere macOS con distribución “Española — ISO”",
    "y el teclado identificado como ISO (KeyboardSetupAssistant).",
]
svg.append(f'<text x="{nx}" y="{ny+4}" font-size="19" font-weight="800" fill="#6d675e">NOTAS</text>')
for i, line in enumerate(NOTAS):
    svg.append(f'<text x="{nx}" y="{ny + 34 + i * 24}" font-size="13.5" fill="#6d675e">{esc(line)}</text>')
svg.append('</svg>')

import os
path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "totem-keymap-chuleta.svg")
with open(path, "w") as f:
    f.write("\n".join(svg))
print(f"OK → {path}")
