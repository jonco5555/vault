import pytest
from nacl.encoding import Base64Encoder
from nacl.public import PrivateKey

from vault.crypto import asymmetric


def test_generate_key_pair_creates_valid_keys_and_file():
    privkey_b64, pubkey_b64 = asymmetric.generate_key_pair()
    priv = PrivateKey(privkey_b64, encoder=Base64Encoder)
    pub = priv.public_key
    assert pub.encode(encoder=Base64Encoder) == pubkey_b64


def test_encrypt_and_decrypt_success():
    privkey_b64, pubkey_b64 = asymmetric.generate_key_pair()
    message = b"hello, mixnet!"
    ciphertext = asymmetric.encrypt(message, pubkey_b64)
    assert ciphertext != message
    plaintext = asymmetric.decrypt(ciphertext, privkey_b64)
    assert plaintext == message


def test_decrypt_with_wrong_key_fails():
    _, pubkey_b64_1 = asymmetric.generate_key_pair()
    privkey_b64_2, _ = asymmetric.generate_key_pair()
    message = b"test message"
    ciphertext = asymmetric.encrypt(message, pubkey_b64_1)
    with pytest.raises(ValueError, match="Decryption failed"):
        asymmetric.decrypt(ciphertext, privkey_b64_2)


def test_encrypt_with_invalid_pubkey_raises():
    message = b"test"
    # Invalid base64 (not a valid key)
    bad_pubkey = b"notavalidkey=="
    with pytest.raises(Exception):
        asymmetric.encrypt(message, bad_pubkey)


def test_decrypt_with_invalid_privkey_raises():
    ciphertext = b"notarealciphertext"
    bad_privkey = b"notavalidkey=="
    with pytest.raises(Exception):
        asymmetric.decrypt(ciphertext, bad_privkey)


def test_double_encryption_and_decryption():
    privkey_b64_1, pubkey_b64_1 = asymmetric.generate_key_pair()
    privkey_b64_2, pubkey_b64_2 = asymmetric.generate_key_pair()
    message = b"double encryption test payload"
    ciphertext1 = asymmetric.encrypt(message, pubkey_b64_1)
    ciphertext2 = asymmetric.encrypt(ciphertext1, pubkey_b64_2)
    decrypted1 = asymmetric.decrypt(ciphertext2, privkey_b64_2)
    assert decrypted1 == ciphertext1
    decrypted2 = asymmetric.decrypt(decrypted1, privkey_b64_1)
    assert decrypted2 == message
