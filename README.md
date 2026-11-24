# The World in One Day — Tuesday 24 November 2026

A program that draws a one-page newspaper front page summing up the
world's news of Tuesday 24 November 2026: 36 stories across 7 regions,
every one dated to that day.

## What the page shows

- A navy top strip stating the premise: 36 stories, 7 regions, all dated
  Tuesday 24 November 2026.
- The masthead date in a thin serif face, a red rule, and a three-part
  red subhead (Kyiv, COP31, the $6tn market rout).
- A row of six big numbers: the $6tn lost since the US midterms,
  India's Rs 15,000 crore Nepal package, the Sensex's 1,484-point fall,
  300 on shift at the Serang factory, Pant's 128 in Wellington, and the
  24 dead in the Serang factory fire.
- A coloured region bar (Europe 7, Middle East 1, Americas 7,
  Asia-Pacific 17, Africa 2, Oceania 1, World 1).
- Three lead stories with drawn scenes: Russian drones over the Kyiv
  region, COP31's collapse in Antalya, and Trump blaming Democrats for
  the market rout.
- Twelve illustrated tiles (New Delhi, Cikande, Lisbon, Benghazi, the
  Gulf of Finland, Seoul, Yerevan, Beijing, Dhaka, Wellington, Mumbai,
  Tehran), each with its own small drawn scene.
- A world map with numbered pins for the stories, an "Also on Tuesday"
  list of the remaining 21 stories, a DATE CHECK box explaining which
  well-known events were left out because they happened on earlier days,
  and a sources footer.

## How it is built

Pure Python 3.13 standard library — no Pillow, no numpy, no fonts, no
network, no clock, no randomness. Everything is drawn by hand:

- Every letter comes from a vector stroke alphabet defined in the
  program (an 8-unit em, cap top to baseline, with descenders). Text is
  rendered as thick round-ended strokes at any size; the masthead uses
  a thinner refined face with small serif ticks on the stems.
- Every picture — skylines, drones, a conference table, candlesticks,
  trains, flames, a warship, a ballot box, a warning triangle — is
  drawn from rectangles, discs and polygons.
- Every tile scene is positioned with fractions of its own 40-pixel
  band only, and a clipping rectangle is set while a scene draws, so no
  illustration can ever escape its band and cover a headline or kicker.
- A built-in layout checker verifies that every text block fits its box
  with at least 4 pixels to spare, that no scene pixel leaves its band,
  and that nothing leaves the 1024×1024 canvas. It prints its issue
  count and the program exits non-zero unless the count is 0.
- The PNG is encoded by hand (zlib + struct). Two runs produce a
  byte-identical file.

## How to run it

```sh
MAKEFUN_OUTPUT_DIR=<directory> python3 main.py
```

It creates the directory if needed and writes `<directory>/entry.png`
(1024×1024, under 1 MiB). It prints the layout checker's verdict first;
if the checker finds any issue the program stops without writing a file.
