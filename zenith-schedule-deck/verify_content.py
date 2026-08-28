#!/usr/bin/env python3
"""Verify the deck against content.js, and report every delta vs the spreadsheet.

1. Every string in content.js must appear verbatim in the PPTX.
2. Every in-scope spreadsheet value must either appear in the deck, or be listed
   as one of Kevin's approved corrections.
"""
import datetime, json, os, pathlib, re, subprocess, sys
import openpyxl
from pptx import Presentation

HERE = pathlib.Path(__file__).resolve().parent
BUILD = pathlib.Path(os.environ.get("ZENITH_BUILD_DIR", HERE / "build"))
# The source schedule workbook. Set ZENITH_SOURCE_XLSX to skip straight to the
# content.js check when the spreadsheet is not to hand.
SRC = os.environ.get("ZENITH_SOURCE_XLSX", "")
DECK = str(BUILD / "Zenith_ENG_Schedule.pptx")
CONTENT = str(HERE / "content.js")

IN_SCOPE = list(range(7, 22)) + list(range(27, 45)) + [46]
SKIP = {22, 45}

sq = lambda s: re.sub(r'\s+', ' ', str(s)).strip()


def fmt(v):
    if isinstance(v, datetime.datetime):
        return f'{v.month}/{v.day}/{v.year}'
    return sq(v)


# ---- all text in the deck ----
prs = Presentation(DECK)
chunks = []
for slide in prs.slides:
    for shp in slide.shapes:
        if shp.has_text_frame:
            chunks.append(sq(shp.text_frame.text))
        if shp.has_table:
            for row in shp.table.rows:
                for cell in row.cells:
                    chunks.append(sq(cell.text))
blob = '  '.join(chunks)
print(f'deck: {len(prs.slides)} slides, {len(chunks)} text objects')

# ---- 1. content.js -> deck ----
js = subprocess.run(
    ['node', '-e', f'console.log(JSON.stringify(require("{CONTENT}")))'],
    capture_output=True, text=True, check=True).stdout
C = json.loads(js)

wanted = []
for key in ('slide1', 'slide2', 'slide3', 'slide4'):
    s = C[key]
    for r in s['rows']:
        wanted += [x for x in r if isinstance(x, str) and x.strip()]
    for co in s.get('callouts', []):
        wanted += [co['label'], co['text']]
    if s.get('closingNote'):
        wanted.append(s['closingNote'])

missing = [w for w in wanted if sq(w) not in blob]
print(f'content.js: {len(wanted)} strings checked, {len(missing)} missing')
if missing:
    for w in missing:
        print('  MISSING:', w[:110])
    sys.exit(1)

# ---- 2. spreadsheet -> deck, with approved deltas ----
APPROVED = {
    '3/16/2026': 'Launch / Best Buy / Walmart moved to 3/16/2027 (year typo)',
    '12/11/2026': 'MP Apps approved finish moved to 12/15/2026 (15d from 11/30)',
    'SW Integration - sprint0': 'spacing fixed to "sprint 0"',
}
APPROVED_SUBSTR = ['stop-ship', 'Intial', 'intial',
                   'on 11/30 With', 'next week next Wednesday',
                   'Hardware Builds & Go to Market']

if not SRC or not os.path.isfile(SRC):
    print('\nSkipping the spreadsheet cross-check (set ZENITH_SOURCE_XLSX to enable).')
    sys.exit(0)

wb = openpyxl.load_workbook(SRC, data_only=True)
ws = wb['Zenith ENG Schedule - Bottom Up']
unexplained, corrected = [], []
for r in IN_SCOPE:
    if r in SKIP:
        continue
    for col in (2, 3, 4, 5, 7):
        v = ws.cell(r, col).value
        if v is None or str(v).strip() == '':
            continue
        t = fmt(v)
        if t in blob:
            continue
        if t in APPROVED or any(k in t for k in APPROVED_SUBSTR):
            corrected.append((r, t))
        else:
            unexplained.append((r, t))

print(f'spreadsheet: {len(corrected)} values differ by approved correction, '
      f'{len(unexplained)} unexplained')
if unexplained:
    for r, t in unexplained:
        print(f'  UNEXPLAINED row {r}: {t[:110]}')
    sys.exit(1)

print('\nPASS - deck matches content.js, and every spreadsheet difference is an '
      'approved correction')
print('\nApproved corrections applied:')
for r, t in corrected:
    print(f'  row {r}: {t[:100]}')
