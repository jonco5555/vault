#!/usr/bin/env python3
"""
Test script for SSL certificate functionality.
"""
import sys
import os

# Add src to path for testing
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from vault.crypto.ssl import generate_ca_cert_and_key, generate_client_cert
from vault.crypto.certificate_manager import CertificateManager

def test_ssl_functionality():
    """Test SSL certificate generation functionality."""
    print('Testing CA certificate generation...')
    ca_cert, ca_key = generate_ca_cert_and_key()
    print(f'✓ CA cert length: {len(ca_cert)} bytes')
    print(f'✓ CA key length: {len(ca_key)} bytes')

    print('\nTesting client certificate generation...')
    client_cert, client_key = generate_client_cert(ca_cert, ca_key, 'test-component')
    print(f'✓ Client cert length: {len(client_cert)} bytes')
    print(f'✓ Client key length: {len(client_key)} bytes')

    print('\nTesting certificate manager...')
    cm = CertificateManager()
    cm.initialize()
    ctx = cm.issue_client_certificate('test-component')
    print(f'✓ SSL context created for: {ctx.component_name}')
    
    print('\n✓ All SSL tests passed!')

if __name__ == '__main__':
    test_ssl_functionality()