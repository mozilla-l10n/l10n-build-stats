# Localization Build Stats

Script to extract completion levels of Firefox and Firefox for Android
from the [Firefox repository](https://github.com/mozilla-firefox/firefox).

## Table of Contents

- [Installation](#installation)
- [Configuration](#configuration)
- [Usage](#usage)
- [Development](#development)
- [Testing](#testing)
- [Architecture](#architecture)
- [Data Backfills](#data-backfills)

## Installation

### Prerequisites

- Python 3.11 or higher
- Git
- Access to mozilla-firefox and firefox-l10n repositories

### Setup

1. Clone this repository:
```bash
git clone https://github.com/mozilla/l10n-build-stats.git
cd l10n-build-stats
```

2. Create and activate a virtual environment:
```bash
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r scripts/requirements.txt
```

4. For development, also install dev dependencies:
```bash
pip install -r scripts/requirements-dev.txt
```

## Configuration

1. Create a `config/config` file based on your local setup:
```
mozilla_firefox_path="/path/to/mozilla-unified"
l10n_path="/path/to/firefox-l10n"
```

2. For Google Sheets export, copy `api_config.env.example` to `api_config.env` and fill in your credentials:
```bash
cp api_config.env.example api_config.env
# Edit api_config.env with your Google service account details
```

## Usage

### Extract Firefox Desktop Statistics

```bash
python scripts/firefox_stats.py --version 147.0
```

### Extract Firefox for Android Statistics

```bash
python scripts/fenix_stats.py --version 147.0
```

### Build Chart Data

```bash
python scripts/build_chart_json.py --version 147.0
```

### Export to CSV

```bash
python scripts/csv_extract_product.py --product firefox
python scripts/csv_extract_product.py --product fenix
```

### Upload to Google Sheets

```bash
python scripts/export_to_gsheet.py
```
## Data Backfills

### Firefox desktop (v68 to v127)

This data is used to backfill Firefox statistics from version 68 to 127.

`other_data/hg-changesets.json` is generated from
[product-details](https://product-details.mozilla.org/1.0/l10n/), and includes
the list of changesets used to build Firefox. Changesets are from Mercurial
repositories in [l10n-central](https://hg.mozilla.org/l10n-central).

`other_data/hg-commits.json` includes the commit information (date, commit message) for each
changeset in `hg-changesets.json`.

For each hg commit in `other_data/hg-commits.json`, `git-commits.json` includes the best
match from [firefox-l10n](https://github.com/mozilla-l10n/firefox-l10n) (a
monorepo generated from individual hg repositories).

Scripts are available in [this gist](https://gist.github.com/flodolo/eaed76d43e5c7858ed596a35838eec1d).

### Firefox for Android (v111 to v125)

Data is generated from the archived GitHub repository
[mozilla-mobile/firefox-android](https://github.com/mozilla-mobile/firefox-android),
using tags as reference (e.g. `fenix-v111.0` for v111).

### Firefox for Android (v79 to v110)

Data is generated from two archived repositories:
* [fenix](https://github.com/mozilla-mobile/fenix)
* [android-components](https://github.com/mozilla-mobile/android-components)

Versions are out of sync, so using the version declared in
`buildSrc/src/main/java/AndroidComponents.kt` within the `fenix` repository.

## License

This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at http://mozilla.org/MPL/2.0/.
