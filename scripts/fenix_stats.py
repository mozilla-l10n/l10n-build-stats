#!/usr/bin/env python3

# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

"""
Extract completion statistics for Firefox for Android (fenix)

python fenix_stats.py --version 147.0
"""

from __future__ import annotations

import logging
import os
import sys

from base_stats import StatsExtractor
from functions import StringList, parse_file, update_git_repository
from moz.l10n.paths import L10nConfigPaths, get_android_locale


logger = logging.getLogger(__name__)


class FenixStatsExtractor(StatsExtractor):
    """Stats extractor for Firefox for Android (Fenix)."""

    def _get_config_params(self) -> list[str]:
        """Get config parameters needed for Fenix."""
        return ["mozilla_firefox_path"]

    def get_product_name(self) -> str:
        """Get product name."""
        return "fenix"

    def setup_repositories(self, firefox_releases: dict[str, str], *paths: str) -> None:
        """Update mozilla-firefox repository to the release tag."""
        source_path = paths[0]
        update_git_repository(firefox_releases[self.version], source_path)

    def extract_string_list(self, *paths: str) -> tuple[StringList, list[str]]:
        """
        Extract localization strings for Firefox for Android.

        Args:
            *paths: Tuple containing (source_path,)

        Returns:
            Tuple of (string_list dict, list of locales)

        Raises:
            SystemExit: If required TOML config files are missing
        """
        source_path = paths[0]

        toml_paths: dict[str, str] = {
            "fenix": os.path.join(source_path, "mobile", "android", "fenix", "l10n.toml"),
            "android-components": os.path.join(
                source_path, "mobile", "android", "android-components", "l10n.toml"
            ),
        }

        string_list: StringList = {}
        all_locales: list[str] = []
        locales: list[str] = []

        for product, toml_path in toml_paths.items():
            if not os.path.exists(toml_path):
                sys.exit(f"Missing config file {os.path.relpath(toml_path, source_path)}.")

            project_config_paths = L10nConfigPaths(
                toml_path, locale_map={"android_locale": get_android_locale}
            )
            basedir = project_config_paths.base
            reference_files = [ref_path for ref_path in project_config_paths.ref_paths]

            for reference_file in reference_files:
                key = f"{product}:{os.path.relpath(reference_file, basedir)}"
                parse_file(reference_file, key, "source", string_list, self.version)

            locales = list(project_config_paths.all_locales)
            locales.sort()
            # Storing a superset of all locales across TOML files
            all_locales = list(set(locales + all_locales))

            all_files = [
                (ref_path, tgt_path)
                for (ref_path, tgt_path), _ in project_config_paths.all().items()
            ]
            for locale in locales:
                locale_files = [
                    (ref_path, tgt_path)
                    for (ref_path, raw_tgt_path) in all_files
                    if os.path.exists(
                        tgt_path := project_config_paths.format_target_path(
                            raw_tgt_path, locale
                        )
                    )
                ]

                for source_file, l10n_file in locale_files:
                    # Ignore missing files for locale
                    if not os.path.exists(l10n_file):
                        continue
                    key = f"{product}:{os.path.relpath(source_file, basedir)}"
                    if key not in string_list:
                        logger.warning(
                            f"Extra file {os.path.relpath(l10n_file, basedir)} in {locale}"
                        )
                        continue
                    parse_file(l10n_file, key, locale, string_list, self.version)

        return string_list, locales


def main() -> None:
    """Main entry point for fenix stats extraction."""
    FenixStatsExtractor.main()


if __name__ == "__main__":
    main()
