import os
import math
from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
S = 256
img = Image.new("RGBA", (S, S), (0, 0, 0, 0))
d = ImageDraw.Draw(img)

top = (26, 40, 74)
bot = (46, 78, 130)
for y in range(S):
    t = y / S
    c = tuple(int(top[i] + (bot[i] - top[i]) * t) for i in range(3))
    d.line([(0, y), (S, y)], fill=c + (255,))

mask = Image.new("L", (S, S), 0)
ImageDraw.Draw(mask).rounded_rectangle([4, 4, S - 4, S - 4], radius=52, fill=255)
img.putalpha(mask)
d = ImageDraw.Draw(img)

gold = (240, 196, 82)
box = [40, 40, S - 40, S - 40]
d.arc(box, start=140, end=390, fill=gold, width=16)
ang = math.radians(140)
cx, cy = S / 2, S / 2
r = (S - 80) / 2
ax, ay = cx + r * math.cos(ang), cy + r * math.sin(ang)
d.polygon([(ax - 4, ay - 22), (ax + 22, ay - 6), (ax - 12, ay + 10)], fill=gold)

font = None
for fp in [r"C:\Windows\Fonts\arialbd.ttf", r"C:\Windows\Fonts\segoeuib.ttf"]:
    if os.path.exists(fp):
        font = ImageFont.truetype(fp, 118)
        break
if font is None:
    font = ImageFont.load_default()
text = "E7"
tb = d.textbbox((0, 0), text, font=font)
tw, th = tb[2] - tb[0], tb[3] - tb[1]
d.text(((S - tw) / 2 - tb[0], (S - th) / 2 - tb[1] - 4), text,
       fill=(255, 255, 255), font=font)

out = os.path.join(HERE, "icon.ico")
img.save(out, sizes=[(16, 16), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)])
img.save(os.path.join(HERE, "icon.png"))
print("Icone salvo em", out)
