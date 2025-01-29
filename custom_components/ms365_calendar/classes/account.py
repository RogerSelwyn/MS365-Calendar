"""Generic Permissions processes."""

import logging

from O365 import Account

from ..const import (
    CONST_UTC_TIMEZONE,
    TOKEN_ERROR_CORRUPT,
    TOKEN_ERROR_LEGACY,
    TOKEN_FILE_CORRUPTED,
    TOKEN_FILE_OUTDATED,
    TOKEN_INVALID,
)
from ..integration.const_integration import DOMAIN

_LOGGER = logging.getLogger(__name__)


class MS365Account:
    """Class for Account setup."""

    def __init__(self, perms):
        """Initialise the account."""
        self._perms = perms
        self.account = None
        self.is_authenticated = False

    def try_authentication(self, credentials, main_resource, entity_name):
        """Try authenticating to O365."""
        _LOGGER.debug("Setup account")
        self.account = None
        self.is_authenticated = False
        try:
            self.account = Account(
                credentials,
                token_backend=self._perms.token_backend,
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
