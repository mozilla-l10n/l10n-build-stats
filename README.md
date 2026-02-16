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

## Development

### Code Quality

This project uses:
- **ruff** for linting and formatting
- **pyright** for type checking
- **pytest** for testing

Run all checks:
```bash
# Linting
ruff check scripts

# Formatting
ruff format scripts

# Type checking
pyright scripts

# Run all checks (as in CI)
ruff check scripts && ruff format scripts --check && pyright scripts
```

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=scripts --cov-report=term --cov-report=html

# Run specific test file
pytest tests/test_functions.py

# Run with verbose output
pytest -v
```

### Project Structure

```
l10n-build-stats/
├── scripts/
│   ├── base_stats.py           # Base class for stats extractors
│   ├── config.py               # Configuration management
│   ├── functions.py            # Shared utility functions
│   ├── fenix_stats.py          # Firefox for Android extractor
│   ├── firefox_stats.py        # Firefox Desktop extractor
│   ├── build_chart_json.py     # Chart data builder
│   ├── csv_extract_product.py  # CSV export utility
│   └── export_to_gsheet.py     # Google Sheets uploader
├── tests/
│   ├── test_functions.py       # Unit tests for functions
│   ├── test_config.py          # Unit tests for config
│   └── conftest.py             # Shared pytest fixtures
├── stats/                       # Output JSON files
├── docs/                        # Documentation and charts
└── config/                      # Configuration files
```

## Architecture

### Stats Extraction Flow

1. **Configuration Loading**: Read paths from `config/config`
2. **Repository Setup**: Checkout correct git tags/commits
3. **String Extraction**: Parse l10n files using `moz-l10n`
4. **Completion Calculation**: Compare locale strings to source
5. **Output**: Save results as JSON in `stats/`

### Base Class Pattern

The project uses an abstract base class (`StatsExtractor`) to reduce code duplication:

```python
class StatsExtractor(ABC):
    """Base class for stats extraction."""

    @abstractmethod
    def extract_string_list(self, *paths) -> tuple[StringList, list[str]]:
        """Extract strings for the product."""
        pass

    @abstractmethod
    def get_product_name(self) -> str:
        """Return product name."""
        pass
```

Concrete implementations:
- `FenixStatsExtractor` - Firefox for Android
- `FirefoxStatsExtractor` - Firefox Desktop

### Configuration Management

The `Config` class provides:
- Centralized configuration loading
- Path validation
- Better error messages
- Easy testing with mocks

### Logging

All scripts use Python's `logging` module with consistent formatting:
```
%(asctime)s - %(name)s - %(levelname)s - %(message)s
```

Log levels:
- `INFO`: Normal progress messages
- `WARNING`: Non-critical issues (missing files, etc.)
- `ERROR`: Critical errors
- `DEBUG`: Verbose output (disabled by default)

## Testing

### Test Coverage

The project aims for >80% test coverage. Current coverage includes:
- Configuration management
- Utility functions (version parsing, file filtering)
- Completion calculation
- Error handling

### Writing Tests

Tests use `pytest` with fixtures for common test data:

```python
def test_calculates_completion_percentage(tmp_path, sample_string_list):
    """Test completion percentage calculation."""
    # Test implementation
```

### Continuous Integration

GitHub Actions runs on every push and PR:
1. Linting (ruff)
2. Type checking (pyright)
3. Tests with coverage (pytest)
4. Coverage upload (codecov)

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

## Contributing

1. Create a new branch for your changes
2. Make your changes with appropriate tests
3. Run the full test suite and linting
4. Submit a pull request

### Code Style

- Follow PEP 8 (enforced by ruff)
- Use type hints for all function signatures
- Add docstrings for public functions
- Keep functions focused and small
- Write tests for new functionality

## License

This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at http://mozilla.org/MPL/2.0/.
