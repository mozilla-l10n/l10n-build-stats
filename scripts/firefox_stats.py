#!/usr/bin/env python3

# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

"""
Extract completion statistics for Fenix

python firefox_stats.py --path path_to_mozilla_firefox_clone
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys

from functions import (
    StringList,
    get_firefox_releases,
    parse_file,
    read_config,
    store_completion,
    update_git_repository,
)
from moz.l10n.paths import L10nConfigPaths


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def extract_string_list(
    source_path: str, l10n_path: str
) -> tuple[StringList, list[str]]:
    """
    Extract localization strings for Firefox Desktop.

    Args:
        source_path: Path to mozilla-firefox repository
        l10n_path: Path to firefox-l10n repository

    Returns:
        Tuple of (string_list dict, list of locales)

    Raises:
        SystemExit: If required config files are missing
    """
    toml_path: str = os.path.join(source_path, "browser", "locales", "l10n.toml")
    if not os.path.exists(toml_path):
        sys.exit(f"Missing config file {os.path.relpath(toml_path, source_path)}.")

    # Only look at release locales
    locales_path: str = os.path.join(
        source_path, "browser", "locales", "shipped-locales"
    )
    with open(locales_path) as f:
        locales: list[str] = f.read().splitlines()
    locales.remove("en-US")
    locales.sort()

    string_list: StringList = {}

    project_config_paths = L10nConfigPaths(toml_path)
    basedir = project_config_paths.base
    reference_files = [ref_path for ref_path in project_config_paths.ref_paths]

    for reference_file in reference_files:
        rel_file: str = os.path.relpath(reference_file, basedir)
        parse_file(reference_file, rel_file, "source", string_list)

    for locale in locales:
        missing_files: list[str] = []
        for rel_file in string_list:
            l10n_file_name: str = os.path.join(
                l10n_path, locale, rel_file.replace("locales/en-US/", "")
            )
            if not os.path.exists(l10n_file_name):
                missing_files.append(os.path.relpath(l10n_file_name, l10n_path))
                continue

            parse_file(l10n_file_name, rel_file, locale, string_list)
        if missing_files:
            logger.warning(f"Missing {len(missing_files)} files for locale {locale}:")
            for missing_file in missing_files:
                logger.warning(f"  {missing_file}")

    return string_list, locales


def get_l10n_repo_changeset(source_path: str) -> str:
    """
    Get the l10n repository changeset from Firefox source.

    Args:
        source_path: Path to mozilla-firefox repository

    Returns:
        Git commit hash for the l10n repository

    Raises:
        FileNotFoundError: If l10n-changesets.json is missing
        KeyError: If 'it' locale data is missing
    """
    l10n_changesets: str = os.path.join(
        source_path, "browser", "locales", "l10n-changesets.json"
    )
    with open(l10n_changesets) as f:
        data: dict[str, dict[str, str]] = json.load(f)
        return data["it"]["revision"]


def main() -> None:
    """Main entry point for firefox stats extraction."""
    cl_parser = argparse.ArgumentParser()
    cl_parser.add_argument(
        "--version",
        required=True,
        dest="version",
        help="Version of Firefox to check",
    )
    args = cl_parser.parse_args()

    try:
        version: str = args.version
        source_path, l10n_path = read_config(["mozilla_firefox_path", "l10n_path"])

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

        # Store completion levels in JSON file
        store_completion(string_list, version, locales, "firefox")
    except RuntimeError as e:
        logger.error(f"Runtime error: {e}")
        sys.exit(1)
    except (FileNotFoundError, KeyError) as e:
        logger.error(f"Configuration error: {e}")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Unexpected error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
