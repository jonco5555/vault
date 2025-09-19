import datetime

from cryptography import x509
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.x509.oid import NameOID


def generate_cert_and_keys(
    common_name: str = "example.com",
):
    priv_key, pub_key = generate_ec_key_pair()
    cert, pubkey_pem, privkey_pem = generate_ec_certificate(
        priv_key,
        pub_key,
        common_name=common_name,
    )
    return cert, pubkey_pem, privkey_pem


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
) -> tuple[str, str, str]:
    """
    Generate a self-signed X.509 certificate using EC keys.

    Args:
        private_key: EC private key object
        public_key: EC public key object (optional, will be derived from private_key if not provided)
        common_name: Domain name for the certificate

    Returns:
        Tuple containing (certificate_path, public_key_path, private_key_path)
    """
    # Create a self-signed certificate
    subject = x509.Name(
        [
            x509.NameAttribute(NameOID.COMMON_NAME, common_name),
        ]
    )

    # Certificate validity period
    not_valid_before = datetime.datetime.now(datetime.timezone.utc)
    not_valid_after = not_valid_before + datetime.timedelta(days=365)

    # Build certificate
    certificate = (
        x509.CertificateBuilder()
        .subject_name(subject)
        .issuer_name(subject)
        .public_key(public_key)
        .serial_number(x509.random_serial_number())
        .not_valid_before(not_valid_before)
        .not_valid_after(not_valid_after)
        .add_extension(
            x509.SubjectAlternativeName(
                [x509.DNSName(common_name), x509.DNSName("localhost")]
            ),
            critical=False,
        )
        .add_extension(x509.BasicConstraints(ca=True, path_length=None), critical=True)
        .sign(private_key, hashes.SHA256(), default_backend())
    )

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
