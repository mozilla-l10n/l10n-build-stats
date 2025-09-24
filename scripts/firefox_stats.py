#!/usr/bin/env python3

# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

"""
Extract completion statistics for Fenix

python firefox_stats.py --path path_to_mozilla_firefox_clone
"""

from __future__ import annotations
from typing import Any


from compare_locales import parser
from functions import (
    get_firefox_releases,
    read_config,
    store_completion,
    update_git_repository,
    StringList,
)
from moz.l10n.paths import L10nConfigPaths
import argparse
import json
import os
import sys


def extract_string_list(
    source_path: str, l10n_path: str
) -> tuple[StringList, list[str]]:
    toml_path: str = os.path.join(source_path, "browser", "locales", "l10n.toml")
    if not os.path.exists(toml_path):
        sys.exit(f"Missing config file {os.path.relpath(toml_path, source_path)}.")

    # Only look at release locales
    locales_path: str = os.path.join(
        source_path, "browser", "locales", "shipped-locales"
    )
    with open(locales_path, "r") as f:
        locales: list[str] = f.read().splitlines()
    locales.remove("en-US")
    locales.sort()

    string_list: StringList = {}

    project_config_paths: L10nConfigPaths = L10nConfigPaths(toml_path)
    basedir: str = project_config_paths.base
    reference_files: list[str] = [
        ref_path for ref_path in project_config_paths.ref_paths
    ]

    for reference_file in reference_files:
        file_name: str = os.path.relpath(reference_file, basedir)
        if os.path.basename(file_name).startswith("."):
            continue

        string_list[file_name] = {
            "source": [],
        }

        file_extension: str = os.path.splitext(file_name)[1]
        try:
            file_parser: Any = parser.getParser(file_extension)
            file_parser.readFile(reference_file)
            entities: list[Any] = file_parser.parse()
            for entity in entities:
                # Ignore Junk
                if isinstance(entity, parser.Junk):
                    continue
                string_list[file_name]["source"].append(str(entity))
                if file_extension == ".ftl":
                    # Store attributes separately
                    for attribute in entity.attributes:
                        attr_string_id = f"{entity}.{attribute}"
                        string_list[file_name]["source"].append(attr_string_id)
        except Exception as e:
            print(f"Error parsing file: {file_name}")
            string_list.pop(file_name)
            print(e)

    for locale in locales:
        for file_name in string_list:
            string_list[file_name][locale] = []

            l10n_file_name: str = os.path.join(
                l10n_path, locale, file_name.replace("locales/en-US/", "")
            )
            if not os.path.exists(l10n_file_name):
                print(f"Missing file for {locale}: {l10n_file_name}")
                continue

            file_extension = os.path.splitext(l10n_file_name)[1]
            try:
                file_parser = parser.getParser(file_extension)  # type: ignore[assignment]
                file_parser.readFile(l10n_file_name)
                entities = file_parser.parse()
                for entity in entities:
                    # Ignore Junk
                    if isinstance(entity, parser.Junk):
                        continue
                    # Don't count entity or attribute if it doesn't exist in source
                    entity_id = str(entity)
                    if entity_id in string_list[file_name]["source"]:
                        string_list[file_name][locale].append(entity_id)
                    if file_extension == ".ftl":
                        # Store attributes separately
                        for attribute in entity.attributes:
                            attr_string_id = f"{entity}.{attribute}"
                            if attr_string_id in string_list[file_name]["source"]:
                                string_list[file_name][locale].append(attr_string_id)
            except Exception as e:
                print(
                    f"Error parsing file: {os.path.relpath(l10n_file_name, l10n_path)}"
                )
                print(e)

    return string_list, locales


def get_l10n_repo_changeset(source_path: str) -> str:
    l10n_changesets: str = os.path.join(
        source_path, "browser", "locales", "l10n-changesets.json"
    )
    with open(l10n_changesets, "r") as f:
        data: dict[str, dict[str, str]] = json.load(f)
        return data["it"]["revision"]


def main() -> None:
    cl_parser = argparse.ArgumentParser()
    cl_parser.add_argument(
        "--version",
        required=True,
        dest="version",
        help="Version of Firefox to check",
    )
    args = cl_parser.parse_args()

    version: str = args.version
    [source_path, l10n_path] = read_config(["mozilla_firefox_path", "l10n_path"])

    # Get the release tags from mozilla-unified
    firefox_releases = get_firefox_releases(source_path)
    if version not in firefox_releases:
        sys.exit(f"Version {version} not available as a release in repository tags")

    # Update the source repository to the tag
    update_git_repository(firefox_releases[version], source_path)

    # Get the version of the l10n repo
    l10n_changeset: str = get_l10n_repo_changeset(source_path)
    update_git_repository(l10n_changeset, l10n_path)

    # Extract list statistics
    string_list, locales = extract_string_list(source_path, l10n_path)

    # Store completion levels in CSV file
    store_completion(string_list, version, locales, "firefox")


if __name__ == "__main__":
    main()
