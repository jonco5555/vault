import pytest
from threshold_crypto.data import ThresholdCryptoError
from vault.crypto.threshold import (
    generate_key_and_shares,
    encrypt,
    partial_decrypt,
    decrypt,
)


def test_generate_key_and_shares_threshold():
    threshold = 2
    num_of_shares = 5
    _, key_shares = generate_key_and_shares(threshold, num_of_shares)
    assert len(key_shares) == num_of_shares


def test_encrypt_and_partial_decrypt_and_combine():
    threshold = 2
    num_of_shares = 3
    message = "hello threshold"
    pub_key, key_shares = generate_key_and_shares(threshold, num_of_shares)
    encrypted = encrypt(message, pub_key)
    # Get partial decryptions from shares
    partial_1 = partial_decrypt(encrypted, key_shares[0])
    partial_2 = partial_decrypt(encrypted, key_shares[1])
    # Combine partial decryptions
    recovered = decrypt([partial_1, partial_2], encrypted, threshold, num_of_shares)
    assert recovered == message


def test_partial_decrypt_invalid_share():
    threshold = 2
    num_of_shares = 3
    message = "test"
    pub_key, _ = generate_key_and_shares(threshold, num_of_shares)
    encrypted = encrypt(message, pub_key)
    # Use an invalid share (simulate by passing wrong type)
    with pytest.raises(Exception):
        partial_decrypt(encrypted, "not_a_key_share")


def test_combine_partial_decryptions_insufficient_shares():
    threshold = 3
    num_of_shares = 5
    message = "insufficient"
    pub_key, key_shares = generate_key_and_shares(threshold, num_of_shares)
    encrypted = encrypt(message, pub_key)
    # Only provide fewer than threshold partial decryptions
    partials = [
        partial_decrypt(encrypted, key_shares[0]),
        partial_decrypt(encrypted, key_shares[1]),
    ]
    with pytest.raises(ThresholdCryptoError):
        decrypt(partials, encrypted, threshold, num_of_shares)
