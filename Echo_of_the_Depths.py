# ECHO OF THE DEPTHS - 5 bolumlu, prosedurel 3B gerilim/korku oyunu
# Gereksinimler: Python 3.10+, ursina, pillow
# Kurulum: py -m pip install ursina pillow
# Calistirma: py Echo_of_the_Depths.py
# Tum dokular, sesler ve dusman modelleri oyun acilirken yerel olarak uretilir.

from __future__ import annotations
import os
import sys
import math
import random
import wave
import struct
import traceback
from collections import deque

try:
    from ursina import *
    from panda3d.core import (
        AmbientLight as PandaAmbientLight,
        PointLight as PandaPointLight,
        Spotlight as PandaSpotlight,
        PerspectiveLens,
        Fog,
    )
    from PIL import Image, ImageDraw, ImageChops
except ImportError as exc:
    print("Gerekli kutuphane bulunamadi:", exc)
    print("Terminalde su komutu calistir: py -m pip install ursina pillow")
    input("Cikmak icin Enter...")
    raise SystemExit(1)

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
window.color = color.rgb(4, 5, 8)
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
ASSET_DIR = "echo_assets"
TEX_DIR = os.path.join(ASSET_DIR, "textures")
SFX_DIR = os.path.join(ASSET_DIR, "audio")
os.makedirs(TEX_DIR, exist_ok=True)
os.makedirs(SFX_DIR, exist_ok=True)


def blend_noise(img: Image.Image, amount: float = 0.12) -> Image.Image:
    noise = Image.effect_noise(img.size, 24).convert("RGB")
    return Image.blend(img.convert("RGB"), noise, amount)


def build_chapter_textures(chapter_index: int, style: dict) -> tuple[str, str, str]:
    """PIL ile bolume ozel duvar, zemin ve metal dokulari uretir."""
    wall_path = os.path.join(TEX_DIR, f"wall_{chapter_index}.png")
    floor_path = os.path.join(TEX_DIR, f"floor_{chapter_index}.png")
    metal_path = os.path.join(TEX_DIR, f"metal_{chapter_index}.png")
    if all(os.path.exists(p) for p in (wall_path, floor_path, metal_path)):
        return wall_path, floor_path, metal_path

    wc = style["wall"]
    fc = style["floor"]
    tc = style["trim"]
    wall = Image.new("RGB", (256, 256), wc)
    d = ImageDraw.Draw(wall)
    if style["room_style"] == "wood":
        for x in range(0, 256, 32):
            d.rectangle((x, 0, x + 4, 255), fill=tuple(max(0, c - 28) for c in wc))
            d.line((x + 9, 0, x + 9, 255), fill=tuple(min(255, c + 13) for c in wc), width=1)
        for y in (0, 82, 86, 250):
            d.rectangle((0, y, 255, y + 4), fill=tc)
        for x in range(12, 256, 64):
            d.rectangle((x, 112, x + 43, 224), outline=tuple(max(0, c - 32) for c in wc), width=3)
    elif style["room_style"] == "tile":
        for y in range(0, 256, 32):
            d.line((0, y, 256, y), fill=tuple(max(0, c - 25) for c in wc), width=2)
            off = 0 if (y // 32) % 2 == 0 else 16
            for x in range(off, 256, 32):
                d.line((x, y, x, y + 32), fill=tuple(max(0, c - 25) for c in wc), width=2)
        d.rectangle((0, 205, 255, 255), fill=tuple(max(0, c - 30) for c in wc))
    elif style["room_style"] == "bark":
        for x in range(-30, 280, 22):
            d.line((x, 0, x + random.randint(-12, 12), 256), fill=tuple(max(0, c - 25) for c in wc), width=random.randint(2, 5))
        for _ in range(45):
            x, y = random.randrange(256), random.randrange(256)
            d.ellipse((x, y, x + random.randrange(3, 9), y + random.randrange(3, 9)), fill=tuple(min(255, c + 17) for c in wc))
    elif style["room_style"] == "concrete":
        for y in range(0, 256, 64):
            d.line((0, y, 256, y), fill=tuple(max(0, c - 28) for c in wc), width=3)
        for _ in range(18):
            x, y = random.randrange(256), random.randrange(256)
            d.line((x, y, x + random.randrange(-20, 20), y + random.randrange(8, 28)), fill=tuple(min(255, c + 19) for c in wc), width=1)
    else:
        for x in range(0, 256, 64):
            d.rectangle((x, 0, x + 3, 256), fill=tc)
        for y in range(18, 256, 48):
            d.line((0, y, 256, y), fill=tuple(max(0, c - 25) for c in wc), width=3)
        for x in range(12, 256, 64):
            d.ellipse((x, 25, x + 26, 51), outline=tc, width=2)
    blend_noise(wall, .13).save(wall_path)

    floor = Image.new("RGB", (256, 256), fc)
    fd = ImageDraw.Draw(floor)
    if style["room_style"] in ("wood", "bark"):
        for y in range(0, 256, 32):
            fd.line((0, y, 256, y), fill=tuple(max(0, c - 22) for c in fc), width=3)
            for x in range((y // 32 % 2) * 48, 256, 96):
                fd.line((x, y, x, y + 32), fill=tuple(max(0, c - 18) for c in fc), width=2)
        for _ in range(35):
            x, y = random.randrange(256), random.randrange(256)
            fd.line((x, y, x + random.randrange(12, 45), y + random.randrange(-3, 4)), fill=tuple(min(255, c + 14) for c in fc), width=1)
    else:
        for y in range(0, 256, 32):
            fd.line((0, y, 256, y), fill=tuple(min(255, c + 20) for c in fc), width=2)
            off = (y // 32 % 2) * 16
            for x in range(off, 256, 32):
                fd.line((x, y, x, y + 32), fill=tuple(min(255, c + 20) for c in fc), width=2)
        for x in range(6, 256, 64):
            fd.ellipse((x, 7, x + 4, 11), fill=tc)
    blend_noise(floor, .10).save(floor_path)

    metal = Image.new("RGB", (128, 128), tuple(min(255, c + 12) for c in tc))
    md = ImageDraw.Draw(metal)
    for y in range(0, 128, 12):
        md.line((0, y, 128, y), fill=tuple(max(0, c - 35) for c in tc), width=2)
    for x in (9, 118):
        for y in (9, 118):
            md.ellipse((x - 3, y - 3, x + 3, y + 3), fill=(28, 30, 34), outline=(190, 190, 175))
    blend_noise(metal, .08).save(metal_path)
    return wall_path, floor_path, metal_path


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


build_audio_files()
try:
    ambience_audio = Audio(os.path.join(SFX_DIR, "ambience.wav"), autoplay=True, loop=True, volume=.22)
    step_audio = Audio(os.path.join(SFX_DIR, "step.wav"), autoplay=False, volume=.35)
    pulse_audio = Audio(os.path.join(SFX_DIR, "pulse.wav"), autoplay=False, volume=.6)
    sting_audio = Audio(os.path.join(SFX_DIR, "sting.wav"), autoplay=False, volume=.8)
    pickup_audio = Audio(os.path.join(SFX_DIR, "pickup.wav"), autoplay=False, volume=.6)
except Exception:
    ambience_audio = step_audio = pulse_audio = sting_audio = pickup_audio = None

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
for index in range(6):
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
Entity(parent=torch, model="cylinder", scale=(.105, .38, .105), rotation_x=90, color=hx("#252a30"))
Entity(parent=torch, model="cylinder", scale=(.15, .10, .15), position=(0, 0, .20), rotation_x=90, color=hx("#9ca5a7"))
Entity(parent=torch, model="cylinder", scale=(.12, .07, .12), position=(0, 0, .255), rotation_x=90, color=hx("#d8d7c8"))
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

stamina_back = Entity(parent=camera.ui, model="quad", position=(0, -.405), scale=(.27, .009), color=hx("#2a2927"))
stamina_bar = Entity(parent=camera.ui, model="quad", position=(0, -.405), scale=(.27, .006), color=hx("#c6a35d"))
map_back = Entity(parent=camera.ui, model="quad", position=(.67, .17), scale=(.34, .32), color=color.rgba(8, 12, 13, 220), enabled=False)
map_text = Text(parent=camera.ui, text="", position=(.51, .28), scale=.56, color=hx("#c9d4b4"), enabled=False)

fade = Entity(parent=camera.ui, model="quad", scale=2, color=color.black, z=-2)
fade.alpha = 0
card_back = Entity(parent=camera.ui, model="quad", scale=(1.25, .50), color=color.rgba(6, 8, 9, 225), z=-1, enabled=False)
card_title = Text(parent=camera.ui, text="", origin=(0, 0), position=(0, .11), scale=1.55, color=hx("#e9d6aa"), enabled=False)
card_body = Text(parent=camera.ui, text="", origin=(0, 0), position=(0, -.015), scale=.85, color=hx("#d2d0c6"), enabled=False)
card_sub = Text(parent=camera.ui, text="", origin=(0, 0), position=(0, -.16), scale=.66, color=hx("#a7b7a7"), enabled=False)

# -----------------------------------------------------------------------------
# Global oyun durumu
# -----------------------------------------------------------------------------
chapter_index = 0
world_root = None
wall_colliders: list[tuple[float, float, float, float]] = []
furniture_colliders: list[tuple[float, float, float, float]] = []
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

def show_toast(message: str, duration: float = 2.8) -> None:
    global toast_timer
    hud_toast.text = message
    toast_timer = duration


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
        return color.rgb(int(value[0]), int(value[1]), int(value[2]))
    return value


def make_ring(x: float, y: float, z: float, radius: float, tint, parent=None, rotation=(0, 0, 0), thickness=.075):
    """Create a ring from small spheres so no external torus model is required."""
    group = Entity(parent=parent if parent is not None else world_root, position=(x, y, z), rotation=rotation)
    for index in range(16):
        angle = math.tau * index / 16
        Entity(parent=group, model="sphere",
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


def add_collider(x: float, z: float, width: float, depth: float, target=None) -> None:
    wall_colliders.append((x, z, width / 2, depth / 2))


def can_stand(x: float, z: float, radius: float = PLAYER_RADIUS) -> bool:
    if x < .55 or z < .55 or x > WORLD - .55 or z > WORLD - .55:
        return False
    for cx, cz, hw, hd in wall_colliders:
        if abs(x - cx) < hw + radius and abs(z - cz) < hd + radius:
            return False
    for cx, cz, hw, hd in furniture_colliders:
        if abs(x - cx) < hw + radius and abs(z - cz) < hd + radius:
            return False
    return True


def add_box(x: float, y: float, z: float, sx: float, sy: float, sz: float,
            tint, texture=None, collision=False, parent=None, rotation_y=0):
    e = Entity(parent=parent if parent is not None else world_root, model="cube", position=(x, y, z),
               scale=(sx, sy, sz), color=palette_color(tint), texture=texture, rotation_y=rotation_y)
    if collision:
        furniture_colliders.append((x, z, sx / 2, sz / 2))
    return e


def add_cylinder(x: float, y: float, z: float, scale, tint, rotation=(0, 0, 0), parent=None):
    return Entity(parent=parent if parent is not None else world_root, model="cylinder", position=(x, y, z),
                  scale=scale, color=palette_color(tint), rotation=rotation)


def make_wall_segment(axis: str, fixed: float, start: float, end: float, wall_tex, tint, metal_tex=None):
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
    Entity(parent=world_root, model="cube", position=pos, scale=scale,
           texture=wall_tex, texture_scale=(max(1, length / 2.8), WALL_H / 2.8),
           color=color.white)
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
        if rng.random() > .31:
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


def build_lamps(style: dict):
    global room_lights
    room_lights = []
    rng = random.Random(3210 + chapter_index)
    for room in range(GRID * GRID):
        if rng.random() < .58:
            cx, cz = room_center(room)
            room_lights.append((cx, cz, rng.random() * 10))
            Entity(parent=world_root, model="cylinder", position=(cx, WALL_H - .15, cz),
                   scale=(.72, .10, .72), color=hx("#262a2c"))
            Entity(parent=world_root, model="sphere", position=(cx, WALL_H - .38, cz),
                   scale=(.28, .12, .28), color=palette_color(style["glow"]))


def build_exit_gate(style: dict):
    cx, cz = room_center(GRID * GRID - 1)
    # Cikis terminali ve kemerli kapisi.
    add_box(cx, 1.95, cz - 4.25, 2.85, 3.9, .36, style["trim"], collision=False)
    add_box(cx, 1.88, cz - 4.00, 2.20, 3.45, .10, hx("#10151a"))
    for sx in (-1.12, 1.12):
        add_box(cx + sx, 1.8, cz - 4.20, .12, 3.55, .20, style["glow"])
    add_box(cx, 3.63, cz - 4.20, 2.35, .14, .20, style["glow"])
    add_box(cx, .88, cz - 5.15, 1.8, 1.6, .62, hx("#252c32"), collision=True)
    add_box(cx, 1.75, cz - 5.15, 1.7, .08, .58, style["trim"])
    for xoff in (-.48, 0, .48):
        Entity(parent=world_root, model="sphere", position=(cx + xoff, 1.85, cz - 5.18), scale=.11, color=palette_color(style["glow"]))
    return (cx, cz - 4.9)


def build_world():
    global world_root, wall_colliders, furniture_colliders, room_lights
    if world_root is not None:
        destroy(world_root)
    world_root = Entity()
    wall_colliders = []
    furniture_colliders = []
    style = CHAPTERS[chapter_index]
    wall_path, floor_path, metal_path = build_chapter_textures(chapter_index + 1, style)
    wall_tex = load_texture(wall_path)
    floor_tex = load_texture(floor_path)
    metal_tex = load_texture(metal_path)
    make_maze()

    # Zemin ve tavan: her oda farkli ton/rotasyonla kaplanir.
    for room in range(GRID * GRID):
        cx, cz = room_center(room)
        Entity(parent=world_root, model="plane", position=(cx, .015, cz), scale=(CELL, 1, CELL),
               texture=floor_tex, texture_scale=(2.5, 2.5), color=color.white)
        Entity(parent=world_root, model="plane", position=(cx, WALL_H, cz), rotation_x=180,
               scale=(CELL, 1, CELL), texture=wall_tex, texture_scale=(2.5, 2.5),
               color=hx("#77716a"), double_sided=True)
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
                make_wall_segment("z", fixed, start, gap - DOOR_W / 2, wall_tex, style["trim"], metal_tex)
                make_wall_segment("z", fixed, gap + DOOR_W / 2, end, wall_tex, style["trim"], metal_tex)
                # Kapinin iki yaninda dekoratif kolon ve ust lento.
                for dz in (-DOOR_W / 2, DOOR_W / 2):
                    add_box(fixed, WALL_H / 2, gap + dz, .48, WALL_H, .52, style["trim"], metal_tex)
                add_box(fixed, WALL_H - .16, gap, .52, .32, DOOR_W, style["trim"], metal_tex)
            else:
                make_wall_segment("z", fixed, start, end, wall_tex, style["trim"], metal_tex)

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
                make_wall_segment("x", fixed, start, gap - DOOR_W / 2, wall_tex, style["trim"], metal_tex)
                make_wall_segment("x", fixed, gap + DOOR_W / 2, end, wall_tex, style["trim"], metal_tex)
                for dx in (-DOOR_W / 2, DOOR_W / 2):
                    add_box(gap + dx, WALL_H / 2, fixed, .52, WALL_H, .48, style["trim"], metal_tex)
                add_box(gap, WALL_H - .16, fixed, DOOR_W, .32, .52, style["trim"], metal_tex)
            else:
                make_wall_segment("x", fixed, start, end, wall_tex, style["trim"], metal_tex)

    decorate_rooms(style, wall_tex, metal_tex)
    build_lamps(style)
    gate_pos = build_exit_gate(style)
    return gate_pos

# -----------------------------------------------------------------------------
# Koleksiyon nesneleri
# -----------------------------------------------------------------------------
def build_pickup_model(kind: str, pos: tuple[float, float], style: dict):
    x, z = pos
    root = Entity(parent=world_root, position=(x, .45, z))
    tint = style["glow"]
    if kind == "sigorta":
        Entity(parent=root, model="cylinder", scale=(.20, .54, .20), color=hx("#d4a34d"))
        Entity(parent=root, model="cube", scale=(.23, .12, .24), y=.20, color=hx("#30383a"))
        Entity(parent=root, model="cube", scale=(.06, .14, .06), y=.33, color=hx("#f3d58d"))
    elif kind == "disk":
        Entity(parent=root, model="cylinder", scale=(.48, .10, .48), color=hx("#a5b9b2"))
        Entity(parent=root, model="cylinder", scale=(.16, .12, .16), color=hx("#33474a"))
        Entity(parent=root, model="sphere", scale=.07, y=.08, color=palette_color(tint))
    elif kind == "role":
        Entity(parent=root, model="cube", scale=(.36, .46, .22), color=hx("#526b48"))
        Entity(parent=root, model="cube", scale=(.24, .08, .05), y=.08, z=-.13, color=palette_color(tint))
        Entity(parent=root, model="sphere", scale=.10, y=.24, z=-.14, color=hx("#d9ecad"))
        Entity(parent=root, model="cylinder", scale=(.035, .32, .035), y=.35, color=hx("#afb9a3"))
    elif kind == "vana":
        Entity(parent=root, model="cylinder", scale=(.17, .32, .17), color=hx("#87949b"))
        make_ring(0, .10, 0, .30, tint, parent=root, thickness=.045)
        for angle in range(0, 360, 90):
            a = math.radians(angle)
            Entity(parent=root, model="cube", scale=(.08, .34, .08),
                   position=(math.sin(a) * .23, .10, math.cos(a) * .23), rotation_y=angle, color=hx("#b8c2c2"))
    else:
        make_ring(0, 0, 0, .27, tint, parent=root, thickness=.055)
        Entity(parent=root, model="cylinder", scale=(.12, .28, .12), color=hx("#b69b65"))
        Entity(parent=root, model="cube", scale=(.08, .28, .08), rotation_z=45, color=hx("#e5ca8b"))
    ring = make_ring(x, .05, z, .32, tint, thickness=.055)
    glow = Entity(parent=world_root, model="sphere", position=(x, .45, z), scale=.72, color=color.rgba(tint[0], tint[1], tint[2], 28), unlit=True)
    return {"kind": kind, "root": root, "ring": ring, "glow": glow, "x": x, "z": z, "phase": random.random() * 6}


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
        battery = Entity(parent=world_root, position=(x, .38, z))
        Entity(parent=battery, model="cube", scale=(.26, .48, .20), color=hx("#4b956b"))
        Entity(parent=battery, model="cube", position=(0, .26, 0), scale=(.14, .07, .21), color=hx("#b5c5a1"))
        ring = make_ring(x, .05, z, .24, hx("#8fd4a2"), thickness=.045)
        pickups.append({"kind": "battery", "root": battery, "ring": ring, "glow": None, "x": x, "z": z, "phase": random.random() * 6})

# -----------------------------------------------------------------------------
# Dusman: prosedurel, detayli, animasyonlu siluet
# -----------------------------------------------------------------------------
class Stalker:
    def __init__(self, parent, style: dict):
        self.root = Entity(parent=parent, enabled=False)
        self.root.position = (CELL * 1.5, 0, CELL * 1.5)
        skin = hx("#%02x%02x%02x" % style["enemy"])
        dark = hx("#202329")
        pale = hx("#b8b4a0")
        self.hips = Entity(parent=self.root, position=(0, 1.12, 0))
        Entity(parent=self.hips, model="sphere", scale=(.48, .28, .32), color=dark)
        self.torso = Entity(parent=self.hips, position=(0, .37, 0))
        Entity(parent=self.torso, model="sphere", scale=(.54, .88, .34), color=skin)
        Entity(parent=self.torso, model="cube", scale=(.08, .78, .04), position=(0, -.02, -.19), color=dark)
        # Kaburga benzeri katmanlar: stilize, kan/grafik unsur yok.
        for i in range(5):
            Entity(parent=self.torso, model="cube", scale=(.43, .035, .035), position=(0, -.18 + i * .13, .17), color=pale)
        self.head = Entity(parent=self.torso, position=(0, .72, .02))
        Entity(parent=self.head, model="sphere", scale=(.42, .57, .40), color=skin)
        Entity(parent=self.head, model="sphere", scale=(.33, .20, .12), position=(0, -.13, .20), color=dark)
        eye_tint = style["enemy_eye"]
        for sx in (-.12, .12):
            Entity(parent=self.head, model="sphere", position=(sx, .06, .205), scale=(.075, .055, .045), color=palette_color(eye_tint), unlit=True)
        # Omuz cikintilari ve uzun kollar.
        self.arm_l = Entity(parent=self.torso, position=(-.32, .30, 0))
        self.arm_r = Entity(parent=self.torso, position=(.32, .30, 0))
        for arm, side in ((self.arm_l, -1), (self.arm_r, 1)):
            Entity(parent=arm, model="sphere", scale=(.19, .24, .18), color=dark)
            Entity(parent=arm, model="cube", position=(0, -.39, 0), scale=(.16, .72, .16), color=skin, rotation_z=side * 7)
            Entity(parent=arm, model="sphere", position=(0, -.78, .02), scale=(.14, .16, .14), color=dark)
            for finger in range(4):
                Entity(parent=arm, model="cube", position=((finger - 1.5) * .055, - .94, .04),
                       scale=(.035, .28, .035), rotation_z=(finger - 1.5) * 8, color=pale)
        self.leg_l = Entity(parent=self.hips, position=(-.15, -.12, 0))
        self.leg_r = Entity(parent=self.hips, position=(.15, -.12, 0))
        for leg in (self.leg_l, self.leg_r):
            Entity(parent=leg, model="cube", position=(0, -.36, 0), scale=(.18, .75, .19), color=skin)
            Entity(parent=leg, model="cube", position=(0, -.78, .10), scale=(.22, .18, .40), color=dark)
        for side in (-1, 1):
            Entity(parent=self.torso, model="cone", position=(side * .23, .55, -.04), scale=(.14, .36, .14), rotation_z=side * 28, color=dark)
        self.phase = 0.0
        self.state = "dormant"
        self.timer = 0.0
        self.lost = 0.0
        self.last_seen = (CELL / 2, CELL / 2)
        self.patrol_room = GRID * 2 + 2
        self.spawn_countdown = style["spawn"]
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


def spawn_enemy():
    global enemy_state
    if enemy is None or enemy.root.enabled:
        return
    player_room = room_at(player.x, player.z)
    dist = graph_distances(player_room)
    far_rooms = [r for r in range(GRID * GRID) if dist[r] >= 3]
    room = random.choice(far_rooms or list(range(1, GRID * GRID)))
    x, z = room_center(room)
    enemy.root.position = (x, 0, z)
    enemy.root.enabled = True
    enemy.state = "roam"
    enemy.patrol_room = random.randrange(GRID * GRID)
    enemy.timer = random.uniform(4.5, 7.5)
    enemy_state = "roam"
    show_toast("Uzakta bir hareket var. Sesini dusur.", 3.0)
    if sting_audio:
        sting_audio.play()

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
    hud_objective.text = objective_text()
    hud_hint.text = "WASD hareket  |  SHIFT kos  |  C egil  |  E etkilesim  |  F fener  |  R telsiz  |  TAB harita"
    hud_battery.text = f"FENER {int(battery_charge):02d}%"
    hud_battery.color = hx("#dfc98d") if battery_charge > 25 else hx("#dd7868")
    hud_progress.text = f"BOLUM {chapter_index + 1}/5"
    stamina_bar.scale_x = .27 * max(0, stamina / 100)
    stamina_bar.x = -.135 + .135 * max(0, stamina / 100)
    stamina_bar.color = hx("#b94c43") if exhausted else hx("#c6a35d")
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


def complete_chapter():
    global chapter_index, ending, chapter_intro
    if chapter_items_collected < CHAPTERS[chapter_index]["required"]:
        show_toast(CHAPTERS[chapter_index]["gate_text"], 3.4)
        return
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
    chapter_items_collected = 0
    battery_charge = 100.0 if chapter_index == 0 else min(100.0, battery_charge + 15)
    flashlight_on = False
    crouching = False
    stamina = 100.0
    exhausted = False
    chapter_clock = 0.0
    spawn_clock = 0.0
    caught_lock = False
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
    camera.position = (0, 1.68, 0)
    camera.rotation = (0, 0, 0)
    camera_pitch = 0
    scene.setFog(fog)
    fog.setColor(*(c / 255 for c in style["fog"]), 1.0)
    fog.setExpDensity(.020 + chapter_index * .0025)
    ambient.setColor(style["ambient"])
    spot.setColor((0, 0, 0, 1))
    update_hud()
    card_title.text = style["name"]
    card_body.text = style["story"]
    card_sub.text = f"{style['subtitle']}  |  Yakalanirsan bolum ilerlemen korunur."
    card_back.enabled = card_title.enabled = card_body.enabled = card_sub.enabled = True
    set_frozen(True)
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
    global caught_lock, battery_charge, stamina, exhausted, flashlight_on
    if caught_lock or frozen:
        return
    caught_lock = True
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
        for cx, cz, hw, hd in wall_colliders:
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
    same_floor = True
    visible = distance < enemy.sight * (0.55 if crouching else 1.0) and line_of_sight(enemy.root.x, enemy.root.z, player.x, player.z)
    hearing_radius = enemy.hearing * (0.22 if crouching else (1.35 if moving_fast else .55))
    heard = distance < hearing_radius and not crouching
    lit = flashlight_hits_enemy()

    if enemy.state == "roam":
        enemy.timer -= dt
        if visible or heard:
            enemy.state = "chase"
            enemy.timer = 24 + chapter_index * 4
            enemy.last_seen = (player.x, player.z)
            enemy.lost = 0
            if sting_audio:
                sting_audio.play()
            show_toast("Seni fark etti! Kose don, gorusunu kes.", 2.4)
        else:
            if enemy.timer <= 0 or math.hypot(enemy.root.x - room_center(enemy.patrol_room)[0], enemy.root.z - room_center(enemy.patrol_room)[1]) < 1.2:
                options = [r for r in range(GRID * GRID) if r != room_at(enemy.root.x, enemy.root.z)]
                enemy.patrol_room = random.choice(options)
                enemy.timer = random.uniform(5, 8)
            tx, tz = path_waypoint(enemy.root.x, enemy.root.z, *room_center(enemy.patrol_room))
            move_enemy_toward(tx, tz, enemy.speed * .62, dt)

    elif enemy.state == "chase":
        if visible or heard:
            enemy.last_seen = (player.x, player.z)
            enemy.lost = 0
        else:
            enemy.lost += dt
        tx, tz = enemy.last_seen
        wx, wz = path_waypoint(enemy.root.x, enemy.root.z, tx, tz)
        speed = enemy.speed
        if lit:
            speed *= enemy.light_slow
        if crouching and not visible:
            speed *= .78
        move_enemy_toward(wx, wz, speed, dt)
        enemy.timer -= dt
        if distance < 1.2 and (visible or enemy.lost < 1.5):
            caught_by_enemy()
            return
        if enemy.timer <= 0 or enemy.lost > 8 or distance > 37:
            enemy.state = "search"
            enemy.timer = 5.5

    elif enemy.state == "search":
        enemy.timer -= dt
        tx, tz = path_waypoint(enemy.root.x, enemy.root.z, *enemy.last_seen)
        move_enemy_toward(tx, tz, enemy.speed * .72, dt)
        if visible or heard:
            enemy.state = "chase"
            enemy.timer = 22 + chapter_index * 4
            enemy.last_seen = (player.x, player.z)
        elif enemy.timer <= 0:
            enemy.state = "roam"
            enemy.timer = 4
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
    gate_x, gate_z = (GRID - .5) * CELL, (GRID - .5) * CELL - 4.9
    dist_gate = math.hypot(gate_x - player.x, gate_z - player.z)
    if dist_gate < 3.2 and dist_gate < best + .5:
        if chapter_items_collected >= style["required"]:
            hud_prompt.text = "[E] Cikis terminalini etkinlestir"
            near_action = complete_chapter
        else:
            hud_prompt.text = f"Cikis kilitli: {chapter_items_collected}/{style['required']} {style['item_name']}"
            near_action = None


def input(key):
    global flashlight_on, crouching, show_map, camera_pitch
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
                f"Pil: {int(battery_charge)}%\n\n"
                "Harita prosedurel.\nR: telsizden hedef yonu."
            )
    elif key == "f11":
        window.fullscreen = not window.fullscreen


def update():
    global camera_pitch, battery_charge, flashlight_on, stamina, exhausted
    global chapter_clock, toast_timer, walk_phase, step_counter, noise_level

    dt = min(time.dt, .04)
    if frozen:
        if fade.alpha > 0 and not caught_lock and not ending:
            fade.alpha = max(0, fade.alpha - dt * .9)
        return
    chapter_clock += dt

    # Fare/kamera.
    mx, my = mouse.velocity
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
    distance = distance_to_enemy()
    threat = max(0, 1 - distance / 25) if enemy and enemy.root.enabled else 0
    if threat > .35 and random.random() < dt * (1.2 + threat * 1.8):
        if pulse_audio:
            pulse_audio.volume = .12 + threat * .45
            pulse_audio.pitch = .82 + threat * .42
            pulse_audio.play()

    # Yakindaki oda isiklari; uzak odalardaki isiklar kapali kalir.
    nearest_lamps = sorted(room_lights, key=lambda p: (p[0] - player.x) ** 2 + (p[1] - player.z) ** 2)[:6]
    for i, (node, light) in enumerate(light_pool):
        if i < len(nearest_lamps):
            lx, lz, phase = nearest_lamps[i]
            d2 = (lx - player.x) ** 2 + (lz - player.z) ** 2
            if d2 < 440:
                flicker = .72 if math.sin(chapter_clock * (23 + i) + phase) > .985 else 1.0
                if threat > .45 and random.random() < dt * .8:
                    flicker *= .12
                node.setPos(lx, WALL_H - .65, lz)
                light.setColor((1.15 * flicker, .78 * flicker, .48 * flicker, 1))
                scene.setLight(node)
            else:
                light.setColor((0, 0, 0, 1))
                scene.clearLight(node)
        else:
            light.setColor((0, 0, 0, 1))
            scene.clearLight(node)

    # Nesnelerin hafif donmesi/parlamasi.
    for item in pickups:
        item["phase"] += dt * 2.1
        item["root"].y = .46 + math.sin(item["phase"]) * .10
        item["root"].rotation_y += dt * 35
        item["ring"].rotation_y += dt * 32
        scale = .62 + math.sin(item["phase"] * 1.7) * .05
        item["ring"].scale = scale

    update_interactions()
    update_hud()
    toast_timer -= dt
    if toast_timer <= 0:
        hud_toast.text = ""

# -----------------------------------------------------------------------------
# Baslat
# -----------------------------------------------------------------------------
try:
    start_chapter()
    app.run()
except Exception:
    print("\nOYUNDA BIR HATA OLUSTU:\n")
    traceback.print_exc()
    with open("echo_hata.txt", "w", encoding="utf-8") as error_file:
        traceback.print_exc(file=error_file)
    sys.stdin.readline()