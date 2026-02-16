"""Base class for stats extraction scripts."""

from __future__ import annotations

import argparse
import logging
import sys

from abc import ABC, abstractmethod

from config import read_config
from functions import (
    StringList,
    get_firefox_releases,
    store_completion,
    update_git_repository,
)


logger = logging.getLogger(__name__)


class StatsExtractor(ABC):
    """
    Abstract base class for statistics extraction.

    Subclasses must implement extract_string_list() and get_product_name().
    """

    def __init__(self, version: str):
        """
        Initialize stats extractor.

        Args:
            version: Product version to extract (e.g., "147.0")
        """
        self.version = version
        self.config_params = self._get_config_params()

    @abstractmethod
    def _get_config_params(self) -> list[str]:
        """
        Get list of config parameters needed.

        Returns:
            List of config parameter names
        """
        pass

    @abstractmethod
    def extract_string_list(self, *paths: str) -> tuple[StringList, list[str]]:
        """
        Extract string list and locales for the product.

        Args:
            *paths: Configuration paths (from config file)

        Returns:
            Tuple of (string_list dict, list of locales)
        """
        pass

    @abstractmethod
    def get_product_name(self) -> str:
        """
        Get the product name.

        Returns:
            Product name ("firefox" or "fenix")
        """
        pass

    @abstractmethod
    def setup_repositories(self, firefox_releases: dict[str, str], *paths: str) -> None:
        """
        Update repositories to the correct versions.

        Args:
            firefox_releases: Dict mapping versions to git tags
            *paths: Configuration paths
        """
        pass

    def run(self) -> None:
        """
        Main extraction workflow.

        Raises:
            SystemExit: On any error
        """
        try:
            # Read configuration
            config_paths = read_config(self.config_params)

            # Get repository path (first config param is always source path)
            source_path = config_paths[0]

            # Get Firefox releases
            firefox_releases = get_firefox_releases(source_path)
            if self.version not in firefox_releases:
                logger.error(
                    f"Version {self.version} not available as a release in repository tags"
                )
                sys.exit(1)

            # Setup repositories
            self.setup_repositories(firefox_releases, *config_paths)

            # Extract statistics
            logger.info(f"Extracting statistics for {self.get_product_name()} {self.version}")
            string_list, locales = self.extract_string_list(*config_paths)

            # Store completion levels
            store_completion(string_list, self.version, locales, self.get_product_name())
            logger.info("Statistics extraction completed successfully")

        except RuntimeError as e:
            logger.error(f"Runtime error: {e}")
            sys.exit(1)
        except Exception as e:
            logger.error(f"Unexpected error: {e}", exc_info=True)
            sys.exit(1)

    @classmethod
    def main(cls) -> None:
        """
        CLI entry point for the stats extractor.

        Parses command-line arguments and runs the extractor.
        """
        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        )

        parser = argparse.ArgumentParser(
            description=f"Extract localization statistics for {cls.__name__}"
        )
        parser.add_argument(
            "--version",
            required=True,
            dest="version",
            help="Version to extract (e.g., '147.0')",
        )
        args = parser.parse_args()

        extractor = cls(args.version)
        extractor.run()
