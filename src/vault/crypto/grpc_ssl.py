"""
gRPC SSL/TLS utilities for secure communication between vault components.
"""
import grpc
from typing import Optional


def create_server_credentials(
    server_cert_pem: bytes,
    server_key_pem: bytes,
    ca_cert_pem: Optional[bytes] = None,
    require_client_auth: bool = True,
) -> grpc.ServerCredentials:
    """
    Create gRPC server credentials with SSL/TLS support.
    
    Args:
        server_cert_pem: Server certificate in PEM format
        server_key_pem: Server private key in PEM format
        ca_cert_pem: CA certificate for client verification (optional)
        require_client_auth: Whether to require client certificate authentication
        
    Returns:
        gRPC server credentials
    """
    if require_client_auth and ca_cert_pem:
        # Mutual TLS - server and client both authenticate
        return grpc.ssl_server_credentials(
            [(server_key_pem, server_cert_pem)],
            root_certificates=ca_cert_pem,
            require_client_auth=True,
        )
    else:
        # Server-only authentication
        return grpc.ssl_server_credentials([(server_key_pem, server_cert_pem)])


def create_channel_credentials(
    client_cert_pem: Optional[bytes] = None,
    client_key_pem: Optional[bytes] = None,
    ca_cert_pem: Optional[bytes] = None,
) -> grpc.ChannelCredentials:
    """
    Create gRPC channel credentials for secure client connections.
    
    Args:
        client_cert_pem: Client certificate in PEM format (for mutual TLS)
        client_key_pem: Client private key in PEM format (for mutual TLS)
        ca_cert_pem: CA certificate to verify server certificate
        
    Returns:
        gRPC channel credentials
    """
    if client_cert_pem and client_key_pem:
        # Mutual TLS - both client and server authenticate
        return grpc.ssl_channel_credentials(
            root_certificates=ca_cert_pem,
            private_key=client_key_pem,
            certificate_chain=client_cert_pem,
        )
    else:
        # Server-only authentication (client verifies server)
        return grpc.ssl_channel_credentials(root_certificates=ca_cert_pem)


def create_secure_channel(
    target: str,
    client_cert_pem: Optional[bytes] = None,
    client_key_pem: Optional[bytes] = None,
    ca_cert_pem: Optional[bytes] = None,
    options: Optional[list] = None,
):
    """
    Create a secure gRPC channel with SSL/TLS.
    
    Args:
        target: The server address (e.g., "localhost:50051")
        client_cert_pem: Client certificate in PEM format (for mutual TLS)
        client_key_pem: Client private key in PEM format (for mutual TLS)
        ca_cert_pem: CA certificate to verify server certificate
        options: Additional gRPC channel options
        
    Returns:
        Secure gRPC channel
    """
    credentials = create_channel_credentials(client_cert_pem, client_key_pem, ca_cert_pem)
    return grpc.aio.secure_channel(target, credentials, options=options)


class SSLContext:
    """
    Container for SSL certificates and keys used by vault components.
    """
    
    def __init__(
        self,
        ca_cert_pem: bytes,
        ca_key_pem: Optional[bytes] = None,
        cert_pem: Optional[bytes] = None,
        key_pem: Optional[bytes] = None,
        component_name: Optional[str] = None,
    ):
        """
        Initialize SSL context.
        
        Args:
            ca_cert_pem: CA certificate in PEM format
            ca_key_pem: CA private key in PEM format (only needed for CA)
            cert_pem: Component certificate in PEM format
            key_pem: Component private key in PEM format
            component_name: Name of the component (for logging)
        """
        self.ca_cert_pem = ca_cert_pem
        self.ca_key_pem = ca_key_pem
        self.cert_pem = cert_pem
        self.key_pem = key_pem
        self.component_name = component_name or "unknown"
    
    def create_server_credentials(self, require_client_auth: bool = True) -> grpc.ServerCredentials:
        """Create server credentials using this SSL context."""
        if not self.cert_pem or not self.key_pem:
            raise ValueError(f"Component {self.component_name} missing certificate or key for server credentials")
        
        return create_server_credentials(
            self.cert_pem,
            self.key_pem,
            self.ca_cert_pem,
            require_client_auth,
        )
    
    def create_channel_credentials(self) -> grpc.ChannelCredentials:
        """Create channel credentials using this SSL context."""
        return create_channel_credentials(
            self.cert_pem,
            self.key_pem,
            self.ca_cert_pem,
        )
    
    def create_secure_channel(self, target: str, options: Optional[list] = None):
        """Create secure gRPC channel using this SSL context."""
        return create_secure_channel(
            target,
            self.cert_pem,
            self.key_pem,
            self.ca_cert_pem,
            options,
        )