# Prices and the "Every X at today's price" videos

Product-intent videos ("Every RTX card, ranked, with today's price") are what search traffic looks for, and a competitor channel got 472K views from one of them (see [Analytics](analytics.md#what-the-numbers-say)).
Their facts must be right, so they never come from a model: they come from two files.

| File | What it holds | Who writes it |
|---|---|---|
| `data/products/<family>.json` | items of a family, one narration line per item (`{price}` is filled in), the editorial tier letter S-F, the search query and match regex used to find the price, optional `alt` line, `gone` scene, `extra` scene, `takeaway`, `vote` | by hand (families: `ryzen7`, `intel_i7`, `rtx`, `radeon`) |
| `data/prices/<YYYY-MM-DD>.json` | the lowest standalone price of each item that day (`null` = no listing) | collected from PcComponentes (below) |

## Collect the prices (about 10 minutes, with Claude in Chrome)

PcComponentes blocks scripts that are not a real browser, so the assistant reads the listing inside the user's Chrome with `scripts/pccomponentes_prices.js`:

1. For every item: open `https://www.pccomponentes.com/search?query=<query>&sort=price_asc`, define `pcExtract` (the file's body) and run `await pcExtract({match: '<match>', kind: 'cpu' | 'gpu'})` (kind comes from the item).
2. Collect the answers as `{"<family>:<id>": {"price": 194, "name": "listing title"} | null}` and store them: `echo '<json>' | .venv/bin/python scripts/save_prices.py` (it merges into today's file and rejects unknown ids).
3. A listing is the **cheapest standalone part**: PCs and laptops that contain it are ignored; marketplace sellers are included.

## Build the scripts

```bash
PYTHONPATH=. .venv/bin/python scripts/build_every_script.py all          # newest prices, refuses prices older than 3 days
PYTHONPATH=. .venv/bin/python scripts/build_every_script.py rtx --prices data/prices/2026-11-23.json
```

It leaves out items without a price, sorts the rest by price, builds the tier scenes, adds the `gone` scene when every item listed in it has no price (the RTX 40 series, the RX 7000 series), runs the normal validator
and writes `data/scripts/every_<family>.json`. **Read the printed board**: the tier letters are editorial and some lines say things that are only true on some days (the dataset's `alt` lines handle the price comparisons);
change the dataset when a price move makes a letter or a claim false (a "bargain" that no longer is one).

## In the daily batch

`genera_batch.py` gives one slot to an "Every X" video when the newest price file is at most 3 days old: it builds the script of the family shown longest ago (`data/batches/log.json` remembers `family`) and
replaces the `tier` pick, or the last pick. `--no-every` turns it off. With stale prices it prints why and carries on without. So `genera` starts with: *if the newest `data/prices/` file is older than 2 days, collect new prices first*.

## Adding a family

Copy a file in `data/products/`, list 6-9 items with their lines, then collect prices for the new ids. Titles and hashtags come from the file (`title_name`, `hashtags`); the video's title always starts with "Every".

## Price moves

Every `data/prices/<date>.json` is also the history. `python scripts/price_drops.py [--min 10]` lists the moves between the two newest files, `--history rtx:5070` shows one product day by day, and `genera_batch.py` mentions in its plan when 8% moves exist (a good day for an "Every X" video). The only source today is PcComponentes read through Chrome; an affiliate feed would need an affiliate account first.
