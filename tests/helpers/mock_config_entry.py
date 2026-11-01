"""Mock config entry."""

from copy import deepcopy

from pytest_homeassistant.common import MockConfigEntry

from ..integration import MS365ConfigEntry


class MS365MockConfigEntry(MockConfigEntry):
    """Mock config entry with MS365 runtime_data."""

    def __init__(self, *args, **kwargs) -> None:
        """Initialise MS365MockConfigEntry."""
        self.runtime_data: MS365ConfigEntry = None
        super().__init__(*args, **kwargs)


def config_entry_setup(input_config_entry, base_attributes=None, api_option_attributes=None, delete_attributes=None):
    """Create config entry."""
    config_entry = deepcopy(input_config_entry)
    if base_attributes:
        for key, value in base_attributes.items():
            config_entry[key] = value
    if api_option_attributes:
        for key, value in api_option_attributes.items():
            config_entry["api_options"][key] = value
    if delete_attributes:
        for key in delete_attributes:
            del config_entry[key]
    return config_entry
