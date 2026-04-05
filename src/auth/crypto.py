import os
from pathlib import Path
from typing import Tuple

from argon2 import PasswordHasher
from argon2.low_level import Type
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

# Argon2id parameters suitable for local personal app
PH = PasswordHasher(
    time_cost=2,
    memory_cost=65536,
    parallelism=1,
    hash_len=32,
    salt_len=16,
    type=Type.ID,
)

# In-memory master key cache (cleared on restart)
_master_key_cache: dict[str, bytes] = {}


def hash_password(password: str) -> str:
    """Hash a password with Argon2id."""
    return PH.hash(password)


def verify_password(password: str, hash_str: str) -> bool:
    """Verify a password against an Argon2id hash."""
    try:
        PH.verify(hash_str, password)
        return True
    except Exception:
        return False


def derive_master_key(password: str, salt: bytes) -> bytes:
    """Derive a 32-byte master key from password and salt using Argon2id raw hash."""
    from argon2.low_level import hash_secret_raw

    return hash_secret_raw(
        secret=password.encode("utf-8"),
        salt=salt,
        time_cost=2,
        memory_cost=65536,
        parallelism=1,
        hash_len=32,
        type=Type.ID,
    )


def cache_master_key(token: str, key: bytes) -> None:
    _master_key_cache[token] = key


def get_cached_master_key(token: str) -> bytes | None:
    return _master_key_cache.get(token)


def clear_master_key(token: str) -> None:
    _master_key_cache.pop(token, None)


def generate_salt() -> bytes:
    return os.urandom(16)


def encrypt_file(plaintext_path: Path, ciphertext_path: Path, key: bytes) -> None:
    """Encrypt a file with AES-256-GCM."""
    aesgcm = AESGCM(key)
    nonce = os.urandom(12)
    plaintext = plaintext_path.read_bytes()
    ciphertext = aesgcm.encrypt(nonce, plaintext, None)
    ciphertext_path.write_bytes(nonce + ciphertext)


def decrypt_file(ciphertext_path: Path, plaintext_path: Path, key: bytes) -> None:
    """Decrypt a file encrypted with AES-256-GCM."""
    aesgcm = AESGCM(key)
    data = ciphertext_path.read_bytes()
    nonce = data[:12]
    ciphertext = data[12:]
    plaintext = aesgcm.decrypt(nonce, ciphertext, None)
    plaintext_path.write_bytes(plaintext)


def decrypt_bytes(ciphertext: bytes, key: bytes) -> bytes:
    """Decrypt bytes in memory."""
    aesgcm = AESGCM(key)
    nonce = ciphertext[:12]
    encrypted = ciphertext[12:]
    return aesgcm.decrypt(nonce, encrypted, None)


def encrypt_bytes(plaintext: bytes, key: bytes) -> bytes:
    """Encrypt bytes in memory."""
    aesgcm = AESGCM(key)
    nonce = os.urandom(12)
    return nonce + aesgcm.encrypt(nonce, plaintext, None)
