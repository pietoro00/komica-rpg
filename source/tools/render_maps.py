import json, sys
from PIL import Image
g = json.load(open(sys.argv[1], encoding='utf-8'))
IMG = sys.argv[2]
cache = {}
def im(n):
    if n not in cache: cache[n] = Image.open(f"{IMG}/{n}.png").convert("RGBA").resize((24, 24), Image.NEAREST)
    return cache[n]
outs = []
for mid, m in g["maps"].items():
    rows = m["rows"]; H, W = len(rows), len(rows[0])
    c = Image.new("RGBA", (W * 24, H * 24))
    for y, r in enumerate(rows):
        for x, ch in enumerate(r):
            c.paste(im(g["tiles"][ch][0]), (x * 24, y * 24))
    for e in m["ents"]:
        s = im(e["sprite"]).copy()
        if "show" in e: s.putalpha(s.getchannel("A").point(lambda a: a * 0.6))
        c.alpha_composite(s, (e["x"] * 24, e["y"] * 24))
    c.save(f"/tmp/map_{mid}.png"); outs.append(mid)
print(outs)
