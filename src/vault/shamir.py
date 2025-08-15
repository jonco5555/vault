from Crypto.Protocol.SecretSharing import Shamir


class SharesManager:
    def __init__(self, total_shares: int, threshold: int):
        self.total_shares = total_shares
        self.threshold = threshold

    def split_secret(self, secret: bytes) -> list[tuple[int, bytes]]:
        """
        Splits a secret into multiple shares using Shamir's Secret Sharing scheme.

        Args:
            secret (bytes): The secret to split into shares, expected to be a byte string of 16 bytes.

        Returns:
            list[tuple[int, bytes]]: A list of shares, where each share is a tuple containing the share index (int) and the share bytes (16 bytes).

        Raises:
            ValueError: If the secret is invalid.
        """
        shares = Shamir.split(self.threshold, self.total_shares, secret)
        return shares

    def combine_shares(self, shares: list[tuple[int, bytes]]) -> bytes:
        """
        Combines Shamir secret shares to reconstruct the original secret.

        Args:
            shares (list[tuple[int, bytes]]): A list of tuples, each containing a share index and its corresponding share bytes.

        Returns:
            bytes: The reconstructed secret.

        Raises:
            ValueError: If the shares are invalid or insufficient to reconstruct the secret.
        """
        secret = Shamir.combine(shares)
        return secret
