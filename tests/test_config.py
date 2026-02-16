"""Tests for config module."""

import os
import tempfile

from pathlib import Path

import pytest

import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

from config import Config, ConfigError


class TestConfig:
    """Tests for Config class."""

    def test_load_valid_config(self, tmp_path):
        """Test loading a valid config file."""
        config_file = tmp_path / "config"
        config_file.write_text(
            """
# Comment line
mozilla_firefox_path="/path/to/firefox"
l10n_path=/path/to/l10n

# Another comment
stats_path = "/path/to/stats"
"""
        )

        config = Config(str(config_file))
        assert config.get("mozilla_firefox_path", validate=False) == "/path/to/firefox"
        assert config.get("l10n_path", validate=False) == "/path/to/l10n"
        assert config.get("stats_path", validate=False) == "/path/to/stats"

    def test_missing_config_file(self):
        """Test error when config file doesn't exist."""
        with pytest.raises(ConfigError, match="Config file not found"):
            Config("/nonexistent/path/config")

    def test_invalid_config_line_no_equals(self, tmp_path):
        """Test error when config line has no = separator."""
        config_file = tmp_path / "config"
        config_file.write_text("invalid_line_without_equals")

        with pytest.raises(ConfigError, match="missing '=' separator"):
            Config(str(config_file))

    def test_invalid_config_line_empty_key(self, tmp_path):
        """Test error when config line has empty key."""
        config_file = tmp_path / "config"
        config_file.write_text("=value_without_key")

        with pytest.raises(ConfigError, match="empty key"):
            Config(str(config_file))

    def test_get_missing_key(self, tmp_path):
        """Test error when getting non-existent key."""
        config_file = tmp_path / "config"
        config_file.write_text('key1="value1"')

        config = Config(str(config_file))
        with pytest.raises(ConfigError, match="Configuration key 'missing' not found"):
            config.get("missing")

    def test_get_with_path_validation(self, tmp_path):
        """Test path validation when getting config value."""
        # Create a real directory
        real_path = tmp_path / "real_dir"
        real_path.mkdir()

        config_file = tmp_path / "config"
        config_file.write_text(f'valid_path="{real_path}"\nfake_path="/fake/path"')

        config = Config(str(config_file))

        # Should work for existing path
        assert config.get("valid_path") == str(real_path)

        # Should fail for non-existent path with validation
        with pytest.raises(ConfigError, match="does not exist"):
            config.get("fake_path", validate=True)

        # Should work without validation
        assert config.get("fake_path", validate=False) == "/fake/path"

    def test_get_multiple(self, tmp_path):
        """Test getting multiple config values."""
        config_file = tmp_path / "config"
        config_file.write_text('key1="value1"\nkey2="value2"\nkey3="value3"')

        config = Config(str(config_file))
        values = config.get_multiple(["key1", "key2", "key3"], validate=False)

        assert values == ("value1", "value2", "value3")

    def test_get_multiple_missing_key(self, tmp_path):
        """Test error when one of multiple keys is missing."""
        config_file = tmp_path / "config"
        config_file.write_text('key1="value1"')

        config = Config(str(config_file))
        with pytest.raises(ConfigError, match="Configuration key 'key2' not found"):
            config.get_multiple(["key1", "key2"], validate=False)

    def test_all_keys(self, tmp_path):
        """Test getting all configuration keys."""
        config_file = tmp_path / "config"
        config_file.write_text('key1="value1"\nkey2="value2"\n# comment\nkey3="value3"')

        config = Config(str(config_file))
        keys = config.all_keys

        assert set(keys) == {"key1", "key2", "key3"}

    def test_strips_quotes(self, tmp_path):
        """Test that quotes are stripped from values."""
        config_file = tmp_path / "config"
        config_file.write_text(
            """
double_quoted="value with double quotes"
single_quoted='value with single quotes'
no_quotes=value without quotes
"""
        )

        config = Config(str(config_file))
        assert config.get("double_quoted", validate=False) == "value with double quotes"
        assert config.get("single_quoted", validate=False) == "value with single quotes"
        assert config.get("no_quotes", validate=False) == "value without quotes"

    def test_empty_config_file(self, tmp_path):
        """Test loading empty config file."""
        config_file = tmp_path / "config"
        config_file.write_text("# Only comments\n\n# And empty lines\n")

        config = Config(str(config_file))
        assert len(config.all_keys) == 0
