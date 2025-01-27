#!/usr/bin/env python3

# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

"""
Extract completion statistics for product over time, store them as CSV

python extract_product.py --path path_to_mozilla_unified_clone
"""

from functions import get_stats_path
import argparse
import csv
import json
import os
import re


def main():
    cl_parser = argparse.ArgumentParser()
    cl_parser.add_argument(
        "--product",
        required=True,
        dest="product",
        help="Product name",
        choices=["fenix", "firefox"],
    )
    args = cl_parser.parse_args()

    product = args.product
    stats_path = get_stats_path()

    version_re = re.compile(r"_([\d_]*)")

    # List all JSON files starting with the product name
    json_files = [
        f
        for f in os.listdir(stats_path)
        if f.startswith(product) and f.endswith(".json")
    ]
    json_files.sort()

    locale_data = {}
    locales = []
    for json_file in json_files:
        with open(os.path.join(stats_path, json_file), "r") as f:
            data = json.load(f)
            version = version_re.search(json_file).group(1).replace("_", ".")
            for locale, percentage in data.items():
                if version not in locale_data:
                    locale_data[version] = {}
                if locale not in locales:
                    locales.append(locale)
                locale_data[version][locale] = percentage
    locales.sort()

    csv_file = os.path.join(stats_path, f"{product}_locales.csv")
    with open(csv_file, "w") as csv_file:
        fieldnames = ["Version", "Major version"] + locales
        writer = csv.DictWriter(csv_file, fieldnames=fieldnames, lineterminator="\n")

        writer.writeheader()
        for version, percentages in locale_data.items():
            row = {
                "Version": f"'{version}",
                "Major version": int(version.split(".")[0]),
            }  # Force as string when imported in Google Sheets
            row.update(percentages)
            writer.writerow(row)


if __name__ == "__main__":
    main()
