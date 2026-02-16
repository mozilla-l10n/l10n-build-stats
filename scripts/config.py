"""Configuration management for l10n-build-stats."""

from __future__ import annotations

import os
import sys

from pathlib import Path
from logging_config import get_logger


logger = get_logger(__name__)


class ConfigError(Exception):
    """Raised when configuration is invalid or missing."""

    pass


class Config:
    """Configuration manager for l10n-build-stats."""

    def __init__(self, config_path: str | None = None):
        """
        Initialize configuration.

        Args:
            config_path: Path to config file. If None, uses default location.

        Raises:
            ConfigError: If config file is missing or invalid
        """
        if config_path is None:
            root_folder = Path(__file__).parent.parent
            config_path = str(root_folder / "config" / "config")

        self.config_path = config_path
        self._paths: dict[str, str] = {}
        self._load()

    def _load(self) -> None:
        """
        Load configuration from file.

        Raises:
            ConfigError: If config file doesn't exist or has invalid format
        """
        if not os.path.exists(self.config_path):
            raise ConfigError(f"Config file not found: {self.config_path}")

        logger.debug(f"Loading config from {self.config_path}")

        with open(self.config_path) as cfg_file:
            for line_num, line in enumerate(cfg_file, 1):
                line = line.strip()

                # Skip comments and empty lines
                if not line or line.startswith("#"):
                    continue

                # Parse key=value
                if "=" not in line:
                    raise ConfigError(
                        f"Invalid config line {line_num}: missing '=' separator"
                    )

                key, _, value = line.partition("=")
                key = key.strip()
                value = value.strip().strip('"\'')

                if not key:
                    raise ConfigError(f"Invalid config line {line_num}: empty key")

                self._paths[key] = value

        logger.debug(f"Loaded {len(self._paths)} config entries")

    def get(self, key: str, validate: bool = True) -> str:
        """
        Get configuration value by key.

        Args:
            key: Configuration key
            validate: Whether to validate that the path exists

        Returns:
            Configuration value

        Raises:
            ConfigError: If key not found or path doesn't exist (when validate=True)
        """
        if key not in self._paths:
            raise ConfigError(f"Configuration key '{key}' not found")

        value = self._paths[key]

        if validate and not os.path.exists(value):
            raise ConfigError(
                f"Path for '{key}' does not exist: {value}\n"
                f"Please check your config file at {self.config_path}"
            )

        return value

    def get_multiple(self, keys: list[str], validate: bool = True) -> tuple[str, ...]:
        """
        Get multiple configuration values.

        Args:
            keys: List of configuration keys
            validate: Whether to validate that paths exist

        Returns:
            Tuple of configuration values

        Raises:
            ConfigError: If any key not found or path doesn't exist
        """
        return tuple(self.get(key, validate=validate) for key in keys)

    @property
    def all_keys(self) -> list[str]:
        """Get list of all configuration keys."""
        return list(self._paths.keys())


# Global config instance (lazy-loaded)
_config: Config | None = None


def get_config() -> Config:
    """
    Get the global configuration instance.

    Returns:
        Config instance

    Raises:
        ConfigError: If config cannot be loaded
    """
    global _config
    if _config is None:
        _config = Config()
    return _config


def read_config(params: list[str]) -> tuple[str, ...]:
    """
    Read configuration values (backwards compatibility wrapper).

    Args:
        params: List of configuration keys to read

    Returns:
        Tuple of configuration values

    Raises:
        SystemExit: If configuration is invalid
    """
    try:
        config = get_config()
        return config.get_multiple(params)
    except ConfigError as e:
        logger.error(f"Configuration error: {e}")
        sys.exit(1)
