import pytest
from cryptography.fernet import InvalidToken

from app.core.crypto import (
    decrypt_text,
    encrypt_text,
    generate_data_key,
    unwrap_data_key,
    wrap_data_key,
)


def test_wrap_unwrap_data_key() -> None:
    data_key = generate_data_key()
    wrapped = wrap_data_key(data_key)
    assert wrapped != data_key
    assert unwrap_data_key(wrapped) == data_key


def test_encrypt_decrypt_round_trip() -> None:
    data_key = generate_data_key()
    token = encrypt_text(data_key, "sensitive profile data")
    assert token != "sensitive profile data"
    assert decrypt_text(data_key, token) == "sensitive profile data"


def test_ciphertext_from_other_key_cannot_be_read() -> None:
    token = encrypt_text(generate_data_key(), "secret")
    with pytest.raises(InvalidToken):
        decrypt_text(generate_data_key(), token)
