#!/usr/bin/env python3

# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

"""
Extract completion statistics for Firefox Desktop

python firefox_stats.py --version 147.0
"""

from __future__ import annotations

import json
import os
import sys

from base_stats import StatsExtractor
from functions import StringList, parse_file, update_git_repository
from logging_config import get_logger
from moz.l10n.paths import L10nConfigPaths


logger = get_logger(__name__)


class FirefoxStatsExtractor(StatsExtractor):
    """Stats extractor for Firefox Desktop."""

    def _get_config_params(self) -> list[str]:
        """Get config parameters needed for Firefox."""
        return ["mozilla_firefox_path", "l10n_path"]

    def get_product_name(self) -> str:
        """Get product name."""
        return "firefox"

    def setup_repositories(self, firefox_releases: dict[str, str], *paths: str) -> None:
        """Update both mozilla-firefox and l10n repositories."""
        source_path, l10n_path = paths

        # Update source repository to the release tag
        update_git_repository(firefox_releases[self.version], source_path)

        # Get and update l10n repository changeset
        l10n_changeset = self._get_l10n_repo_changeset(source_path)
        update_git_repository(l10n_changeset, l10n_path)

    def _get_l10n_repo_changeset(self, source_path: str) -> str:
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

    def extract_string_list(self, *paths: str) -> tuple[StringList, list[str]]:
        """
        Extract localization strings for Firefox Desktop.

        Args:
            *paths: Tuple containing (source_path, l10n_path)

        Returns:
            Tuple of (string_list dict, list of locales)

        Raises:
            SystemExit: If required config files are missing
        """
        source_path, l10n_path = paths

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
                logger.warning(
                    f"Missing {len(missing_files)} files for locale {locale}:"
                )
                for missing_file in missing_files:
                    logger.warning(f"  {missing_file}")

        return string_list, locales


def main() -> None:
    """Main entry point for firefox stats extraction."""
    FirefoxStatsExtractor.main()


if __name__ == "__main__":
    main()
