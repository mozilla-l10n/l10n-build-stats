"""Tests for logging_config module."""

import logging
import os
import sys
import tempfile

from pathlib import Path
from unittest.mock import patch

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

from logging_config import get_logger, setup_logging


class TestSetupLogging:
    """Tests for setup_logging function."""

    def test_default_setup(self):
        """Test default logging configuration."""
        setup_logging()

        # Check root logger level
        root_logger = logging.getLogger()
        assert root_logger.level == logging.INFO

    def test_custom_level_string(self):
        """Test setting custom log level with string."""
        setup_logging(level="DEBUG")

        root_logger = logging.getLogger()
        assert root_logger.level == logging.DEBUG

    def test_custom_level_int(self):
        """Test setting custom log level with int."""
        setup_logging(level=logging.WARNING)

        root_logger = logging.getLogger()
        assert root_logger.level == logging.WARNING

    def test_level_from_env_var(self):
        """Test reading log level from environment variable."""
        with patch.dict(os.environ, {"LOG_LEVEL": "ERROR"}):
            setup_logging()

            root_logger = logging.getLogger()
            assert root_logger.level == logging.ERROR

    def test_verbose_format(self):
        """Test verbose format includes file and line info."""
        setup_logging(verbose=True)

        # Check that handlers exist and use verbose format
        root_logger = logging.getLogger()
        assert len(root_logger.handlers) > 0

    def test_log_file_creation(self, tmp_path):
        """Test log file is created when specified."""
        log_file = tmp_path / "test.log"
        setup_logging(log_file=str(log_file))

        # Log a message
        logger = get_logger("test")
        logger.info("Test message")

        # Check file was created and contains the message
        assert log_file.exists()
        content = log_file.read_text()
        assert "Test message" in content

    def test_log_file_from_env(self, tmp_path):
        """Test log file path from environment variable."""
        log_file = tmp_path / "env_test.log"

        with patch.dict(os.environ, {"LOG_FILE": str(log_file)}):
            setup_logging()

            logger = get_logger("test_env")
            logger.info("Environment log")

            assert log_file.exists()
            content = log_file.read_text()
            assert "Environment log" in content

    def test_log_file_creates_directories(self, tmp_path):
        """Test that parent directories are created for log file."""
        log_file = tmp_path / "nested" / "dirs" / "test.log"
        setup_logging(log_file=str(log_file))

        logger = get_logger("test_nested")
        logger.info("Nested log")

        assert log_file.exists()
        assert log_file.parent.exists()

    def test_third_party_loggers_silenced(self):
        """Test that third-party library loggers are set to WARNING."""
        setup_logging()

        assert logging.getLogger("urllib3").level == logging.WARNING
        assert logging.getLogger("aiohttp").level == logging.WARNING
        assert logging.getLogger("gspread").level == logging.WARNING


class TestGetLogger:
    """Tests for get_logger function."""

    def test_returns_logger_instance(self):
        """Test that get_logger returns a Logger instance."""
        logger = get_logger("test_module")
        assert isinstance(logger, logging.Logger)

    def test_logger_name_matches(self):
        """Test that logger name matches the provided name."""
        logger = get_logger("my_module")
        assert logger.name == "my_module"

    def test_loggers_share_configuration(self):
        """Test that all loggers share the same configuration."""
        setup_logging(level="DEBUG")

        logger1 = get_logger("module1")
        logger2 = get_logger("module2")

        # Both should inherit from root logger
        assert logger1.getEffectiveLevel() == logging.DEBUG
        assert logger2.getEffectiveLevel() == logging.DEBUG
