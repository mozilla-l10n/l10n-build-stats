# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Purpose

Extract and report localization completion levels for Firefox Desktop and Firefox for Android (Fenix), comparing source strings in `mozilla-firefox/firefox` against translations in `mozilla-l10n/firefox-l10n`. Output is consumed by the chart in `docs/` (GitHub Pages) and a Google Sheets workbook.

## Common commands

Setup (Python 3.13+):
```bash
python -m venv .venv && source .venv/bin/activate
pip install -r scripts/requirements.txt -r scripts/requirements-dev.txt
```

Run a full extraction for a version (drives every step the CI does, including the Google Sheets upload):
```bash
bash scripts/extract_version.sh 150.0    # also accepts dot releases like 150.0.2
```

Individual stages (run in this order; each stage feeds the next):
```bash
python scripts/firefox_stats.py --version 150.0       # writes stats/firefox_150_0.json
python scripts/fenix_stats.py   --version 150.0       # writes stats/fenix_150_0.json
python scripts/csv_extract_product.py --product firefox   # writes stats/firefox_locales.csv
python scripts/csv_extract_product.py --product fenix
python scripts/build_chart_json.py --version 150.0    # writes docs/data/data.json
python scripts/export_to_gsheet.py                    # uploads CSVs to Google Sheets
```

Lint, format, type-check, test (matches `.github/workflows/linter.yml`):
```bash
ruff check scripts
ruff format scripts --check
pyright scripts
pytest tests/ --cov=scripts --cov-report=term
pytest tests/test_functions.py::TestParseFile -v   # single test class
```

## Required configuration

Two files are required before running locally; both are gitignored and synthesized by CI from secrets/inputs:

- `config/config` — shell-style `key="value"` lines, parsed by `scripts/config.py`. Required keys: `mozilla_firefox_path` (clone of `mozilla-firefox/firefox`) and `l10n_path` (clone of `mozilla-l10n/firefox-l10n`). Use `config/config.dist` as a template.
- `api_config.env` — INI file under a `[GDOCS]` section with Google service-account credentials and `spreadsheet_key`. Only needed for `export_to_gsheet.py`. Use `api_config.env.example` as a template.

The `firefox_stats.py` extractor checks out the matching `FIREFOX_*_RELEASE` tag in `mozilla_firefox_path` and the changeset referenced by `browser/locales/l10n-changesets.json` (the `it` locale, used as the canonical source-of-truth) in `l10n_path`. **Running locally mutates those clones via `git checkout`** — never point the config at a worktree with uncommitted changes.

## Architecture

### Extraction pipeline

`scripts/base_stats.py` defines `StatsExtractor`, an ABC that owns the workflow: read config → load Firefox release tags → check out repos → call `extract_string_list()` → write completion JSON via `store_completion()`. `firefox_stats.py` and `fenix_stats.py` are thin subclasses that differ only in:
- which config keys they need (`_get_config_params`),
- how they navigate the source tree to find `l10n.toml` files,
- how they resolve target locale paths (Fenix uses `moz.l10n`'s `get_android_locale` mapping; Firefox reads `shipped-locales` and resolves files under `<l10n_path>/<locale>/...`).

When adding a new product, subclass `StatsExtractor` and follow the same pattern; do not duplicate the workflow logic.

### String parsing (`scripts/functions.py`)

`parse_file()` is the heart of the comparison. For each reference (`source`) file it records every entry id; for each locale file it records ids that **also exist in the source set**. Completion = `len(locale_ids) / len(source_ids)` summed across files. Two Android-specific filters in `meta_include()` skip strings the build won't ship:
- `{http://mozac.org/tools}removedIn` < current major version
- `{http://schemas.android.com/tools}ignore` containing `UnusedResources`

The `version` arg to `parse_file()` is only consulted for those Android meta filters; Firefox Desktop calls pass it implicitly empty.

### Filename ↔ version convention

Stats JSON files are named `<product>_<version-with-underscores>.json` (e.g., `firefox_150_0_2.json` for `150.0.2`). `get_version_from_filename()` is the canonical parser — use it instead of ad-hoc string splitting, since dot releases have a variable number of components.

### Data flow to outputs

- `stats/<product>_<version>.json` — per-version completion percentages (0.0–1.0 floats)
- `stats/<product>_locales.csv` — pivoted history, one row per version, one column per locale; `Version` is prefixed with `'` to force Sheets to treat it as text
- `docs/data/data.json` — last 30 major versions, keyed by locale, with display names fetched from the Pontoon API; consumed by `docs/js/script.js`

### CI extraction (`.github/workflows/extract.yml`)

Runs weekly and on manual dispatch. The workflow does the local setup itself: sparse-checks out `mozilla-firefox/firefox` at `FIREFOX_<version>_RELEASE`, full-checks out `mozilla-l10n/firefox-l10n`, writes `config/config` pointing at those workspaces, decodes `GSHEETS_CONFIG` into `api_config.env`, and runs `extract_version.sh`. The sparse-checkout path list mirrors `firefox-l10n-source`'s update config plus the two Fenix `l10n.toml` paths — keep it in sync if `fenix_stats.py` starts reading additional source trees.

## Backfill data (`other_data/`)

Static JSON files that capture Firefox/Fenix metadata for versions that predate the current monorepo layout (Firefox 68–127, Fenix 79–125). Generation scripts live in [this gist](https://gist.github.com/flodolo/eaed76d43e5c7858ed596a35838eec1d), not in this repo. Treat these files as inputs, not regenerable artifacts.
