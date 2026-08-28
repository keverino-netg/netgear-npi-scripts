# Zenith schedule deck

Builds the 4-slide NETGEAR Zenith ENG schedule deck (Orbi brand) from schedule
data, and verifies that nothing was silently dropped or reworded on the way in.

The reusable part is the layout engine, not the Zenith content. Swap the rows in
`content.js` and it will re-fit every table and callout for the new data: it
picks the type size, sizes the columns to their contents, and refuses to write a
deck where anything overflows the slide.

## Why this exists

Generating a PowerPoint table by hand means guessing at row heights and column
widths, then opening the file, spotting a wrapped date or clipped row, tweaking
a number, and repeating. This does the guessing arithmetically instead:

- **Real font metrics.** `measure.py` reads the actual Outfit TTF and reports how
  many lines a string wraps to at a given size and box width. No character-count
  estimates.
- **Correct line height.** PowerPoint's `lineSpacingMultiple` scales the font's
  natural line height, not the point size. Outfit reports ascent 1000 / descent
  -260 per 1000 em, so one single-spaced line is 1.26 em. Miss this and every
  height is 26% short, which is what makes text spill out of its box.
- **Content-driven columns.** Columns holding short values (Duration, dates) are
  sized to their widest entry plus slack, so a date can never drop one character
  to a second line. Text columns share what is left.
- **Type size is chosen, not set.** Each slide tries the largest size in a ladder
  and steps down only until the content fits its band.
- **Fit check before write.** Every slide reports its band, table height and
  bottom edge. If anything would cross the content floor the build fails rather
  than shipping a broken slide.

## Setup

```bash
npm install
pip3 install -r requirements.txt

# The netgear-slides skill ships the brand assets (bars, textures, icons).
# Its path depends on how the plugin was installed:
export NETGEAR_SLIDES_ASSETS="$(find ~ -type d -path '*netgear-slides/assets' 2>/dev/null | head -1)"
```

Rendering the preview PNGs also needs LibreOffice and Poppler:

```bash
brew install --cask libreoffice
brew install poppler
```

## Build

```bash
./render.sh
```

That prepares the brand assets and fonts, builds the deck, renders every slide to
PNG, runs the coordinate checks, and verifies the content. Output lands in
`build/`.

To cross-check the deck against the original spreadsheet as well:

```bash
export ZENITH_SOURCE_XLSX=/path/to/Zenith_ENG_Schedule.xlsx
./render.sh
```

Build only, without the render and checks:

```bash
npm run build
```

## Files

| File | Does |
|---|---|
| `content.js` | All slide copy and schedule rows. This is the file you edit. |
| `build_deck.js` | Layout engine and slide construction. |
| `measure.py` | Wrapped line counts and text widths from the real Outfit metrics. |
| `prep_assets.py` | Downloads Outfit, rasterises the brand SVGs, checks for the magenta chroma-key bug. |
| `verify_content.py` | Confirms every string reaches the deck, and that spreadsheet differences are all approved corrections. |
| `render.sh` | Runs the whole pipeline. |

## Editing the deck

Slide copy and rows live in `content.js`. Rows are
`[task, duration, start, finish, bold, description]`; the `description` field is
only used by the wide slides (3 and 4).

Two slide shapes are available:

- `splitSlide` -- schedule table on the left, callout cards on the right. Used
  for slides 1 and 2. Row heights are uniform, and the table and card stack are
  each centred against the taller of the two.
- `wideSlide` -- full-width table with a Description column, plus an optional
  closing banner pinned to the bottom of the band. Used for slides 3 and 4.

After any edit, run `./render.sh` and look at the PNGs in `build/`. The fit
report prints the numbers, but the render is what catches a layout that is
technically within bounds and still reads badly.

## Verification

`verify_content.py` enforces two things:

1. Every string in `content.js` appears verbatim in the built deck.
2. Every value in the source spreadsheet either appears in the deck, or is listed
   as an approved correction in the `APPROVED` / `APPROVED_SUBSTR` tables.

The second check is the useful one. It means a typo fix or a date change has to
be recorded deliberately, and anything that goes missing by accident fails the
build. When the schedule is corrected again, add the old value to those tables
with a note explaining the change.

## Corrections applied to the source data

The schedule as supplied had several issues, all confirmed with the schedule
owner before being changed. They are documented in the header of `content.js`
and enforced by `verify_content.py`.

| Was | Now | Why |
|---|---|---|
| Launch / Best Buy / Walmart on 3/16/2026 | 3/16/2027 | Year typo. 2026 put launch 11 months before the units were ready to ship. |
| MP Apps approved finish 12/11/2026 | 12/15/2026 | 15 days from the 11/30 submission. |
| "Intial" (2 places) | "Initial" | Typo. |
| "SW Integration - sprint0" | "sprint 0" | Matches sprints 1 to 4. |
| "stop-ship" | "stopship" | The schedule used both spellings. |
| "Release Candidates on 11/30 With all bugs fixed" | "... on 11/30. With all bugs fixed" | Two sentences had been run together. |
| "published next week next Wednesday September 2" | "published next Wednesday September 2" | Duplicated wording. |
| "Hardware Builds & Go to Market" section row | removed | Slides 3 and 4 titles now carry it. |

Control Run FAI keeps its 3d duration across 12/24 to 1/1 -- the span accounts
for the holidays and is intentional.

## Brand rules

The deck follows the `netgear-slides` and `netgear-brand` skills: Orbi light-blue
accent, Outfit throughout (embedded in the PPTX so recipients need nothing
installed), wave texture background, Orbi vertical bar, and the slanted
parallelogram horizontal bar rasterised from the brand SVG rather than drawn as a
rectangle.

Two deliberate departures, both at the schedule owner's request:

- Slide titles keep their original capitalisation instead of being converted to
  sentence case.
- No bold anywhere in the table bodies or at the end of titles.

The wide slides also use per-row heights rather than uniform ones. A Description
column makes uniform rows impossible without wasting roughly 40% of the band,
which would cost two type sizes.
