"""Encrypted storage for farmer login passwords shown to the main administrator.

Django normally stores only a one-way password hash. CropCare AI additionally keeps an
encrypted copy because this project explicitly requires the main superuser to be able
to view the originally assigned farmer password later. The encryption key is derived
from DJANGO_SECRET_KEY, so changing that key makes existing saved passwords unreadable.
"""

import base64
import hashlib

from cryptography.fernet import Fernet, InvalidToken
from django.conf import settings


class CredentialVaultError(RuntimeError):
    """Raised when a stored credential cannot be encrypted or decrypted."""


def _fernet() -> Fernet:
    secret_key = str(settings.SECRET_KEY).encode("utf-8")
    digest = hashlib.sha256(secret_key).digest()
    return Fernet(base64.urlsafe_b64encode(digest))


def encrypt_password(raw_password: str) -> str:
    if not raw_password:
        raise CredentialVaultError("A non-empty farmer password is required.")
    return _fernet().encrypt(raw_password.encode("utf-8")).decode("ascii")


def decrypt_password(encrypted_password: str) -> str:
    if not encrypted_password:
        return ""
    try:
        return _fernet().decrypt(encrypted_password.encode("ascii")).decode("utf-8")
    except (InvalidToken, ValueError, UnicodeDecodeError) as exc:
        raise CredentialVaultError(
            "The saved farmer password cannot be decrypted. Confirm that "
            "DJANGO_SECRET_KEY has not changed."
        ) from exc
