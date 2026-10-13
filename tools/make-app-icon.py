"""
Erzeugt das Home-Bildschirm-Icon der Seite:

    assets/apple-touch-icon.png    180x180, Nachtblau-Verlauf, Schiff weiss,
                                   magentafarbene Linie darunter

Die Silhouette stammt aus tools/ship-icon-source.png (weisses Schiff auf
dunklem Grund). Sie wird als Maske herausgeloest und neu eingefaerbt.

Optional: --report-set ORDNER schreibt zusaetzlich die Variante mit dem
urspruenglichen dunklen Grund (#1D1511) und derselben Linie in vier Groessen
(180, 192, 512, 512 maskable), damit die Berichts-App zur Seite passt.

Benoetigt: pip install pillow numpy
Aufruf:    python tools/make-app-icon.py [--report-set ORDNER]
"""

import argparse
from pathlib import Path

import numpy as np
from PIL import Image, ImageChops, ImageDraw

ROOT = Path(__file__).resolve().parent.parent
SOURCE = ROOT / "tools" / "ship-icon-source.png"
OUT = ROOT / "assets" / "apple-touch-icon.png"

S = 512                                   # Arbeitsgroesse, alles wird daraus skaliert

WHITE = (255, 255, 255)
MAGENTA = (182, 31, 82)
PAGE_BG = ((14, 40, 71), (31, 90, 160))   # Verlauf oben -> unten
REPORT_BG = (29, 21, 17)                  # Grund des bisherigen Icons

LINE_GAP, LINE_H = 15, 8                  # Abstand Rumpf -> Linie, Liniendicke bei S=512
GROUP_SHIFT = -12                         # Schiff + Linie zusammen optisch mittig
MASKABLE_SCALE = 70 / 83                  # Schiff 70 % statt 83 % der Breite (Safe Zone)


def load_mask():
    lum = np.asarray(Image.open(SOURCE).convert("RGB")).astype(float).mean(axis=2)
    bg = lum[2, 2]
    alpha = np.clip((lum - bg) / (255 - bg), 0, 1)
    mask = Image.fromarray((alpha * 255).astype("uint8"), "L")
    ys, xs = np.where(alpha > 0.5)
    return mask, (int(xs.min()), int(xs.max()), int(ys.max()))


MASK, (X0, X1, SHIP_BOTTOM) = load_mask()


def background(spec):
    if isinstance(spec[0], tuple):
        t = np.linspace(0, 1, S)[:, None, None]
        arr = np.array(spec[0])[None, None, :] * (1 - t) + np.array(spec[1])[None, None, :] * t
        return Image.fromarray(np.repeat(arr, S, axis=1).astype("uint8"), "RGB")
    return Image.new("RGB", (S, S), spec)


def group(scale=1.0):
    """Schiff + Linie als transparente Ebene, optional um die Mitte verkleinert."""
    ship = Image.new("RGBA", (S, S), WHITE + (0,))
    ship.putalpha(ImageChops.offset(MASK, 0, GROUP_SHIFT))

    line = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    y = SHIP_BOTTOM + GROUP_SHIFT + LINE_GAP
    ImageDraw.Draw(line).rectangle([X0, y, X1, y + LINE_H - 1], fill=MAGENTA + (255,))

    layer = Image.alpha_composite(ship, line)
    if scale != 1.0:
        n = round(S * scale)
        small = layer.resize((n, n), Image.LANCZOS)
        layer = Image.new("RGBA", (S, S), (0, 0, 0, 0))
        layer.paste(small, ((S - n) // 2, (S - n) // 2))
    return layer


def render(bg_spec, scale=1.0):
    base = background(bg_spec).convert("RGBA")
    return Image.alpha_composite(base, group(scale)).convert("RGB")


def save(img, path, size):
    path.parent.mkdir(parents=True, exist_ok=True)
    out = img if size == S else img.resize((size, size), Image.LANCZOS)
    out.save(path, optimize=True)
    print(f"{path}  ({size}x{size}, {path.stat().st_size / 1024:.0f} KB)")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--report-set", type=Path, metavar="ORDNER",
                    help="zusaetzlich das dunkle Icon-Set fuer die Berichts-App schreiben")
    args = ap.parse_args()

    # iOS rundet die Ecken selbst und will keine Transparenz: volle Flaeche, RGB.
    save(render(PAGE_BG), OUT, 180)

    if args.report_set:
        d = args.report_set
        full, maskable = render(REPORT_BG), render(REPORT_BG, MASKABLE_SCALE)
        save(full, d / "apple-touch-icon.png", 180)
        save(full, d / "icon-192.png", 192)
        save(full, d / "icon-512.png", 512)
        save(maskable, d / "icon-512-maskable.png", 512)
