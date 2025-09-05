#! /usr/bin/env bash

function interrupt_code()
# This code runs if user hits control-c
{
  printf "\n*** Operation interrupted ***\n"
  exit $?
}

# Trap keyboard interrupt (control-c)
trap interrupt_code SIGINT

function setupVirtualEnv() {
    # Create virtualenv folder if missing
    if [ ! -d $root_path/.venv ]
    then
        echo "Setting up new virtualenv..."
        uv venv || exit 1
    fi

    # Install or update dependencies
    source $root_path/.venv/bin/activate || exit 1
    uv pip install -r $script_path/requirements.txt --upgrade
    deactivate
}

script_path="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
root_path="$(dirname "${script_path}")"

# Check for exactly one argument
if [ "$#" -ne 1 ]; then
  echo -e "Not enough arguments.\nUsage: $0 <version-number (e.g. 138.0)>" >&2
  exit 1
fi

VERSION="$1"
# Check if the version number ends with .0, if not warn and add it.
if [[ $VERSION != *.0 ]]; then
  VERSION="${VERSION}.0"
  echo -e "Warning: Version number should end with .0. Changed to: $VERSION"
fi

setupVirtualEnv
source $root_path/.venv/bin/activate || exit 1

python scripts/fenix_stats.py --version $VERSION
python scripts/csv_extract_product.py --product fenix

python scripts/firefox_stats.py --version $VERSION
python scripts/csv_extract_product.py --product firefox

# Generate JSON for chart
python scripts/build_chart_json.py --version $VERSION
