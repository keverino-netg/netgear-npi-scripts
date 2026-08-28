#!/usr/bin/env python3
"""Measure Outfit text so PPTX boxes and table rows fit exactly.

Reads a JSON job list on stdin. Each job is either:
  {"op": "lines", text, pt, w_in, bold}  -> wrapped line count in that box width
  {"op": "width", text, pt, bold}        -> single-line width in inches
Writes a JSON array of results to stdout.

Uses the real Outfit TTF metrics at 144 DPI (PowerPoint's export resolution).
Line counts are measured against a slightly narrower box (SAFETY) so the
computed count is never lower than what PowerPoint actually renders.
"""
import json, os, pathlib, sys
from PIL import ImageFont

DPI = 144.0
SAFETY = 0.96          # wrap 4% early -> conservative (never under-counts lines)

# Fonts are downloaded into the build directory by prep_assets.py.
BUILD = os.environ.get("ZENITH_BUILD_DIR",
                       str(pathlib.Path(__file__).resolve().parent / "build"))
REG = os.path.join(BUILD, "Outfit-Regular.ttf")
BLD = os.path.join(BUILD, "Outfit-Bold.ttf")
_cache = {}


def font(pt, bold):
    key = (round(pt, 2), bool(bold))
    if key not in _cache:
        _cache[key] = ImageFont.truetype(BLD if bold else REG, int(round(pt * DPI / 72.0)))
    return _cache[key]


def text_width(text, pt, bold=False):
    """Single-line rendered width, in inches."""
    return font(pt, bold).getlength(str(text)) / DPI


def wrapped_lines(text, pt, w_in, bold=False, safety=None):
    """Greedy word wrap, mirroring how PowerPoint breaks a paragraph."""
    if not text:
        return 1
    f = font(pt, bold)
    limit = w_in * DPI * (SAFETY if safety is None else safety)
    lines, cur = 1, ""
    for word in str(text).split():
        trial = (cur + " " + word).strip()
        if f.getlength(trial) <= limit or not cur:
            cur = trial
        else:
            lines += 1
            cur = word
    return lines


def run(job):
    if job.get("op", "lines") == "width":
        return text_width(job["text"], job["pt"], job.get("bold", False))
    return wrapped_lines(job["text"], job["pt"], job["w_in"], job.get("bold", False),
                         job.get("safety"))


if __name__ == "__main__":
    print(json.dumps([run(j) for j in json.load(sys.stdin)]))
