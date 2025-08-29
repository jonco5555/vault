import pytest

from vault.crypto.shamir import SharesManager


def test_split_secret_valid():
    manager = SharesManager(total_shares=5, threshold=3)
    secret = b"1234567890abcdef"  # 16 bytes
    shares = manager.split_secret(secret)
    assert isinstance(shares, list)
    assert len(shares) == 5
    for idx, share_bytes in shares:
        assert isinstance(idx, int)
        assert isinstance(share_bytes, bytes)
        assert len(share_bytes) == 16


def test_combine_shares_valid():
    manager = SharesManager(total_shares=5, threshold=3)
    secret = b"1234567890abcdef"
    shares = manager.split_secret(secret)
    selected_shares = shares[:3]
    reconstructed = manager.combine_shares(selected_shares)
    assert reconstructed == secret


@pytest.mark.skip(
    "Reconstruction may succeed but still produce the incorrect secret if any of the presented shares is incorrect (due to data corruption or to a malicious participant)."
)
def test_combine_shares_insufficient():
    manager = SharesManager(total_shares=5, threshold=4)
    secret = b"1234567890abcdef"
    shares = manager.split_secret(secret)
    insufficient_shares = shares[:3]
    with pytest.raises(ValueError):
        manager.combine_shares(insufficient_shares)


def test_split_secret_invalid_length():
    manager = SharesManager(total_shares=5, threshold=3)
    invalid_secret = b"tooshort"
    with pytest.raises(ValueError):
        manager.split_secret(invalid_secret)


def test_combine_shares_invalid_format():
    manager = SharesManager(total_shares=5, threshold=3)
    # Not a tuple of (int, bytes)
    invalid_shares = [(1, b"123"), (2, b"456")]
    with pytest.raises(ValueError):
        manager.combine_shares(invalid_shares)
