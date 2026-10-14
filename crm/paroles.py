"""Paroļu jaukšana ar PBKDF2-SHA256 un nejaušu sāli."""

import hashlib
import hmac
import secrets

ITERACIJAS = 200_000


def _jauc(parole: str, salt: bytes) -> bytes:
    return hashlib.pbkdf2_hmac("sha256", parole.encode("utf-8"), salt, ITERACIJAS)


def jauna(parole: str) -> tuple[bytes, bytes]:
    """Atgriež (salt, hash) jaunai parolei."""
    salt = secrets.token_bytes(16)
    return salt, _jauc(parole, salt)


def parbaudit(parole: str, salt: bytes, hash_: bytes) -> bool:
    return hmac.compare_digest(_jauc(parole, salt), hash_)


_FIKTIVS_SALT, _FIKTIVS_HASH = jauna(secrets.token_hex(16))


def fiktiva_parbaude(parole: str) -> None:
    """Nezināmam e-pastam patērē tikpat laika kā īstai pārbaudei."""
    parbaudit(parole, _FIKTIVS_SALT, _FIKTIVS_HASH)
