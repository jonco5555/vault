import datetime
import ipaddress
from typing import Optional, Tuple

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


def generate_ca_cert_and_key(
    common_name: str = "Vault Root CA",
    validity_days: int = 3650,
) -> Tuple[bytes, bytes]:
    """
    Generate a Certificate Authority (CA) certificate and private key.
    
    Args:
        common_name: Name for the CA certificate
        validity_days: Number of days the CA certificate is valid
        
    Returns:
        Tuple of (ca_cert_pem, ca_key_pem)
    """
    # Generate CA private key
    ca_private_key = ec.generate_private_key(ec.SECP256R1(), default_backend())
    
    # Create CA certificate
    subject = x509.Name([
        x509.NameAttribute(NameOID.COMMON_NAME, common_name),
        x509.NameAttribute(NameOID.ORGANIZATION_NAME, "Vault System"),
        x509.NameAttribute(NameOID.ORGANIZATIONAL_UNIT_NAME, "Security"),
    ])
    
    not_valid_before = datetime.datetime.now(datetime.timezone.utc)
    not_valid_after = not_valid_before + datetime.timedelta(days=validity_days)
    
    ca_cert = (
        x509.CertificateBuilder()
        .subject_name(subject)
        .issuer_name(subject)  # Self-signed for CA
        .public_key(ca_private_key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(not_valid_before)
        .not_valid_after(not_valid_after)
        .add_extension(
            x509.BasicConstraints(ca=True, path_length=None),
            critical=True,
        )
        .add_extension(
            x509.KeyUsage(
                key_cert_sign=True,
                crl_sign=True,
                digital_signature=False,
                key_encipherment=False,
                key_agreement=False,
                content_commitment=False,
                data_encipherment=False,
                encipher_only=False,
                decipher_only=False,
            ),
            critical=True,
        )
        .sign(ca_private_key, hashes.SHA256(), default_backend())
    )
    
    ca_cert_pem = ca_cert.public_bytes(serialization.Encoding.PEM)
    ca_key_pem = ca_private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    )
    
    return ca_cert_pem, ca_key_pem


def generate_client_cert(
    ca_cert_pem: bytes,
    ca_key_pem: bytes,
    common_name: str,
    validity_days: int = 365,
) -> Tuple[bytes, bytes]:
    """
    Generate a client certificate signed by the CA.
    
    Args:
        ca_cert_pem: CA certificate in PEM format
        ca_key_pem: CA private key in PEM format  
        common_name: Common name for the client certificate
        validity_days: Number of days the certificate is valid
        
    Returns:
        Tuple of (client_cert_pem, client_key_pem)
    """
    # Load CA certificate and key
    ca_cert = x509.load_pem_x509_certificate(ca_cert_pem, default_backend())
    ca_private_key = serialization.load_pem_private_key(
        ca_key_pem, password=None, backend=default_backend()
    )
    
    # Generate client private key
    client_private_key = ec.generate_private_key(ec.SECP256R1(), default_backend())
    
    # Create client certificate
    subject = x509.Name([
        x509.NameAttribute(NameOID.COMMON_NAME, common_name),
        x509.NameAttribute(NameOID.ORGANIZATION_NAME, "Vault System"),
    ])
    
    not_valid_before = datetime.datetime.now(datetime.timezone.utc)
    not_valid_after = not_valid_before + datetime.timedelta(days=validity_days)
    
    client_cert = (
        x509.CertificateBuilder()
        .subject_name(subject)
        .issuer_name(ca_cert.subject)
        .public_key(client_private_key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(not_valid_before)
        .not_valid_after(not_valid_after)
        .add_extension(
            x509.BasicConstraints(ca=False, path_length=None),
            critical=True,
        )
        .add_extension(
            x509.KeyUsage(
                digital_signature=True,
                key_encipherment=True,
                key_agreement=True,
                key_cert_sign=False,
                crl_sign=False,
                content_commitment=False,
                data_encipherment=False,
                encipher_only=False,
                decipher_only=False,
            ),
            critical=True,
        )
        .add_extension(
            x509.ExtendedKeyUsage([
                x509.oid.ExtendedKeyUsageOID.CLIENT_AUTH,
                x509.oid.ExtendedKeyUsageOID.SERVER_AUTH,
            ]),
            critical=True,
        )
        .add_extension(
            x509.SubjectAlternativeName([
                x509.DNSName("localhost"),
                x509.DNSName(common_name),
                x509.IPAddress(ipaddress.IPv4Address("127.0.0.1")),
            ]),
            critical=False,
        )
        .sign(ca_private_key, hashes.SHA256(), default_backend())
    )
    
    client_cert_pem = client_cert.public_bytes(serialization.Encoding.PEM)
    client_key_pem = client_private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    )
    
    return client_cert_pem, client_key_pem


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
