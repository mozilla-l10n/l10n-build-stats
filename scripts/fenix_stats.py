#!/usr/bin/env python3

# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

"""
Extract completion statistics for Firefox for Android (fenix)

python fenix_stats.py --path path_to_mozilla_unified_clone
"""

from compare_locales import paths
from functions import (
    get_firefox_releases,
    read_config,
    store_completion,
    update_repository,
)
import xml.etree.ElementTree as ET
import argparse
import os
import sys


def parse_XML_file(file_path, source=False):
    """
    Parse the strings.xml file and return a list of string IDs.

    If it's the source locale, exclude strings with tools:ignore="UnusedResources".
    """
    string_ids = []

    try:
        tree = ET.parse(file_path)
        root = tree.getroot()
        for string in root.findall("string"):
            if source:
                tools_ignore = string.attrib.get(
                    "{http://schemas.android.com/tools}ignore", ""
                )
                if "UnusedResources" not in tools_ignore.split(","):
                    string_ids.append(string.attrib["name"])
            else:
                string_ids.append(string.attrib["name"])
    except ET.ParseError as e:
        print(f"Error parsing XML file: {e}")
    except Exception as e:
        print(f"Unexpected error: {e}")

    return string_ids


def extract_string_list(source_path):
    toml_paths = {
        "fenix": os.path.join(source_path, "mobile", "android", "fenix", "l10n.toml"),
        "android-components": os.path.join(
            source_path, "mobile", "android", "android-components", "l10n.toml"
        ),
    }

    string_list = {}
    all_locales = []
    for product, toml_path in toml_paths.items():
        if not os.path.exists(toml_path):
            sys.exit(f"Missing config file {os.path.relpath(toml_path, source_path)}.")

        basedir = os.path.dirname(toml_path)
        project_config = paths.TOMLParser().parse(toml_path, env={"l10n_base": ""})
        basedir = os.path.join(basedir, project_config.root)

        # Get the list of message IDs for the source locale
        files = paths.ProjectFiles(None, [project_config])
        for l10n_file, source_file, _, _ in files:
            key = f"{product}:{os.path.relpath(source_file, basedir)}"
            string_list[key] = {
                "source": parse_XML_file(source_file, source=True),
            }

        locales = project_config.all_locales
        # Storing a superset of all locales across TOML files
        all_locales = list(set(locales + all_locales))
        for locale in locales:
            files = paths.ProjectFiles(locale, [project_config])
            for l10n_file, source_file, _, _ in files:
                # Ignore missing files for locale
                if not os.path.exists(l10n_file):
                    continue
                key = f"{product}:{os.path.relpath(source_file, basedir)}"
                if key not in string_list:
                    print(
                        f"Extra file {os.path.relpath(l10n_file, basedir)} in {locale}"
                    )
                    continue
                # Remove extra strings not available in source
                string_list[key][locale] = [
                    id
                    for id in parse_XML_file(l10n_file)
                    if id in string_list[key]["source"]
                ]

    return string_list, locales


def main():
    cl_parser = argparse.ArgumentParser()
    cl_parser.add_argument(
        "--version",
        required=True,
        dest="version",
        help="Version of Firefox to check",
    )
    args = cl_parser.parse_args()

    version = args.version
    [source_path] = read_config(["mozilla_unified_path"])

    # Get the release tags from mozilla-unified
    firefox_releases = get_firefox_releases(source_path)
    if version not in firefox_releases:
        sys.exit(f"Version {version} not available as a release in repository tags")

    # Update the repository to the tag
    update_repository(firefox_releases[version], source_path)

    # Extract list statistics
    string_list, locales = extract_string_list(source_path)

    # Store completion levels in CSV file
    store_completion(string_list, version, locales, "fenix")


if __name__ == "__main__":
    main()
