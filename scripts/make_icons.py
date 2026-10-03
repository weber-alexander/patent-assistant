"""Create app icons from the original logo.

Works with real transparency as well as with a baked-in checkerboard or a
light background: the dark rounded square is detected by colour, then a clean
anti-aliased rounded mask is drawn instead of reusing the original edges.

Run once after changing the logo:  uv run python scripts/make_icons.py
"""

from pathlib import Path

from PIL import Image, ImageDraw

ASSETS = Path(__file__).resolve().parent.parent / "src" / "patent_assistant" / "assets"
SIZE = 512
CORNER_RADIUS = 0.22  # share of the side length, typical for app icons
INSET = 0.01  # trim a thin edge to avoid background fringes
SUPERSAMPLE = 4  # draw the mask larger, then shrink it for smooth corners

source = Image.open(ASSETS / "logo_original.png").convert("RGBA")

# 1) Detect the icon by colour: dark or saturated pixels belong to it,
#    light grey (checkerboard) and white do not.
rgb = source.convert("RGB")
mask = Image.new("L", rgb.size, 0)
mask.putdata([255 if (max(p) - min(p) > 60 or sum(p) < 330) else 0 for p in rgb.getdata()])
left, top, right, bottom = mask.getbbox()

# 2) Square crop around the detected icon, slightly inset
side = min(right - left, bottom - top)
inset = round(side * INSET)
cx, cy = (left + right) // 2, (top + bottom) // 2
half = side // 2 - inset
icon = source.crop((cx - half, cy - half, cx + half, cy + half)).resize((SIZE, SIZE), Image.LANCZOS)

# 3) Clean rounded mask with anti-aliasing
big = SIZE * SUPERSAMPLE
rounded = Image.new("L", (big, big), 0)
ImageDraw.Draw(rounded).rounded_rectangle(
    (0, 0, big - 1, big - 1), radius=round(big * CORNER_RADIUS), fill=255
)
icon.putalpha(rounded.resize((SIZE, SIZE), Image.LANCZOS))

icon.save(ASSETS / "logo.png")
icon.save(ASSETS / "logo.ico", sizes=[(s, s) for s in (16, 24, 32, 48, 64, 128, 256)])
print("Icons erstellt:", ASSETS / "logo.png", ASSETS / "logo.ico")
