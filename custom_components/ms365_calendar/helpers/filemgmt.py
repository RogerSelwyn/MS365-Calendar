"""File management processes."""

import os

from homeassistant.core import HomeAssistant

from ..const import MS365_STORAGE


def build_config_file_path(hass: HomeAssistant, filepath):  # pragma: no cover
    """Create config path."""
    root = hass.config.config_dir

    return os.path.join(root, MS365_STORAGE, filepath)
