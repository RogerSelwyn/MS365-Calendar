"""File management processes."""

import os

from ..const import (
    MS365_STORAGE,
)


def build_config_file_path(hass, filepath):
    """Create config path."""
    root = hass.config.config_dir

    return os.path.join(root, MS365_STORAGE, filepath)
