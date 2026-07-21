"""Render docs/demo.gif -- a faithful animation of one bay-hack loop run.

DEV TOOL ONLY. Needs Pillow (`pip install pillow`); it is NOT a runtime dependency
of bay-hack -- the committed GIF has no deps. Frames are drawn from the REAL loop
output (bayhack.dashboard.run_loop), in the matcha house style.

    python scripts/make_gif.py
"""
from __future__ import annotations

import os
import sys

from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from bayhack.dashboard import run_loop  # noqa: E402

W, H = 720, 420
INK = (40, 55, 42)
MATCHA = (92, 174, 90)
DEEP = (60, 132, 70)
MUTED = (111, 130, 116)
LINE = (230, 239, 232)
WASH = (242, 248, 243)
LOWSIG = (238, 242, 251)
DYE = (47, 111, 214)


def font(size, bold=False):
    names = (["/System/Library/Fonts/Supplemental/Arial Bold.ttf"] if bold else
             ["/System/Library/Fonts/Supplemental/Arial.ttf"]) + \
            ["/System/Library/Fonts/Helvetica.ttc", "/Library/Fonts/Arial.ttf"]
    for p in names:
        try:
            return ImageFont.truetype(p, size)
        except OSError:
            continue
    return ImageFont.load_default()


F_TITLE = font(32, bold=True)
F_SUB = font(17)
F_LABEL = font(12, bold=True)
F_NUM = font(12)
F_BANNER = font(17, bold=True)


def dye(f):
    f = max(0.0, min(1.0, f))
    return tuple(int(LOWSIG[i] + (DYE[i] - LOWSIG[i]) * f) for i in range(3))


def label(d, xy, text, fnt, fill, spacing=0):
    if spacing:
        x, y = xy
        for ch in text:
            d.text((x, y), ch, font=fnt, fill=fill)
            x += d.textlength(ch, font=fnt) + spacing
    else:
        d.text(xy, text, font=fnt, fill=fill)


def frame(rounds, upto, x_star, runs_used, grid, final=False):
    img = Image.new("RGB", (W, H), "white")
    d = ImageDraw.Draw(img)
    # header
    d.text((40, 26), "bay-hack", font=F_TITLE, fill=DEEP)
    d.text((40, 66), "two world models close the liquid-handling loop", font=F_SUB, fill=INK)
    d.line((40, 100, W - 40, 100), fill=LINE, width=1)

    # proposed experiments (wells reveal one per frame)
    label(d, (40, 116), "PROPOSED EXPERIMENTS", F_LABEL, DEEP, spacing=2)
    x0, y0, sz, gap = 40, 140, 42, 12
    for i, r in enumerate(rounds[:upto]):
        x = x0 + i * (sz + gap)
        best = i == max(range(upto), key=lambda k: rounds[k].best_y) and \
            r.best_y == max(rounds[j].best_y for j in range(upto))
        d.rounded_rectangle((x, y0, x + sz, y0 + sz), radius=8, fill=dye(r.fluor),
                            outline=MATCHA if best else LINE, width=3 if best else 1)
        well = r.well
        d.text((x + sz / 2 - d.textlength(well, font=F_NUM) / 2, y0 + sz + 5),
               well, font=F_NUM, fill=MUTED)

    # convergence mini-chart
    label(d, (40, 214), "CONVERGENCE  (best-so-far)", F_LABEL, DEEP, spacing=2)
    cx, cy, cw, ch = 40, 238, W - 80, 96
    d.rectangle((cx, cy, cx + cw, cy + ch), outline=LINE, width=1)
    n = len(rounds)
    def px(i): return cx + 14 + (cw - 28) * (0.5 if n < 2 else i / (n - 1))
    def py(v): return cy + ch - 12 - (ch - 24) * max(0.0, min(1.0, v))
    d.line((cx, py(1), cx + cw, py(1)), fill=(157, 184, 160), width=1)  # max response
    pts = [(px(i), py(rounds[i].best_y)) for i in range(upto)]
    if len(pts) >= 2:
        d.line(pts, fill=MATCHA, width=3, joint="curve")
    for i in range(upto):
        d.ellipse((px(i) - 4, py(rounds[i].fluor) - 4, px(i) + 4, py(rounds[i].fluor) + 4),
                  fill=(201, 216, 242), outline=DYE)
        d.ellipse((px(i) - 3.5, py(rounds[i].best_y) - 3.5, px(i) + 3.5, py(rounds[i].best_y) + 3.5),
                  fill=DEEP)

    # banner
    by = 356
    if final:
        d.rounded_rectangle((40, by, W - 40, by + 44), radius=12, fill=WASH, outline=MATCHA, width=1)
        d.ellipse((56, by + 17, 66, by + 27), fill=MATCHA)
        msg = f"ACCEPT in {runs_used} runs vs ~{grid} grid  |  follow-up: 20 uL to H12"
        d.text((78, by + 13), msg, font=F_BANNER, fill=DEEP)
    else:
        r = rounds[upto - 1] if upto else None
        txt = (f"{r.phase} {r.well}:  {r.stock_ul:.1f} uL stock + "
               f"{r.diluent_ul:.1f} uL diluent   signal={r.fluor:.3f}   "
               f"gate: {r.decision}") if r else \
            "scientific model proposing the next physical experiment..."
        d.text((40, by + 13), txt, font=F_SUB, fill=MUTED)
    return img


def main():
    d = run_loop(seed=7)
    rounds = [type("R", (), r)() for r in d["rounds"]]  # attr access
    for r, raw in zip(rounds, d["rounds"]):
        r.__dict__.update(raw)
    frames = [frame(rounds, 0, d["x_star"], d["runs_used"], d["grid"])]  # intro
    for f in range(1, len(rounds) + 1):
        frames.append(frame(rounds, f, d["x_star"], d["runs_used"], d["grid"]))
    final = frame(rounds, len(rounds), d["x_star"], d["runs_used"], d["grid"], final=True)
    frames += [final] * 3  # hold the payoff
    durations = [700] + [650] * len(rounds) + [1500, 1500, 1500]
    out = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                       "docs", "demo.gif")
    frames[0].save(out, save_all=True, append_images=frames[1:], duration=durations,
                   loop=0, optimize=True)
    print(f"wrote {out}  ({os.path.getsize(out) // 1024} KB, {len(frames)} frames)")


if __name__ == "__main__":
    main()
