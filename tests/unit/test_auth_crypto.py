import os

import src.config
from src.auth.crypto import get_no_auth_master_key


def test_get_no_auth_master_key_length_and_stability():
    key1 = get_no_auth_master_key()
    key2 = get_no_auth_master_key()
    assert len(key1) == 32
    assert key1 == key2


def test_get_no_auth_master_key_differs_with_different_secret_key():
    original = get_no_auth_master_key()
    old_secret = os.environ.get("SECRET_KEY")
    try:
        os.environ["SECRET_KEY"] = "another-secret-key"
        src.config.get_settings.cache_clear()
        different = get_no_auth_master_key()
        assert different != original
        assert len(different) == 32
    finally:
        if old_secret is not None:
            os.environ["SECRET_KEY"] = old_secret
        else:
            os.environ.pop("SECRET_KEY", None)
        src.config.get_settings.cache_clear()
