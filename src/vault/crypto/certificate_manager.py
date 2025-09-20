"""
Certificate Manager for vault components.
Handles CA certificate generation, client certificate issuance, and distribution.
"""
import logging
from typing import Dict, Optional, Tuple

from vault.crypto.grpc_ssl import SSLContext
from vault.crypto.ssl import generate_ca_cert_and_key, generate_client_cert

logger = logging.getLogger(__name__)


class CertificateManager:
    """
    Manages SSL certificates for vault components.
    Generates CA certificate and issues client certificates.
    """
    
    def __init__(self, ca_common_name: str = "Vault Root CA"):
        """
        Initialize certificate manager.
        
        Args:
            ca_common_name: Common name for the CA certificate
        """
        self.ca_common_name = ca_common_name
        self.ca_cert_pem: Optional[bytes] = None
        self.ca_key_pem: Optional[bytes] = None
        self._component_contexts: Dict[str, SSLContext] = {}
        self._initialized = False
    
    def initialize(self) -> None:
        """Initialize the certificate manager by generating CA certificate."""
        if self._initialized:
            logger.warning("Certificate manager already initialized")
            return
        
        logger.info(f"Generating CA certificate: {self.ca_common_name}")
        self.ca_cert_pem, self.ca_key_pem = generate_ca_cert_and_key(
            common_name=self.ca_common_name
        )
        self._initialized = True
        logger.info("Certificate manager initialized successfully")
    
    def get_ca_certificate(self) -> bytes:
        """
        Get the CA certificate in PEM format.
        
        Returns:
            CA certificate in PEM format
            
        Raises:
            RuntimeError: If certificate manager is not initialized
        """
        if not self._initialized or not self.ca_cert_pem:
            raise RuntimeError("Certificate manager not initialized")
        return self.ca_cert_pem
    
    def issue_client_certificate(
        self,
        component_name: str,
        common_name: Optional[str] = None,
        validity_days: int = 365,
    ) -> SSLContext:
        """
        Issue a client certificate for a vault component.
        
        Args:
            component_name: Name of the component (e.g., "user", "bootstrap", "share-server")
            common_name: Common name for the certificate (defaults to component_name)
            validity_days: Number of days the certificate is valid
            
        Returns:
            SSLContext containing the certificates for the component
            
        Raises:
            RuntimeError: If certificate manager is not initialized
        """
        if not self._initialized:
            raise RuntimeError("Certificate manager not initialized")
        
        if not common_name:
            common_name = component_name
        
        logger.info(f"Issuing certificate for component: {component_name} (CN: {common_name})")
        
        # Generate client certificate
        cert_pem, key_pem = generate_client_cert(
            self.ca_cert_pem,
            self.ca_key_pem,
            common_name=common_name,
            validity_days=validity_days,
        )
        
        # Create SSL context for the component
        ssl_context = SSLContext(
            ca_cert_pem=self.ca_cert_pem,
            cert_pem=cert_pem,
            key_pem=key_pem,
            component_name=component_name,
        )
        
        # Store context for later retrieval
        self._component_contexts[component_name] = ssl_context
        
        logger.info(f"Certificate issued successfully for component: {component_name}")
        return ssl_context
    
    def get_component_context(self, component_name: str) -> Optional[SSLContext]:
        """
        Get the SSL context for a specific component.
        
        Args:
            component_name: Name of the component
            
        Returns:
            SSLContext for the component, or None if not found
        """
        return self._component_contexts.get(component_name)
    
    def create_ca_ssl_context(self) -> SSLContext:
        """
        Create an SSL context with CA credentials (for components that need to issue certificates).
        
        Returns:
            SSLContext with CA certificate and key
            
        Raises:
            RuntimeError: If certificate manager is not initialized
        """
        if not self._initialized:
            raise RuntimeError("Certificate manager not initialized")
        
        return SSLContext(
            ca_cert_pem=self.ca_cert_pem,
            ca_key_pem=self.ca_key_pem,
            component_name="ca",
        )
    
    def list_issued_certificates(self) -> list[str]:
        """
        List all components that have been issued certificates.
        
        Returns:
            List of component names
        """
        return list(self._component_contexts.keys())


# Global certificate manager instance
_global_cert_manager: Optional[CertificateManager] = None


def get_certificate_manager() -> CertificateManager:
    """
    Get the global certificate manager instance.
    Creates and initializes it if it doesn't exist.
    
    Returns:
        Global certificate manager instance
    """
    global _global_cert_manager
    
    if _global_cert_manager is None:
        _global_cert_manager = CertificateManager()
        _global_cert_manager.initialize()
    
    return _global_cert_manager


def set_certificate_manager(cert_manager: CertificateManager) -> None:
    """
    Set the global certificate manager instance.
    
    Args:
        cert_manager: Certificate manager instance to set as global
    """
    global _global_cert_manager
    _global_cert_manager = cert_manager