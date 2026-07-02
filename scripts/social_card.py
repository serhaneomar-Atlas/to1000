#!/usr/bin/env python3
"""social_card.py — visuels de marque ESTÁDIO (Pillow), sans photo source.

- make_card(...)   : carte sociale 1200x630 par article (titre flash-info +
                     label + compteur CR7 + marque). Look broadcast premium.
- make_banner(...) : bannières de couverture (Facebook / Twitter) + avatar.

Identité : fond #05070b, or #f2c14e, Anton (display) + Hanken (corps). 100% vectoriel/typographique → aucun souci de droits d'image.
"""
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont, ImageFilter

ROOT = Path(__file__).resolve().parent.parent
FONTS = ROOT / "assets" / "fonts"
INK = (5, 7, 11)
PANEL = (13, 17, 24)
GOLD = (242, 193, 78)
GOLD_HOT = (255, 214, 107)
CHALK = (238, 242, 246)
MUTE = (154, 166, 180)


def _font(name, size):
    return ImageFont.truetype(str(FONTS / name), size)


def _glow(size, center, radius, color, alpha=90):
    """Halo doux (or) via ellipse floue sur calque alpha."""
    layer = Image.new("RGBA", size, (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    x, y = center
    d.ellipse([x - radius, y - radius, x + radius, y + radius], fill=color + (alpha,))
    return layer.filter(ImageFilter.GaussianBlur(radius // 2))


def _wrap(draw, text, font, max_w):
    words, lines, cur = text.split(), [], ""
    for w in words:
        t = (cur + " " + w).strip()
        if draw.textlength(t, font=font) <= max_w:
            cur = t
        else:
            if cur:
                lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return lines


def make_card(title, label="FOOTBALL", counter="975/1000", out_path="card.png",
              size=(1200, 630)):
    W, H = size
    img = Image.new("RGB", size, INK)
    # halos or (haut-droite + accent bas-gauche)
    img.paste(Image.alpha_composite(img.convert("RGBA"),
              _glow(size, (int(W * 0.86), int(H * 0.16)), int(H * 0.7), GOLD, 60)).convert("RGB"), (0, 0))
    img = Image.alpha_composite(img.convert("RGBA"),
          _glow(size, (int(W * 0.05), int(H * 1.0)), int(H * 0.6), GOLD, 45)).convert("RGB")
    d = ImageDraw.Draw(img)
    pad = 70

    # barre d'accent or à gauche
    d.rectangle([0, 0, 10, H], fill=GOLD)

    # eyebrow : marque + label
    f_eye = _font("HankenGrotesk.ttf", 28)
    eye = f"TO1000.COM   ·   {label.upper()}"
    d.text((pad, 58), eye, font=f_eye, fill=GOLD)

    # titre (Anton, wrap, ancré bas-gauche façon lower-third)
    f_title = _font("Anton-Regular.ttf", 72)
    max_w = W - pad * 2
    lines = _wrap(d, title, f_title, max_w)[:4]
    lh = 84
    block_h = lh * len(lines)
    y = H - 165 - block_h
    for ln in lines:
        d.text((pad, y), ln, font=f_title, fill=CHALK)
        y += lh

    # footer : compteur CR7 (chip or) + url
    f_lab = _font("HankenGrotesk.ttf", 30)
    chip = f"⚽ {counter}"
    # chip sans emoji (Pillow ne rend pas l'emoji couleur) → puce ronde
    chip = counter
    cw = d.textlength(chip, font=f_lab)
    cx, cy = pad, H - 92
    d.rounded_rectangle([cx, cy, cx + cw + 44, cy + 48], radius=24, fill=GOLD)
    d.ellipse([cx + 16, cy + 18, cx + 28, cy + 30], fill=INK)
    d.text((cx + 40, cy + 9), chip, font=f_lab, fill=INK)
    d.text((W - pad - d.textlength("to1000.com", font=f_lab), cy + 9),
           "to1000.com", font=f_lab, fill=MUTE)

    _save(img, out_path)
    return out_path


def _save(img, out_path):
    """Format selon l'extension. JPEG requis pour les cartes : Instagram
    (auto-post Make) refuse le PNG — avant, un proxy wsrv.nl convertissait."""
    out = Path(out_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    if out.suffix.lower() in (".jpg", ".jpeg"):
        img.save(out, "JPEG", quality=88, optimize=True)
    else:
        img.save(out, "PNG")


def make_banner(kind="twitter", out_path="banner.png"):
    sizes = {"twitter": (1500, 500), "facebook": (1640, 624), "avatar": (500, 500)}
    W, H = sizes[kind]
    img = Image.new("RGB", (W, H), INK)
    img = Image.alpha_composite(img.convert("RGBA"),
          _glow((W, H), (int(W * 0.5), int(H * 0.5)), int(H * 0.9), GOLD, 55)).convert("RGB")
    d = ImageDraw.Draw(img)
    if kind == "avatar":
        f = _font("Anton-Regular.ttf", 150)
        d.text((W / 2, H / 2 - 40), "TO", font=f, fill=CHALK, anchor="mm")
        d.text((W / 2, H / 2 + 90), "1000", font=f, fill=GOLD, anchor="mm")
    else:
        f_big = _font("Anton-Regular.ttf", int(H * 0.34))
        f_sub = _font("HankenGrotesk.ttf", int(H * 0.075))
        d.text((W / 2, H * 0.40), "TO1000", font=f_big, fill=CHALK, anchor="mm")
        # "1000" en or par-dessus
        wm = d.textlength("TO1000", font=f_big)
        w10 = d.textlength("1000", font=f_big)
        d.text((W / 2 + wm / 2 - w10, H * 0.40), "1000", font=f_big, fill=GOLD, anchor="lm")
        d.text((W / 2, H * 0.72), "L'ACTU FOOT, DROIT AU BUT · CR7 VERS 1000 BUTS",
               font=f_sub, fill=MUTE, anchor="mm")
        d.rectangle([W / 2 - 120, H * 0.60, W / 2 + 120, H * 0.60 + 4], fill=GOLD)
    _save(img, out_path)
    return out_path


if __name__ == "__main__":
    import sys
    make_banner("twitter", ROOT / "public/social/brand/header-twitter.png")
    make_banner("facebook", ROOT / "public/social/brand/cover-facebook.png")
    make_banner("avatar", ROOT / "public/social/brand/avatar.png")
    make_card("Le Canada file en huitièmes grâce au but de Eustaquio dans les arrêts de jeu",
              "MONDIAL 2026", "975/1000", ROOT / "public/social/samples/demo1.png")
    make_card("Ronaldo « à fond derrière Neymar » avant le choc de Coupe du monde",
              "CR7", "975/1000", ROOT / "public/social/samples/demo2.png")
    make_card("Gonçalo Ramos rejoint l'AC Milan en provenance du PSG pour 60 M£",
              "MERCATO", "975/1000", ROOT / "public/social/samples/demo3.png")
    print("visuels générés dans public/social/")
