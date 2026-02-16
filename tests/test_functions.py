"""Tests for functions module."""

import json
import os

# Add parent directory to path to import scripts
import sys

from unittest.mock import patch


sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

from functions import (
    get_json_files,
    get_stats_path,
    get_version_from_filename,
    store_completion,
)


class TestGetVersionFromFilename:
    """Tests for get_version_from_filename function."""

    def test_single_digit_version(self):
        """Test version extraction with single digit major version."""
        version, major = get_version_from_filename("firefox_147_0.json")
        assert version == "147.0"
        assert major == "147"

    def test_multiple_digits_version(self):
        """Test version extraction with multiple version components."""
        version, major = get_version_from_filename("fenix_100_1_2.json")
        assert version == "100.1.2"
        assert major == "100"

    def test_fenix_product(self):
        """Test version extraction for fenix product."""
        version, major = get_version_from_filename("fenix_79_0.json")
        assert version == "79.0"
        assert major == "79"


class TestGetStatsPath:
    """Tests for get_stats_path function."""

    def test_returns_absolute_path(self):
        """Test that stats path is absolute."""
        path = get_stats_path()
        assert os.path.isabs(path)

    def test_ends_with_stats(self):
        """Test that path ends with 'stats'."""
        path = get_stats_path()
        assert path.endswith("stats")


class TestStoreCompletion:
    """Tests for store_completion function."""

    def test_calculates_completion_percentage(self, tmp_path):
        """Test completion percentage calculation."""
        string_list = {
            "file1.ftl": {
                "source": ["msg1", "msg2", "msg3", "msg4"],
                "it": ["msg1", "msg2", "msg3"],
                "fr": ["msg1", "msg2"],
            },
            "file2.ftl": {
                "source": ["msg5", "msg6"],
                "it": ["msg5", "msg6"],
                "fr": ["msg5"],
            },
        }
        locales = ["source", "it", "fr"]
        version = "147.0"
        product = "firefox"

        with patch("functions.get_stats_path", return_value=str(tmp_path)):
            store_completion(string_list, version, locales, product)

        output_file = tmp_path / "firefox_147_0.json"
        assert output_file.exists()

        with open(output_file) as f:
            data = json.load(f)

        # it: 5/6 = 0.8333
        # fr: 3/6 = 0.5
        assert data["it"] == 0.8333
        assert data["fr"] == 0.5

    def test_excludes_source_locale(self, tmp_path):
        """Test that 'source' locale is not included in output."""
        string_list = {
            "file1.ftl": {
                "source": ["msg1", "msg2"],
                "it": ["msg1"],
            },
        }
        locales = ["source", "it"]
        version = "100.0"
        product = "fenix"

        with patch("functions.get_stats_path", return_value=str(tmp_path)):
            store_completion(string_list, version, locales, product)

        output_file = tmp_path / "fenix_100_0.json"
        with open(output_file) as f:
            data = json.load(f)

        assert "source" not in data
        assert "it" in data


class TestGetJsonFiles:
    """Tests for get_json_files function."""

    def test_filters_by_product(self, tmp_path):
        """Test that only matching product files are returned."""
        # Create test files
        (tmp_path / "firefox_100_0.json").touch()
        (tmp_path / "firefox_101_0.json").touch()
        (tmp_path / "fenix_100_0.json").touch()
        (tmp_path / "other.json").touch()

        with patch("functions.get_stats_path", return_value=str(tmp_path)):
            firefox_files = get_json_files("firefox")
            fenix_files = get_json_files("fenix")

        assert len(firefox_files) == 2
        assert len(fenix_files) == 1
        assert "firefox_100_0.json" in firefox_files
        assert "firefox_101_0.json" in firefox_files
        assert "fenix_100_0.json" in fenix_files

    def test_returns_sorted_list(self, tmp_path):
        """Test that files are returned in sorted order."""
        (tmp_path / "firefox_102_0.json").touch()
        (tmp_path / "firefox_100_0.json").touch()
        (tmp_path / "firefox_101_0.json").touch()

        with patch("functions.get_stats_path", return_value=str(tmp_path)):
            files = get_json_files("firefox")

        assert files == [
            "firefox_100_0.json",
            "firefox_101_0.json",
            "firefox_102_0.json",
        ]
