# 產生《糟糕島物語》所有像素素材（16x16 繪製，輸出放大 3 倍為 48x48 PNG）
# 用法：python make_assets.py ../KomicaRPG/wwwroot/img
# 全部是程式畫的原創素材，可自由使用、修改。
import os
import random
import sys
from PIL import Image

OUT = sys.argv[1] if len(sys.argv) > 1 else "img"
SCALE = 3
os.makedirs(OUT, exist_ok=True)

PAL = {
    "k": "#1a1420", "e": "#ffffff", "i": "#2a2a2a",
    "g": "#5fa845", "G": "#4a8a36", "L": "#4caf50", "l": "#2e7d32", "t": "#7a4a22",
    "p": "#d8b878", "P": "#c4a060", "q": "#e8cc90",
    "w": "#3a7bd5", "W": "#8fc0f5",
    "r": "#b8433a", "R": "#8a2f28",
    "b": "#e8d8b0", "B": "#b89868", "d": "#6b3e1e",
    "s": "#8a8a92", "S": "#5a5a64", "f": "#6a5a4a", "F": "#4a3e34",
    "y": "#ffd54a", "o": "#ff9a2a",
    "h": "#f2c79a", "n": "#5a3a1a", "u": "#3a5ad5", "U": "#26367a",
    "x": "#e0e0e0", "v": "#8a4ac8", "V": "#3a1a5a", "m": "#ff3040",
    "c": "#4ad0a0", "C": "#2a9070",
    "a": "#9a9aa8", "A": "#6a6a78",
    "z": "#bfefff", "Z": "#70b8e0", "j": "#d8f4ff",
    "1": "#e8d49a", "2": "#d0b878", "3": "#4a3a5a", "4": "#e4e4ec", "5": "#c0c0cc",
    "6": "#7a8494", "7": "#4a5262", "8": "#10141c", "9": "#3ae08a", "0": "#050508",
    "!": "#5ae0f0", "@": "#c0faff", "#": "#e0501a", "$": "#ffb020",
    "%": "#7c7898", "&": "#66627e", "*": "#ff8ac0", "+": "#2ad0d0",
    "-": "#1e4a3a", ":": "#2e6a4a", ";": "#9a2a3a", "<": "#e0b040", ">": "#9ab0d0",
    "?": "#f6eed8", "/": "#3a3040", "=": "#c8b0e8", "^": "#b0f0a0",
}


def rgba(c):
    h = PAL[c]
    return tuple(int(h[i:i + 2], 16) for i in (1, 3, 5)) + (255,)


def blank():
    return Image.new("RGBA", (16, 16), (0, 0, 0, 0))


def solid(c):
    return Image.new("RGBA", (16, 16), rgba(c))


def draw(rows, base=None, sub=None):
    img = base.copy() if base else blank()
    for y, row in enumerate(rows[:16]):
        row = row.ljust(16, ".")[:16]
        for x, ch in enumerate(row):
            if sub and ch in sub:
                ch = sub[ch]
            if ch == ".":
                continue
            img.putpixel((x, y), rgba(ch))
    return img


def speckle(img, c, density, seed):
    r = random.Random(seed)
    for y in range(16):
        for x in range(16):
            if r.random() < density:
                img.putpixel((x, y), rgba(c))
    return img


def rect(img, x0, y0, x1, y1, c):
    for y in range(max(0, y0), min(15, y1) + 1):
        for x in range(max(0, x0), min(15, x1) + 1):
            img.putpixel((x, y), rgba(c))


def over(base, top):
    out = base.copy()
    out.alpha_composite(top)
    return out


def save(img, name):
    img.resize((16 * SCALE, 16 * SCALE), Image.NEAREST).save(os.path.join(OUT, name + ".png"))


# =====================================================================
# 地形
# =====================================================================
grass = speckle(solid("g"), "G", 0.12, 1)
for (x, y) in [(3, 4), (11, 10), (7, 13)]:
    grass.putpixel((x, y), rgba("L"))
    grass.putpixel((x + 1, y - 1), rgba("L"))
save(grass, "grass")

flower = grass.copy()
for (x, y, c) in [(3, 3, "y"), (11, 6, "e"), (6, 11, "r"), (13, 13, "y")]:
    for dx, dy in [(0, -1), (0, 1), (-1, 0), (1, 0)]:
        flower.putpixel((x + dx, y + dy), rgba(c))
    flower.putpixel((x, y), rgba("o"))
save(flower, "flower")

path = speckle(solid("p"), "P", 0.14, 2)
speckle(path, "q", 0.06, 3)
save(path, "path")

water = solid("w")
for y, off in [(3, 1), (8, 6), (13, 3)]:
    for x in range(off, off + 5):
        water.putpixel((x % 16, y), rgba("W"))
    for x in range(off + 8, off + 11):
        water.putpixel((x % 16, y + 1), rgba("W"))
save(water, "water")

TREE = [
    "......kkkk......",
    "....kkLLLLkk....",
    "...kLLLlLLLLk...",
    "..kLLlLLLLlLLk..",
    "..kLLLLLlLLLLk..",
    ".kLlLLLLLLLlLLk.",
    ".kLLLlLLlLLLLLk.",
    ".klLLLLLLLLLlLk.",
    "..klLLlLLLLLlk..",
    "..kllllllllllk..",
    "...kkkllllkkk...",
    "......kttk......",
    "......kttk......",
    "......kttk......",
    ".....kttttk.....",
    "................",
]
save(draw(TREE, base=grass), "tree")

roof = solid("r")
for y in range(16):
    for x in range(16):
        if y % 4 == 3 or (x + (y // 4) * 2) % 4 == 0:
            roof.putpixel((x, y), rgba("R"))
save(roof, "roof")
roof_blue = solid("u")
for y in range(16):
    for x in range(16):
        if y % 4 == 3 or (x + (y // 4) * 2) % 4 == 0:
            roof_blue.putpixel((x, y), rgba("U"))
save(roof_blue, "roof_blue")

wall = solid("b")
for y in range(16):
    for x in range(0, 16, 4):
        wall.putpixel((x, y), rgba("B"))
rect(wall, 0, 15, 15, 15, "B")
save(wall, "wall")

window = wall.copy()
rect(window, 3, 3, 12, 11, "k")
rect(window, 4, 4, 11, 10, "W")
rect(window, 7, 4, 8, 10, "k")
rect(window, 4, 7, 11, 7, "k")
rect(window, 4, 4, 5, 5, "e")
save(window, "window")

door = wall.copy()
rect(door, 3, 2, 12, 15, "k")
rect(door, 4, 3, 11, 15, "d")
rect(door, 7, 3, 8, 15, "t")
door.putpixel((10, 9), rgba("y"))
save(door, "door")

poster = wall.copy()
rect(poster, 3, 2, 12, 13, "k")
rect(poster, 4, 3, 11, 12, "*")
rect(poster, 4, 9, 11, 12, "+")
rect(poster, 6, 4, 9, 7, "h")
rect(poster, 6, 4, 9, 4, "y")
poster.putpixel((7, 6), rgba("k"))
poster.putpixel((9, 6), rgba("k"))
save(poster, "poster")

stone = solid("s")
for y in range(16):
    if y % 4 == 3:
        rect(stone, 0, y, 15, y, "S")
    else:
        off = 0 if (y // 4) % 2 == 0 else 4
        for x in range(off, 16, 8):
            stone.putpixel((x, y), rgba("S"))
save(stone, "stone")

floor = solid("f")
rect(floor, 0, 7, 15, 7, "F")
rect(floor, 0, 15, 15, 15, "F")
rect(floor, 7, 0, 7, 6, "F")
rect(floor, 15, 8, 15, 14, "F")
speckle(floor, "F", 0.04, 9)
save(floor, "floor")

towerdoor = stone.copy()
rect(towerdoor, 4, 3, 11, 15, "k")
rect(towerdoor, 5, 2, 10, 2, "k")
rect(towerdoor, 5, 4, 10, 15, "i")
save(towerdoor, "towerdoor")

stairs = floor.copy()
for i, y in enumerate(range(1, 13, 3)):
    rect(stairs, 2, y, 13, y + 1, "s" if i % 2 == 0 else "a")
    rect(stairs, 2, y + 2, 13, y + 2, "S")
save(stairs, "stairs")

sand = speckle(solid("1"), "2", 0.13, 11)
speckle(sand, "?", 0.04, 12)
save(sand, "sand")

bridge = water.copy()
for y in range(0, 16, 4):
    rect(bridge, 1, y, 14, y + 2, "t")
    rect(bridge, 1, y + 3, 14, y + 3, "d")
rect(bridge, 0, 0, 0, 15, "d")
rect(bridge, 15, 0, 15, 15, "d")
save(bridge, "bridge")

save(draw([
    "................",
    "................",
    "..........kk....",
    ".........kdtk...",
    "........kdtdk...",
    ".......kdtdk....",
    "..kkk.kdtdtk....",
    ".kdttkdtdtdk....",
    ".kdtdtdtdtk.kk..",
    "..kdtdtdtdkkdtk.",
    "..kkdtdtdtdtdtk.",
    "...kkkkkdtdtdk..",
    "........kkkkk...",
    "................",
    "................",
    "................",
], base=sand), "wreck")

ROCK = [
    "................",
    "................",
    "................",
    ".....kkkkk......",
    "...kkaaaaakk....",
    "..kaaxaaaaaak...",
    "..kaxaaaaaaAk...",
    ".kaaaaaaaaAAAk..",
    ".kaaaaaaaAAAAk..",
    ".kAaaaaAAAAAAk..",
    ".kAAAAAAAAAAAk..",
    "..kkAAAAAAAkk...",
    "....kkkkkkk.....",
    "................",
    "................",
    "................",
]
save(draw(ROCK, base=grass), "rock")
save(draw(ROCK, base=sand), "rock_sand")

fence = grass.copy()
rect(fence, 0, 5, 15, 6, "t")
rect(fence, 0, 10, 15, 11, "t")
for x in (2, 13):
    rect(fence, x, 3, x + 1, 14, "d")
save(fence, "fence")

mist = speckle(solid("%"), "&", 0.18, 21)
speckle(mist, "=", 0.03, 22)
save(mist, "mist")
save(draw(TREE, base=mist, sub={"L": ":", "l": "-"}), "tree_dark")

dock = solid("t")
for x in range(0, 16, 4):
    rect(dock, x, 0, x, 15, "d")
for y, x in [(3, 1), (11, 2), (6, 5), (13, 9), (2, 10), (9, 13)]:
    dock.putpixel((x, y), rgba("n"))
save(dock, "dock")
save(draw([
    "................",
    "....kkkkkkk.....",
    "...kdtttttdk....",
    "...kkkkkkkkk....",
    "..kdttttttttdk..",
    "..kdttttttttdk..",
    "..kkkkkkkkkkkk..",
    "..kdttttttttdk..",
    "..kdttttttttdk..",
    "..kkkkkkkkkkkk..",
    "..kdttttttttdk..",
    "...kdttttttdk...",
    "....kkkkkkkk....",
    "................",
    "................",
    "................",
], base=dock), "barrel")

carpet = solid(";")
rect(carpet, 0, 0, 15, 0, "<")
rect(carpet, 0, 15, 15, 15, "<")
for x in range(2, 16, 4):
    carpet.putpixel((x, 7), rgba("<"))
    carpet.putpixel((x + 1, 8), rgba("<"))
save(carpet, "carpet")

marble = solid("4")
r = random.Random(31)
for _ in range(3):
    x, y = r.randint(0, 15), r.randint(0, 15)
    for _ in range(8):
        marble.putpixel((x % 16, y % 16), rgba("5"))
        x += 1
        y += r.choice([0, 1])
rect(marble, 0, 15, 15, 15, "5")
rect(marble, 15, 0, 15, 15, "5")
save(marble, "marble")

mwall = solid("3")
rect(mwall, 0, 14, 15, 15, "/")
frame = mwall.copy()
rect(frame, 2, 2, 13, 12, "<")
rect(frame, 3, 3, 12, 11, "W")
rect(frame, 3, 8, 12, 11, "L")
rect(frame, 9, 4, 11, 6, "y")
rect(frame, 5, 6, 7, 8, "l")
save(frame, "frame")
frame404 = mwall.copy()
rect(frame404, 2, 2, 13, 12, "A")
rect(frame404, 3, 3, 12, 11, "i")
for i in range(8):
    frame404.putpixel((4 + i, 4 + i // 1 if 4 + i <= 11 else 11), rgba("m"))
    frame404.putpixel((11 - i, 4 + i), rgba("m"))
save(frame404, "frame404")
save(draw([
    "...kkkkkkkkkk...",
    "...k44444444k...",
    "....k555555k....",
    "....k445544k....",
    "....k445544k....",
    "....k445544k....",
    "....k445544k....",
    "....k445544k....",
    "....k445544k....",
    "....k445544k....",
    "....k445544k....",
    "....k445544k....",
    "....k555555k....",
    "...k44444444k...",
    "...kkkkkkkkkk...",
    "................",
], base=marble), "pillar")

metal = solid("6")
rect(metal, 0, 7, 15, 7, "7")
rect(metal, 7, 0, 7, 15, "7")
for (x, y) in [(2, 2), (12, 2), (2, 12), (12, 12)]:
    metal.putpixel((x, y), rgba(">"))
save(metal, "metal")
mw = solid("7")
rect(mw, 0, 0, 15, 1, "6")
rect(mw, 0, 8, 15, 8, "6")
for x in range(1, 16, 5):
    mw.putpixel((x, 4), rgba(">"))
    mw.putpixel((x + 2, 12), rgba(">"))
save(mw, "metal_wall")
banner = mw.copy()
rect(banner, 4, 1, 11, 14, "r")
rect(banner, 4, 14, 5, 15, "r")
rect(banner, 10, 14, 11, 15, "r")
rect(banner, 5, 5, 10, 9, "e")
rect(banner, 6, 7, 9, 7, "k")
save(banner, "banner")

circuit = solid("8")
for (x0, y0, x1, y1) in [(0, 3, 6, 3), (6, 3, 6, 10), (6, 10, 15, 10), (10, 0, 10, 6), (2, 12, 2, 15), (12, 13, 15, 13)]:
    rect(circuit, x0, y0, x1, y1, "9")
for (x, y) in [(6, 3), (6, 10), (10, 6), (2, 12)]:
    rect(circuit, x - 1, y - 1, x + 1, y + 1, "^")
save(circuit, "circuit")
void = speckle(solid("0"), "/", 0.05, 41)
save(void, "void")
datawall = solid("U")
r = random.Random(51)
for y in range(1, 16, 3):
    x = 0
    while x < 16:
        ln = r.randint(1, 4)
        if r.random() < 0.6:
            rect(datawall, x, y, x + ln - 1, y, r.choice(["!", "Z", "9"]))
        x += ln + 1
save(datawall, "datawall")
core = solid("U")
rect(core, 0, 0, 15, 0, "Z")
rect(core, 0, 0, 0, 15, "Z")
rect(core, 7, 4, 8, 11, "!")
rect(core, 4, 7, 11, 8, "!")
rect(core, 7, 7, 8, 8, "@")
save(core, "core")
lava = solid("#")
r = random.Random(61)
for _ in range(14):
    x, y = r.randint(0, 14), r.randint(0, 14)
    rect(lava, x, y, x + 1, y, "$")
save(lava, "lava")
shelf = solid("d")
for y in (1, 6, 11):
    rect(shelf, 1, y, 14, y + 3, "n")
    xx = 1
    for c in "rUyCvroU":
        rect(shelf, xx, y, xx, y + 3, c)
        xx += 2
    rect(shelf, 0, y + 4, 15, y + 4, "t")
save(shelf, "shelf")
counter = floor.copy()
rect(counter, 0, 4, 15, 15, "d")
rect(counter, 0, 4, 15, 6, "t")
rect(counter, 0, 7, 15, 7, "k")
save(counter, "counter")

# =====================================================================
# 人物（頭部模板 × 身體 × 配色）
# =====================================================================
HEADS = {
    "short": [
        "................",
        "......kkkk......",
        ".....kHHHHk.....",
        "....kHHHHHHk....",
        "....kHhhhhHk....",
        "....khkhhkhk....",
        "....khhhhhhk....",
        ".....kkhhkk.....",
    ],
    "back": [
        "................",
        "......kkkk......",
        ".....kHHHHk.....",
        "....kHHHHHHk....",
        "....kHHHHHHk....",
        "....kHHHHHHk....",
        "....kHHHHHHk....",
        ".....kkhhkk.....",
    ],
    "side": [  # 側臉（朝右）：頭髮在後腦，臉和眼睛在右邊
        "................",
        "......kkkk......",
        ".....kHHHHk.....",
        "....kHHHHHHk....",
        "....kHHHHhhk....",
        "....kHHHhkhhk...",
        "....kHHhhhhk....",
        ".....kHhhhk.....",
    ],
    "long": [
        "................",
        "......kkkk......",
        ".....kHHHHk.....",
        "....kHHHHHHk....",
        "...kHHhhhhHHk...",
        "...kHhkhhkhHk...",
        "...kHhhhhhhHk...",
        "...kHkkhhkkHk...",
    ],
    "witch": [
        ".......kk.......",
        "......kAAk......",
        ".....kAAAAk.....",
        "..kkkAAyAAAkkk..",
        ".kAAAAAAAAAAAAk.",
        "..kkHhkhhkhHkk..",
        "...kHhhhhhhHk...",
        "...kHkkhhkkHk...",
    ],
    "helmet": [
        ".......kk.......",
        "......kAAk......",
        ".....kHHHHk.....",
        "....kHHHHHHk....",
        "....kHkkkkHk....",
        "....kHhkkhHk....",
        "....kHhhhhHk....",
        ".....kkHHkk.....",
    ],
    "jester": [
        "..k..........k..",
        ".kAk........kHk.",
        ".kAAk.kkkk.kHHk.",
        "..kAAkAAHHkHHk..",
        "...kAAAAHHHHk...",
        "....khkhhkhk....",
        "....khhhhhhk....",
        ".....kkhhkk.....",
    ],
    "hood": [
        "................",
        "......kkkk......",
        ".....kHHHHk.....",
        "....kHHHHHHk....",
        "...kHHkkkkHHk...",
        "...kHkhkkhkHk...",
        "...kHkhhhhkHk...",
        "...kHHkkkkHHk...",
    ],
    "cap": [
        "................",
        "......kkkk......",
        ".....kAAAAk.....",
        "....kAAAAAAkk...",
        "....kHhhhhHAAk..",
        "....khkhhkhkk...",
        "....khhhhhhk....",
        ".....kkhhkk.....",
    ],
    "faceless": [
        "................",
        "......kkkk......",
        ".....kiiiik.....",
        "....kiiiiiik....",
        "....kiiiiiik....",
        "....kimiimik....",
        "....kiiiiiik....",
        ".....kkiikk.....",
    ],
    "bald": [
        "................",
        "......kkkk......",
        ".....khhhhk.....",
        "....khhhhhhk....",
        "....kHhhhhHk....",
        "....khkhhkhk....",
        "....kxhhhhxk....",
        ".....kxxxxk.....",
    ],
}
BODY = [
    "....kCCCCCCk....",
    "...khCCCCCChk...",
    "...khCCyyCChk...",
    "....kCCCCCCk....",
    "....kPPkkPPk....",
    "....kPPkkPPk....",
    "....kkk..kkk....",
    "................",
]
BODY_ROBE = [
    "....kCCCCCCk....",
    "...khCCCCCChk...",
    "...khCCyyCChk...",
    "...kCCCCCCCCk...",
    "...kCCCCCCCCk...",
    "...kPCCCCCCPk...",
    "...kkkkkkkkkk...",
    "................",
]
BODY_TAG = [
    "....kCCCCCCk....",
    "...khCeeeeChk...",
    "...khCemmeChk...",
    "....kCeeeeCk....",
    "....kPPkkPPk....",
    "....kPPkkPPk....",
    "....kkk..kkk....",
    "................",
]

BODY_WALK1 = [  # 正面：右腳（畫面左側）著地、左腳抬起
    "....kCCCCCCk....",
    "...khCCCCCChk...",
    "...khCCyyCChk...",
    "....kCCCCCCk....",
    "....kPPkkPPk....",
    "....kPPk.kkk....",
    "....kkk.........",
    "................",
]
BODY_WALK2 = [  # 正面：另一隻腳抬起
    "....kCCCCCCk....",
    "...khCCCCCChk...",
    "...khCCyyCChk...",
    "....kCCCCCCk....",
    "....kPPkkPPk....",
    "....kkk.kPPk....",
    ".........kkk....",
    "................",
]
BODY_BACK = [
    "....kCCCCCCk....",
    "...khCCCCCChk...",
    "...khCCCCCChk...",
    "....kCCCCCCk....",
    "....kPPkkPPk....",
    "....kPPkkPPk....",
    "....kkk..kkk....",
    "................",
]
BODY_BACK_WALK1 = [
    "....kCCCCCCk....",
    "...khCCCCCChk...",
    "...khCCCCCChk...",
    "....kCCCCCCk....",
    "....kPPkkPPk....",
    "....kPPk.kkk....",
    "....kkk.........",
    "................",
]
BODY_BACK_WALK2 = [
    "....kCCCCCCk....",
    "...khCCCCCChk...",
    "...khCCCCCChk...",
    "....kCCCCCCk....",
    "....kPPkkPPk....",
    "....kkk.kPPk....",
    ".........kkk....",
    "................",
]
BODY_SIDE = [  # 側面（朝右）站立
    ".....kCCCCCk....",
    ".....kCCCCCk....",
    ".....kCCChCk....",
    ".....kCCCCCk....",
    ".....kPPPPPk....",
    ".....kPPPPPk....",
    ".....kkkkkkkk...",
    "................",
]
BODY_SIDE_WALK1 = [  # 側面跨步：前手往前、後手往後
    ".....kCCCCCk....",
    "....khCCCCCk....",
    ".....kCCCCChk...",
    ".....kCCCCCk....",
    "....kPPPkPPPk...",
    "...kPPk...kPPk..",
    "...kkk.....kkkk.",
    "................",
]
BODY_SIDE_WALK2 = [  # 側面跨步：另一邊的手在前
    ".....kCCCCCk....",
    ".....kCCCCChk...",
    "....khCCCCCk....",
    ".....kCCCCCk....",
    "....kPPPkPPPk...",
    "...kPPk...kPPk..",
    "...kkk.....kkkk.",
    "................",
]


def person(name, head, pal, body=BODY, extra=None):
    rows = HEADS[head] + body
    if extra:
        rows = list(rows)
        for i, rr in extra.items():
            rows[i] = rr
    save(draw(rows, sub=pal), name)


# 主角與隊友
HERO = {"H": "n", "C": "u", "P": "U"}
person("hero", "short", HERO)
person("hero_back", "back", HERO, BODY_BACK)
# 主角的走路動畫：正面、背面各兩格（左右腳輪流抬起），側面（朝右，朝左時左右翻轉）一格站立＋兩格跨步
person("hero_d1", "short", HERO, BODY_WALK1)
person("hero_d2", "short", HERO, BODY_WALK2)
person("hero_u1", "back", HERO, BODY_BACK_WALK1)
person("hero_u2", "back", HERO, BODY_BACK_WALK2)
person("hero_side", "side", HERO, BODY_SIDE)
person("hero_s1", "side", HERO, BODY_SIDE_WALK1)
person("hero_s2", "side", HERO, BODY_SIDE_WALK2)
person("sage", "witch", {"H": "x", "A": "v", "C": "V", "P": "v"}, BODY_ROBE)
person("del", "helmet", {"H": "a", "A": "u", "C": "s", "P": "S", "h": "h"})
person("gag", "jester", {"H": "y", "A": "r", "C": "o", "P": "u"})
person("snow", "long", {"H": "x", "C": "i", "P": "i", "y": "r"}, BODY_ROBE)
# NPC
person("elder", "bald", {"H": "x", "C": "v", "P": "V"}, BODY_ROBE)
person("nurse", "long", {"H": "*", "C": "e", "P": "e", "y": "*"}, BODY_ROBE)
person("clerk", "cap", {"H": "n", "A": "C", "C": "c", "P": "U"})
person("smith", "short", {"H": "i", "C": "d", "P": "i"})
person("fatguy", "short", {"H": "i", "C": "r", "P": "U"}, extra={9: "..khCCCCCCCChk..", 10: "..khCCyyyyCChk.."})
person("kid", "short", {"H": "y", "C": "o", "P": "U"})
person("catlady", "long", {"H": "o", "C": "L", "P": "l"}, BODY_ROBE)
person("oldman", "bald", {"H": "a", "C": "B", "P": "d"})
person("wguy", "short", {"H": "C", "C": "y", "P": "U"})
person("guardian", "hood", {"H": "<", "C": "<", "P": "d"}, BODY_ROBE)
person("streamer", "cap", {"H": "v", "A": "m", "C": "i", "P": "U"})
person("fansub", "long", {"H": "n", "C": "+", "P": "U"})
person("otaku", "short", {"H": "i", "C": "*", "P": "U"})
person("xd", "short", {"H": "y", "C": "W", "P": "s"})
person("fisher", "hood", {"H": "C", "C": "C", "P": "d"})
person("sailor", "cap", {"H": "n", "A": "e", "C": "u", "P": "e"})
person("artist", "long", {"H": "V", "C": "y", "P": "U"})
person("villager", "short", {"H": "n", "C": "L", "P": "d"})
person("villager2", "long", {"H": "t", "C": "r", "P": "d"}, BODY_ROBE)
person("tagged", "short", {"H": "n", "C": "a", "P": "A"}, BODY_TAG)
person("tagged2", "long", {"H": "t", "C": "a", "P": "A"}, BODY_TAG)
person("soldier", "helmet", {"H": "e", "A": "m", "C": "e", "P": "a"}, BODY_TAG)
person("deserter", "helmet", {"H": "a", "A": "a", "C": "a", "P": "S"})
person("general", "helmet", {"H": "<", "A": "m", "C": "<", "P": "i"}, BODY_TAG)
person("troll", "hood", {"H": "l", "C": "C", "P": "d", "y": "y"}, BODY_ROBE)
person("faceless_man", "faceless", {"C": "i", "P": "i", "h": "i", "y": "m"})

# 貓、物件
save(draw([
    "................", "................", "................", "................",
    "....k...k.......",
    "...kok.kok......",
    "...koookook.....",
    "...kokookok.....",
    "...kooo*ook.....",
    "....kooook...kk.",
    "...kooooook.kok.",
    "...koeeooook.ok.",
    "...koeeoooookok.",
    "...kooooooooko..",
    "....kkkkkkkkk...",
    "................",
]), "cat")

save(draw([
    "................",
    ".......k........",
    "......kzk.......",
    ".....kzjzk......",
    "....kzjjzZk.....",
    "....kzjzzZk.....",
    "...kzjzzzZZk....",
    "...kzzzzZZZk....",
    "....kzzZZZk.....",
    "....kzzZZZk.....",
    ".....kzZZk......",
    "......kZk.......",
    ".....kSSSk......",
    "....kSSSSSk.....",
    "....kkkkkkk.....",
    "................",
]), "crystal")

save(draw([
    "................",
    ".kkkkkkkkkkkkkk.",
    ".kppppppppppppk.",
    ".kp???pp????ppk.",
    ".kp?a?pp?aa?ppk.",
    ".kp???pp????ppk.",
    ".kp?a?pp?aa?ppk.",
    ".kp???pp????ppk.",
    ".kppppppppppppk.",
    ".kpp????p???ppk.",
    ".kpp?aa?p?a?ppk.",
    ".kpp????p???ppk.",
    ".kppppppppppppk.",
    ".kkkkkkkkkkkkkk.",
    "...kdk....kdk...",
    "...kkk....kkk...",
], sub={"p": "P"}), "board")

save(draw([
    "................", "................", "................",
    "..kkkkkkkkkkkk..",
    "..kttttttttttk..",
    "..ktkkkkktkktk..",
    "..kttttttttttk..",
    "..ktkkktkkkktk..",
    "..kttttttttttk..",
    "..kkkkkkkkkkkk..",
    "......ktk.......",
    "......ktk.......",
    "......ktk.......",
    ".....kkkkk......",
    "................", "................",
]), "sign")

chest = blank()
rect(chest, 2, 5, 13, 14, "k")
rect(chest, 3, 6, 12, 13, "t")
rect(chest, 3, 8, 12, 8, "k")
rect(chest, 7, 7, 8, 10, "y")
save(chest, "chest")
chest_open = blank()
rect(chest_open, 2, 2, 13, 6, "k")
rect(chest_open, 3, 3, 12, 5, "d")
rect(chest_open, 2, 7, 13, 14, "k")
rect(chest_open, 3, 8, 12, 13, "t")
rect(chest_open, 4, 8, 11, 9, "i")
save(chest_open, "chest_open")

seal = solid("7")
rect(seal, 1, 1, 14, 14, "k")
rect(seal, 2, 2, 13, 13, "6")
rect(seal, 7, 2, 8, 13, "7")
rect(seal, 5, 6, 10, 10, "<")
rect(seal, 7, 7, 8, 9, "k")
save(seal, "seal")
mseal = mwall.copy()
rect(mseal, 2, 1, 13, 15, "k")
rect(mseal, 3, 2, 12, 15, "/")
for i, c in enumerate("Q"):
    pass
rect(mseal, 4, 5, 5, 9, "m")
rect(mseal, 7, 5, 8, 9, "m")
rect(mseal, 10, 5, 11, 9, "m")
save(mseal, "seal404")

# =====================================================================
# 怪物
# =====================================================================
WORM = [
    "................", "................", "................", "................",
    "..........kkkk..",
    ".........kGGGGk.",
    ".........kGkGkk.",
    "....kkk..kGGGGk.",
    "...kGGGkkkGGGk..",
    "..kGgGGGkGgGGk..",
    ".kGGGGGGGGGGk...",
    ".kGgGGgGGgGk....",
    ".kGGGGGGGGGk....",
    "..kkkkkkkkk.....",
    "................", "................",
]
save(draw(WORM), "worm")
save(draw(WORM, sub={"G": "v", "g": "="}), "worm_king")
save(draw(WORM, sub={"G": "#", "g": "$"}), "worm_fire")

SLIME = [
    "................", "................", "................", "................", "................",
    ".......kk.......",
    "......kcck......",
    ".....kcceck.....",
    "....kcccccck....",
    "...kcckcckcck...",
    "...kcccccccck...",
    "..kcccckkcccck..",
    "..kCcccccccCk...",
    "...kCCCCCCCCk...",
    "....kkkkkkkk....",
    "................",
]
save(draw(SLIME, sub={"c": "Z", "C": "w"}), "slime_blue")
save(draw(SLIME, sub={"c": "*", "C": "v"}), "slime_paint")
save(draw(SLIME, sub={"c": "/", "C": "0", "e": "m"}), "slime_dark")

save(draw([
    "................", "................", "................",
    ".kk........kk...",
    "krrk......krrk..",
    "krk.......krk...",
    ".krk.kkkk.krk...",
    "..kkkrrrrkkk....",
    "..krrekkerrk....",
    ".krrrrrrrrrrk...",
    "krRrrrrrrrrRk...",
    "krRRRRRRRRRRk...",
    ".kRk.kRk.kRk....",
    "..k...k...k.....",
    "................", "................",
]), "crab")

save(draw([
    "................", "................",
    ".....kkkkkk.....",
    "....kWWWWWWk....",
    "...kWeWWWWWWk...",
    "...kWWWWWWWWk...",
    "...kWkWWWWkWk...",
    "...kWWWWWWWWk...",
    "...kkWkWkWkkk...",
    "....kW.W.Wk.....",
    "....W.kW.kW.....",
    "...kW..W..W.....",
    "...W..kW..kW....",
    "....W..W...W....",
    "................", "................",
]), "jelly")

save(draw([
    "................",
    "......kkkk......",
    "....kkrrrrkk....",
    "...krryrrrrrk...",
    "..krrryyrreerk..",
    "..krrrrryrrrrk..",
    ".krreerrryrrrrk.",
    ".krrrrrrrryyrrk.",
    ".kkkkkkkkkkkkkk.",
    "....kbbbbbbk....",
    "....kbkbbkbk....",
    "....kbbbbbbk....",
    "....kbbkkbbk....",
    "....kbbbbbbk....",
    ".....kkkkkk.....",
    "................",
]), "mush")

BAT = [
    "................", "................", "................", "................",
    ".k....k..k....k.",
    "kvk...kvvk...kvk",
    "kvvk.kvvvvk.kvvk",
    "kvvvkvmvvmvkvvvk",
    "kvvvvvvvvvvvvvvk",
    "kvVvvvvkkvvvvVvk",
    "kV.kvvvvvvvvk.Vk",
    "k...kvvvvvvk...k",
    ".....kvvvvk.....",
    "......kkkk......",
    "................", "................",
]
save(draw(BAT, sub={"v": "&", "V": "/"}), "bat_neta")
save(draw(BAT, sub={"v": "i", "V": "0", "m": "y"}), "crow")
save(draw(BAT, sub={"v": "*", "V": "v"}), "bat_thumb")

save(draw([
    "..k..........k..",
    ".kAk........kAk.",
    ".kAAk.kkkk.kAAk.",
    "..kAkkVVVVkkAk..",
    "...kVVVVVVVVk...",
    "..kVVmmVVmmVVk..",
    "..kVVVVVVVVVVk..",
    "..kVVkeeeekVVk..",
    "...kVVkkkkVVk...",
    "..kkkVVVVVVkkk..",
    ".kVVkyyyyyykVVk.",
    ".kVk.ykkkky.kVk.",
    ".kk..yyyyyy..kk.",
    "....kVVkkVVk....",
    "....kVk..kVk....",
    "....kk....kk....",
]), "demon")

save(draw([
    "................", "................",
    "..........k.....",
    ".........kyk....",
    "..........k.....",
    "..........k.....",
    "......kkkkk.....",
    "...kkkwwwwwkk...",
    "kkkwwwwwwwkewk..",
    "kwkwwwwwwwwwwwk.",
    ".kwwWWWWWwwwkkk.",
    "kwkwwwwwwwwwkek.",
    "kkkkwwwwwwwwkk..",
    "....kkkkkkkk....",
    "................", "................",
]), "fish")

save(draw([
    "................", "................", "................",
    "....kkk.kkk.....",
    "...keeekeeekk...",
    "..keeeeeeeeeekk.",
    ".keeeeeeeekkkkk.",
    ".keeeeeeeekaaaak",
    ".keeeeeeeekakaak",
    ".keeeeeeeekaaaak",
    "..keeeeeeeekkkk.",
    "...kkkkkkkk.....",
    "...kak..kak.....",
    "...kkk..kkk.....",
    "................", "................",
]), "sheep")

save(draw([
    "................", "................", "................",
    ".....kkkkkk.....",
    "...kkhhhhhhkk...",
    "..khhhhhhhhhhk..",
    ".khhkkhhhhkkhhk.",
    ".khhhhhhhhhhhhk.",
    "khhkkkkkkkkkkhhk",
    "khkrrrrrrrrrrkhk",
    "khkreeeeeeeerkhk",
    "khkrrrrrrrrrrkhk",
    ".khkkkkkkkkkkhk.",
    "..khhhhhhhhhhk..",
    "...kkkkkkkkkk...",
    "................",
], sub={"h": "*"}), "mouth")

WOLF = [
    "................", "................", "................",
    "...kk.kk........",
    "..kaakaak.......",
    ".kaaaaaaak......",
    "kamaaaaaaak..kk.",
    "kaaaaaaaaaakkak.",
    ".kekaaaaaaaaaaak",
    "..kkaaaaaaaaaaAk",
    "....kaaaaaaaaaak",
    "....kAaaaaaaaAk.",
    "....kAk..kAkkAk.",
    "....kkk..kkkkkk.",
    "................", "................",
]
save(draw(WOLF, sub={"a": "o", "A": "#"}), "fox")
save(draw(WOLF, sub={"a": "x", "A": "a"}), "dog")

GHOST = [
    "................",
    "......kkkk......",
    "....kkeeeekk....",
    "...keeeeeeeek...",
    "..keeeeeeeeeek..",
    "..keekkeekkeek..",
    "..keekkeekkeek..",
    "..keeeeeeeeeek..",
    "..keeekkkkeeek..",
    "..keeeeeeeeeek..",
    "..keeeeeeeeeek..",
    "..keeeeeeeeeek..",
    "..keekeeekeeek..",
    "..kek.kek.keek..",
    "..kk...k...kk...",
    "................",
]
save(draw(GHOST, sub={"e": "j"}), "ghost")
save(draw(GHOST, sub={"e": "<", "k": "n"}), "phantom")
save(draw(GHOST, sub={"e": "/", "k": "0"}), "blackhist")

save(draw([
    "................",
    ".kkkkkkkkkkkkkk.",
    ".kyyyyyyyyyyyyk.",
    ".kykkkkkkkkkkyk.",
    ".kykWWWWWWWWkyk.",
    ".kykWkkWWkkWkyk.",
    ".kykWmkWWmkWkyk.",
    ".kykWWWWWWWWkyk.",
    ".kykkkkkkkkkkyk.",
    ".kykeekeekeekyk.",
    ".kykkkkkkkkkkyk.",
    ".kyyyyyyyyyyyyk.",
    ".kkkkkkkkkkkkkk.",
    "..kk........kk..",
    "................", "................",
]), "mimic")

save(draw([
    "................", "................",
    "......kkkk......",
    "....kkeeeekk....",
    "...keeemeeeek...",
    "..keeeuuuueeek..",
    ".keeeuuUUuueeek.",
    ".kemuuUkkUuueek.",
    ".keeuuUkkUuumek.",
    ".keeeuuUUuueeek.",
    "..keeeuuuueeek..",
    "...keeeemeeek...",
    "....kkeeeekk....",
    "......kkkk......",
    "................", "................",
], sub={"u": "m", "U": "R"}), "eye")

save(draw([
    "..........y.o...",
    ".........o.y....",
    "........kk......",
    ".......kSk......",
    ".....kkkkkk.....",
    "...kkiiiiiikk...",
    "..kiiiiiiiiiik..",
    "..kieiiiiiiiik..",
    ".kieeiiiiiiiiik.",
    ".kiiiimiimiiiik.",
    ".kiiiiiiiiiiiik.",
    "..kiiikkkkiiik..",
    "..kiiiiiiiiiik..",
    "...kkiiiiiikk...",
    ".....kkkkkk.....",
    "................",
]), "bomb")

BOSS = [
    "......kkkk......",
    "....kkVVVVkk....",
    "...kVVVVVVVVk...",
    "..kVVVVVVVVVVk..",
    "..kVVmmVVmmVVk..",
    "..kVVmmVVmmVVk..",
    ".kVVVVVVVVVVVVk.",
    ".kVVVVkkkkVVVVk.",
    "kvVVVVkmmkVVVVvk",
    "kvvVVVVkkVVVVvvk",
    "kvvvVVVVVVVVvvvk",
    ".kvvvVVVVVVvvvk.",
    ".kvvvvVVVVvvvvk.",
    "..kvvk.kvk.kvvk.",
    "...kk...k...kk..",
    "................",
]
save(draw(BOSS, sub={"V": "0", "v": "/"}), "faceless")
save(draw(BOSS, sub={"V": "R", "v": "<", "m": "@"}), "faceless_true")

save(draw([
    ".....kkkkkk.....",
    "...kkvvvvvvkk...",
    "..kvvvvvvvvvvk..",
    ".kvvvvvvvvvvvvk.",
    ".kvvmmvvvvmmvvk.",
    ".kvvmkvvvvmkvvk.",
    ".kvvvvvvvvvvvvk.",
    "..kvvvVVVVvvvk..",
    "..kvVkvVVvkVvk..",
    ".kvVk.kvvk.kVvk.",
    "kvVk..kvVk..kVvk",
    "kVk..kvVk....kVk",
    "kVk..kVk.....kVk",
    ".kVk.kVk....kVk.",
    "..kk..kVk..kVk..",
    "......kk....kk..",
], sub={"v": "C", "V": "-"}), "kraken")

print("done:", len([f for f in os.listdir(OUT) if f.endswith(".png")]), "files")

# =====================================================================
# 島上的武將與知名人物（虛構角色，造型為原創）
# =====================================================================
HEADS.update({
    "party": [  # 生日哥：派對帽
        "........k.......",
        ".......kmk......",
        "......kymyk.....",
        ".....kmyymmk....",
        "....kHHHHHHk....",
        "....khkhhkhk....",
        "....khhhhhhk....",
        ".....kkhhkk.....",
    ],
    "cat": [  # 照燒貓：貓耳、貓臉、鬍鬚
        "....k......k....",
        "...kHk....kHk...",
        "...kHHk..kHHk...",
        "...kHHHkkHHHk...",
        "...kHHHHHHHHk...",
        "...kHHkHHkHHk...",
        "..kkHHHnnHHHkk..",
        "....kkHHHHkk....",
    ],
    "glasses": [  # 智障神：眼鏡、張大嘴
        "................",
        "......kkkk......",
        ".....kHHHHk.....",
        "....kHHHHHHk....",
        "....kHhhhhHk....",
        "....kkkhkkkk....",
        "....khhhhhhk....",
        ".....kkmmkk.....",
    ],
})
BODY_BOX = [  # 抱著模型箱
    "....kCCCCCCk....",
    "...khCCCCCChk...",
    "..kbbbbbbbbbbk..",
    "..kbmmbbbbmmbk..",
    "..kbbbbbbbbbbk..",
    "...kkkkkkkkkk...",
    "....kkk..kkk....",
    "................",
]
BODY_APRON = [  # 圍裙
    "....kCCCCCCk....",
    "...khCxxxxChk...",
    "...khCxxxxChk...",
    "....kxxxxxxk....",
    "....kxxxxxxk....",
    "....kPPkkPPk....",
    "....kkk..kkk....",
    "................",
]
person("bday", "party", {"H": "n", "C": "*", "P": "U"})
person("teriyaki", "cat", {"H": "o", "C": "#", "P": "d", "n": "R"}, BODY_APRON)
person("zz", "glasses", {"H": "i", "C": "%", "P": "U"}, BODY_BOX)
person("yijing", "hood", {"H": "V", "C": "v", "P": "V", "y": "y"}, BODY_ROBE)
person("watermelon", "short", {"H": "n", "C": "L", "P": "l", "y": "m"})
person("fangshi", "cap", {"H": "i", "A": "o", "C": "s", "P": "U"})
person("doodler", "long", {"H": "y", "C": "c", "P": "U", "y": "m"})

# 戰鬥用：智障神（把限定版箱子舉過頭）
save(draw([
    "..kkkkkkkkkkkk..",
    "..kbbbbbbbbbbk..",
    "..kbmmbbbbmmbk..",
    "..kbbbbbbbbbbk..",
    "..kkkkkkkkkkkk..",
    "...kh..kk..hk...",
    "...kh.kHHk.hk...",
    "...khkHHHHkhk...",
    "....kkkhkkkk....",
    "....khhhhhhk....",
    ".....kmmmmk.....",
    "...kkCCCCCCkk...",
    "..khCCCyyCCChk..",
    "..kkCCCCCCCCkk..",
    "....kPPkkPPk....",
    "....kkk..kkk....",
], sub={"H": "i", "C": "%", "P": "U"}), "zz_battle")

# 戰鬥用：暴走模型（站在底座上的可動模型）
save(draw([
    "................",
    "......kkkk......",
    ".....kzzzzk.....",
    "....kzhhhhzk....",
    "....kzkhhkzk....",
    "....kzhhhhzk....",
    ".....kkmmkk.....",
    "....kmmmmmmk....",
    "...kmkmmmmkmk...",
    "...k.kmmmmk.k...",
    ".....kmmmmk.....",
    "....kmmmmmmk....",
    ".....kh..hk.....",
    ".....kh..hk.....",
    "..kkkkkkkkkkkk..",
    "..kssssssssssk..",
]), "figure")
