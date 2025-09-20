#!/usr/bin/env python3
"""
Integration test for SSL certificate functionality across components.
"""
import sys
import os
import asyncio

# Add src to path for testing
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from vault.crypto.certificate_manager import CertificateManager
from vault.crypto.grpc_ssl import SSLContext

async def test_ssl_integration():
    """Test SSL certificate generation and gRPC integration."""
    print('=== SSL/TLS Integration Test ===\n')
    
    # Test certificate manager
    print('1. Testing Certificate Manager...')
    cert_manager = CertificateManager()
    cert_manager.initialize()
    print(f'✓ Certificate manager initialized with CA: {cert_manager.ca_common_name}')
    
    # Test issuing certificates for various components
    components = ['user-test', 'bootstrap', 'setup-master', 'setup-unit', 'share-server']
    ssl_contexts = {}
    
    print('\n2. Issuing certificates for components...')
    for component in components:
        ssl_context = cert_manager.issue_client_certificate(component)
        ssl_contexts[component] = ssl_context
        print(f'✓ Certificate issued for: {component}')
    
    # Test that all components have the same CA certificate
    print('\n3. Verifying certificate trust chain...')
    ca_cert = cert_manager.get_ca_certificate()
    for component, ssl_context in ssl_contexts.items():
        assert ssl_context.ca_cert_pem == ca_cert, f"CA cert mismatch for {component}"
        assert ssl_context.cert_pem is not None, f"No client cert for {component}"
        assert ssl_context.key_pem is not None, f"No client key for {component}"
    print(f'✓ All {len(components)} components share the same CA certificate')
    
    # Test SSL context functionality
    print('\n4. Testing SSL context functionality...')
    user_context = ssl_contexts['user-test']
    try:
        # Test credential creation
        server_creds = user_context.create_server_credentials()
        channel_creds = user_context.create_channel_credentials()
        print('✓ SSL credentials created successfully')
        
        # Note: We can't test actual gRPC connections without running servers,
        # but we can verify that the credentials are created without errors
        
    except Exception as e:
        print(f'✗ SSL context test failed: {e}')
        return False
    
    print('\n5. Testing global certificate manager...')
    from vault.crypto.certificate_manager import get_certificate_manager
    global_cm = get_certificate_manager()
    assert global_cm is not None, "Global certificate manager not available"
    print('✓ Global certificate manager accessible')
    
    print('\n✓ All SSL/TLS integration tests passed!')
    return True

if __name__ == '__main__':
    success = asyncio.run(test_ssl_integration())
    if not success:
        sys.exit(1)