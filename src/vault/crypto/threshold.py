import threshold_crypto as tc
from threshold_crypto.data import (
    PublicKey,
    KeyShare,
    EncryptedMessage,
    PartialDecryption,
    ThresholdParameters,
)


def generate_key_and_shares(
    threshold: int, num_of_shares: int
) -> tuple[PublicKey, list[KeyShare], ThresholdParameters]:
    """
    Generates a new key pair and splits the private key into shares.

    Args:
        threshold (int): Minimum number of shares required to reconstruct the private key.
        num_of_shares (int): Total number of shares to create.

    Returns:
        PublicKey: The generated public key.
        list[KeyShare]: List of generated key shares.
        ThresholdParameters: The parameters used for threshold encryption.
    """
    curve_params = tc.CurveParameters()
    threshold_params = tc.ThresholdParameters(t=threshold, n=num_of_shares)
    pub_key, key_shares = tc.create_public_key_and_shares_centralized(
        curve_params, threshold_params
    )
    pub_key: PublicKey
    key_shares: list[KeyShare]
    return pub_key, key_shares, threshold_params


def encrypt(message: str, pub_key: PublicKey) -> EncryptedMessage:
    """
    Encrypts a message using the provided public key.
        message (str): The plaintext message to be encrypted.
        pub_key (PublicKey): The public key used for encryption.
        EncryptedMessage: The encrypted message object.

    Returns:
        EncryptedMessage: The encrypted message object.
    """
    return tc.encrypt_message(message, pub_key)


def partial_decrypt(
    encrypted_message: EncryptedMessage, key_share: KeyShare
) -> PartialDecryption:
    """
    Partially decrypts an encrypted message using a key share.

    Args:
        encrypted_message (EncryptedMessage): The encrypted message to be partially decrypted.
        key_share (KeyShare): The key share used for partial decryption.

    Returns:
        PartialDecryption: The partially decrypted message.
    """
    return tc.compute_partial_decryption(encrypted_message, key_share)


def decrypt(
    partial_decryptions: list[PartialDecryption],
    encrypted_message: EncryptedMessage,
    threshold_params: ThresholdParameters,
) -> str:
    """
    Combines partial decryptions and decrypts encrypted message.

    Args:
        partial_decryptions (list[PartialDecryption]): List of partial decryptions.
        encrypted_message (EncryptedMessage): The original encrypted message.
        threshold_params (ThresholdParameters): The threshold parameters used during key generation.

    Returns:
        str: The recovered plaintext message.
    """
    return tc.decrypt_message(partial_decryptions, encrypted_message, threshold_params)
