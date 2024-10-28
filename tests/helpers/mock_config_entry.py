"""Mock config entry."""

from pytest_homeassistant_custom_component.common import MockConfigEntry

from ..integration import MS365ConfigEntry


class MS365MockConfigEntry(MockConfigEntry):
    """Mock config entry with MS365 runtime_data."""

    def __init__(self, *args, **kwargs) -> None:
        """Initialise MS365MockConfigEntry."""
        self.runtime_data: MS365ConfigEntry = None
        super().__init__(*args, **kwargs)
