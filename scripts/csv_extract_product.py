#!/usr/bin/env python3

# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

"""
Extract completion statistics for product over time, store them as CSV

python extract_product.py --path path_to_mozilla_firefox_clone
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
        choices=["fenix", "firefox", "fxios"],
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

    raw_build_data = {}
    locales = []
    for json_file in json_files:
        with open(os.path.join(stats_path, json_file), "r") as f:
            data = json.load(f)
            version = version_re.search(json_file).group(1).replace("_", ".")
            major_version = version.split(".")[0]
            for locale, percentage in data.items():
                if major_version not in raw_build_data:
                    raw_build_data[major_version] = {
                        "version": version,
                        "completion": {},
                    }
                if locale not in locales:
                    locales.append(locale)
                raw_build_data[major_version]["completion"][locale] = percentage
    locales.sort()

    # Sort the dictionary by major version
    build_data = {
        k: raw_build_data[k] for k in sorted(raw_build_data, key=lambda x: int(x))
    }

    csv_file = os.path.join(stats_path, f"{product}_locales.csv")
    with open(csv_file, "w") as csv_file:
        fieldnames = ["Version", "Major version"] + locales
        writer = csv.DictWriter(csv_file, fieldnames=fieldnames, lineterminator="\n")

        writer.writeheader()
        for major_version, version_data in build_data.items():
            row = {
                "Version": f"'{version_data['version']}",
                "Major version": int(major_version),
            }  # Force as string when imported in Google Sheets
            row.update(version_data["completion"])
            writer.writerow(row)


if __name__ == "__main__":
    main()
