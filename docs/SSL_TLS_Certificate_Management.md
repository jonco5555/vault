# SSL/TLS Certificate Management for Vault

This document describes the SSL/TLS certificate management system implemented for secure gRPC communications in the Vault project.

## Overview

The vault system now uses a Certificate Authority (CA) based trust model for secure gRPC communications between all components. Instead of using insecure channels, all components now:

1. Use certificates signed by a central Certificate Authority (CA)
2. Establish mutual TLS (mTLS) connections for authentication
3. Verify the identity of communication partners through certificate validation

## Architecture

### Certificate Authority (CA)

The system uses a single Certificate Authority that:
- Generates a self-signed root CA certificate
- Issues client certificates for all vault components
- Provides the trust anchor for all certificate validation

### Components

All vault components receive certificates signed by the CA:
- **User clients**: Each user gets a unique certificate for authentication
- **Bootstrap server**: Certificate for the bootstrap service
- **Setup Master**: Certificate for the setup coordination service  
- **Setup Units**: Certificates for individual service instances
- **Share Servers**: Certificates for threshold sharing services

## Implementation

### Core Modules

#### `src/vault/crypto/ssl.py`
Enhanced SSL module providing:
- `generate_ca_cert_and_key()`: Creates CA certificate and private key
- `generate_client_cert()`: Issues client certificates signed by CA
- Support for both server and client authentication certificates

#### `src/vault/crypto/certificate_manager.py`
Central certificate management:
- `CertificateManager`: Main class for certificate operations
- `get_certificate_manager()`: Global singleton access
- Automatic certificate issuance for components
- CA certificate distribution

#### `src/vault/crypto/grpc_ssl.py`
gRPC SSL utilities:
- `SSLContext`: Container for certificates and keys
- `create_secure_channel()`: Factory for secure gRPC channels
- `create_server_credentials()`: Factory for secure server credentials
- Support for both mutual TLS and server-only authentication

### Updated Components

#### User Class (`src/vault/user/user.py`)
```python
# Before: Insecure channels
async with grpc.aio.insecure_channel(f"{self._server_ip}:{self._server_port}") as channel:
    # ... gRPC calls

# After: Secure channels with client certificates
async with self._ssl_context.create_secure_channel(f"{self._server_ip}:{self._server_port}") as channel:
    # ... gRPC calls
```

#### Bootstrap Class (`src/vault/bootstrap/bootstrap.py`)
```python
# Before: Self-signed certificates
self._cert, self._ssl_pubkey, self._ssl_privkey = generate_cert_and_keys()
creds = grpc.ssl_server_credentials([(self._ssl_privkey, self._cert)])

# After: CA-signed certificates
cert_manager = get_certificate_manager()
self._ssl_context = cert_manager.issue_client_certificate("bootstrap")
server_credentials = self._ssl_context.create_server_credentials()
```

## Usage

### Basic Certificate Setup

```python
from vault.crypto.certificate_manager import get_certificate_manager

# Get the global certificate manager (creates CA if needed)
cert_manager = get_certificate_manager()

# Issue certificate for a component
ssl_context = cert_manager.issue_client_certificate("my-component")
```

### Secure gRPC Server

```python
import grpc
from vault.crypto.certificate_manager import get_certificate_manager

# Get SSL context for the server
cert_manager = get_certificate_manager()
ssl_context = cert_manager.issue_client_certificate("my-server")

# Create secure gRPC server
server = grpc.aio.server()
server_credentials = ssl_context.create_server_credentials()
server.add_secure_port("[::]:50051", server_credentials)
```

### Secure gRPC Client

```python
from vault.crypto.certificate_manager import get_certificate_manager

# Get SSL context for the client
cert_manager = get_certificate_manager()
ssl_context = cert_manager.issue_client_certificate("my-client")

# Create secure connection
async with ssl_context.create_secure_channel("server:50051") as channel:
    stub = MyServiceStub(channel)
    response = await stub.MyMethod(request)
```

## Security Benefits

### Mutual Authentication
- Both client and server verify each other's identity
- Prevents unauthorized components from connecting
- Protects against man-in-the-middle attacks

### Certificate-Based Authorization  
- Each component has a unique certificate identity
- Enables fine-grained access control
- Audit trails for component interactions

### Encrypted Communication
- All gRPC traffic is encrypted using TLS
- Protects sensitive data in transit
- Meets security compliance requirements

## Migration Notes

### Backward Compatibility
The implementation maintains API compatibility by:
- Optional SSL context parameters in constructors
- Automatic certificate generation when not provided
- Graceful fallback to default certificate manager

### Testing
- `test_ssl.py`: Basic SSL functionality tests
- `test_ssl_integration.py`: End-to-end certificate management tests
- All core SSL components validated

### Configuration
The certificate manager can be customized:
```python
from vault.crypto.certificate_manager import CertificateManager, set_certificate_manager

# Create custom certificate manager
custom_cm = CertificateManager(ca_common_name="Custom Vault CA")
custom_cm.initialize()

# Set as global instance
set_certificate_manager(custom_cm)
```

## Certificate Lifecycle

1. **Initialization**: CA certificate generated on first use
2. **Issuance**: Client certificates created on demand for components
3. **Distribution**: Certificates automatically provided to components
4. **Validation**: All gRPC connections verify certificate chains
5. **Renewal**: Certificates valid for 365 days (configurable)

## Troubleshooting

### Common Issues

1. **Certificate verification failed**
   - Ensure all components use the same CA certificate
   - Check certificate validity dates
   - Verify hostname/IP matches certificate SAN

2. **Connection refused on secure port**
   - Confirm server is using secure port (`add_secure_port`)
   - Check that client is using secure channel credentials
   - Verify certificates are properly configured

3. **Import errors**
   - Install required dependencies: `grpcio`, `cryptography`
   - Ensure proper Python path configuration

### Debug Mode
Enable detailed logging for certificate operations:
```python
import logging
logging.getLogger('vault.crypto').setLevel(logging.DEBUG)
```

## Future Enhancements

1. **Certificate Rotation**: Automatic certificate renewal before expiration
2. **Certificate Revocation**: CRL or OCSP support for revoked certificates  
3. **Hardware Security**: Integration with HSMs for key protection
4. **External CA**: Support for enterprise certificate authorities
5. **Certificate Policies**: Configurable certificate validation rules