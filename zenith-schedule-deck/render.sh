#!/bin/bash
# Build the deck, render every slide to PNG, and run the fit/coordinate checks.
#
#   ./render.sh
#
# Requires NETGEAR_SLIDES_ASSETS to point at the netgear-slides skill assets/
# directory. Optional: ZENITH_SOURCE_XLSX to cross-check against the source
# spreadsheet, ZENITH_BUILD_DIR to build somewhere other than ./build.
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BUILD="${ZENITH_BUILD_DIR:-$HERE/build}"
export ZENITH_BUILD_DIR="$BUILD"
mkdir -p "$BUILD"

if [ ! -d "$HERE/node_modules" ]; then
  echo "Installing node dependencies..."
  (cd "$HERE" && npm install --silent)
fi

echo "==> Preparing brand assets and fonts"
python3 "$HERE/prep_assets.py"

echo "==> Building deck"
node "$HERE/build_deck.js"

echo "==> Rendering slides"
rm -f "$BUILD"/Zenith_ENG_Schedule.pdf "$BUILD"/slide-*.png
soffice --headless --convert-to pdf "$BUILD/Zenith_ENG_Schedule.pptx" \
        --outdir "$BUILD" >/dev/null 2>&1
pdftoppm -r 110 -png "$BUILD/Zenith_ENG_Schedule.pdf" "$BUILD/slide"

echo "==> Coordinate sanity check"
BUILD="$BUILD" python3 - <<'EOF'
import os
from pptx import Presentation
from pptx.util import Emu

p = Presentation(os.path.join(os.environ['BUILD'], 'Zenith_ENG_Schedule.pptx'))
sw, sh = Emu(p.slide_width).inches, Emu(p.slide_height).inches
assert abs(sw - 13.333) < 0.01 and abs(sh - 7.5) < 0.01, f'Wrong canvas {sw}x{sh}'
for i, s in enumerate(p.slides, 1):
    xs = [Emu(x.left).inches + Emu(x.width).inches
          for x in s.shapes if x.width and x.left is not None]
    hs = [Emu(x.height).inches for x in s.shapes if x.height]
    assert max(xs) > 13.0, f'slide {i}: nothing reaches the right edge'
    assert max(hs) > 7.0, f'slide {i}: vertical bar is not full height'
print('Coordinate sanity OK')
EOF

echo "==> Content verification"
python3 "$HERE/verify_content.py"

echo
echo "Deck:   $BUILD/Zenith_ENG_Schedule.pptx"
echo "Slides: $(ls "$BUILD"/slide-*.png | wc -l | tr -d ' ') PNGs in $BUILD"
