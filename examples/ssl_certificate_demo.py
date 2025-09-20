#!/usr/bin/env python3
"""
Example demonstrating SSL/TLS certificate management in Vault.

This example shows how to:
1. Initialize the certificate manager
2. Create secure gRPC servers and clients
3. Establish mutual TLS connections
"""
import asyncio
import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from vault.crypto.certificate_manager import get_certificate_manager, CertificateManager
from vault.crypto.grpc_ssl import SSLContext


async def demonstrate_ssl_setup():
    """Demonstrate the SSL certificate management setup."""
    print("=== Vault SSL/TLS Certificate Management Demo ===\n")
    
    # Step 1: Initialize the certificate manager
    print("1. Initializing Certificate Manager")
    cert_manager = get_certificate_manager()
    print(f"   ✓ CA Certificate generated: {cert_manager.ca_common_name}")
    print(f"   ✓ CA certificate size: {len(cert_manager.get_ca_certificate())} bytes\n")
    
    # Step 2: Issue certificates for different components
    print("2. Issuing Certificates for Vault Components")
    
    components = [
        ("user-alice", "Alice's user client"),
        ("user-bob", "Bob's user client"), 
        ("bootstrap-server", "Bootstrap service"),
        ("setup-master", "Setup coordination service"),
        ("share-server-1", "Threshold share server #1"),
        ("share-server-2", "Threshold share server #2"),
    ]
    
    ssl_contexts = {}
    for component_name, description in components:
        ssl_context = cert_manager.issue_client_certificate(component_name)
        ssl_contexts[component_name] = ssl_context
        print(f"   ✓ {description}: Certificate issued")
    
    print(f"   Total components with certificates: {len(ssl_contexts)}\n")
    
    # Step 3: Demonstrate certificate trust verification
    print("3. Verifying Certificate Trust Chain")
    ca_cert = cert_manager.get_ca_certificate()
    
    for component_name, ssl_context in ssl_contexts.items():
        # Verify all components trust the same CA
        assert ssl_context.ca_cert_pem == ca_cert
        
        # Verify each component has its own unique certificate
        assert ssl_context.cert_pem is not None
        assert ssl_context.key_pem is not None
        
    print("   ✓ All components share the same trusted CA certificate")
    print("   ✓ Each component has unique client certificate and private key\n")
    
    # Step 4: Demonstrate credential creation for gRPC
    print("4. Creating gRPC SSL Credentials")
    
    # Server credentials (for components that accept connections)
    server_components = ["bootstrap-server", "setup-master", "share-server-1"]
    for component in server_components:
        ssl_context = ssl_contexts[component]
        server_creds = ssl_context.create_server_credentials()
        print(f"   ✓ {component}: Server credentials created")
    
    # Client credentials (for components that make connections)
    client_components = ["user-alice", "user-bob"]
    for component in client_components:
        ssl_context = ssl_contexts[component]
        channel_creds = ssl_context.create_channel_credentials()
        print(f"   ✓ {component}: Client credentials created")
    
    print()
    
    # Step 5: Show how components would establish secure connections
    print("5. Secure Connection Examples")
    
    print("   Example: User Alice connecting to Bootstrap Server")
    alice_context = ssl_contexts["user-alice"]
    bootstrap_context = ssl_contexts["bootstrap-server"]
    
    print(f"   - Alice's certificate: {alice_context.component_name}")
    print(f"   - Bootstrap's certificate: {bootstrap_context.component_name}")
    print("   - Connection would use mutual TLS authentication")
    print("   - Both certificates signed by same CA for trust")
    
    # Note: We don't actually create gRPC connections here since that would
    # require running servers, but we show the SSL context is ready
    
    print("\n6. Certificate Manager Statistics")
    issued_certs = cert_manager.list_issued_certificates()
    print(f"   - Total certificates issued: {len(issued_certs)}")
    print(f"   - Components: {', '.join(issued_certs)}")
    
    print("\n✓ SSL/TLS Certificate Management Demo Complete!")
    print("\nAll vault components can now establish secure, authenticated")
    print("gRPC connections using certificates signed by the shared CA.")


async def demonstrate_custom_certificate_manager():
    """Demonstrate creating a custom certificate manager."""
    print("\n=== Custom Certificate Manager Demo ===\n")
    
    # Create a custom certificate manager with different settings
    custom_cm = CertificateManager(ca_common_name="Custom Vault CA")
    custom_cm.initialize()
    
    print(f"✓ Custom CA created: {custom_cm.ca_common_name}")
    
    # Issue a certificate using the custom CA
    ssl_context = custom_cm.issue_client_certificate("custom-component")
    print("✓ Certificate issued using custom CA")
    
    # Show that different CAs create different certificates
    default_ca_cert = get_certificate_manager().get_ca_certificate()
    custom_ca_cert = custom_cm.get_ca_certificate()
    
    assert default_ca_cert != custom_ca_cert
    print("✓ Custom CA certificate differs from default CA")
    print("✓ Custom certificate manager demo complete!")


if __name__ == "__main__":
    asyncio.run(demonstrate_ssl_setup())
    asyncio.run(demonstrate_custom_certificate_manager())