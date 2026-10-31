# ECHO OF THE DEPTHS - 5 bolumlu, prosedurel 3B gerilim/korku oyunu
# Gereksinimler: Python 3.10+, ursina, pillow
# Kurulum: py -m pip install ursina pillow
# Calistirma: py Echo_of_the_Depths.py
# Tum dokular, sesler ve dusman modelleri oyun acilirken yerel olarak uretilir.
# Performans: oda chunk streaming + oyuncu/kamera/yaratik yakinlik alanlari.

from __future__ import annotations
import os
import sys
import math
import random
import wave
import struct
import traceback
import threading
from pathlib import Path
from collections import deque

if sys.version_info < (3, 12):
    message = (f"Bu oyun icin Python 3.12 veya daha yenisi gerekiyor. Su anki surum: "
               f"{sys.version.split()[0]}")
    print(message)
    try:
        log_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "echo_hata.txt")
        with open(log_path, "w", encoding="utf-8") as log:
            log.write(message + "\n")
    except OSError:
        pass
    input("Cikmak icin Enter...")
    raise SystemExit(1)

try:
    from ursina import *
    from panda3d.core import (
        AmbientLight as PandaAmbientLight,
        PointLight as PandaPointLight,
        Spotlight as PandaSpotlight,
        PerspectiveLens,
        Fog,
    )
    from PIL import Image, ImageDraw, ImageChops, ImageFilter
    # Ursina does not register a built-in model named "cylinder".
    # Use its procedural Cylinder mesh instead.
    from ursina.models.procedural.cylinder import Cylinder as UrsinaCylinder
    from ursina.models.procedural.cone import Cone as UrsinaCone
except ImportError as exc:
    print("Gerekli kutuphane bulunamadi:", exc)
    print("Terminalde su komutu calistir: py -m pip install ursina pillow")
    input("Cikmak icin Enter...")
    raise SystemExit(1)

# Tek bir paylasilan, prosedurel silindir modeli; tum esyalar bunu kullanir.
CYLINDER_MODEL = UrsinaCylinder(resolution=12, start=-0.5)
CONE_MODEL = UrsinaCone(resolution=8, radius=0.5, height=1.0)

# -----------------------------------------------------------------------------
# Genel ayarlar
# -----------------------------------------------------------------------------
APP_NAME = "ECHO OF THE DEPTHS"
CELL = 12.0
GRID = 7
WORLD = CELL * GRID
WALL_H = 4.2
WALL_T = 0.34
DOOR_W = 3.25
PLAYER_RADIUS = 0.38
SAVE_VERSION = 1

random.seed()

app = Ursina(title=APP_NAME)
window.title = APP_NAME
window.color = color.rgb32(7, 10, 14)
# Panda3D sahne temizleme rengini de ayarla; beyaz bos ekran gorunmesini engeller.
application.base.setBackgroundColor(0.012, 0.018, 0.026, 1.0)
window.fps_counter.enabled = True
window.exit_button.visible = True
window.vsync = True
camera.fov = 92
camera.clip_plane_far = 170
mouse.locked = True

# Renk yardimcisi
hx = color.hex

# Her bolum kendi paletini, dokusunu ve dusman gorunumunu kullanir.
CHAPTERS = [
    {
        "name": "KARANLIK MALIKANE", "subtitle": "Bolum 1 / Uyanis",
        "story": "Eski guc panelini calistir. Ana cikisa giden kilidi ac.",
        "item": "sigorta", "item_name": "Sigorta", "required": 5,
        "gate": "Ana kapi", "gate_text": "5 sigortayi panele yerlestir ve ana kapidan cik.",
        "wall": (82, 57, 43), "floor": (57, 38, 29), "trim": (135, 91, 55),
        "glow": (255, 190, 103), "fog": (22, 13, 10), "ambient": (0.17, 0.12, 0.09, 1),
        "enemy": (87, 105, 87), "enemy_eye": (255, 177, 82),
        "speed": 2.65, "sight": 21, "hearing": 13, "spawn": 55,
        "drain": 0.65, "room_style": "wood",
    },
    {
        "name": "KAPATILMIS HASTANE", "subtitle": "Bolum 2 / Arsiv",
        "story": "Hasta arsivindeki 5 veri diskini bul. Asansor sistemini yeniden baslat.",
        "item": "disk", "item_name": "Veri diski", "required": 5,
        "gate": "Asansor", "gate_text": "Bes veri diskini arsiv konsoluna tak ve asansore bin.",
        "wall": (91, 101, 99), "floor": (48, 58, 57), "trim": (130, 160, 151),
        "glow": (115, 231, 204), "fog": (8, 20, 21), "ambient": (0.09, 0.15, 0.15, 1),
        "enemy": (76, 103, 101), "enemy_eye": (124, 255, 224),
        "speed": 3.05, "sight": 24, "hearing": 15, "spawn": 48,
        "drain": 0.8, "room_style": "tile",
    },
    {
        "name": "SISLI ORMAN ISTASYONU", "subtitle": "Bolum 3 / Yanki",
        "story": "Orman istasyonundaki 5 sinyal rolesini topla. Vericiyi etkinlestir.",
        "item": "role", "item_name": "Sinyal rolesi", "required": 5,
        "gate": "Verici kapisi", "gate_text": "Tum rolesleri vericiye tak ve disari giden sinyali ac.",
        "wall": (62, 79, 60), "floor": (42, 57, 39), "trim": (113, 128, 76),
        "glow": (184, 220, 116), "fog": (10, 24, 14), "ambient": (0.10, 0.15, 0.09, 1),
        "enemy": (68, 88, 58), "enemy_eye": (209, 241, 123),
        "speed": 3.45, "sight": 27, "hearing": 18, "spawn": 42,
        "drain": 1.0, "room_style": "bark",
    },
    {
        "name": "YERALTI SIGINAGI", "subtitle": "Bolum 4 / Basinc",
        "story": "Siginagin derinliklerinde 5 basinc vanasini bul. Celik kapinin kilidini dusur.",
        "item": "vana", "item_name": "Basinc vanasi", "required": 5,
        "gate": "Celik kapi", "gate_text": "Bes vanayi kontrol konsoluna yerlestir ve celik kapidan gec.",
        "wall": (78, 82, 91), "floor": (39, 43, 51), "trim": (139, 146, 151),
        "glow": (255, 164, 91), "fog": (11, 14, 21), "ambient": (0.09, 0.10, 0.14, 1),
        "enemy": (82, 86, 104), "enemy_eye": (255, 154, 87),
        "speed": 3.9, "sight": 30, "hearing": 21, "spawn": 36,
        "drain": 1.25, "room_style": "concrete",
    },
    {
        "name": "SAAT KULESI", "subtitle": "Bolum 5 / Son Yanki",
        "story": "Saatin 6 kayip parcasini bul. Mekanizmayi calistir ve son cikisa ulas.",
        "item": "parca", "item_name": "Saat parcasi", "required": 6,
        "gate": "Son kapi", "gate_text": "Alti parcayi saate yerlestir. Son kapiyi ac.",
        "wall": (67, 57, 79), "floor": (41, 34, 56), "trim": (168, 135, 83),
        "glow": (236, 198, 113), "fog": (15, 10, 25), "ambient": (0.12, 0.09, 0.16, 1),
        "enemy": (93, 76, 116), "enemy_eye": (246, 207, 127),
        "speed": 4.35, "sight": 34, "hearing": 24, "spawn": 31,
        "drain": 1.55, "room_style": "clock",
    },
]

# -----------------------------------------------------------------------------
# Dokular ve sesler: harici gorsel dosyasi gerektirmez.
# -----------------------------------------------------------------------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ASSET_DIR = os.path.join(BASE_DIR, "echo_assets")
TEX_DIR = os.path.join(ASSET_DIR, "textures")
SFX_DIR = os.path.join(ASSET_DIR, "audio")
os.makedirs(TEX_DIR, exist_ok=True)
os.makedirs(SFX_DIR, exist_ok=True)


def blend_noise(img: Image.Image, amount: float = 0.12) -> Image.Image:
    """Layered surface grain, subtle wear and fine scratches for game-ready materials."""
    base = img.convert("RGB")
    coarse = Image.effect_noise((64, 64), 32).convert("L").resize(
        base.size, Image.Resampling.BICUBIC
    )
    fine = Image.effect_noise(base.size, 48).convert("L")
    layered = ImageChops.blend(coarse, fine, .62)
    multiplier = layered.point(
        lambda value: max(198, min(255, 232 + int((value - 128) * .18)))
    )
    multiplier_rgb = Image.merge("RGB", (multiplier, multiplier, multiplier))
    weathered = ImageChops.multiply(base, multiplier_rgb)
    result = Image.blend(base, weathered, min(.55, amount * 1.45))

    overlay = Image.new("RGBA", result.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    rng = random.Random(4100 + int(amount * 10000) + result.size[0])
    width, height = result.size
    for _ in range(220):
        x, y = rng.randrange(width), rng.randrange(height)
        end_x = min(width - 1, x + rng.randrange(5, 42))
        end_y = max(0, min(height - 1, y + rng.randint(-2, 2)))
        tint = ((8, 6, 5, rng.randrange(9, 25)) if rng.random() < .72
                else (224, 207, 174, rng.randrange(8, 20)))
        draw.line((x, y, end_x, end_y), fill=tint, width=1)
    result = Image.alpha_composite(result.convert("RGBA"), overlay).convert("RGB")
    return result.filter(ImageFilter.UnsharpMask(radius=.7, percent=65, threshold=3))


def _shade(rgb, delta):
    return tuple(max(0, min(255, int(c + delta))) for c in rgb)


def build_chapter_textures(chapter_index: int, style: dict) -> tuple[str, str, str]:
    """Bolume gore 512px, katmanli ve tekrar edilebilir duvar/zemin/metal dokulari."""
    wall_path = os.path.join(TEX_DIR, f"wall_{chapter_index}_v6.png")
    floor_path = os.path.join(TEX_DIR, f"floor_{chapter_index}_v6.png")
    metal_path = os.path.join(TEX_DIR, f"metal_{chapter_index}_v6.png")
    if all(os.path.exists(p) and os.path.getsize(p) > 12000 for p in (wall_path, floor_path, metal_path)):
        return wall_path, floor_path, metal_path

    size = 512
    wc, fc, tc = style["wall"], style["floor"], style["trim"]
    mode = style["room_style"]

    wall = Image.new("RGB", (size, size), wc)
    d = ImageDraw.Draw(wall)
    if mode == "wood":
        plank = 64
        for y in range(0, size, plank):
            base = _shade(wc, (-9, 3, 8, -4)[(y // plank) % 4])
            d.rectangle((0, y, size, y + plank - 3), fill=base)
            d.line((0, y, size, y), fill=_shade(wc, -34), width=4)
            d.line((0, y + plank - 3, size, y + plank - 3), fill=_shade(wc, 20), width=2)
            for _ in range(18):
                x = random.randrange(size)
                yy = y + random.randrange(5, plank - 5)
                run = random.randrange(18, 130)
                d.line((x, yy, min(size, x + run), yy + random.choice((-2, -1, 0, 1, 2))), fill=_shade(base, random.choice((-20, -13, 11, 16))), width=1)
            if y % 128 == 0:
                x = random.randrange(35, size - 55)
                yy = y + random.randrange(12, 52)
                d.ellipse((x, yy, x + 34, yy + 13), outline=_shade(wc, -38), width=3)
                d.ellipse((x + 8, yy + 3, x + 25, yy + 10), outline=_shade(wc, 23), width=1)
        for x in range(18, size, 128):
            for y in range(28, size, 128):
                d.ellipse((x - 3, y - 3, x + 3, y + 3), fill=_shade(tc, -25))
        d.rectangle((0, 0, size - 1, size - 1), outline=_shade(tc, -20), width=5)
    elif mode == "tile":
        tile_w, tile_h = 64, 64
        for y in range(0, size, tile_h):
            for x in range(0, size, tile_w):
                base = _shade(wc, random.randint(-8, 10))
                d.rectangle((x + 2, y + 2, x + tile_w - 3, y + tile_h - 3), fill=base)
                d.line((x + 3, y + 3, x + tile_w - 4, y + 3), fill=_shade(base, 24), width=2)
                d.line((x + 3, y + 3, x + 3, y + tile_h - 4), fill=_shade(base, 15), width=2)
                d.line((x + 3, y + tile_h - 4, x + tile_w - 4, y + tile_h - 4), fill=_shade(base, -28), width=2)
        for _ in range(32):
            x, y = random.randrange(size), random.randrange(size)
            r = random.randrange(3, 15)
            d.ellipse((x-r, y-r, x+r, y+r), fill=_shade(wc, random.choice((-25, -18, 14))))
    elif mode == "bark":
        for x in range(-12, size + 16, 30):
            xx = x + random.randint(-8, 8)
            d.line((xx, 0, xx + random.randint(-12, 12), size), fill=_shade(wc, random.randint(-31, -15)), width=random.randint(3, 7))
            d.line((xx + 8, 0, xx + random.randint(2, 15), size), fill=_shade(wc, random.randint(10, 24)), width=2)
        for _ in range(65):
            x, y = random.randrange(size), random.randrange(size)
            rx, ry = random.randrange(2, 13), random.randrange(3, 19)
            d.ellipse((x-rx, y-ry, x+rx, y+ry), fill=_shade(wc, random.choice((-26, -18, 15, 22))))
        for y in (90, 285, 450):
            d.line((0, y, size, y + random.randint(-8, 8)), fill=_shade(wc, -35), width=5)
    elif mode == "concrete":
        for y in range(0, size, 128):
            d.line((0, y, size, y), fill=_shade(wc, -27), width=4)
            d.line((0, y + 5, size, y + 5), fill=_shade(wc, 16), width=2)
        for x in (128, 384):
            d.line((x, 0, x, size), fill=_shade(wc, -22), width=3)
        for _ in range(35):
            x, y = random.randrange(size), random.randrange(size)
            length = random.randrange(10, 65)
            d.line((x, y, x + random.randrange(-14, 14), y + length), fill=_shade(wc, random.choice((-38, -28, 18))), width=1)
        for _ in range(65):
            x, y = random.randrange(size), random.randrange(size)
            r = random.randrange(2, 7)
            d.ellipse((x-r, y-r, x+r, y+r), fill=_shade(wc, random.choice((-29, -18, 20))))
    else:  # saat kulesi: koyu lake ahsap + ince pirinc citalar
        for y in range(0, size, 96):
            d.rectangle((0, y, size, y + 92), fill=_shade(wc, random.randint(-8, 8)))
            d.line((0, y, size, y), fill=_shade(tc, -20), width=5)
            d.line((0, y + 5, size, y + 5), fill=_shade(tc, 12), width=2)
            for x in range(36, size, 128):
                d.rectangle((x, y + 16, x + 78, y + 78), outline=_shade(tc, -3), width=3)
                d.ellipse((x + 22, y + 32, x + 56, y + 66), outline=_shade(tc, 16), width=2)

    # Nem lekeleri ve ince kir tabakasi: tekrar eden dokunun duz gorunmesini onler.
    for _ in range(45 if mode in ("tile", "concrete", "bark") else 22):
        x, y = random.randrange(size), random.randrange(size)
        rx, ry = random.randrange(5, 32), random.randrange(4, 24)
        d.ellipse((x-rx, y-ry, x+rx, y+ry), fill=_shade(wc, random.choice((-24, -15, 12))))
    # Fine scratches and hairline cracks are baked into the image (no frame cost).
    for _ in range(150):
        x, y = random.randrange(size), random.randrange(size)
        length = random.randrange(5, 58)
        d.line((x, y, min(size - 1, x + length), min(size - 1, y + random.choice((-2, -1, 0, 1, 2)))),
               fill=_shade(wc, random.choice((-42, -30, -18, 16, 24))), width=1)
    for _ in range(16):
        x, y = random.randrange(size), random.randrange(size)
        d.line((x, y, x + random.randrange(-18, 19), min(size - 1, y + random.randrange(12, 48))),
               fill=_shade(wc, -34), width=2)
    blend_noise(wall, .13).save(wall_path, optimize=True)

    floor = Image.new("RGB", (size, size), fc)
    fd = ImageDraw.Draw(floor)
    if mode in ("wood", "bark", "clock"):
        for y in range(0, size, 48):
            fd.rectangle((0, y, size, y + 45), fill=_shade(fc, random.randint(-8, 9)))
            fd.line((0, y, size, y), fill=_shade(fc, -35), width=4)
            fd.line((0, y + 44, size, y + 44), fill=_shade(fc, 19), width=2)
            for x in range((y // 48 % 2) * 80, size, 160):
                fd.line((x, y, x, y + 45), fill=_shade(fc, -22), width=2)
            for _ in range(12):
                x = random.randrange(size)
                yy = y + random.randrange(4, 42)
                fd.line((x, yy, min(size, x + random.randrange(12, 90)), yy + random.randint(-1, 1)), fill=_shade(fc, random.choice((-24, -12, 14))), width=1)
    else:
        for y in range(0, size, 64):
            for x in range(0, size, 64):
                base = _shade(fc, random.randint(-7, 8))
                fd.rectangle((x + 2, y + 2, x + 62, y + 62), fill=base)
                fd.line((x + 3, y + 3, x + 61, y + 3), fill=_shade(base, 17), width=2)
                fd.line((x + 3, y + 61, x + 61, y + 61), fill=_shade(base, -24), width=2)
        for _ in range(50):
            x, y = random.randrange(size), random.randrange(size)
            r = random.randrange(2, 10)
            fd.ellipse((x-r, y-r, x+r, y+r), fill=_shade(fc, random.choice((-30, -18, 17))))
    # Ground-in dirt and fine scuffs for close-up floor detail.
    for _ in range(260):
        x, y = random.randrange(size), random.randrange(size)
        r = random.choice((1, 1, 2, 3))
        fd.ellipse((x-r, y-r, x+r, y+r), fill=_shade(fc, random.choice((-34, -23, -12, 15))))
    for _ in range(90):
        x, y = random.randrange(size), random.randrange(size)
        fd.line((x, y, min(size - 1, x + random.randrange(4, 42)), y + random.choice((-1, 0, 1))),
                fill=_shade(fc, random.choice((-30, -18, 18))), width=1)
    blend_noise(floor, .11).save(floor_path, optimize=True)

    metal = Image.new("RGB", (size, size), _shade(tc, -8))
    md = ImageDraw.Draw(metal)
    for y in range(0, size, 32):
        md.line((0, y, size, y), fill=_shade(tc, -35), width=3)
        md.line((0, y + 4, size, y + 4), fill=_shade(tc, 22), width=2)
    for _ in range(90):
        x, y = random.randrange(size), random.randrange(size)
        md.line((x, y, min(size, x + random.randrange(4, 38)), y + random.randint(-2, 2)), fill=_shade(tc, random.choice((-46, -28, 22, 34))), width=1)
    for x in (18, size - 18):
        for y in (18, size - 18):
            md.ellipse((x - 7, y - 7, x + 7, y + 7), fill=(30, 34, 38), outline=_shade(tc, 35), width=3)
    # Oxidation specks and rubbed metal edges.
    for _ in range(220):
        x, y = random.randrange(size), random.randrange(size)
        r = random.choice((1, 2, 3))
        md.ellipse((x-r, y-r, x+r, y+r), fill=_shade(tc, random.choice((-55, -38, -20, 28))))
    blend_noise(metal, .09).save(metal_path, optimize=True)
    return wall_path, floor_path, metal_path


def build_chapter_detail_textures(chapter_index: int, style: dict) -> tuple[str, str]:
    """Create a distinct damaged wall variant and a chapter-specific ceiling."""
    alt_path = os.path.join(TEX_DIR, f"wall_alt_{chapter_index}_v6.png")
    ceiling_path = os.path.join(TEX_DIR, f"ceiling_{chapter_index}_v6.png")
    if all(os.path.exists(p) and os.path.getsize(p) > 9000 for p in (alt_path, ceiling_path)):
        return alt_path, ceiling_path

    size = 512
    wc, fc, tc = style["wall"], style["floor"], style["trim"]
    mode = style["room_style"]
    rng = random.Random(6300 + chapter_index * 97)

    # Secondary wall material is deliberately unlike the primary wall map.
    alt = Image.new("RGB", (size, size), _shade(wc, -17))
    d = ImageDraw.Draw(alt)
    if mode == "wood":
        # Peeling wallpaper over old timber, torn seams and water marks.
        for y in range(0, size, 86):
            base = _shade(wc, rng.randint(-12, 10))
            d.rectangle((0, y, size, y + 78), fill=base)
            d.line((0, y + 78, size, y + 78), fill=_shade(wc, -42), width=4)
            for x in range(rng.randrange(12, 42), size, 96):
                d.rectangle((x, y + 8, min(size, x + rng.randrange(28, 70)), y + 68),
                            fill=_shade(base, rng.choice((-20, -12, 9))))
        for _ in range(26):
            x, y = rng.randrange(size), rng.randrange(size)
            d.polygon([(x, y), (min(size-1, x+40), y+6),
                       (min(size-1, x+24), min(size-1, y+55))],
                      fill=_shade(wc, -37))
    elif mode == "tile":
        # Hospital wall: glazed tiles, discoloured grout and fine cracks.
        for y in range(0, size, 72):
            offset = 0 if (y // 72) % 2 == 0 else 36
            for x in range(-72 + offset, size, 72):
                x0, x1 = max(0, x+3), min(size-1, x+67)
                d.rounded_rectangle((x0, y+3, x1, min(size-1, y+67)), radius=4,
                                    fill=_shade(wc, rng.randint(-18, 5)),
                                    outline=_shade(wc, -39), width=3)
                d.line((x0+5, y+8, x1-5, y+8), fill=_shade(wc, 19), width=2)
        for _ in range(20):
            x, y = rng.randrange(size), rng.randrange(size)
            d.line((x, y, min(size-1, x+rng.randrange(8, 42)),
                    min(size-1, y+rng.randrange(8, 54))), fill=_shade(wc, -44), width=2)
    elif mode == "bark":
        # Forest station: bark-like vertical fibres with moss islands.
        for x in range(-10, size, 24):
            xx = x + rng.randrange(-7, 8)
            d.line((xx, 0, xx+rng.randrange(-16, 16), size),
                   fill=_shade(wc, rng.choice((-42, -28, 18))), width=rng.randrange(2, 8))
        for _ in range(58):
            x, y = rng.randrange(size), rng.randrange(size)
            rx, ry = rng.randrange(5, 24), rng.randrange(4, 15)
            d.ellipse((x-rx, y-ry, x+rx, y+ry), fill=_shade((77, 91, 54), rng.randrange(-12, 14)))
    elif mode == "concrete":
        # Silo concrete: formwork seams, branching cracks and rust streaks.
        for y in (96, 220, 370, 486):
            d.line((0, y, size, y), fill=_shade(wc, -39), width=5)
            d.line((0, y+5, size, y+5), fill=_shade(wc, 12), width=2)
        for _ in range(26):
            x, y = rng.randrange(size), rng.randrange(size)
            points = [(x, y)]
            for _ in range(rng.randrange(3, 7)):
                x = max(0, min(size-1, x+rng.randrange(-18, 19)))
                y = max(0, min(size-1, y+rng.randrange(9, 28)))
                points.append((x, y))
            d.line(points, fill=_shade(wc, -48), width=2)
        for _ in range(16):
            x, y = rng.randrange(size), rng.randrange(size)
            d.line((x, y, x+rng.randrange(-5, 6), min(size-1, y+70)),
                   fill=(91, 53, 37), width=rng.randrange(2, 5))
    else:
        # Clock tower: dark lacquer panels, brass inlay and circular gear marks.
        for y in range(0, size, 80):
            d.rectangle((0, y, size, y+75), fill=_shade(wc, rng.randrange(-14, 3)))
            d.line((0, y, size, y), fill=_shade(tc, -21), width=4)
            for x in range(40, size, 128):
                d.rectangle((x, y+13, x+72, y+64), outline=_shade(tc, 5), width=3)
                d.ellipse((x+21, y+24, x+51, y+54), outline=_shade(tc, -8), width=2)
                d.ellipse((x+33, y+36, x+39, y+42), fill=_shade(tc, 20))

    for _ in range(100):
        x, y = rng.randrange(size), rng.randrange(size)
        r = rng.randrange(2, 15)
        d.ellipse((x-r, y-r, x+r, y+r), fill=_shade(wc, rng.choice((-40, -26, -14, 10))))
    blend_noise(alt, .16).save(alt_path, optimize=True)

    # Ceiling is a separate material, never another copy of the wall.
    ceiling_base = _shade(wc, -31)
    ceiling = Image.new("RGB", (size, size), ceiling_base)
    cd = ImageDraw.Draw(ceiling)
    if mode in ("wood", "clock"):
        for y in range(0, size, 96):
            cd.rectangle((0, y, size, y+88), fill=_shade(ceiling_base, rng.randrange(-8, 5)))
            cd.line((0, y, size, y), fill=_shade(tc, -25), width=5)
            for x in range(28, size, 128):
                cd.line((x, y+12, x, y+80), fill=_shade(tc, -32), width=3)
    elif mode == "tile":
        for y in range(0, size, 64):
            cd.line((0, y, size, y), fill=_shade(ceiling_base, -27), width=3)
        for x in range(0, size, 128):
            cd.line((x, 0, x, size), fill=_shade(ceiling_base, -24), width=3)
        for _ in range(42):
            x, y = rng.randrange(size), rng.randrange(size)
            cd.ellipse((x-10, y-4, x+10, y+4), fill=(29, 39, 39))
    elif mode == "bark":
        for x in range(0, size, 38):
            cd.line((x, 0, x+rng.randrange(-20, 20), size), fill=_shade(ceiling_base, rng.choice((-21, -10, 8))), width=8)
        for _ in range(45):
            x, y = rng.randrange(size), rng.randrange(size)
            cd.ellipse((x-16, y-8, x+16, y+8), fill=(31, 43, 28))
    else:
        for y in range(0, size, 80):
            cd.line((0, y, size, y), fill=_shade(ceiling_base, -25), width=4)
        for x in range(0, size, 128):
            cd.line((x, 0, x, size), fill=_shade(ceiling_base, -25), width=4)
        for _ in range(36):
            x, y = rng.randrange(size), rng.randrange(size)
            cd.line((x, y, min(size-1, x+30), min(size-1, y+52)), fill=_shade(ceiling_base, -40), width=2)
    blend_noise(ceiling, .12).save(ceiling_path, optimize=True)
    return alt_path, ceiling_path


def build_jumpscare_texture() -> str:
    """Stylised, non-graphic close-up face used for a very brief scare flash."""
    path = os.path.join(TEX_DIR, "stalker_face_v1.png")
    if os.path.exists(path) and os.path.getsize(path) > 9000:
        return path
    size = 512
    img = Image.new("RGBA", (size, size), (5, 7, 9, 255))
    d = ImageDraw.Draw(img)
    rng = random.Random(19041)
    # Shadowed hood and a narrow, distorted mask-like face.
    d.ellipse((56, 8, 456, 520), fill=(13, 16, 18, 255), outline=(52, 54, 48, 255), width=12)
    d.polygon([(104, 96), (206, 46), (306, 49), (408, 130), (365, 442), (146, 445)],
              fill=(26, 30, 29, 255))
    d.ellipse((137, 135, 374, 423), fill=(54, 57, 51, 255), outline=(84, 82, 69, 255), width=8)
    d.polygon([(146, 170), (228, 194), (205, 239), (142, 230)], fill=(4, 6, 8, 255))
    d.polygon([(366, 170), (285, 194), (308, 239), (369, 230)], fill=(4, 6, 8, 255))
    d.ellipse((174, 190, 205, 216), fill=(210, 185, 126, 255))
    d.ellipse((308, 190, 339, 216), fill=(210, 185, 126, 255))
    d.ellipse((185, 198, 197, 210), fill=(255, 228, 177, 255))
    d.ellipse((317, 198, 329, 210), fill=(255, 228, 177, 255))
    d.polygon([(243, 214), (275, 214), (264, 302), (246, 302)], fill=(8, 10, 11, 255))
    d.ellipse((195, 289, 322, 390), fill=(5, 6, 7, 255), outline=(106, 93, 74, 255), width=7)
    for x in range(205, 316, 14):
        d.polygon([(x, 295), (x+9, 296), (x+6, 326), (x+2, 326)], fill=(176, 166, 142, 255))
    for _ in range(210):
        x, y = rng.randrange(size), rng.randrange(size)
        shade = rng.randrange(8, 48)
        d.line((x, y, min(size-1, x+rng.randrange(2, 18)), min(size-1, y+rng.randrange(-6, 8))),
               fill=(shade, shade, shade, rng.randrange(35, 110)), width=1)
    img = img.filter(ImageFilter.GaussianBlur(.55))
    img.save(path)
    return path


def build_audio_files() -> None:
    def make(name: str, duration: float, fn):
        path = os.path.join(SFX_DIR, name + ".wav")
        if os.path.exists(path):
            return path
        sr = 22050
        with wave.open(path, "wb") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(sr)
            frames = bytearray()
            for i in range(int(sr * duration)):
                t = i / sr
                v = max(-1.0, min(1.0, fn(t, duration)))
                frames.extend(struct.pack("<h", int(v * 24000)))
            wf.writeframes(frames)
        return path

    make("ambience", 5.0, lambda t, d: .12 * math.sin(t * 2 * math.pi * 43) + .06 * math.sin(t * 2 * math.pi * 47) + random.uniform(-.025, .025))
    make("step", .16, lambda t, d: random.uniform(-.55, .55) * (1 - t / d) ** 3)
    make("pulse", .32, lambda t, d: math.sin(t * 2 * math.pi * (65 - 25 * t / d)) * (1 - t / d) ** 2)
    make("sting", .75, lambda t, d: (math.sin(t * 2 * math.pi * 110) + .5 * math.sin(t * 2 * math.pi * 58)) * (1 - t / d) ** 2)
    make("pickup", .18, lambda t, d: math.sin(t * 2 * math.pi * (720 - 400 * t / d)) * (1 - t / d))
    make("knock", .58, lambda t, d: .78 * math.sin(t * 2 * math.pi * 74) * math.exp(-t * 8) * (1 if t < .16 else .28) + .12 * random.uniform(-1, 1) * math.exp(-t * 12))
    make("whisper", 1.15, lambda t, d: (.22 * random.uniform(-1, 1) + .12 * math.sin(t * 2 * math.pi * 37)) * (math.sin(math.pi * t / d) ** 1.4))
    make("jumpscare", .46, lambda t, d: (.72 * math.sin(2 * math.pi * (155 - 75 * t / d) * t) + .22 * random.uniform(-1, 1)) * (1 - t / d) ** .45)


# Ses dosyalari ve dokular arka planda hazirlanir. Boylece pencere acilmadan
# once uzun dosya/texture uretimi yapilip kullaniciya siyah ekran gosterilmez.
ambience_audio = step_audio = pulse_audio = sting_audio = pickup_audio = None
knock_audio = whisper_audio = jumpscare_audio = None
audio_initialized = False
scare_overlay = None
jumpscare_timer = 0.0
jumpscare_cooldown = 0.0
ambient_event_timer = 18.0
scare_overlay = None
jumpscare_timer = 0.0
jumpscare_cooldown = 0.0
ambient_event_timer = 18.0


def initialize_audio() -> None:
    """Audio nesnelerini Ursina ana thread'inde guvenli sekilde yukle."""
    global ambience_audio, step_audio, pulse_audio, sting_audio, pickup_audio, audio_initialized
    global knock_audio, whisper_audio, jumpscare_audio
    if audio_initialized:
        return
    audio_initialized = True
    try:
        ambience_audio = Audio(os.path.join(SFX_DIR, "ambience.wav"), autoplay=True, loop=True, volume=.22)
        step_audio = Audio(os.path.join(SFX_DIR, "step.wav"), autoplay=False, volume=.35)
        pulse_audio = Audio(os.path.join(SFX_DIR, "pulse.wav"), autoplay=False, volume=.6)
        sting_audio = Audio(os.path.join(SFX_DIR, "sting.wav"), autoplay=False, volume=.8)
        pickup_audio = Audio(os.path.join(SFX_DIR, "pickup.wav"), autoplay=False, volume=.44)
        knock_audio = Audio(os.path.join(SFX_DIR, "knock.wav"), autoplay=False, volume=.18)
        whisper_audio = Audio(os.path.join(SFX_DIR, "whisper.wav"), autoplay=False, volume=.15)
        jumpscare_audio = Audio(os.path.join(SFX_DIR, "jumpscare.wav"), autoplay=False, volume=.62)
    except Exception:
        ambience_audio = step_audio = pulse_audio = sting_audio = pickup_audio = None
        knock_audio = whisper_audio = jumpscare_audio = None

# -----------------------------------------------------------------------------
# Aydinlatma ve kamera
# -----------------------------------------------------------------------------
ambient = PandaAmbientLight("echo-ambient")
ambient_np = scene.attachNewNode(ambient)
scene.setLight(ambient_np)

spot = PandaSpotlight("player-flashlight")
lens = PerspectiveLens()
lens.setFov(72)
spot.setLens(lens)
spot.setExponent(18)
spot.setAttenuation((1, 0, .028))
spot_np = camera.attachNewNode(spot)
spot_np.setPos(.2, -.12, .12)
spot_np.setHpr(0, -2, 0)

light_pool = []
for index in range(3):
    p = PandaPointLight(f"room-light-{index}")
    p.setAttenuation((1, 0, .045))
    node = scene.attachNewNode(p)
    light_pool.append((node, p))

fog = Fog("echo-fog")
fog.setExpDensity(.022)
scene.setFog(fog)

# -----------------------------------------------------------------------------
# Kalici oyuncu ve arayuz
# -----------------------------------------------------------------------------
player = Entity(position=(CELL / 2, 0, CELL / 2), rotation_y=0)
camera.parent = player
camera.position = (0, 1.68, 0)
camera.rotation = (0, 0, 0)

# El, fener ve bileklik: basit kutu yerine katmanli birinci sahis modeli.
hand = Entity(parent=camera, position=(-.34, -.34, .42), rotation=(0, 0, -12))
Entity(parent=hand, model="sphere", scale=(.16, .12, .22), position=(0, 0, .03), color=hx("#b88768"))
Entity(parent=hand, model="cube", scale=(.14, .16, .28), position=(0, -.015, -.12), color=hx("#29313a"))
torch = Entity(parent=camera, position=(.28, -.24, .55), rotation=(0, 0, -5))
Entity(parent=torch, model=CYLINDER_MODEL, scale=(.105, .38, .105), rotation_x=90, color=hx("#252a30"))
Entity(parent=torch, model=CYLINDER_MODEL, scale=(.15, .10, .15), position=(0, 0, .20), rotation_x=90, color=hx("#9ca5a7"))
Entity(parent=torch, model=CYLINDER_MODEL, scale=(.12, .07, .12), position=(0, 0, .255), rotation_x=90, color=hx("#d8d7c8"))
Entity(parent=torch, model="cube", scale=(.10, .035, .045), position=(0, -.08, .06), color=hx("#a9813e"))

# UI panelleri
hud_title = Text(parent=camera.ui, text=APP_NAME, position=(-.86, .465), scale=.78, color=hx("#d5c49e"))
hud_chapter = Text(parent=camera.ui, text="", position=(-.86, .425), scale=.68, color=hx("#aab4a7"))
hud_objective = Text(parent=camera.ui, text="", position=(-.86, .375), scale=.82, color=hx("#f0e4ca"))
hud_hint = Text(parent=camera.ui, text="", position=(-.86, .325), scale=.62, color=hx("#b8b1a2"))
hud_battery = Text(parent=camera.ui, text="FENER 100%", position=(.62, -.445), scale=.72, color=hx("#e7d19b"))
hud_status = Text(parent=camera.ui, text="", origin=(0, 0), position=(0, .43), scale=.82, color=hx("#e1b47c"))
hud_prompt = Text(parent=camera.ui, text="", origin=(0, 0), position=(0, -.105), scale=1.0, color=hx("#f7e7c4"))
hud_toast = Text(parent=camera.ui, text="", origin=(0, 0), position=(0, .30), scale=.95, color=hx("#f5dba7"))
hud_progress = Text(parent=camera.ui, text="", position=(.60, .465), scale=.74, color=hx("#d5c49e"))

# Ilk pencere gorunur gorunmez kullaniciya yukleme ekrani goster.
startup_panel = Entity(parent=camera.ui, model="quad", scale=(1.65, .52),
                        color=color.rgba32(5, 8, 10, 238), z=-1)
startup_title = Text(parent=camera.ui, text=APP_NAME, origin=(0, 0),
                     position=(0, .075), scale=1.45, color=hx("#e5d1a2"))
startup_message = Text(parent=camera.ui, text="Ilk bolumun dosyalari hazirlaniyor...",
                       origin=(0, 0), position=(0, -.075), scale=.82,
                       color=hx("#bdc4b5"))

stamina_back = Entity(parent=camera.ui, model="quad", position=(0, -.405), scale=(.27, .009), color=hx("#2a2927"))
stamina_bar = Entity(parent=camera.ui, model="quad", position=(0, -.405), scale=(.27, .006), color=hx("#c6a35d"))
map_back = Entity(parent=camera.ui, model="quad", position=(.67, .17), scale=(.34, .32), color=color.rgba32(8, 12, 13, 220), enabled=False)
map_text = Text(parent=camera.ui, text="", position=(.51, .28), scale=.56, color=hx("#c9d4b4"), enabled=False)

fade = Entity(parent=camera.ui, model="quad", scale=2, color=color.black, z=-2)
fade.alpha = 0
card_back = Entity(parent=camera.ui, model="quad", scale=(1.25, .50), color=color.rgba32(6, 8, 9, 225), z=-1, enabled=False)
card_title = Text(parent=camera.ui, text="", origin=(0, 0), position=(0, .11), scale=1.55, color=hx("#e9d6aa"), enabled=False)
card_body = Text(parent=camera.ui, text="", origin=(0, 0), position=(0, -.015), scale=.85, color=hx("#d2d0c6"), enabled=False)
card_sub = Text(parent=camera.ui, text="", origin=(0, 0), position=(0, -.16), scale=.66, color=hx("#a7b7a7"), enabled=False)
puzzle_back = Entity(parent=camera.ui, model="quad", scale=(1.22, .76), color=color.rgba32(7, 11, 14, 246), z=-1, enabled=False)
puzzle_title = Text(parent=camera.ui, text="", origin=(0, 0), position=(0, .27), scale=1.28, color=hx("#e2c88e"), enabled=False)
puzzle_clue = Text(parent=camera.ui, text="", origin=(0, 0), position=(0, .09), scale=.78, color=hx("#d9ddd2"), enabled=False)
puzzle_progress = Text(parent=camera.ui, text="", origin=(0, 0), position=(0, -.08), scale=1.12, color=hx("#e5d1a2"), enabled=False)
puzzle_help = Text(parent=camera.ui, text="1-4 tuslari: giris  |  ENTER: onayla  |  BACKSPACE: geri", origin=(0, 0), position=(0, -.27), scale=.62, color=hx("#a9b4b0"), enabled=False)

# -----------------------------------------------------------------------------
# Global oyun durumu
# -----------------------------------------------------------------------------
chapter_index = 0
world_root = None
wall_colliders: list[tuple[float, float, float, float]] = []
furniture_colliders: list[tuple[float, float, float, float]] = []
# Her odanin kendi sahne kok grubu: uzak odalar tek hamlede render disi kalir.
room_nodes: list[Entity] = []
room_active: set[int] = set()
# Fizik/LOS kontrolleri tum haritayi taramak yerine yakin oda kovalarina bakar.
wall_colliders_by_room: list[list[tuple[float, float, float, float]]] = []
furniture_colliders_by_room: list[list[tuple[float, float, float, float]]] = []
room_stream_last = -999.0
lamp_refresh_timer = 0.0
selected_lamps: list[tuple[float, float, float]] = []
room_graph: list[list[int]] = []
door_map: dict[tuple[int, int], tuple[float, float]] = {}
room_lights: list[tuple[float, float, float]] = []
pickups: list[dict] = []
chapter_items_collected = 0
battery_charge = 100.0
flashlight_on = False
crouching = False
stamina = 100.0
exhausted = False
frozen = True
chapter_intro = True
chapter_clock = 0.0
spawn_clock = 0.0
enemy = None
noise_level = 0.0
near_action = None
prompt_cooldown = 0.0
toast_timer = 0.0
camera_pitch = 0.0
walk_phase = 0.0
step_counter = 0
last_player_room = 0
enemy_state = "dormant"
enemy_timer = 0.0
enemy_lost = 0.0
enemy_last_seen = (CELL / 2, CELL / 2)
enemy_patrol_room = 1
caught_lock = False
show_map = False
ending = False
console_pos = (0.0, 0.0)
exit_pos = (0.0, 0.0)
extraction_door = None
puzzle_active = False
puzzle_solved = False
puzzle_entry: list[int] = []
puzzle_attempts = 0
escape_active = False
escape_timer = 0.0
PUZZLES = [
    {"title": "MALIKANE / ANA SIGORTA DEVRESI", "hint": "Not: Yesil = 2, Sari = 4, Kirmizi = 1, Mavi = 3. Sirayi duvar notundaki renklere gore gir.", "sequence": [2, 4, 1, 3]},
    {"title": "HASTANE / HASTA ARSIVI TERMINALI", "hint": "Dosya kenarindaki oda kaydi: 3. kat, 1. koridor, 4. oda, 2. yatak. Dizi bu sirada.", "sequence": [3, 1, 4, 2]},
    {"title": "ORMAN / SINYAL FREKANSI", "hint": "Telsiz gunlugu: Bati, Dogu, Kuzey, Guney. Panelde Bati=4, Dogu=2, Kuzey=1, Guney=3.", "sequence": [4, 2, 1, 3]},
    {"title": "SIGINAK / BASINC HATTI", "hint": "Basinc notu: once 3 numarali hat, sonra 1, ardindan 4 ve son olarak 2.", "sequence": [3, 1, 4, 2]},
    {"title": "SAAT KULESI / SON MEKANIZMA", "hint": "Saat ustasinin kaydi: Kisa, Uzun, Kisa, Cift, Uzun. Kadran tus eslemesi 2, 1, 3, 4, 2.", "sequence": [2, 1, 3, 4, 2]},
]
startup_assets_ready = threading.Event()
startup_queued = False
startup_started = False

def show_toast(message: str, duration: float = 2.8) -> None:
    global toast_timer
    hud_toast.text = message
    toast_timer = duration


def trigger_jumpscare():
    """A brief, non-graphic face flash; it does not lock controls or cause damage."""
    global jumpscare_timer, jumpscare_cooldown
    if scare_overlay is None or jumpscare_cooldown > 0:
        return
    jumpscare_timer = .42
    jumpscare_cooldown = 38.0 + chapter_index * 5.0
    scare_overlay.enabled = True
    scare_overlay.scale = (1.95, 1.95)
    scare_overlay.rotation_z = random.uniform(-2.5, 2.5)
    scare_overlay.color = color.rgba32(255, 255, 255, 245)
    if jumpscare_audio:
        jumpscare_audio.volume = .58
        jumpscare_audio.play()


def set_frozen(value: bool) -> None:
    global frozen
    frozen = value
    mouse.locked = not value


def add_world(entity):
    entity.parent = world_root
    return entity


def palette_color(value):
    """Convert 0-255 RGB tuples to Ursina Color objects."""
    if isinstance(value, tuple) and len(value) == 3 and max(value) > 1:
        return color.rgb32(int(value[0]), int(value[1]), int(value[2]))
    return value


def static_entity(*args, **kwargs):
    """Render static geometry without an update callback every frame."""
    kwargs.setdefault("add_to_scene_entities", False)
    return Entity(*args, **kwargs)


def make_ring(x: float, y: float, z: float, radius: float, tint, parent=None, rotation=(0, 0, 0), thickness=.075):
    """Create a ring from small spheres so no external torus model is required."""
    group = static_entity(parent=parent if parent is not None else room_parent(x, z), position=(x, y, z), rotation=rotation)
    for index in range(12):
        angle = math.tau * index / 12
        static_entity(parent=group, model="sphere",
               position=(math.cos(angle) * radius, 0, math.sin(angle) * radius),
               scale=(thickness, thickness, thickness), color=palette_color(tint))
    return group


def room_center(room: int) -> tuple[float, float]:
    return ((room % GRID + .5) * CELL, (room // GRID + .5) * CELL)


def room_at(x: float, z: float) -> int:
    ix = max(0, min(GRID - 1, int(x // CELL)))
    iz = max(0, min(GRID - 1, int(z // CELL)))
    return iz * GRID + ix


def room_key(a: int, b: int) -> tuple[int, int]:
    return (a, b) if a < b else (b, a)


def room_parent(x: float, z: float):
    """Return the streaming chunk that owns this world-space position."""
    if room_nodes:
        return room_nodes[room_at(x, z)]
    return world_root


def nearby_room_ids(x: float, z: float, reach: int = 1) -> list[int]:
    """Bir konumun etrafindaki oda indexleri (duvar sinirlari icin tamponlu)."""
    center = room_at(x, z)
    cx, cz = center % GRID, center // GRID
    result = []
    for rz in range(max(0, cz - reach), min(GRID, cz + reach + 1)):
        for rx in range(max(0, cx - reach), min(GRID, cx + reach + 1)):
            result.append(rz * GRID + rx)
    return result


def add_collider(x: float, z: float, width: float, depth: float, target=None) -> None:
    collider = (x, z, width / 2, depth / 2)
    wall_colliders.append(collider)
    if wall_colliders_by_room:
        wall_colliders_by_room[room_at(x, z)].append(collider)


def can_stand(x: float, z: float, radius: float = PLAYER_RADIUS) -> bool:
    if x < .55 or z < .55 or x > WORLD - .55 or z > WORLD - .55:
        return False
    room_ids = nearby_room_ids(x, z, 1)
    for room_id in room_ids:
        for cx, cz, hw, hd in wall_colliders_by_room[room_id]:
            if abs(x - cx) < hw + radius and abs(z - cz) < hd + radius:
                return False
        for cx, cz, hw, hd in furniture_colliders_by_room[room_id]:
            if abs(x - cx) < hw + radius and abs(z - cz) < hd + radius:
                return False
    return True


def add_box(x: float, y: float, z: float, sx: float, sy: float, sz: float,
            tint, texture=None, collision=False, parent=None, rotation_y=0):
    e = static_entity(parent=parent if parent is not None else room_parent(x, z), model="cube", position=(x, y, z),
               scale=(sx, sy, sz), color=palette_color(tint), texture=texture, rotation_y=rotation_y)
    if collision:
        collider = (x, z, sx / 2, sz / 2)
        furniture_colliders.append(collider)
        if furniture_colliders_by_room:
            furniture_colliders_by_room[room_at(x, z)].append(collider)
    return e


def add_cylinder(x: float, y: float, z: float, scale, tint, rotation=(0, 0, 0), parent=None):
    return static_entity(parent=parent if parent is not None else room_parent(x, z), model=CYLINDER_MODEL, position=(x, y, z),
                  scale=scale, color=palette_color(tint), rotation=rotation)


def make_wall_segment(axis: str, fixed: float, start: float, end: float, wall_tex, tint, metal_tex=None, wall_alt_tex=None):
    if end - start <= .12:
        return
    mid = (start + end) / 2
    length = end - start
    if axis == "x":
        pos = (mid, WALL_H / 2, fixed)
        scale = (length, WALL_H, WALL_T)
        cx, cz, w, d = mid, fixed, length, WALL_T
    else:
        pos = (fixed, WALL_H / 2, mid)
        scale = (WALL_T, WALL_H, length)
        cx, cz, w, d = fixed, mid, WALL_T, length
    variation = int(abs(fixed * 17 + mid * 29 + chapter_index * 11)) % 5
    surface_tex = wall_alt_tex if wall_alt_tex is not None and variation in (0, 3) else wall_tex
    static_entity(parent=room_parent(cx, cz), model="cube", position=pos, scale=scale,
           texture=surface_tex, texture_scale=(max(1, length / 2.8), WALL_H / 2.8),
           color=color.rgb32(178, 165, 145))
    add_collider(cx, cz, w, d)
    # Duvar diplerinde ahsap/metal supurgelik.
    if axis == "x":
        add_box(mid, .15, fixed, length, .30, WALL_T + .025, tint, metal_tex)
    else:
        add_box(fixed, .15, mid, WALL_T + .025, .30, length, tint, metal_tex)


def make_maze() -> None:
    global room_graph, door_map
    total = GRID * GRID
    room_graph = [[] for _ in range(total)]
    door_map = {}
    visited = {0}
    stack = [0]
    rng = random.Random(900 + chapter_index * 73)
    while stack:
        current = stack[-1]
        x, z = current % GRID, current // GRID
        candidates = []
        if x > 0 and current - 1 not in visited: candidates.append(current - 1)
        if x < GRID - 1 and current + 1 not in visited: candidates.append(current + 1)
        if z > 0 and current - GRID not in visited: candidates.append(current - GRID)
        if z < GRID - 1 and current + GRID not in visited: candidates.append(current + GRID)
        if not candidates:
            stack.pop()
            continue
        nxt = rng.choice(candidates)
        visited.add(nxt)
        room_graph[current].append(nxt)
        room_graph[nxt].append(current)
        stack.append(nxt)
    # Bir miktar yan yol: oyuncu ayni koridora mahkum kalmasin.
    for z in range(GRID):
        for x in range(GRID):
            a = z * GRID + x
            for b in ([a + 1] if x < GRID - 1 else []) + ([a + GRID] if z < GRID - 1 else []):
                if b not in room_graph[a] and rng.random() < .16:
                    room_graph[a].append(b)
                    room_graph[b].append(a)
    for a in range(total):
        for b in room_graph[a]:
            if a < b:
                ax, az = room_center(a)
                bx, bz = room_center(b)
                if abs(ax - bx) > 1:
                    door_map[(a, b)] = ((ax + bx) / 2, az + rng.uniform(-.45, .45))
                else:
                    door_map[(a, b)] = (ax + rng.uniform(-.45, .45), (az + bz) / 2)


def graph_distances(start: int) -> list[int]:
    dist = [-1] * (GRID * GRID)
    dist[start] = 0
    q = deque([start])
    while q:
        a = q.popleft()
        for b in room_graph[a]:
            if dist[b] == -1:
                dist[b] = dist[a] + 1
                q.append(b)
    return dist


def graph_next_step(start: int, goal: int) -> int:
    if start == goal:
        return goal
    previous = {start: None}
    q = deque([start])
    while q:
        a = q.popleft()
        if a == goal:
            break
        for b in room_graph[a]:
            if b not in previous:
                previous[b] = a
                q.append(b)
    if goal not in previous:
        return start
    cur = goal
    while previous[cur] != start:
        cur = previous[cur]
        if cur is None:
            return start
    return cur


def path_waypoint(x: float, z: float, tx: float, tz: float) -> tuple[float, float]:
    a, b = room_at(x, z), room_at(tx, tz)
    if a == b:
        return tx, tz
    nxt = graph_next_step(a, b)
    return door_map.get(room_key(a, nxt), room_center(nxt))

# -----------------------------------------------------------------------------
# Bolum dekorasyonu: farkli temali, cok parcali modeller
# -----------------------------------------------------------------------------
def build_bookshelf(cx: float, cz: float, wall_tex, trim):
    add_box(cx, 1.35, cz, 1.6, 2.7, .48, hx("#34271e"), wall_tex, True)
    for y in (.55, 1.15, 1.75, 2.35):
        add_box(cx, y, cz - .27, 1.58, .08, .07, trim)
        for k in range(4):
            shade = random.choice((hx("#713a31"), hx("#344c55"), hx("#78613b"), hx("#4d5c42")))
            add_box(cx - .57 + k * .37, y + .20, cz - .28, .22, .38, .12, shade, rotation_y=random.uniform(-5, 5))


def build_bed(cx: float, cz: float, trim):
    wood = hx("#39434a")
    add_box(cx, .38, cz, 1.9, .32, 3.0, wood, collision=True)
    add_box(cx, .58, cz, 1.85, .16, 2.9, hx("#bac5bd"))
    add_box(cx, .78, cz - 1.08, 1.72, .28, .62, hx("#d3d7cd"))
    add_box(cx, 1.12, cz - 1.36, 1.95, 1.35, .12, trim)
    for sx in (-.78, .78):
        add_box(cx + sx, .18, cz - 1.25, .10, .36, .12, wood)
        add_box(cx + sx, .18, cz + 1.25, .10, .36, .12, wood)


def build_console(cx: float, cz: float, trim, glow):
    add_box(cx, .62, cz, 1.8, 1.2, .72, hx("#202a2c"), collision=True)
    add_box(cx, 1.29, cz - .24, 1.7, .10, .46, trim)
    for k in range(3):
        add_box(cx - .55 + k * .55, 1.35, cz - .24, .32, .22, .035, glow)
        add_cylinder(cx - .55 + k * .55, .95, cz - .40, (.12, .08, .12), trim)


def build_pipe(cx: float, cz: float, trim):
    for sx in (-.62, .62):
        add_cylinder(cx + sx, 1.8, cz, (.14, 3.6, .14), trim)
        add_cylinder(cx + sx, .35, cz, (.26, .18, .26), hx("#313b42"))
    add_cylinder(cx, 2.9, cz, (.12, 1.35, .12), trim, rotation=(0, 0, 90))
    for sx in (-.5, 0, .5):
        add_cylinder(cx + sx, 2.9, cz, (.04, .26, .04), hx("#1b2228"))


def build_clockwork(cx: float, cz: float, trim, glow):
    add_box(cx, 1.25, cz, 1.8, 2.5, .3, hx("#392b3d"), collision=True)
    for y, r in ((.78, .45), (1.7, .34)):
        gear = make_ring(cx, y, cz - .23, r, trim, rotation=(90, 0, 0), thickness=.055)
        for k in range(8):
            angle = k * 45
            a = math.radians(angle)
            add_box(cx + math.sin(a) * r, y + math.cos(a) * r, cz - .25, .10, .18, .08, glow, rotation_y=angle)
    add_cylinder(cx, 1.25, cz - .33, (.08, .82, .08), trim, rotation=(0, 0, 90))


def decorate_rooms(style: dict, wall_tex, metal_tex):
    rng = random.Random(7000 + chapter_index)
    for room in range(1, GRID * GRID - 1):
        if rng.random() > .24:
            continue
        cx, cz = room_center(room)
        side = rng.choice((0, 1, 2, 3))
        ox = -3.45 if side == 0 else (3.45 if side == 1 else rng.uniform(-1.8, 1.8))
        oz = -3.45 if side == 2 else (3.45 if side == 3 else rng.uniform(-1.8, 1.8))
        px, pz = cx + ox, cz + oz
        mode = style["room_style"]
        if mode == "wood":
            if rng.random() < .55: build_bookshelf(px, pz, wall_tex, hx("#a47b48"))
            else:
                add_box(px, .52, pz, 1.4, 1.0, .85, hx("#493326"), wall_tex, True)
                add_box(px, 1.06, pz, 1.5, .10, .95, hx("#8b6240"))
                add_cylinder(px + .42, 1.2, pz, (.12, .24, .12), hx("#d1a253"))
        elif mode == "tile":
            build_bed(px, pz, hx("#7a9e9c")) if rng.random() < .5 else build_console(px, pz, hx("#a8b6ac"), hx("#68c7b6"))
        elif mode == "bark":
            build_console(px, pz, hx("#92a66a"), hx("#b8d985"))
            add_cylinder(px + 1.1, 1.8, pz, (.24, 3.4, .24), hx("#493b2b"))
        elif mode == "concrete":
            build_pipe(px, pz, hx("#a5afb5"))
            add_box(px + 1.1, .55, pz, 1.2, 1.1, .8, hx("#313942"), metal_tex, True)
        else:
            build_clockwork(px, pz, hx("#b99b62"), hx("#e6c777"))


def decorate_story_details(style: dict, wall_alt_tex, metal_tex):
    """Chapter-specific environmental storytelling props and readable edge clutter."""
    rng = random.Random(8800 + chapter_index * 131)
    mode = style["room_style"]
    for room in range(2, GRID * GRID - 2):
        if rng.random() > .62:
            continue
        cx, cz = room_center(room)
        side = rng.choice(("west", "east", "north", "south"))
        zoff = rng.uniform(-2.4, 2.4)
        xoff = rng.uniform(-2.4, 2.4)
        if side == "west":
            px, pz = cx - 5.72, cz + zoff
            frame_scale = (.10, 1.25, 1.05)
            inner = (px + .07, 1.95, pz)
        elif side == "east":
            px, pz = cx + 5.72, cz + zoff
            frame_scale = (.10, 1.25, 1.05)
            inner = (px - .07, 1.95, pz)
        elif side == "north":
            px, pz = cx + xoff, cz - 5.72
            frame_scale = (1.25, 1.25, .10)
            inner = (px, 1.95, pz + .07)
        else:
            px, pz = cx + xoff, cz + 5.72
            frame_scale = (1.25, 1.25, .10)
            inner = (px, 1.95, pz - .07)

        add_box(px, 1.95, pz, *frame_scale, style["trim"], metal_tex)
        ix, iy, iz = inner
        panel_scale = (.055, .94, .76) if side in ("west", "east") else (.76, .94, .055)
        panel_tint = {
            "wood": hx("#241b18"), "tile": hx("#182624"),
            "bark": hx("#1c2419"), "concrete": hx("#181d24"),
            "clock": hx("#211b28")
        }[mode]
        add_box(ix, iy, iz, *panel_scale, panel_tint, wall_alt_tex)

        if mode == "wood":  # Faded family portrait / torn wallpaper.
            accent = hx("#a78a62")
            for dy in (-.24, 0, .24):
                if side in ("west", "east"):
                    add_box(ix, iy + dy, iz, .035, .025, .48, accent)
                else:
                    add_box(ix, iy + dy, iz, .48, .025, .035, accent)
            add_box(ix, iy, iz, .025, .62, .025, hx("#514038"))
        elif mode == "tile":  # Room indicator and broken call button.
            for dy, tint in ((.27, hx("#4e8d7e")), (.02, hx("#a1a891")), (-.23, hx("#5d6a64"))):
                if side in ("west", "east"):
                    add_box(ix, iy + dy, iz, .025, .045, .38, tint)
                else:
                    add_box(ix, iy + dy, iz, .38, .045, .025, tint)
            add_cylinder(ix, iy - .40, iz, (.09, .08, .09), hx("#bd705b"))
        elif mode == "bark":  # Ranger station map / signal bars.
            for k in range(4):
                offset = -.27 + k * .18
                if side in ("west", "east"):
                    add_box(ix, iy + offset, iz, .03, .035, .45, hx("#788b56"))
                else:
                    add_box(ix, iy + offset, iz, .45, .035, .03, hx("#788b56"))
            add_cylinder(ix, iy, iz, (.12, .08, .12), style["glow"])
        elif mode == "concrete":  # Pressure gauge and emergency stripes.
            add_cylinder(ix, iy, iz, (.24, .12, .24), hx("#87919a"),
                         rotation=(90, 0, 0) if side in ("west", "east") else (0, 0, 90))
            for offset in (-.31, .31):
                if side in ("west", "east"):
                    add_box(ix, iy + offset, iz, .035, .035, .55, hx("#a16a41"))
                else:
                    add_box(ix, iy + offset, iz, .55, .035, .035, hx("#a16a41"))
        else:  # Clockmaker's dial.
            make_ring(ix, iy, iz, .30, hx("#b2945e"), thickness=.035,
                      rotation=(90, 0, 0) if side in ("west", "east") else (0, 0, 90))
            add_cylinder(ix, iy, iz, (.055, .48, .055), hx("#d0b477"),
                         rotation=(0, 0, 90))

        # Small debris sits along room edges; the walkable centre stays clear.
        if rng.random() < .48:
            for _ in range(rng.randrange(2, 5)):
                dx = rng.choice((-4.7, 4.7))
                dz = rng.uniform(-4.2, 4.2)
                add_box(cx + dx, .10, cz + dz, rng.uniform(.28, .8), .16,
                        rng.uniform(.14, .34), hx("#3b342d"), metal_tex,
                        rotation_y=rng.uniform(-35, 35))


def build_lamps(style: dict):
    global room_lights
    room_lights = []
    rng = random.Random(3210 + chapter_index)
    for room in range(GRID * GRID):
        if rng.random() < .42:
            cx, cz = room_center(room)
            room_lights.append((cx, cz, rng.random() * 10))
            static_entity(parent=room_nodes[room], model=CYLINDER_MODEL, position=(cx, WALL_H - .15, cz),
                   scale=(.72, .10, .72), color=hx("#262a2c"))
            static_entity(parent=room_nodes[room], model="sphere", position=(cx, WALL_H - .38, cz),
                   scale=(.28, .12, .28), color=palette_color(style["glow"]))


def build_exit_gate(style: dict):
    """Uzak odada bolum terminali, baslangic odasinda cikis kapisi kur."""
    global extraction_door
    # Kontrol terminali haritanin son odasinda.
    cx, cz = room_center(GRID * GRID - 1)
    terminal_z = cz - 2.8
    add_box(cx, 1.35, terminal_z, 2.3, 2.6, .42, hx("#20282d"), collision=False)
    add_box(cx, 1.52, terminal_z - .24, 1.95, .92, .06, hx("#111b20"))
    add_box(cx, 2.15, terminal_z - .28, 1.45, .08, .035, style["glow"])
    for xoff in (-.65, 0, .65):
        add_box(cx + xoff, .86, terminal_z - .28, .13, .24, .08, style["trim"])
        add_cylinder(cx + xoff, .70, terminal_z - .34, (.11, .08, .11), style["glow"])

    # Ana cikis oyuncunun basladigi oda tarafinda bulunur. Puzzle sonrasi
    # tum haritayi geri kosmak zorunda kalir; kovalamaca bu rotayi kullanir.
    sx, sz = room_center(0)
    door_z = 1.45
    for side in (-1, 1):
        add_box(sx + side * 1.45, 1.92, door_z, .24, 3.84, .34, style["trim"])
        add_box(sx + side * 1.45, 1.92, door_z - .20, .08, 3.52, .08, style["glow"])
    add_box(sx, 3.78, door_z, 3.10, .24, .34, style["trim"])
    extraction_door = add_box(sx, 1.82, door_z + .10, 2.55, 3.42, .12, hx("#101619"))
    add_box(sx, 1.72, door_z + .02, 2.35, .08, .16, style["glow"])
    # Door threshold. Keep it non-colliding so the final interaction is reliable.
    add_box(sx, .08, door_z + 1.25, 2.45, .16, .72, style["trim"])
    return (cx, terminal_z - .75), (sx, door_z + 1.35)


def update_room_streaming(force: bool = False) -> None:
    """Keep the player's nearby rooms, view cone and monster's area enabled."""
    global room_stream_last, room_active
    if not room_nodes:
        return
    if not force and chapter_clock - room_stream_last < .15:
        return
    room_stream_last = chapter_clock

    px, pz = player.x, player.z
    active = set(nearby_room_ids(px, pz, 1))
    yaw = math.radians(player.rotation_y)
    fx, fz = math.sin(yaw), math.cos(yaw)
    view_range = CELL * 3.25
    for room_id in range(GRID * GRID):
        cx, cz = room_center(room_id)
        dx, dz = cx - px, cz - pz
        dist_sq = dx * dx + dz * dz
        if dist_sq > view_range * view_range or dist_sq < .01:
            continue
        dot = (dx * fx + dz * fz) / math.sqrt(dist_sq)
        if dot > .12:
            active.add(room_id)

    if enemy is not None and enemy.root.enabled:
        active.update(nearby_room_ids(enemy.root.x, enemy.root.z, 1))
    active.add(room_at(px, pz))

    for room_id, node in enumerate(room_nodes):
        node.enabled = room_id in active
    room_active = active

def build_world():
    global world_root, wall_colliders, furniture_colliders, room_lights, console_pos, exit_pos
    global room_nodes, room_active, wall_colliders_by_room, furniture_colliders_by_room
    global room_stream_last, selected_lamps, lamp_refresh_timer
    if world_root is not None:
        destroy(world_root)
    world_root = Entity(name="chapter-world")
    wall_colliders = []
    furniture_colliders = []
    room_active = set()
    room_stream_last = -999.0
    selected_lamps = []
    lamp_refresh_timer = 0.0
    style = CHAPTERS[chapter_index]
    wall_path, floor_path, metal_path = build_chapter_textures(chapter_index + 1, style)
    wall_alt_path, ceiling_path = build_chapter_detail_textures(chapter_index + 1, style)
    # Ursina load_texture searches relative to asset_folder; an absolute
    # filename silently returned None on some installations. Specify the
    # texture directory explicitly so all generated PNGs are actually loaded.
    texture_folder = Path(TEX_DIR)
    wall_tex = load_texture(os.path.basename(wall_path), folder=texture_folder)
    floor_tex = load_texture(os.path.basename(floor_path), folder=texture_folder)
    metal_tex = load_texture(os.path.basename(metal_path), folder=texture_folder)
    wall_alt_tex = load_texture(os.path.basename(wall_alt_path), folder=texture_folder)
    ceiling_tex = load_texture(os.path.basename(ceiling_path), folder=texture_folder)
    if not all((wall_tex, floor_tex, metal_tex, wall_alt_tex, ceiling_tex)):
        missing = [name for name, tex in (
            ("wall", wall_tex), ("wall_alt", wall_alt_tex), ("floor", floor_tex),
            ("metal", metal_tex), ("ceiling", ceiling_tex)
        ) if tex is None]
        raise RuntimeError("Doku dosyalari yuklenemedi: " + ", ".join(missing))
    make_maze()
    # Chunk'lar once gorunur kurulur. Ilk stream turu oyuncu konumuna gore
    # guvenli alanlari acik birakir; kapali parent nedeniyle bos/beyaz sahne olusmaz.
    # Normal Entity dugumleri Panda/Ursina sahne agacinda acikca kayitli kalir.
    # Oda meshleri yine statik Entity olarak tutulur; chunk anahtari yalnizca gorunurlugu yonetir.
    room_nodes = [
        Entity(parent=world_root, name=f"room_chunk_{room}", enabled=True)
        for room in range(GRID * GRID)
    ]
    wall_colliders_by_room = [[] for _ in range(GRID * GRID)]
    furniture_colliders_by_room = [[] for _ in range(GRID * GRID)]

    # Zemin ve tavan: her oda ayri chunk icinde tutulur.
    for room in range(GRID * GRID):
        cx, cz = room_center(room)
        # A solid slab guarantees a visible, dark floor even if a graphics
        # backend fails to sample the generated PNG texture.
        static_entity(parent=room_nodes[room], model="cube", position=(cx, -.16, cz), scale=(CELL, .32, CELL),
               texture=floor_tex, texture_scale=(3.8, 3.8), color=color.rgb32(165, 153, 137))
        static_entity(parent=room_nodes[room], model="plane", position=(cx, WALL_H, cz), rotation_x=180,
               scale=(CELL, 1, CELL), texture=ceiling_tex, texture_scale=(2.6, 2.6),
               color=color.rgb32(115, 107, 95), double_sided=True)
        # Tavan kirişi ve koselerde kolonlar.
        for sx in (-5.45, 5.45):
            add_box(cx + sx, WALL_H - .20, cz, .16, .34, CELL, style["trim"], metal_tex)

    # Dikey duvarlar. Bagli odalar arasinda oyuncu/dusman icin aciklik birakilir.
    for gx in range(GRID + 1):
        for rz in range(GRID):
            fixed = gx * CELL
            start, end = rz * CELL, (rz + 1) * CELL
            a = rz * GRID + gx - 1
            b = rz * GRID + gx
            linked = 0 < gx < GRID and b in room_graph[a]
            if linked:
                gap = door_map[room_key(a, b)][1]
                make_wall_segment("z", fixed, start, gap - DOOR_W / 2, wall_tex, style["trim"], metal_tex, wall_alt_tex)
                make_wall_segment("z", fixed, gap + DOOR_W / 2, end, wall_tex, style["trim"], metal_tex, wall_alt_tex)
                # Kapinin iki yaninda dekoratif kolon ve ust lento.
                for dz in (-DOOR_W / 2, DOOR_W / 2):
                    add_box(fixed, WALL_H / 2, gap + dz, .48, WALL_H, .52, style["trim"], metal_tex)
                add_box(fixed, WALL_H - .16, gap, .52, .32, DOOR_W, style["trim"], metal_tex)
            else:
                make_wall_segment("z", fixed, start, end, wall_tex, style["trim"], metal_tex, wall_alt_tex)

    # Yatay duvarlar.
    for gz in range(GRID + 1):
        for rx in range(GRID):
            fixed = gz * CELL
            start, end = rx * CELL, (rx + 1) * CELL
            a = (gz - 1) * GRID + rx
            b = gz * GRID + rx
            linked = 0 < gz < GRID and b in room_graph[a]
            if linked:
                gap = door_map[room_key(a, b)][0]
                make_wall_segment("x", fixed, start, gap - DOOR_W / 2, wall_tex, style["trim"], metal_tex, wall_alt_tex)
                make_wall_segment("x", fixed, gap + DOOR_W / 2, end, wall_tex, style["trim"], metal_tex, wall_alt_tex)
                for dx in (-DOOR_W / 2, DOOR_W / 2):
                    add_box(gap + dx, WALL_H / 2, fixed, .52, WALL_H, .48, style["trim"], metal_tex)
                add_box(gap, WALL_H - .16, fixed, DOOR_W, .32, .52, style["trim"], metal_tex)
            elif gz == 0 and rx == 0:
                # Baslangic odasindaki cikis kapisi icin dis duvarda aciklik.
                gap = CELL / 2
                make_wall_segment("x", fixed, start, gap - DOOR_W / 2, wall_tex, style["trim"], metal_tex, wall_alt_tex)
                make_wall_segment("x", fixed, gap + DOOR_W / 2, end, wall_tex, style["trim"], metal_tex, wall_alt_tex)
            else:
                make_wall_segment("x", fixed, start, end, wall_tex, style["trim"], metal_tex, wall_alt_tex)

    decorate_rooms(style, wall_tex, metal_tex)
    decorate_story_details(style, wall_alt_tex, metal_tex)
    build_lamps(style)
    console_pos, exit_pos = build_exit_gate(style)
    return console_pos

# -----------------------------------------------------------------------------
# Koleksiyon nesneleri
# -----------------------------------------------------------------------------
def build_pickup_model(kind: str, pos: tuple[float, float], style: dict):
    x, z = pos
    room_id = room_at(x, z)
    chunk = room_nodes[room_id]
    root = static_entity(parent=chunk, position=(x, .22, z))
    tint = style["glow"]
    dark_metal = hx("#20272a")
    worn_metal = hx("#70736b")
    if kind == "sigorta":
        # Glass fuse with worn brass end caps and a visible filament.
        static_entity(parent=root, model=CYLINDER_MODEL, scale=(.13, .42, .13), color=hx("#927343"))
        static_entity(parent=root, model=CYLINDER_MODEL, scale=(.17, .09, .17), y=-.22, color=worn_metal)
        static_entity(parent=root, model=CYLINDER_MODEL, scale=(.17, .09, .17), y=.22, color=worn_metal)
        static_entity(parent=root, model="cube", scale=(.035, .26, .035), y=.01, color=hx("#d5b77a"))
    elif kind == "disk":
        # Old black archive platter with recessed centre and label window.
        static_entity(parent=root, model=CYLINDER_MODEL, scale=(.43, .075, .43), color=dark_metal)
        static_entity(parent=root, model=CYLINDER_MODEL, scale=(.24, .082, .24), color=hx("#87908c"))
        static_entity(parent=root, model=CYLINDER_MODEL, scale=(.11, .09, .11), color=hx("#262d31"))
        static_entity(parent=root, model="cube", scale=(.18, .016, .065), position=(.17, .048, -.04), color=hx("#a9a18a"))
        static_entity(parent=root, model="sphere", scale=.035, y=.055, color=palette_color(tint), unlit=True)
    elif kind == "role":
        # Field radio relay with a short aerial and three indicators.
        static_entity(parent=root, model="cube", scale=(.32, .40, .20), color=hx("#303d32"))
        static_entity(parent=root, model="cube", scale=(.24, .08, .04), y=.10, z=-.12, color=hx("#7d806a"))
        static_entity(parent=root, model="cube", scale=(.045, .28, .045), y=.31, x=.10, color=worn_metal)
        for k in range(3):
            static_entity(parent=root, model="sphere", scale=.035,
                          position=(-.075 + k*.075, .12, -.13),
                          color=palette_color(tint) if k == 1 else hx("#5c6055"))
        static_entity(parent=root, model="cube", scale=(.08, .08, .08), y=-.22, z=.04, color=dark_metal)
    elif kind == "vana":
        # Heavy valve assembly with four spokes.
        static_entity(parent=root, model=CYLINDER_MODEL, scale=(.15, .32, .15), color=worn_metal)
        make_ring(0, .12, 0, .28, worn_metal, parent=root, thickness=.045)
        for angle in range(0, 360, 90):
            a = math.radians(angle)
            static_entity(parent=root, model="cube", scale=(.065, .34, .07),
                          position=(math.sin(a)*.22, .12, math.cos(a)*.22),
                          rotation_y=angle, color=hx("#89918e"))
        static_entity(parent=root, model=CYLINDER_MODEL, scale=(.26, .07, .26), y=-.17, color=dark_metal)
    else:
        # Brass gear / clock pinion with six teeth.
        make_ring(0, 0, 0, .25, hx("#a98b54"), parent=root, thickness=.055)
        static_entity(parent=root, model=CYLINDER_MODEL, scale=(.13, .12, .13), color=dark_metal)
        for angle in range(0, 360, 60):
            a = math.radians(angle)
            static_entity(parent=root, model="cube", scale=(.09, .12, .07),
                          position=(math.sin(a)*.27, 0, math.cos(a)*.27),
                          rotation_y=angle, color=hx("#b69b65"))
        static_entity(parent=root, model="cube", scale=(.045, .30, .045), rotation_z=45, color=hx("#d0b477"))

    ring = make_ring(x, .025, z, .22, tint, parent=chunk, thickness=.035)
    glow = static_entity(parent=chunk, model="sphere", position=(x, .22, z), scale=.42,
                         color=color.rgba32(tint[0], tint[1], tint[2], 14), unlit=True)
    return {"kind": kind, "root": root, "ring": ring, "glow": glow,
            "x": x, "z": z, "room": room_id, "phase": random.random() * 6}

def spawn_chapter_items(style: dict):
    global pickups
    pickups = []
    required = style["required"]
    dist = graph_distances(0)
    candidates = [r for r in range(1, GRID * GRID - 1)]
    # Dagilim: hedefler haritanin farkli derinliklerine yerlestirilir.
    candidates.sort(key=lambda r: dist[r])
    selected = []
    for i in range(required):
        target = (i + 1) * (len(candidates) / (required + 1))
        lo = max(0, int(target - 3))
        hi = min(len(candidates), int(target + 4))
        choices = [r for r in candidates[lo:hi] if r not in selected]
        if not choices:
            choices = [r for r in candidates if r not in selected]
        room = random.choice(choices)
        selected.append(room)
        cx, cz = room_center(room)
        ox, oz = random.uniform(-2.0, 2.0), random.uniform(-2.0, 2.0)
        pickups.append(build_pickup_model(style["item"], (cx + ox, cz + oz), style))

    # Istege bagli pil paketleri. Bolum ilerledikce miktar biraz azalir.
    battery_rooms = [r for r in candidates if r not in selected]
    random.shuffle(battery_rooms)
    for room in battery_rooms[:max(2, 5 - chapter_index)]:
        cx, cz = room_center(room)
        x, z = cx + random.uniform(-2.1, 2.1), cz + random.uniform(-2.1, 2.1)
        room_id = room_at(x, z)
        chunk = room_nodes[room_id]
        battery = static_entity(parent=chunk, position=(x, .38, z))
        static_entity(parent=battery, model="cube", scale=(.26, .48, .20), color=hx("#4b956b"))
        static_entity(parent=battery, model="cube", position=(0, .26, 0), scale=(.14, .07, .21), color=hx("#b5c5a1"))
        ring = make_ring(x, .05, z, .24, hx("#8fd4a2"), parent=chunk, thickness=.045)
        pickups.append({"kind": "battery", "root": battery, "ring": ring, "glow": None, "x": x, "z": z, "room": room_id, "phase": random.random() * 6})

# -----------------------------------------------------------------------------
# Dusman: prosedurel, detayli, animasyonlu siluet
# -----------------------------------------------------------------------------
class Stalker:
    def __init__(self, parent, style: dict):
        self.root = static_entity(parent=parent, enabled=False)
        self.root.position = (CELL * 1.5, 0, CELL * 1.5)
        skin = hx("#%02x%02x%02x" % tuple(max(0, int(channel * .62)) for channel in style["enemy"]))
        dark = hx("#090d10")
        pale = hx("#42463f")
        self.hips = static_entity(parent=self.root, position=(0, 1.12, 0))
        static_entity(parent=self.hips, model="sphere", scale=(.48, .28, .32), color=dark)
        self.torso = static_entity(parent=self.hips, position=(0, .37, 0))
        static_entity(parent=self.torso, model="sphere", scale=(.54, .88, .34), color=skin)
        static_entity(parent=self.torso, model="cube", scale=(.08, .78, .04), position=(0, -.02, -.19), color=dark)
        # Kaburga benzeri katmanlar: stilize, kan/grafik unsur yok.
        for i in range(5):
            static_entity(parent=self.torso, model="cube", scale=(.43, .035, .035), position=(0, -.18 + i * .13, .17), color=pale)
        self.head = static_entity(parent=self.torso, position=(0, .72, .02))
        static_entity(parent=self.head, model="sphere", scale=(.34, .65, .34), color=skin)
        static_entity(parent=self.head, model="sphere", scale=(.28, .20, .10), position=(0, -.17, .19), color=dark)
        static_entity(parent=self.head, model="cube", scale=(.045, .46, .045), position=(0, -.32, .22), color=dark)
        eye_tint = style["enemy_eye"]
        for sx in (-.12, .12):
            static_entity(parent=self.head, model="sphere", position=(sx, .08, .205), scale=(.052, .038, .032), color=palette_color(eye_tint), unlit=True)
        # Omuz cikintilari ve uzun kollar.
        self.arm_l = static_entity(parent=self.torso, position=(-.32, .30, 0))
        self.arm_r = static_entity(parent=self.torso, position=(.32, .30, 0))
        for arm, side in ((self.arm_l, -1), (self.arm_r, 1)):
            static_entity(parent=arm, model="sphere", scale=(.19, .24, .18), color=dark)
            static_entity(parent=arm, model="cube", position=(0, -.39, 0), scale=(.16, .72, .16), color=skin, rotation_z=side * 7)
            static_entity(parent=arm, model="sphere", position=(0, -.78, .02), scale=(.14, .16, .14), color=dark)
            for finger in range(4):
                static_entity(parent=arm, model="cube", position=((finger - 1.5) * .055, - .94, .04),
                       scale=(.035, .28, .035), rotation_z=(finger - 1.5) * 8, color=pale)
        self.leg_l = static_entity(parent=self.hips, position=(-.15, -.12, 0))
        self.leg_r = static_entity(parent=self.hips, position=(.15, -.12, 0))
        for leg in (self.leg_l, self.leg_r):
            static_entity(parent=leg, model="cube", position=(0, -.36, 0), scale=(.18, .75, .19), color=skin)
            static_entity(parent=leg, model="cube", position=(0, -.78, .10), scale=(.22, .18, .40), color=dark)
        for side in (-1, 1):
            static_entity(parent=self.torso, model=CONE_MODEL, position=(side * .23, .55, -.04), scale=(.14, .36, .14), rotation_z=side * 28, color=dark)
        self.phase = 0.0
        self.state = "dormant"
        self.timer = 0.0
        self.lost = 0.0
        self.last_seen = (CELL / 2, CELL / 2)
        self.patrol_room = GRID * 2 + 2
        self.spawn_countdown = random.uniform(max(16, style["spawn"] * .38), max(24, style["spawn"] * .58))
        self.presence_timer = 0.0
        self.scared_this_visit = False
        self.speed = style["speed"]
        self.sight = style["sight"]
        self.hearing = style["hearing"]
        self.light_slow = 0.55 - chapter_index * .035

    def animate(self, dt: float, chasing: bool):
        self.phase += dt * (8.5 if chasing else 3.0)
        swing = math.sin(self.phase)
        self.leg_l.rotation_x = swing * (47 if chasing else 15)
        self.leg_r.rotation_x = -swing * (47 if chasing else 15)
        self.arm_l.rotation_x = -swing * (38 if chasing else 12) - 15
        self.arm_r.rotation_x = swing * (38 if chasing else 12) - 15
        self.head.rotation_z = math.sin(self.phase * .37) * 4
        self.torso.rotation_x = 12 if chasing else math.sin(self.phase * .5) * 2
        self.root.y = abs(swing) * (.06 if chasing else .025)


def make_enemy(style: dict):
    global enemy
    enemy = Stalker(world_root, style)


def dismiss_enemy(show_hint: bool = False):
    """End a sighting cleanly; the creature returns after a quiet interval."""
    global enemy_state
    if enemy is None:
        return
    enemy.root.enabled = False
    enemy.state = "dormant"
    enemy.presence_timer = 0.0
    enemy.scared_this_visit = False
    enemy.spawn_countdown = random.uniform(20.0, 32.0) + chapter_index * 1.5
    enemy_state = "dormant"
    if show_hint and random.random() < .45:
        show_toast("Ses uzaklasti. Simdilik yalnizsin.", 2.1)


def spawn_enemy():
    global enemy_state
    if enemy is None or enemy.root.enabled:
        return
    player_room = room_at(player.x, player.z)
    dist = graph_distances(player_room)
    far_rooms = [r for r in range(GRID * GRID) if dist[r] >= 2]
    room = random.choice(far_rooms or list(range(1, GRID * GRID)))
    x, z = room_center(room)
    enemy.root.position = (x, 0, z)
    enemy.root.enabled = True
    enemy.state = "roam"
    enemy.patrol_room = random.randrange(GRID * GRID)
    enemy.timer = random.uniform(4.5, 7.5)
    enemy.presence_timer = random.uniform(17.0, 29.0) + chapter_index * 1.2
    enemy.scared_this_visit = False
    enemy.lost = 0.0
    enemy_state = "roam"
    if whisper_audio:
        whisper_audio.volume = random.uniform(.12, .19)
        whisper_audio.play()
    if random.random() < .58:
        show_toast("Koridorun ucunda bir hareket gordun.", 2.6)

# -----------------------------------------------------------------------------
# Oyun akisi ve bolum hedefleri
# -----------------------------------------------------------------------------
def objective_text() -> str:
    style = CHAPTERS[chapter_index]
    remaining = style["required"] - chapter_items_collected
    return f"{style['item_name']}: {chapter_items_collected}/{style['required']}  |  {max(0, remaining)} kaldi"


def update_hud():
    style = CHAPTERS[chapter_index]
    hud_chapter.text = f"{style['subtitle']}  -  {style['name']}"
    if escape_active:
        hud_objective.text = f"KAC! BASLANGIC CIKISINA DON  |  {max(0, int(escape_timer))} sn"
    elif puzzle_solved:
        hud_objective.text = "Terminal aktif: baslangic cikisina geri don."
    else:
        hud_objective.text = objective_text()
    hud_hint.text = "WASD hareket  |  SHIFT kos  |  C egil  |  E etkilesim  |  F fener  |  R telsiz  |  TAB durum"
    hud_battery.text = f"FENER {int(battery_charge):02d}%"
    hud_battery.color = hx("#dfc98d") if battery_charge > 25 else hx("#dd7868")
    hud_progress.text = f"BOLUM {chapter_index + 1}/5"
    stamina_bar.scale_x = .27 * max(0, stamina / 100)
    stamina_bar.x = -.135 + .135 * max(0, stamina / 100)
    stamina_bar.color = hx("#b94c43") if exhausted else hx("#c6a35d")
    if escape_active:
        hud_status.text = "KOVALAMACA! CIKISA ULAS"
    else:
        hud_status.text = "EGILMIS DURUM" if crouching else ("YAKINDA BIR SEY VAR" if enemy and enemy.root.enabled and distance_to_enemy() < 15 else "")
    hud_status.color = hx("#dc8274") if hud_status.text else hx("#e1b47c")


def distance_to_enemy() -> float:
    if enemy is None or not enemy.root.enabled:
        return 999.0
    return math.hypot(enemy.root.x - player.x, enemy.root.z - player.z)


def radio_message():
    style = CHAPTERS[chapter_index]
    targets = [p for p in pickups if p["kind"] == style["item"]]
    if not targets:
        show_toast(style["gate_text"], 4)
        return
    target = min(targets, key=lambda p: (p["x"] - player.x) ** 2 + (p["z"] - player.z) ** 2)
    dx, dz = target["x"] - player.x, target["z"] - player.z
    angle = math.radians(player.rotation_y)
    forward = dx * math.sin(angle) + dz * math.cos(angle)
    right = dx * math.cos(angle) - dz * math.sin(angle)
    if abs(forward) > abs(right):
        direction = "onunde" if forward > 0 else "arkanda"
    else:
        direction = "saginda" if right > 0 else "solunda"
    meters = round(math.hypot(dx, dz))
    show_toast(f"Telsiz: hedef {direction}, yaklasik {meters} metre.", 3.8)
    if pickup_audio:
        pickup_audio.play()


def collect_pickup(item: dict):
    global chapter_items_collected, battery_charge
    if item["kind"] == "battery":
        battery_charge = min(100, battery_charge + 38)
        show_toast("Pil alindi. Fener sarji +38%", 2.2)
    else:
        chapter_items_collected += 1
        style = CHAPTERS[chapter_index]
        show_toast(f"{style['item_name']} bulundu: {chapter_items_collected}/{style['required']}", 2.5)
        if chapter_items_collected == 1 and enemy and enemy.state == "dormant":
            enemy.spawn_countdown = min(enemy.spawn_countdown, 9.0)
    if pickup_audio:
        pickup_audio.play()
    for obj_name in ("root", "ring", "glow"):
        obj = item.get(obj_name)
        if obj is not None:
            destroy(obj)
    if item in pickups:
        pickups.remove(item)
    update_hud()
    if chapter_items_collected >= CHAPTERS[chapter_index]["required"]:
        show_toast("Hedef tamamlandi. Cikis terminalini bul.", 4.0)


def start_chapter_puzzle():
    global puzzle_active, puzzle_entry, puzzle_attempts
    if puzzle_solved or puzzle_active:
        return
    puzzle_active = True
    puzzle_entry = []
    puzzle_attempts = 0
    info = PUZZLES[chapter_index]
    puzzle_title.text = info["title"]
    puzzle_clue.text = info["hint"] + "\n\nTerminalde 1, 2, 3 ve 4 tuslarini kullan."
    puzzle_progress.text = "GIRIS: _ _ _ _ _"
    puzzle_help.text = "1-4: tus gir  |  BACKSPACE: sil  |  ENTER: onayla  |  ESC: kapat"
    for ui in (puzzle_back, puzzle_title, puzzle_clue, puzzle_progress, puzzle_help):
        ui.enabled = True
    set_frozen(True)
    show_toast("Terminal bulmacasi basladi. Cevreni dinle.", 2.5)


def update_puzzle_display():
    expected = len(PUZZLES[chapter_index]["sequence"])
    dots = [str(n) for n in puzzle_entry] + ["_"] * max(0, expected - len(puzzle_entry))
    puzzle_progress.text = "GIRIS: " + "  ".join(dots[:expected])


def submit_chapter_puzzle():
    global puzzle_active, puzzle_solved, escape_active, escape_timer, enemy_state
    target = PUZZLES[chapter_index]["sequence"]
    if puzzle_entry == target:
        puzzle_active = False
        puzzle_solved = True
        for ui in (puzzle_back, puzzle_title, puzzle_clue, puzzle_progress, puzzle_help):
            ui.enabled = False
        set_frozen(False)
        escape_active = True
        escape_timer = max(58.0, 112.0 - chapter_index * 10.0)
        if extraction_door is not None:
            extraction_door.animate_rotation_y(86, duration=1.4)
        show_toast("DEVRE AKTIF! Yaratik uyandi. BASLANGIC CIKISINA KOS!", 5.0)
        if enemy is not None:
            if not enemy.root.enabled:
                spawn_enemy()
            enemy.state = "chase"
            enemy.last_seen = (player.x, player.z)
            enemy.lost = 0.0
            enemy.timer = escape_timer + 15.0
            enemy.speed = CHAPTERS[chapter_index]["speed"] * 1.10
            enemy_state = "chase"
    else:
        puzzle_entry.clear()
        update_puzzle_display()
        show_toast("SIFRE HATALI! Notu tekrar incele.", 2.2)
        if enemy is not None:
            enemy.spawn_countdown = max(0.0, enemy.spawn_countdown - 8.0)


def cancel_chapter_puzzle():
    global puzzle_active
    puzzle_active = False
    for ui in (puzzle_back, puzzle_title, puzzle_clue, puzzle_progress, puzzle_help):
        ui.enabled = False
    set_frozen(False)
    show_toast("Terminal beklemede. Hazir olunca tekrar dene.", 2.2)


def complete_chapter():
    global chapter_index, ending, chapter_intro, escape_active, escape_timer
    if chapter_items_collected < CHAPTERS[chapter_index]["required"]:
        show_toast(CHAPTERS[chapter_index]["gate_text"], 3.4)
        return
    if not puzzle_solved:
        show_toast("Once uzak terminaldeki bolum bulmacasini coz.", 3.2)
        return
    escape_active = False
    escape_timer = 0.0
    set_frozen(True)
    if chapter_index == len(CHAPTERS) - 1:
        ending = True
        card_title.text = "SON YANKI"
        card_body.text = "Saat yeniden calismaya basladi. Bes bolumun tamamlandi.\nKaranlik artik seni takip etmiyor."
        card_sub.text = "ECHO OF THE DEPTHS  |  OYUN TAMAMLANDI"
        card_back.enabled = card_title.enabled = card_body.enabled = card_sub.enabled = True
        if ambience_audio:
            ambience_audio.volume = .08
        return
    card_title.text = "BOLUM TAMAMLANDI"
    card_body.text = f"{CHAPTERS[chapter_index]['name']} geride kaldi.\nAma bu yerlerin hepsi ayni seye bagli."
    card_sub.text = "Sonraki bolume geciliyor..."
    card_back.enabled = card_title.enabled = card_body.enabled = card_sub.enabled = True
    invoke(next_chapter, delay=3.7)


def next_chapter():
    global chapter_index
    chapter_index += 1
    start_chapter()


def start_chapter():
    global chapter_items_collected, battery_charge, flashlight_on, crouching, stamina
    global exhausted, chapter_clock, spawn_clock, enemy, enemy_state, caught_lock, chapter_intro, camera_pitch, show_map
    global puzzle_active, puzzle_solved, puzzle_entry, escape_active, escape_timer
    chapter_items_collected = 0
    battery_charge = 100.0 if chapter_index == 0 else min(100.0, battery_charge + 15)
    flashlight_on = False
    crouching = False
    stamina = 100.0
    exhausted = False
    chapter_clock = 0.0
    ambient_event_timer = random.uniform(14.0, 24.0)
    spawn_clock = 0.0
    caught_lock = False
    puzzle_active = False
    puzzle_solved = False
    puzzle_entry = []
    escape_active = False
    escape_timer = 0.0
    for ui in (puzzle_back, puzzle_title, puzzle_clue, puzzle_progress, puzzle_help):
        ui.enabled = False
    show_map = False
    map_back.enabled = False
    map_text.enabled = False
    style = CHAPTERS[chapter_index]
    gate_pos = build_world()
    spawn_chapter_items(style)
    make_enemy(style)
    enemy_state = "dormant"
    player.position = (CELL / 2, 0, CELL / 2)
    player.rotation_y = 0
    update_room_streaming(force=True)
    camera.position = (0, 1.68, 0)
    camera.rotation = (0, 0, 0)
    camera_pitch = 0
    scene.setFog(fog)
    fog.setColor(*(c / 255 for c in style["fog"]))
    fog.setExpDensity(.024 + chapter_index * .0028)
    amb = style["ambient"]
    ambient.setColor((min(.16, amb[0] * .48 + .025), min(.16, amb[1] * .48 + .025),
                      min(.16, amb[2] * .48 + .025), 1.0))
    spot.setColor((0, 0, 0, 1))
    update_hud()
    card_title.text = style["name"]
    card_body.text = style["story"]
    card_sub.text = f"{style['subtitle']}  |  Yakalanirsan bolum ilerlemen korunur."
    card_back.enabled = card_title.enabled = card_body.enabled = card_sub.enabled = True
    set_frozen(False)
    invoke(hide_chapter_card, delay=4.2)
    if ambience_audio:
        ambience_audio.volume = .18 + chapter_index * .015


def hide_chapter_card():
    if ending:
        return
    card_back.enabled = card_title.enabled = card_body.enabled = card_sub.enabled = False
    set_frozen(False)
    show_toast("Fenerini kullan, ama her zaman acik tutma.", 3.2)


def caught_by_enemy():
    global caught_lock, battery_charge, stamina, exhausted, flashlight_on, escape_active, escape_timer
    if caught_lock or frozen:
        return
    caught_lock = True
    escape_active = False
    escape_timer = 0.0
    set_frozen(True)
    flashlight_on = False
    battery_charge = max(8, battery_charge - 18)
    stamina = max(50, stamina)
    exhausted = False
    fade.alpha = 0
    fade.animate("alpha", 1, duration=.45)
    card_title.text = "IZINI KAYBETTIN"
    card_body.text = "Gozlerini yeniden actiginda ayni bolumdesin.\nTopladigin esyalar korunuyor."
    card_sub.text = "Fener sarjinin bir bolumu tukendi."
    card_back.enabled = card_title.enabled = card_body.enabled = card_sub.enabled = True
    if sting_audio:
        sting_audio.play()

    def respawn_player():
        global caught_lock
        if enemy:
            enemy.root.enabled = False
            enemy.state = "dormant"
            enemy.spawn_countdown = max(18, CHAPTERS[chapter_index]["spawn"] * .55)
        player.position = (CELL / 2, 0, CELL / 2)
        player.rotation_y = 0
        camera.position = (0, 1.68, 0)
        card_back.enabled = card_title.enabled = card_body.enabled = card_sub.enabled = False
        fade.animate("alpha", 0, duration=.9)
        caught_lock = False
        set_frozen(False)
        show_toast("Bolum ilerlemen korundu. Daha sessiz hareket et.", 3.8)
    invoke(respawn_player, delay=2.9)


def try_interact():
    global near_action
    if near_action:
        callback = near_action
        callback()

# -----------------------------------------------------------------------------
# Dusman algisi ve hareketi
# -----------------------------------------------------------------------------
def line_of_sight(ax: float, az: float, bx: float, bz: float) -> bool:
    length = math.hypot(bx - ax, bz - az)
    steps = max(2, int(length / .55))
    for i in range(1, steps):
        x = ax + (bx - ax) * i / steps
        z = az + (bz - az) * i / steps
        for room_id in nearby_room_ids(x, z, 1):
            for cx, cz, hw, hd in wall_colliders_by_room[room_id]:
                if abs(x - cx) < hw and abs(z - cz) < hd:
                    return False
    return True


def flashlight_hits_enemy() -> bool:
    if not flashlight_on or battery_charge <= 0 or enemy is None or not enemy.root.enabled:
        return False
    dx, dz = enemy.root.x - player.x, enemy.root.z - player.z
    distance = math.hypot(dx, dz)
    if distance > 18 or distance < .1:
        return False
    angle = math.radians(player.rotation_y)
    dot = (dx * math.sin(angle) + dz * math.cos(angle)) / distance
    return dot > .88 and line_of_sight(player.x, player.z, enemy.root.x, enemy.root.z)


def move_enemy_toward(tx: float, tz: float, speed: float, dt: float):
    dx, dz = tx - enemy.root.x, tz - enemy.root.z
    length = math.hypot(dx, dz)
    if length < .12:
        return
    step = min(length, speed * dt)
    nx = enemy.root.x + dx / length * step
    nz = enemy.root.z + dz / length * step
    if can_stand(nx, enemy.root.z, .30):
        enemy.root.x = nx
    if can_stand(enemy.root.x, nz, .30):
        enemy.root.z = nz
    enemy.root.rotation_y = math.degrees(math.atan2(dx, dz))


def update_enemy(dt: float, moving_fast: bool):
    global enemy_state
    if enemy is None:
        return
    if not enemy.root.enabled:
        enemy.spawn_countdown -= dt
        if enemy.spawn_countdown <= 0 and not frozen:
            spawn_enemy()
        return

    distance = distance_to_enemy()
    visible = (distance < enemy.sight * (0.55 if crouching else 1.0)
               and line_of_sight(enemy.root.x, enemy.root.z, player.x, player.z))
    hearing_radius = enemy.hearing * (0.22 if crouching else (1.35 if moving_fast else .55))
    heard = distance < hearing_radius and not crouching
    lit = flashlight_hits_enemy()

    # The first close sighting may trigger one short scare flash per appearance.
    if visible and 2.8 < distance < 8.5 and not enemy.scared_this_visit:
        facing = math.radians(player.rotation_y)
        dx, dz = enemy.root.x - player.x, enemy.root.z - player.z
        dot = (dx * math.sin(facing) + dz * math.cos(facing)) / max(.1, distance)
        if dot > .38 and random.random() < .62:
            trigger_jumpscare()
        enemy.scared_this_visit = True

    if enemy.state == "roam":
        enemy.presence_timer -= dt
        enemy.timer -= dt
        if visible or heard:
            enemy.state = "chase"
            enemy.timer = 18 + chapter_index * 3.5
            enemy.last_seen = (player.x, player.z)
            enemy.lost = 0.0
            if sting_audio:
                sting_audio.volume = .42
                sting_audio.play()
            show_toast("Bir sey seni fark etti. Gorusu kes ve sessizles.", 2.6)
        elif enemy.presence_timer <= 0 and not escape_active:
            dismiss_enemy(show_hint=True)
            return
        else:
            if enemy.timer <= 0 or math.hypot(
                enemy.root.x - room_center(enemy.patrol_room)[0],
                enemy.root.z - room_center(enemy.patrol_room)[1]
            ) < 1.2:
                options = [r for r in range(GRID * GRID) if r != room_at(enemy.root.x, enemy.root.z)]
                enemy.patrol_room = random.choice(options)
                enemy.timer = random.uniform(4.0, 7.0)
            tx, tz = path_waypoint(enemy.root.x, enemy.root.z, *room_center(enemy.patrol_room))
            move_enemy_toward(tx, tz, enemy.speed * .56, dt)

    elif enemy.state == "chase":
        if visible or heard:
            enemy.last_seen = (player.x, player.z)
            enemy.lost = 0.0
        else:
            enemy.lost += dt
        tx, tz = enemy.last_seen
        wx, wz = path_waypoint(enemy.root.x, enemy.root.z, tx, tz)
        speed = enemy.speed
        if lit:
            speed *= enemy.light_slow
            if not escape_active:
                enemy.presence_timer -= dt * .55
        if crouching and not visible:
            speed *= .78
        move_enemy_toward(wx, wz, speed, dt)
        enemy.timer -= dt
        if distance < 1.15 and (visible or enemy.lost < 1.4):
            caught_by_enemy()
            return
        if enemy.timer <= 0 or enemy.lost > 5.8 or distance > 36:
            enemy.state = "search"
            enemy.timer = random.uniform(3.0, 4.7)

    elif enemy.state == "search":
        enemy.timer -= dt
        tx, tz = path_waypoint(enemy.root.x, enemy.root.z, *enemy.last_seen)
        move_enemy_toward(tx, tz, enemy.speed * .62, dt)
        if visible or heard:
            enemy.state = "chase"
            enemy.timer = 16 + chapter_index * 3
            enemy.last_seen = (player.x, player.z)
            enemy.lost = 0.0
        elif enemy.timer <= 0:
            if escape_active:
                # During the final escape it reappears deeper in the route instead of ending the chase.
                enemy.state = "chase"
                enemy.timer = escape_timer + 8.0
                enemy.last_seen = (player.x, player.z)
                enemy.lost = 0.0
            else:
                dismiss_enemy(show_hint=True)
                return

    # A strong light can make it retreat after an encounter, but never during the final chase.
    if lit and distance < 15 and random.random() < dt * .22 and not escape_active:
        enemy.presence_timer -= dt * 2.0
    enemy.animate(dt, enemy.state == "chase")
    enemy_state = enemy.state

# -----------------------------------------------------------------------------
# Etkilesim, kontroller ve ana dongu
# -----------------------------------------------------------------------------
def update_interactions():
    global near_action
    near_action = None
    hud_prompt.text = ""
    best = 2.0
    for item in pickups:
        if item.get("room") not in room_active:
            continue
        dx, dz = item["x"] - player.x, item["z"] - player.z
        dist = math.hypot(dx, dz)
        if dist < best:
            best = dist
            if item["kind"] == "battery":
                hud_prompt.text = "[E] Pil paketi al"
            else:
                hud_prompt.text = f"[E] {CHAPTERS[chapter_index]['item_name']} al"
            near_action = lambda item=item: collect_pickup(item)

    style = CHAPTERS[chapter_index]
    # Uzak odadaki terminal: once hedefleri tamamla, ardindan o bolumun bulmacasini coz.
    cx, cz = console_pos
    dist_console = math.hypot(cx - player.x, cz - player.z)
    if dist_console < 3.0 and dist_console < best + .6:
        if chapter_items_collected < style["required"]:
            hud_prompt.text = f"Terminal kilitli: {chapter_items_collected}/{style['required']} {style['item_name']}"
            near_action = None
        elif not puzzle_solved:
            hud_prompt.text = "[E] Bolum terminalini incele / bulmaca"
            near_action = start_chapter_puzzle
        else:
            hud_prompt.text = "Devre aktif. Baslangic cikisina don!"
            near_action = None

    # Baslangic odasindaki dis kapi: bulmaca cozuldukten ve kovalamacadan sonra cikis.
    ex, ez = exit_pos
    dist_exit = math.hypot(ex - player.x, ez - player.z)
    if dist_exit < 2.7:
        if puzzle_solved:
            hud_prompt.text = "[E] Acik cikistan kac"
            near_action = complete_chapter
        else:
            hud_prompt.text = "Cikis kilitli: terminal bulmacasi gerekli"
            near_action = None


def input(key):
    global flashlight_on, crouching, show_map, camera_pitch
    if puzzle_active:
        if key == "escape":
            cancel_chapter_puzzle()
        elif key in ("1", "2", "3", "4"):
            if len(puzzle_entry) < len(PUZZLES[chapter_index]["sequence"]):
                puzzle_entry.append(int(key))
                update_puzzle_display()
        elif key == "backspace":
            if puzzle_entry:
                puzzle_entry.pop()
                update_puzzle_display()
        elif key == "enter":
            submit_chapter_puzzle()
        return

    if key == "left mouse down" and not frozen:
        mouse.locked = True
        return
    if key == "escape":
        if ending:
            application.quit()
        return
    if frozen:
        return
    if key == "e":
        try_interact()
    elif key == "f":
        if battery_charge > .5:
            flashlight_on = not flashlight_on
            if pickup_audio:
                pickup_audio.play()
        else:
            show_toast("Fenerin pili bitmis. Pil paketi ara.", 2.4)
    elif key == "c":
        crouching = not crouching
        show_toast("Daha sessiz hareket ediyorsun." if crouching else "Ayaga kalktin.", 1.5)
    elif key == "r":
        radio_message()
    elif key == "tab":
        show_map = not show_map
        map_back.enabled = show_map
        map_text.enabled = show_map
        if show_map:
            map_text.text = (
                "HARITA / DURUM\n\n"
                f"Bolum: {chapter_index + 1}/5\n"
                f"Hedef: {chapter_items_collected}/{CHAPTERS[chapter_index]['required']}\n"
                f"Bulmaca: {'Tamam' if puzzle_solved else 'Bekliyor'}\n"
                f"Pil: {int(battery_charge)}%\n\n"
                "R: telsizden hedef yonu."
            )
    elif key == "f11":
        window.fullscreen = not window.fullscreen


def prepare_startup_assets() -> None:
    """Yalnizca ilk bolumun dosyalarini arka planda hazirla.

    Diger bolumlerin dokulari o bolume gecildiginde olusturulur. Boylece
    ilk acilista bes bolumun tum dosyalarini beklemek gerekmez.
    """
    try:
        build_chapter_textures(1, CHAPTERS[0])
        build_chapter_detail_textures(1, CHAPTERS[0])
        build_audio_files()
        build_jumpscare_texture()
    except Exception:
        traceback.print_exc()
        try:
            with open(os.path.join(BASE_DIR, "echo_hata.txt"), "w", encoding="utf-8") as error_file:
                error_file.write("Baslangic dosyalari hazirlanirken hata olustu.\n")
                traceback.print_exc(file=error_file)
        except OSError:
            pass
    finally:
        startup_assets_ready.set()


def begin_startup() -> None:
    """Ilk kare gosterildikten sonra seviyeyi ana Ursina thread'inde kur."""
    global startup_started, scare_overlay
    if startup_started:
        return
    startup_started = True
    startup_message.text = "Ilk bolum olusturuluyor..."
    print("[ECHO] Ses sistemi hazirlaniyor...", flush=True)
    try:
        initialize_audio()
        scare_path = build_jumpscare_texture()
        scare_tex = load_texture(os.path.basename(scare_path), folder=Path(TEX_DIR))
        scare_overlay = Entity(parent=camera.ui, model="quad", scale=(1.95, 1.95),
                               texture=scare_tex, color=color.rgba32(255, 255, 255, 0),
                               z=-1.85, enabled=False)
        print("[ECHO] Malikane haritasi ve modeller olusturuluyor...", flush=True)
        start_chapter()
        print("[ECHO] Ilk bolum hazir.", flush=True)
        application.base.setBackgroundColor(0.012, 0.018, 0.026, 1.0)
        startup_panel.enabled = False
        startup_title.enabled = False
        startup_message.enabled = False
    except Exception as exc:
        print("\nOYUN BASLATILAMADI:\n")
        traceback.print_exc()
        try:
            with open(os.path.join(BASE_DIR, "echo_hata.txt"), "w", encoding="utf-8") as error_file:
                traceback.print_exc(file=error_file)
        except Exception:
            pass
        startup_title.text = "OYUN BASLATILAMADI"
        startup_message.text = f"{type(exc).__name__}: {exc}  |  echo_hata.txt dosyasina bak."


def update():
    global camera_pitch, battery_charge, flashlight_on, stamina, exhausted
    global chapter_clock, toast_timer, walk_phase, step_counter, noise_level
    global startup_queued, lamp_refresh_timer, selected_lamps, escape_timer
    global jumpscare_timer, jumpscare_cooldown, ambient_event_timer

    # App penceresi acilip ilk kare cizildikten sonra yuklemeyi baslat.
    if startup_assets_ready.is_set() and not startup_queued:
        startup_queued = True
        invoke(begin_startup, delay=.25)

    dt = min(time.dt, .04)

    if jumpscare_cooldown > 0:
        jumpscare_cooldown = max(0.0, jumpscare_cooldown - dt)
    if jumpscare_timer > 0 and scare_overlay is not None:
        jumpscare_timer = max(0.0, jumpscare_timer - dt)
        scale = 1.55 + (jumpscare_timer / .42) * .48
        scare_overlay.scale = (scale, scale)
        scare_overlay.color = color.rgba32(255, 255, 255, int(245 * jumpscare_timer / .42))
        if jumpscare_timer <= 0:
            scare_overlay.enabled = False

    if frozen:
        if fade.alpha > 0 and not caught_lock and not ending:
            fade.alpha = max(0, fade.alpha - dt * .9)
        return
    chapter_clock += dt
    ambient_event_timer -= dt
    if ambient_event_timer <= 0 and not escape_active:
        if random.random() < .56 and knock_audio:
            knock_audio.volume = random.uniform(.12, .20)
            knock_audio.play()
        elif whisper_audio:
            whisper_audio.volume = random.uniform(.10, .17)
            whisper_audio.play()
        ambient_event_timer = random.uniform(19.0, 34.0)

    if escape_active:
        escape_timer = max(0.0, escape_timer - dt)
        if escape_timer <= 0 and not caught_lock:
            caught_by_enemy()

    # Fare/kamera.
    # Ursina surumune gore mouse.velocity 2 veya 3 bilesenli olabilir.
    # Sadece yatay/dikey hareketi kullan; tum vektoru iki degiskene acma.
    mouse_delta = mouse.velocity
    try:
        mx = float(mouse_delta[0])
        my = float(mouse_delta[1])
    except (TypeError, IndexError, KeyError):
        mx = my = 0.0
    player.rotation_y += mx * 45
    camera_pitch = max(-82, min(82, camera_pitch - my * 42))
    camera.rotation_x = camera_pitch

    # Hareket.
    forward = held_keys["w"] - held_keys["s"]
    sideways = held_keys["d"] - held_keys["a"]
    mag = math.hypot(forward, sideways)
    if mag:
        forward /= mag
        sideways /= mag
    moving = mag > .01
    sprinting = moving and held_keys["shift"] and not crouching and not exhausted and stamina > 1
    speed = 5.0 if sprinting else (1.45 if crouching else 2.9)
    rad = math.radians(player.rotation_y)
    fx, fz = math.sin(rad), math.cos(rad)
    rx, rz = math.cos(rad), -math.sin(rad)
    dx = (fx * forward + rx * sideways) * speed * dt
    dz = (fz * forward + rz * sideways) * speed * dt
    if can_stand(player.x + dx, player.z):
        player.x += dx
    if can_stand(player.x, player.z + dz):
        player.z += dz

    if sprinting:
        stamina = max(0, stamina - (18 + chapter_index * 1.8) * dt)
    else:
        stamina = min(100, stamina + (5.5 if moving else 9.0) * dt)
    if stamina <= 0:
        exhausted = True
    elif exhausted and stamina > 28:
        exhausted = False

    # Kamera bob ve eldeki fener.
    moving_amount = math.hypot(dx, dz)
    walk_phase += moving_amount * (8.0 if sprinting else 6.0)
    target_height = 1.12 if crouching else 1.68
    camera.y = target_height + (math.sin(walk_phase) * (.035 if sprinting else .018) if moving else 0)
    camera.z = 0
    torch.enabled = True
    if moving and int(walk_phase * 1.6) != step_counter:
        step_counter = int(walk_phase * 1.6)
        if step_audio:
            step_audio.volume = .55 if sprinting else (.12 if crouching else .28)
            step_audio.pitch = random.uniform(.86, 1.08)
            step_audio.play()

    noise_level = 1.0 if sprinting else (.12 if crouching else (.42 if moving else 0.0))
    if flashlight_on:
        battery_charge = max(0, battery_charge - dt * CHAPTERS[chapter_index]["drain"])
        if battery_charge <= 0:
            flashlight_on = False
            show_toast("Fenerin sarji bitti!", 2.5)
    if flashlight_on:
        spot.setColor((1.45, 1.35, 1.12, 1))
        scene.setLight(spot_np)
    else:
        scene.clearLight(spot_np)
        spot.setColor((0, 0, 0, 1))

    # Dusman ve yakinlik efektleri.
    update_enemy(dt, sprinting)
    update_room_streaming()
    distance = distance_to_enemy()
    threat = max(0, 1 - distance / 25) if enemy and enemy.root.enabled else 0
    if threat > .35 and random.random() < dt * (1.2 + threat * 1.8):
        if pulse_audio:
            pulse_audio.volume = .12 + threat * .45
            pulse_audio.pitch = .82 + threat * .42
            pulse_audio.play()

    # Yakindaki oda isiklari; uzak odalardaki isiklar kapali kalir.
    lamp_refresh_timer -= dt
    if lamp_refresh_timer <= 0:
        selected_lamps = sorted(
            room_lights,
            key=lambda p: (p[0] - player.x) ** 2 + (p[1] - player.z) ** 2,
        )[:len(light_pool)]
        lamp_refresh_timer = .30
    for i, (node, light) in enumerate(light_pool):
        if i < len(selected_lamps):
            lx, lz, phase = selected_lamps[i]
            d2 = (lx - player.x) ** 2 + (lz - player.z) ** 2
            if d2 < 440:
                flicker = .72 if math.sin(chapter_clock * (23 + i) + phase) > .985 else 1.0
                if threat > .45 and random.random() < dt * .8:
                    flicker *= .12
                node.setPos(lx, WALL_H - .65, lz)
                glow_rgb = CHAPTERS[chapter_index]["glow"]
                light.setColor(tuple((channel / 255.0) * .72 * flicker for channel in glow_rgb) + (1,))
                scene.setLight(node)
            else:
                light.setColor((0, 0, 0, 1))
                scene.clearLight(node)
        else:
            light.setColor((0, 0, 0, 1))
            scene.clearLight(node)

    # Nesnelerin hafif donmesi/parlamasi.
    for item in pickups:
        if item.get("room") not in room_active:
            continue
        item["phase"] += dt * 1.15
        item["root"].y = .22 + math.sin(item["phase"]) * .025
        item["root"].rotation_y += dt * 10
        item["ring"].rotation_y += dt * 8
        scale = .92 + math.sin(item["phase"] * 1.4) * .035
        item["ring"].scale = scale

    update_interactions()
    update_hud()
    toast_timer -= dt
    if toast_timer <= 0:
        hud_toast.text = ""

# -----------------------------------------------------------------------------
# Baslat / doku paketi olustur
# -----------------------------------------------------------------------------
if "--diagnostics" in sys.argv:
    import ursina as ursina_package
    import panda3d.core as panda_core
    print("ECHO OF THE DEPTHS - TEKNIK BILGI")
    print("Python:", sys.version.replace("\\n", " "))
    print("Ursina:", getattr(ursina_package, "__version__", "surum bilgisi bulunamadi"))
    print("Ursina konumu:", ursina_package.__file__)
    print("Panda3D:", panda_core.PandaSystem.getVersionString())
    print("Doku klasoru:", TEX_DIR)
    print("Bolum sayisi:", len(CHAPTERS))
    raise SystemExit(0)

if "--generate-textures" in sys.argv:
    for texture_index, texture_style in enumerate(CHAPTERS, start=1):
        print(f"[TEXTURE] {texture_index}/5 {texture_style['name']}", flush=True)
        build_chapter_textures(texture_index, texture_style)
    print(f"[TEXTURE] Tum bolum dokulari hazir: {TEX_DIR}", flush=True)
    raise SystemExit(0)

try:
    # Yalnizca ilk bolum varliklari arka planda hazirlanir. Pencere hemen gorunur.
    asset_thread = threading.Thread(
        target=prepare_startup_assets,
        name="EchoAssetPreloader",
        daemon=True,
    )
    asset_thread.start()
    app.run()
except Exception:
    print("\nOYUNDA BIR HATA OLUSTU:\n")
    traceback.print_exc()
    try:
        with open(os.path.join(BASE_DIR, "echo_hata.txt"), "w", encoding="utf-8") as error_file:
            traceback.print_exc(file=error_file)
    except Exception:
        pass
    try:
        sys.stdin.readline()
    except Exception:
        pass