#!/usr/bin/env python3

# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

"""
Build JSON file for charting completion statistics over time
"""

from __future__ import annotations
from typing import Any, Dict, List, Match, Pattern, TypedDict

from functions import get_stats_path
import argparse
import json
import os
import re
import requests
import sys

class LocaleRecord(TypedDict, total=False):
    name: str
    fenix: Dict[int, float | int]
    firefox: Dict[int, float | int]


CompletionData = Dict[str, LocaleRecord]
LocaleNameMap = Dict[str, str]


def get_locale_names() -> LocaleNameMap:
    url: str | None = "https://pontoon.mozilla.org/api/v2/locales"
    page: int = 1
    locale_names: LocaleNameMap = {}
    try:
        while url:
            print(f"Reading locales (page {page})")
            response: requests.Response = requests.get(url)
            response.raise_for_status()
            data: Dict[str, Any] = response.json()
            for locale in data.get("results", {}):
                locale_names[locale["code"]] = locale["name"]
            # Get the next page URL
            url = data.get("next")
            page += 1

        return locale_names
    except requests.RequestException as e:
        print(f"Error fetching data: {e}")
        sys.exit()


def main() -> None:
    cl_parser = argparse.ArgumentParser()
    cl_parser.add_argument(
        "--version",
        required=True,
        dest="version",
        help="Current version",
    )
    args = cl_parser.parse_args()

    # Get locale names from Pontoon
    locale_names: LocaleNameMap = get_locale_names()

    # Only extract data for the last X versions
    max_versions: int = 30
    version_int: int = int(args.version.split(".")[0])
    versions: List[int] = list(range(version_int, version_int - max_versions, -1))

    stats_path: str = get_stats_path()
    version_re: Pattern[str] = re.compile(r"_([\d_]*)")
    completion_data: CompletionData = {}
    for product in ["fenix", "firefox"]:
        # List all JSON files starting with the product name
        json_files: List[str] = [
            f
            for f in os.listdir(stats_path)
            if f.startswith(product) and f.endswith(".json")
        ]
        json_files.sort()

        for json_file in json_files:
            match: Match[str] | None = version_re.search(json_file)
            assert match is not None
            version = match.group(1).replace("_", ".")
            version_nr: int = int(version.split(".")[0])
            if version_nr not in versions:
                continue
            with open(os.path.join(stats_path, json_file), "r") as f:
                version_data: Dict[str, float | int] = json.load(f)
                for locale, percentage in version_data.items():
                    if locale not in completion_data:
                        completion_data[locale] = {
                            "name": locale_names.get(locale, locale),
                        }
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
