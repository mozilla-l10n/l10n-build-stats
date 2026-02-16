#!/usr/bin/env python3

# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

"""
Build JSON file for charting completion statistics over time
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys

from typing import Any, TypedDict

import aiohttp

from functions import get_json_files, get_stats_path, get_version_from_filename
from logging_config import get_logger, setup_logging


logger = get_logger(__name__)


class LocaleRecord(TypedDict, total=False):
    name: str
    fenix: dict[int, float | int]
    firefox: dict[int, float | int]


CompletionData = dict[str, LocaleRecord]
LocaleNameMap = dict[str, str]


async def get_locale_names() -> LocaleNameMap:
    """
    Fetch locale names from Pontoon API asynchronously.

    Returns:
        Dictionary mapping locale codes to display names

    Raises:
        SystemExit: If API requests fail
    """
    url: str | None = "https://pontoon.mozilla.org/api/v2/locales/?fields=code,name"
    page = 1
    locale_names: LocaleNameMap = {}

    try:
        async with aiohttp.ClientSession() as session:
            while url:
                logger.info(f"Reading locales (page {page})")
                async with session.get(url) as response:
                    response.raise_for_status()
                    data: dict[str, Any] = await response.json()
                    for locale in data.get("results", {}):
                        locale_names[locale["code"]] = locale["name"]
                    # Get the next page URL
                    url = data.get("next")
                    page += 1

        return locale_names
    except aiohttp.ClientError as e:
        logger.error(f"Error fetching data: {e}")
        sys.exit(1)


async def async_main(version: str) -> None:
    """
    Async main function for building chart data.

    Args:
        version: Current version to use for filtering
    """
    # Get locale names from Pontoon
    locale_names = await get_locale_names()

    # Only extract data for the last X versions
    max_versions = 30
    version_int = int(version.split(".")[0])
    versions = [str(v) for v in range(version_int, version_int - max_versions, -1)]

    stats_path = get_stats_path()
    completion_data: CompletionData = {}
    for product in ["fenix", "firefox"]:
        # List all JSON files starting with the product name
        json_files = get_json_files(product)

        for json_file in json_files:
            _, major_version = get_version_from_filename(json_file)
            if major_version not in versions:
                continue
            with open(os.path.join(stats_path, json_file)) as f:
                version_data: dict[str, float | int] = json.load(f)
                for locale, percentage in version_data.items():
                    if locale not in completion_data:
                        completion_data[locale] = {
                            "name": locale_names.get(locale, locale),
                        }
                    if product not in completion_data[locale]:
                        completion_data[locale][product] = {}
                    completion_data[locale][product][major_version] = percentage

    output_file = os.path.abspath(
        os.path.join(os.path.dirname(__file__), os.pardir, "docs", "data", "data.json")
    )
    with open(output_file, "w") as f:
        json.dump(completion_data, f)


def main() -> None:
    """Main entry point for building chart JSON."""
    setup_logging()

    cl_parser = argparse.ArgumentParser()
    cl_parser.add_argument(
        "--version",
        required=True,
        dest="version",
        help="Current version",
    )
    args = cl_parser.parse_args()

    asyncio.run(async_main(args.version))


if __name__ == "__main__":
    main()
