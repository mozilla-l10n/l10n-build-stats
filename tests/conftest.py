"""Shared pytest fixtures and configuration."""

import pytest


@pytest.fixture
def sample_string_list():
    """Sample string list for testing."""
    return {
        "browser/firefox.ftl": {
            "source": ["app-name", "menu-file", "menu-edit"],
            "it": ["app-name", "menu-file"],
            "fr": ["app-name"],
        },
        "browser/aboutDialog.ftl": {
            "source": ["update-check", "update-available"],
            "it": ["update-check", "update-available"],
            "fr": ["update-check"],
        },
    }


@pytest.fixture
def sample_locales():
    """Sample locale list for testing."""
    return ["source", "it", "fr", "de"]
