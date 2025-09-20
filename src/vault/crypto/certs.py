from datetime import datetime, timedelta

from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import ExtendedKeyUsageOID, NameOID


def generate_ca_cert_and_key(
    ca_key: rsa.RSAPrivateKey, key_path: str = "ca.key", cert_path: str = "ca.crt"
) -> None:
    ca_key = rsa.generate_private_key(public_exponent=65537, key_size=4096)

    ca_name = x509.Name(
        [
            x509.NameAttribute(NameOID.COMMON_NAME, "My CA"),
        ]
    )

    ca_cert = (
        x509.CertificateBuilder()
        .subject_name(ca_name)
        .issuer_name(ca_name)
        .public_key(ca_key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(datetime.utcnow())
        .not_valid_after(datetime.utcnow() + timedelta(days=3650))
        .add_extension(x509.BasicConstraints(ca=True, path_length=None), critical=True)
        .sign(ca_key, hashes.SHA256())
    )

    # Write CA private key to file
    with open(key_path, "wb") as f:
        f.write(
            ca_key.private_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PrivateFormat.TraditionalOpenSSL,
                encryption_algorithm=serialization.NoEncryption(),
            )
        )

    # Write CA certificate to file
    with open(cert_path, "wb") as f:
        f.write(ca_cert.public_bytes(serialization.Encoding.PEM))


def load_ca_cert(cert_path: str = "ca.crt") -> bytes:
    with open(cert_path, "rb") as f:
        return f.read()


def generate_component_cert_and_key(
    name: str,
    dns_names: list[str] = [],
    ca_cert_path: str = "ca.crt",
    ca_key_path: str = "ca.key",
) -> tuple[bytes, bytes]:
    # Load CA certificate
    ca_cert = x509.load_pem_x509_certificate(load_ca_cert(ca_cert_path))

    # Load CA private key
    with open(ca_key_path, "rb") as f:
        ca_key = serialization.load_pem_private_key(f.read(), password=None)

    server_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)

    server_name = x509.Name(
        [
            x509.NameAttribute(NameOID.COMMON_NAME, name),
        ]
    )

    csr = (
        x509.CertificateSigningRequestBuilder()
        .subject_name(server_name)
        .add_extension(
            x509.SubjectAlternativeName(
                [
                    x509.DNSName("localhost"),
                    x509.DNSName("host.docker.internal"),
                    x509.DNSName(name),
                ]
                + [x509.DNSName(dns) for dns in dns_names]
            ),
            critical=False,
        )
        .sign(server_key, hashes.SHA256())
    )

    server_cert = (
        x509.CertificateBuilder()
        .subject_name(csr.subject)
        .issuer_name(ca_cert.subject)
        .public_key(csr.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(datetime.utcnow())
        .not_valid_after(datetime.utcnow() + timedelta(days=825))
        .add_extension(x509.BasicConstraints(ca=False, path_length=None), critical=True)
        .add_extension(
            x509.ExtendedKeyUsage([ExtendedKeyUsageOID.SERVER_AUTH]), critical=False
        )
        .add_extension(
            csr.extensions.get_extension_for_class(x509.SubjectAlternativeName).value,
            critical=False,
        )
        .sign(ca_key, hashes.SHA256())
    )

    return server_cert.public_bytes(
        serialization.Encoding.PEM
    ), server_key.private_bytes(
        serialization.Encoding.PEM,
        serialization.PrivateFormat.TraditionalOpenSSL,
        serialization.NoEncryption(),
    )
