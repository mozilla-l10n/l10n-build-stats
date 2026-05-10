---
name: generate-summary
description: Generate a Slack-ready summary of localization completion changes between the two most recent major Firefox releases. Compares per-locale completion percentages for the top 25 locales (read from the "Top Locales" worksheet), highlights notable swings (|Δ| ≥ 1.00pp), and lists improvements during dot releases of the latest major. Use when the user asks for a release summary, weekly summary, or Slack post about extracted completion data.
---

# Generate Slack release summary

Run `scripts/generate_summary.py` with the project virtualenv and emit the script's output verbatim, inside a single Markdown code block so the user can copy-paste to Slack with the inline links intact.

## Steps

1. Run the script:
   ```bash
   .venv/bin/python scripts/generate_summary.py
   ```
   If `.venv/bin/python` is missing, fall back to `python scripts/generate_summary.py`.

2. Print the script's stdout exactly as produced, wrapped in a fenced ```` ```markdown ```` block. Do not paraphrase, re-flow, or "improve" the prose — the user copies the block straight into Slack, where Slack's mrkdwn renderer turns the `[label](url)` segments into clickable links.

3. After the code block, add one short line acknowledging what the user typically wants to edit before posting (overall framing, editorial color). Do not invent commentary about why locales moved.

## What the script does

- Reads `docs/data/data.json` (produced by `scripts/build_chart_json.py`) for completion percentages and Pontoon locale display names.
- Reads `api_config.env` for the Google service account, then fetches column `firefox` and column `fenix` from the **Top Locales** worksheet (case-insensitive headers; first 25 non-empty codes per column).
- Identifies the two most recent major versions present in the data, takes the latest dot release of each, and computes per-locale deltas in percentage points.
- For the latest major, also computes improvements between `<major>.0` and the latest dot release (e.g. `150.0 → 150.0.2`), reporting locales where completion rose by ≥ 1.00pp.
- Threshold for "notable" major-over-major changes is `|Δ| ≥ 1.00pp`. To change it, edit `NOTABLE_THRESHOLD_PP` in the script.
- Worksheet gids for the Desktop / Android links are hardcoded as `SHEET_GIDS` in the script (Desktop = 1198308940, Android = 1449426221).

## Failure modes (surface them, don't paper over)

- **Missing `docs/data/data.json`**: tell the user to run `scripts/build_chart_json.py --version <X>` first. Don't try to regenerate it silently — it requires the source repos.
- **Missing or invalid `api_config.env`**: tell the user the file is needed for the Top Locales lookup. Don't fall back to a hardcoded list.
- **`Top Locales` worksheet missing or column mismatch**: surface the script's error verbatim. The expected column headers are `firefox` and `fenix` (case-insensitive).
- **Fewer than two majors in the data**: surface the script's error.
