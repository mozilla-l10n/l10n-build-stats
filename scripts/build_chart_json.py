#!/usr/bin/env python3

# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

"""
Build JSON file for charting completion statistics over time
"""

from functions import get_stats_path
import argparse
import json
import os
import re


def main():
    cl_parser = argparse.ArgumentParser()
    cl_parser.add_argument(
        "--version",
        required=True,
        dest="version",
        help="Current version",
    )
    args = cl_parser.parse_args()

    # Only extract data for the last 25 versions
    version_int = int(args.version.split(".")[0])
    versions = list(range(version_int, version_int - 25, -1))

    stats_path = get_stats_path()
    version_re = re.compile(r"_([\d_]*)")
    completion_data = {}
    for product in ["fenix", "firefox"]:
        # List all JSON files starting with the product name
        json_files = [
            f
            for f in os.listdir(stats_path)
            if f.startswith(product) and f.endswith(".json")
        ]
        json_files.sort()

        for json_file in json_files:
            version = version_re.search(json_file).group(1).replace("_", ".")
            version_nr = int(version.split(".")[0])
            if version_nr not in versions:
                continue
            with open(os.path.join(stats_path, json_file), "r") as f:
                version_data = json.load(f)
                for locale, percentage in version_data.items():
                    if locale not in completion_data:
                        completion_data[locale] = {}
                    if product not in completion_data[locale]:
                        completion_data[locale][product] = {}
                    completion_data[locale][product][version_nr] = percentage

    output_file = os.path.abspath(
        os.path.join(os.path.dirname(__file__), os.pardir, "docs", "data", "data.json")
    )
    with open(output_file, "w") as f:
        json.dump(completion_data, f)


if __name__ == "__main__":
    main()
