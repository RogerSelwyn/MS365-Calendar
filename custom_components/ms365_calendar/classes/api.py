"""Generic Permissions processes."""

import logging
import os

from O365 import (
    Account,
    FileSystemTokenBackend,
)
from O365.connection import (  # pylint: disable=import-error, no-name-in-module
    Connection,
    MSGraphProtocol,
)

from ..const import (
    CONF_ENTITY_NAME,
    CONST_UTC_TIMEZONE,
    COUNTRY_URLS,
    MS365_STORAGE_TOKEN,
    MSAL_AUTHORITY,
    OAUTH_REDIRECT_URL,
    OAUTH_SCOPE_PREFIX,
    PROTOCOL_URL,
    TOKEN_ERROR_CORRUPT,
    TOKEN_ERROR_LEGACY,
    TOKEN_ERROR_MISSING,
    TOKEN_FILE_CORRUPTED,
    TOKEN_FILE_OUTDATED,
    TOKEN_FILENAME,
    TOKEN_INVALID,
    CountryOptions,
)
from ..helpers.filemgmt import build_config_file_path
from ..helpers.utils import get_country
from ..integration.const_integration import DOMAIN
from .config_entry import MS365ConfigEntry

_LOGGER = logging.getLogger(__name__)


class MS365Protocol(MSGraphProtocol):
    """Protocol class"""

    def __init__(self, country: CountryOptions):
        if country != CountryOptions.DEFAULT:
            # Override before super().__init__ to ensure our values are used
            self._protocol_url = COUNTRY_URLS[country][PROTOCOL_URL]
            self._oauth_scope_prefix = COUNTRY_URLS[country][OAUTH_SCOPE_PREFIX]
        super().__init__()


class MS365Connection(Connection):
    """Connection class."""

    def __init__(self, credentials, country=None, **kwargs):
        """Override init to set China cloud specific values."""
        super().__init__(credentials, **kwargs)
        if country != CountryOptions.DEFAULT:
            # Override after super().__init__ to ensure our values are used
            self._msal_authority = COUNTRY_URLS[country][MSAL_AUTHORITY]
            self.oauth_redirect_url = COUNTRY_URLS[country][OAUTH_REDIRECT_URL]


class MS365CustomAccount(Account):
    """Custom Account class."""

    connection_constructor = MS365Connection


class MS365Account:
    """Class for Account setup."""

    def __init__(self, perms, entry_data: MS365ConfigEntry):
        """Initialise the account."""
        self._country = get_country(entry_data)
        self._perms = perms
        self.account = None
        self.is_authenticated = False

    def try_authentication(self, credentials, main_resource, entity_name):
        """Try authenticating to O365."""
        _LOGGER.debug("Setup account")
        self.account = None
        self.is_authenticated = False
        try:
            protocol = MS365Protocol(self._country)
            self.account = MS365CustomAccount(
                credentials,
                country=self._country,
                protocol=protocol,
                token_backend=self._perms.ha_token_backend.token_backend,
                timezone=CONST_UTC_TIMEZONE,
                main_resource=main_resource,
            )
            self.is_authenticated = self.account.is_authenticated
            return False
        except ValueError as err:
            if TOKEN_INVALID in str(err):
                _LOGGER.warning(
                    TOKEN_ERROR_LEGACY,
                    DOMAIN,
                    entity_name,
                    err,
                )
                return TOKEN_FILE_OUTDATED

            _LOGGER.warning(
                TOKEN_ERROR_CORRUPT,
                DOMAIN,
                entity_name,
                err,
            )
            return TOKEN_FILE_CORRUPTED


class MS365Token:
    """Class for Token setup."""

    def __init__(self, hass, config):
        """Initialise the class."""
        self._hass = hass
        self._config = config

        self._token_backend = None

    @property
    def token_backend(self):
        """Return backend token."""
        if not self._token_backend:
            _LOGGER.debug("Setup token")
            self._token_backend = FileSystemTokenBackend(
                token_path=self.token_path,
                token_filename=self.token_filename,
            )
        return self._token_backend

    @property
    def token_filename(self):
        """Return token file name."""
        return self.build_token_filename()

    @property
    def token_path(self):
        """Return token file path."""
        return build_config_file_path(self._hass, MS365_STORAGE_TOKEN)

    def build_token_filename(self):
        """Create the token file name."""
        return TOKEN_FILENAME.format(DOMAIN, f"_{self._config.get(CONF_ENTITY_NAME)}")

    def delete_token(self):
        """Delete the token."""
        full_token_path = os.path.join(self.token_path, self.token_filename)
        if os.path.exists(full_token_path):
            os.remove(full_token_path)

    def check_token_exists(self):
        """Check if token file exists.."""
        full_token_path = os.path.join(self.token_path, self.token_filename)
        if not os.path.exists(full_token_path) or not os.path.isfile(full_token_path):
            _LOGGER.warning(TOKEN_ERROR_MISSING, full_token_path)
            return False
        return True
