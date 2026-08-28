#!/usr/bin/env python3
"""Rasterise NETGEAR brand SVG assets to PNG for embedding in the Zenith deck."""
import base64, json, os, pathlib, re, sys, urllib.request, cairosvg
from PIL import Image

# Brand assets ship with the netgear-slides skill. Point NETGEAR_SLIDES_ASSETS at
# that skill's assets/ directory (it moves around depending on how the plugin is
# installed). Everything this script produces lands in the build directory.
HERE = pathlib.Path(__file__).resolve().parent
SK = os.environ.get("NETGEAR_SLIDES_ASSETS")
if not SK or not os.path.isdir(SK):
    sys.exit("Set NETGEAR_SLIDES_ASSETS to the netgear-slides skill assets/ directory.\n"
             "Find it with:  find ~ -type d -path '*netgear-slides/assets' 2>/dev/null")
BUILD = pathlib.Path(os.environ.get("ZENITH_BUILD_DIR", HERE / "build"))
OUT = BUILD / "assets"
OUT.mkdir(parents=True, exist_ok=True)

ORBI = "#1E96FC"

# Outfit is the NETGEAR corporate typeface. The TTFs are embedded into the PPTX
# so recipients do not need it installed, and measure.py reads their metrics.
OUTFIT = {
    "Outfit-Regular.ttf": "https://fonts.gstatic.com/s/outfit/v15/QGYyz_MVcBeNP4NjuGObqx1XmO1I4TC1C4E.ttf",
    "Outfit-Bold.ttf":    "https://fonts.gstatic.com/s/outfit/v15/QGYyz_MVcBeNP4NjuGObqx1XmO1I4deyC4E.ttf",
    "Outfit-Thin.ttf":    "https://fonts.gstatic.com/s/outfit/v15/QGYyz_MVcBeNP4NjuGObqx1XmO1I4TC0C4E.ttf",
}
for name, url in OUTFIT.items():
    dest = BUILD / name
    if not dest.exists():
        urllib.request.urlretrieve(url, dest)
        print(f"  downloaded {name}")

def rasterise(src, dst, scale):
    cairosvg.svg2png(url=src, write_to=dst, scale=scale)
    im = Image.open(dst)
    print(f"  {os.path.basename(dst):40s} {im.size}")
    return im.size

# Horizontal bar - slanted parallelogram, native 214x11 (ratio 19.45:1)
rasterise(f"{SK}/PPT-horizontal-bar-Light-Blue.svg", f"{OUT}/hbar.png", 10)

# Vertical bar - Orbi, native 64x1080
rasterise(f"{SK}/PPT-vertical-bar-Orbi.svg", f"{OUT}/vbar.png", 2)

# Verify no magenta in the rasterised bars
for name in ("hbar.png", "vbar.png"):
    im = Image.open(f"{OUT}/{name}").convert("RGBA")
    px = im.load()
    bad = 0
    for y in range(0, im.size[1], max(1, im.size[1] // 200)):
        for x in range(0, im.size[0], max(1, im.size[0] // 200)):
            r, g, b, a = px[x, y]
            if a > 10 and r - g > 80 and b - g > 80 and g < 120:
                bad += 1
    assert bad == 0, f"{name} has {bad} magenta pixels"
print("  magenta check: clean")

# Icon - recolour stroke, rasterise at 8x native (32 -> 256).
# Orbi blue for cards on white; white for the reversed closing banner.
raw = open(f"{SK}/icon-list.svg").read()
for name, colour in (("icon-list", ORBI), ("icon-list-white", "#FFFFFF")):
    rec = raw.replace('stroke="black"', f'stroke="{colour}"') \
             .replace('fill="black"', f'fill="{colour}"')
    open(str(BUILD / f"{name}.svg"), "w").write(rec)
    rasterise(str(BUILD / f"{name}.svg"), f"{OUT}/{name}.png", 8)

# Texture - light waves, copy as-is (already a JPG)
import shutil
shutil.copy(f"{SK}/C-texture-waves-light.jpg", f"{OUT}/texture.jpg")
print(f"  texture.jpg {Image.open(f'{OUT}/texture.jpg').size}")

# Emit base64 manifest for the Node build
manifest = {}
for f, mime in (("hbar.png", "image/png"), ("vbar.png", "image/png"),
                ("icon-list.png", "image/png"), ("icon-list-white.png", "image/png"),
                ("texture.jpg", "image/jpeg")):
    with open(f"{OUT}/{f}", "rb") as fh:
        manifest[f.split(".")[0].replace("-", "_")] = mime + ";base64," + base64.b64encode(fh.read()).decode()
json.dump(manifest, open(str(BUILD / "assets.json"), "w"))
print(f"wrote {BUILD / 'assets.json'}")
