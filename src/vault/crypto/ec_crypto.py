import base64
import datetime
import os

from cryptography import x509
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives.kdf.hkdf import HKDF
from cryptography.x509.oid import NameOID


def generate_cert_and_keys(
    common_name: str = "example.com",
    organization_name: str = "Example Organization",
    country_name: str = "US",
    valid_days: int = 365,
    output_dir: str = "./certs",
):
    private_key, public_key = generate_ec_key_pair()
    cert, pub_key, priv_key = generate_ec_certificate(
        private_key,
        public_key,
        common_name=common_name,
        organization_name=organization_name,
        country_name=country_name,
        valid_days=valid_days,
        output_dir=output_dir,
    )
    return cert, pub_key, priv_key


def generate_ec_key_pair(
    curve=ec.SECP256R1(),
) -> tuple[ec.EllipticCurvePrivateKey, ec.EllipticCurvePublicKey]:
    """Generate an elliptic curve key pair"""
    private_key = ec.generate_private_key(curve, default_backend())
    public_key = private_key.public_key()

    return private_key, public_key


def generate_ec_certificate(
    private_key: ec.EllipticCurvePrivateKey,
    public_key: ec.EllipticCurvePublicKey = None,
    common_name: str = "example.com",
    organization_name: str = "Example Organization",
    country_name: str = "US",
    valid_days: int = 365,
    output_dir: str = "./certs",
) -> tuple[str, str, str]:
    """
    Generate a self-signed X.509 certificate using EC keys.

    Args:
        private_key: EC private key object
        public_key: EC public key object (optional, will be derived from private_key if not provided)
        common_name: Domain name for the certificate
        organization_name: Organization name for the certificate
        country_name: Two-letter country code
        valid_days: Number of days the certificate will be valid
        output_dir: Directory to save the files

    Returns:
        Tuple containing (certificate_path, public_key_path, private_key_path)
    """
    # Create output directory if it doesn't exist
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    # If public_key is not provided, derive it from private_key
    if public_key is None:
        public_key = private_key.public_key()

    # Create a self-signed certificate
    subject = issuer = x509.Name(
        [
            x509.NameAttribute(NameOID.COUNTRY_NAME, country_name),
            x509.NameAttribute(NameOID.ORGANIZATION_NAME, organization_name),
            x509.NameAttribute(NameOID.COMMON_NAME, common_name),
        ]
    )

    # Certificate validity period
    not_valid_before = datetime.datetime.utcnow()
    not_valid_after = not_valid_before + datetime.timedelta(days=valid_days)

    # Build certificate
    certificate = (
        x509.CertificateBuilder()
        .subject_name(subject)
        .issuer_name(issuer)
        .public_key(public_key)
        .serial_number(x509.random_serial_number())
        .not_valid_before(not_valid_before)
        .not_valid_after(not_valid_after)
        .add_extension(
            x509.SubjectAlternativeName([x509.DNSName(common_name)]), critical=False
        )
        .add_extension(x509.BasicConstraints(ca=True, path_length=None), critical=True)
        .sign(private_key, hashes.SHA256(), default_backend())
    )

    # Serialize and save certificate and keys
    cert_path = os.path.join(output_dir, "ec_certificate.pem")
    public_key_path = os.path.join(output_dir, "ec_public_key.pem")
    private_key_path = os.path.join(output_dir, "ec_private_key.pem")

    # Write certificate to file
    with open(cert_path, "wb") as f:
        f.write(certificate.public_bytes(serialization.Encoding.PEM))

    # Write public key to file
    with open(public_key_path, "wb") as f:
        f.write(
            public_key.public_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PublicFormat.SubjectPublicKeyInfo,
            )
        )

    # Write private key to file
    with open(private_key_path, "wb") as f:
        f.write(
            private_key.private_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PrivateFormat.PKCS8,
                encryption_algorithm=serialization.NoEncryption(),
            )
        )

    print(f"Generated EC certificate and keys in {output_dir}")
    # return cert_path, public_key_path, private_key_path
    return (
        certificate.public_bytes(serialization.Encoding.PEM),
        public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo,
        ),
        private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption(),
        ),
    )


def ecies_encrypt(data: bytes, recipient_public_key: ec.EllipticCurvePublicKey) -> dict:
    """
    Encrypt data using ECIES scheme:
    1. Generate ephemeral EC key pair
    2. Perform ECDH to derive shared secret
    3. Derive symmetric encryption key using HKDF
    4. Encrypt data with AES-GCM

    Args:
        data: The data to encrypt (string or bytes)
        recipient_public_key: Recipient's EC public key object

    Returns:
        Dictionary with ephemeral public key, nonce, tag, and ciphertext (all base64 encoded)
    """
    # Convert string to bytes if needed
    if isinstance(data, str):
        data = data.encode("utf-8")

    # Generate ephemeral key pair for this message
    ephemeral_private_key = ec.generate_private_key(ec.SECP256R1(), default_backend())
    ephemeral_public_key = ephemeral_private_key.public_key()

    # Perform ECDH key exchange to get shared secret
    shared_key = ephemeral_private_key.exchange(ec.ECDH(), recipient_public_key)

    # Derive encryption key using HKDF
    derived_key = HKDF(
        algorithm=hashes.SHA256(),
        length=32,  # 256 bits for AES-256
        salt=None,
        info=b"ECIES Encryption",
        backend=default_backend(),
    ).derive(shared_key)

    # Generate a random 96-bit IV/nonce for AES-GCM
    nonce = os.urandom(12)

    # Create an encryptor object
    encryptor = Cipher(
        algorithms.AES(derived_key), modes.GCM(nonce), backend=default_backend()
    ).encryptor()

    # Encrypt the data
    ciphertext = encryptor.update(data) + encryptor.finalize()

    # Get the authentication tag
    tag = encryptor.tag

    # Serialize ephemeral public key
    serialized_ephemeral_public_key = ephemeral_public_key.public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    )

    # Return all components needed for decryption
    return {
        "ephemeral_public_key": base64.b64encode(
            serialized_ephemeral_public_key
        ).decode("utf-8"),
        "nonce": base64.b64encode(nonce).decode("utf-8"),
        "tag": base64.b64encode(tag).decode("utf-8"),
        "ciphertext": base64.b64encode(ciphertext).decode("utf-8"),
    }


def ecies_decrypt(
    encrypted_data: dict, private_key: ec.EllipticCurvePrivateKey
) -> bytes:
    """
    Decrypt data using ECIES scheme:
    1. Extract ephemeral public key
    2. Perform ECDH to derive the same shared secret
    3. Derive the same symmetric encryption key
    4. Decrypt data with AES-GCM

    Args:
        encrypted_data: Dictionary with encrypted components
        private_key: Recipient's EC private key object

    Returns:
        Decrypted data as bytes
    """
    # Decode all components
    ephemeral_public_key_bytes = base64.b64decode(
        encrypted_data["ephemeral_public_key"]
    )
    nonce = base64.b64decode(encrypted_data["nonce"])
    tag = base64.b64decode(encrypted_data["tag"])
    ciphertext = base64.b64decode(encrypted_data["ciphertext"])

    # Deserialize ephemeral public key
    ephemeral_public_key = serialization.load_pem_public_key(
        ephemeral_public_key_bytes, backend=default_backend()
    )

    # Perform ECDH key exchange to get the same shared secret
    shared_key = private_key.exchange(ec.ECDH(), ephemeral_public_key)

    # Derive the same encryption key
    derived_key = HKDF(
        algorithm=hashes.SHA256(),
        length=32,
        salt=None,
        info=b"ECIES Encryption",
        backend=default_backend(),
    ).derive(shared_key)

    # Create a decryptor object
    decryptor = Cipher(
        algorithms.AES(derived_key), modes.GCM(nonce, tag), backend=default_backend()
    ).decryptor()

    # Decrypt the data
    return decryptor.update(ciphertext) + decryptor.finalize()


def load_ec_key_from_file(
    key_path: str, is_private: bool = True
) -> ec.EllipticCurvePrivateKey | ec.EllipticCurvePublicKey:
    """
    Load an EC key from a PEM file

    Args:
        key_path: Path to the key file
        is_private: Whether this is a private key (True) or public key (False)

    Returns:
        EC key object (private or public)
    """
    with open(key_path, "rb") as f:
        key_data = f.read()

    if is_private:
        return serialization.load_pem_private_key(
            key_data, password=None, backend=default_backend()
        )
    else:
        return serialization.load_pem_public_key(key_data, backend=default_backend())


def load_certificate_from_file(cert_path: str) -> x509.Certificate:
    """
    Load an X.509 certificate from a PEM file

    Args:
        cert_path: Path to the certificate file

    Returns:
        X.509 certificate object
    """
    with open(cert_path, "rb") as f:
        cert_data = f.read()

    return x509.load_pem_x509_certificate(cert_data, default_backend())


# Example usage
if __name__ == "__main__":
    # Generate EC key pair and certificate
    private_key, public_key = generate_ec_key_pair()

    # Generate certificate using the EC key pair
    cert_path, pub_key_path, priv_key_path = generate_ec_certificate(
        private_key,
        public_key,
        common_name="securedomain.com",
        organization_name="Cryptography Examples Inc.",
    )

    print(f"Certificate generated at: {cert_path}")

    # Load the certificate to verify
    cert = load_certificate_from_file(cert_path)
    print(f"Certificate subject: {cert.subject}")
    print(f"Certificate issuer: {cert.issuer}")
    print(f"Valid from: {cert.not_valid_before}")
    print(f"Valid until: {cert.not_valid_after}")

    # Example message for encryption
    message = "This is a secure message protected with EC cryptography"

    # Encrypt with the public key
    encrypted = ecies_encrypt(message, public_key)
    print(f"Encrypted message: {encrypted}")

    # Decrypt with the private key
    decrypted = ecies_decrypt(encrypted, private_key)
    print(f"Decrypted message: {decrypted.decode('utf-8')}")

    # Verify the entire process worked correctly
    assert decrypted.decode("utf-8") == message
    print("EC certificate generation, encryption, and decryption successful!")
