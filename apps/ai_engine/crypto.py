from cryptography.fernet import Fernet, InvalidToken
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured


class CredentialDecryptionError(Exception):
    """Raised when a stored credential cannot be decrypted safely."""


def _cipher():
    key = settings.AI_CREDENTIAL_ENCRYPTION_KEY.strip()
    if not key:
        raise ImproperlyConfigured(
            "AI_CREDENTIAL_ENCRYPTION_KEY must be set before storing AI credentials."
        )
    try:
        return Fernet(key.encode("ascii"))
    except (UnicodeEncodeError, ValueError) as exc:
        raise ImproperlyConfigured(
            "AI_CREDENTIAL_ENCRYPTION_KEY must be a valid Fernet key."
        ) from exc


def encrypt_credential(value):
    if not value:
        raise ValueError("An API key is required.")
    return _cipher().encrypt(value.encode("utf-8")).decode("ascii")


def decrypt_credential(value):
    if not value:
        raise CredentialDecryptionError("No encrypted API key is stored.")
    try:
        return _cipher().decrypt(value.encode("ascii")).decode("utf-8")
    except (InvalidToken, UnicodeDecodeError, UnicodeEncodeError) as exc:
        raise CredentialDecryptionError(
            "The stored API key cannot be decrypted with the configured encryption key."
        ) from exc
