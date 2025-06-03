"""Generic Permissions processes."""

import logging
import os
import time
from typing import Optional

from O365 import (
    Account,
    FileSystemTokenBackend,
)
from O365.connection import (  # pylint: disable=import-error, no-name-in-module
    Connection,
    MSGraphProtocol,
)
from portalocker import Lock
from portalocker.exceptions import LockException

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
        super().__init__(
            timezone=CONST_UTC_TIMEZONE,
        )


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
            self._token_backend = MS365LockableFileSystemTokenBackend(
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


class MS365LockableFileSystemTokenBackend(FileSystemTokenBackend):
    """
    A token backend that ensures atomic operations when working with tokens
    stored on a file system. Avoids concurrent instances of O365 racing
    to refresh the same token file. It does this by wrapping the token refresh
    method in the Portalocker package's Lock class, which itself is a wrapper
    around Python's fcntl and win32con.
    """

    def __init__(self, *args, **kwargs):
        self.max_tries: int = kwargs.pop("max_tries", 3)
        self.fs_wait: bool = False
        super().__init__(*args, **kwargs)

    def should_refresh_token(
        self, con: Optional[Connection] = None, username: Optional[str] = None
    ):
        """
        Method for refreshing the token when there are concurrently running
        O365 instances. Determines if we need to call the MSAL and refresh
        the token and its file, or if another Connection instance has already
        updated it, and we should just load that updated token from the file.

        It will always return False, None, OR raise an error if a token file
        couldn't be accessed after X tries. That is because this method
        completely handles token refreshing via the passed Connection object
        argument. If it determines that the token should be refreshed, it locks
        the token file, calls the Connection's 'refresh_token' method (which
        loads the fresh token from the server into memory and the file), then
        unlocks the file. Since refreshing has been taken care of, the calling
        method does not need to refresh and we return None.

        If we are blocked because the file is locked, that means another
        instance is using it. We'll change the backend's state to waiting,
        sleep for 2 seconds, reload a token into memory from the file (since
        another process is using it, we can assume it's being updated), and
        loop again.

        If this newly loaded token is not expired, the other instance loaded
        a new token to file, and we can happily move on and return False.
        (since we don't need to refresh the token anymore). If the same token
        was loaded into memory again and is still expired, that means it wasn't
        updated by the other instance yet. Try accessing the file again for X
        more times. If we don't succeed after the loop has terminated, raise a
        runtime exception
        """
        _LOGGER.debug("Start should_refresh_token")

        # 1) check if the token is already a new one:
        if old_access_token := self.get_access_token(username=username):
            self.load_token()  # retrieve again the token from the backend
            new_access_token = self.get_access_token(username=username)
            if old_access_token["secret"] != new_access_token["secret"]:
                # The token is different so the refresh took part somewhere else.
                # Return False so the connection can update the token access from
                # the backend into the session
                return False

        # 2) Here the token stored in the token backend and in the token cache
        #    of this instance is the same
        for i in range(self.max_tries, 0, -1):
            try:
                with Lock(
                    self.token_path, "r+", fail_when_locked=True, timeout=0
                ) as token_file:
                    # we were able to lock the file ourselves so proceed to refresh the token
                    # we have to do the refresh here as we must do it with the lock applied
                    _LOGGER.debug(
                        "Locked oauth token file. Refreshing the token now..."
                    )
                    token_refreshed = con.refresh_token()
                    if token_refreshed is False:
                        raise RuntimeError("Token Refresh Operation not working")

                    # we have refreshed the auth token ourselves to we must take care of
                    # updating the header and save the token file
                    con.update_session_auth_header()
                    _LOGGER.debug(
                        "New oauth token fetched. Saving the token data into the file"
                    )
                    token_file.write(self.serialize())
                _LOGGER.debug("Unlocked oauth token file")
                return None
            except LockException:
                # somebody else has adquired a lock so will be in the process of updating the token
                self.fs_wait = True
                _LOGGER.debug(
                    "Oauth file locked. Sleeping for 2 seconds... retrying %s more times.",
                    i - 1,
                )
                time.sleep(2)
                _LOGGER.debug(
                    "Waking up and rechecking token file for update from other instance..."
                )
                # Assume the token has been already updated
                self.load_token()
                # Check if new token has been created.
                if not self.token_is_expired():
                    _LOGGER.debug("Token file has been updated in other instance...")
                    # Return False so the connection can update the token access from the
                    # backend into the session
                    return False

        # if we exit the loop, that means we were locked out of the file after
        # multiple retries give up and throw an error - something isn't right
        raise RuntimeError(f"Could not access locked token file after {self.max_tries}")
