import threshold_crypto as tc
from Crypto.PublicKey.ECC import EccPoint
from threshold_crypto.data import (
    EncryptedMessage,
    KeyShare,
    PublicKey,
)

from vault.common import types
from vault.common.generated import vault_pb2 as pb2
from vault.common.generated.vault_pb2 import Secret


def generate_key_and_shares(
    threshold: int, num_of_shares: int
) -> tuple[types.Key, list[types.Key]]:
    """
    Generates an encryption key and its threshold shares.

    Args:
        threshold (int): The minimum number of shares required to reconstruct the key.
        num_of_shares (int): The total number of shares to generate.

    Returns:
        tuple[Key, list[Key]]: A tuple containing the generated encryption key and a list of shares.
    """
    pub_key, key_shares = tc.create_public_key_and_shares_centralized(
        tc.CurveParameters(), tc.ThresholdParameters(t=threshold, n=num_of_shares)
    )
    pub_key: PublicKey
    key_shares: list[KeyShare]
    encryption_key = types.Key(x=str(pub_key.Q.x), y=str(pub_key.Q.y))
    shares = [types.Key(x=str(s.x), y=str(s.y)) for s in key_shares]
    return encryption_key, shares


def encrypt(message: str, encryption_key: types.Key) -> Secret:
    """
    Encrypts a message using the provided encryption key.

    Args:
        message (str): The plaintext message to encrypt.
        encryption_key (Key): The public encryption key used for encryption.

    Returns:
        Secret: An object containing the encrypted message components (C1, C2, ciphertext).
    """
    encrypted_message = tc.encrypt_message(
        message, PublicKey(EccPoint(int(encryption_key.x), int(encryption_key.y)))
    )
    return Secret(
        c1=pb2.Key(x=str(encrypted_message.C1.x), y=str(encrypted_message.C1.y)),
        c2=pb2.Key(x=str(encrypted_message.C2.x), y=str(encrypted_message.C2.y)),
        ciphertext=encrypted_message.ciphertext,
    )


def partial_decrypt(secret: Secret, share: types.Key) -> types.PartialDecryption:
    """
    Performs a partial decryption of a secret using a given share.

    Args:
        secret (Secret): The encrypted secret to be partially decrypted.
        share (Key): The share (Key) used for partial decryption.

    Returns:
        types.PartialDecryption: The result of the partial decryption.
    """
    partial_decrypted = tc.compute_partial_decryption(
        EncryptedMessage(
            EccPoint(int(secret.c1.x), int(secret.c1.y)),
            EccPoint(int(secret.c2.x), int(secret.c2.y)),
            secret.ciphertext,
        ),
        KeyShare(int(share.x), int(share.y), tc.CurveParameters()),
    )
    return types.PartialDecryption(
        x=str(partial_decrypted.x),
        yc1=types.Key(x=str(partial_decrypted.yC1.x), y=str(partial_decrypted.yC1.y)),
    )


def decrypt(
    partial_decryptions: list[types.PartialDecryption],
    secret: Secret,
    threshold: int,
    num_of_shares: int,
) -> str:
    """
    Decrypts a secret using a list of partial decryptions and threshold parameters.

    Args:
        partial_decryptions (list[types.PartialDecryption]): List of partial decryption results.
        secret (Secret): The encrypted secret to decrypt.
        threshold (int): Minimum number of shares required for decryption.
        num_of_shares (int): Total number of shares.

    Returns:
        str: The decrypted plaintext message.
    """
    threshold_params = tc.ThresholdParameters(t=threshold, n=num_of_shares)
    decryptions = [
        tc.PartialDecryption(
            x=int(pd.x),
            yC1=EccPoint(int(pd.yc1.x), int(pd.yc1.y)),
            curve_params=tc.CurveParameters(),
        )
        for pd in partial_decryptions
    ]
    encrypted_message = EncryptedMessage(
        EccPoint(int(secret.c1.x), int(secret.c1.y)),
        EccPoint(int(secret.c2.x), int(secret.c2.y)),
        secret.ciphertext,
    )
    return tc.decrypt_message(decryptions, encrypted_message, threshold_params)
