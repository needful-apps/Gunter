import socket
from unittest import mock

import pytest

from app import WhoisService


class TestWhoisService:
    @pytest.fixture
    def whois_service(self):
        return WhoisService()

    def test_is_ip_valid(self, whois_service):
        """Test IP validation with valid IPs."""
        assert whois_service._is_ip("8.8.8.8")
        assert whois_service._is_ip("192.168.1.1")
        assert whois_service._is_ip("2001:0db8:85a3:0000:0000:8a2e:0370:7334")

    def test_is_ip_invalid(self, whois_service):
        """Test IP validation with invalid values."""
        assert not whois_service._is_ip("example.com")
        assert not whois_service._is_ip("not-an-ip")
        assert not whois_service._is_ip("999.999.999.999")

    @mock.patch("app.IPWhois")
    def test_get_ip_whois_success(self, mock_ip_whois, whois_service):
        """Test successful IP WHOIS lookup."""
        # Setup mock response
        mock_ip_whois_instance = mock.MagicMock()
        mock_ip_whois_instance.lookup_rdap.return_value = {
            "asn": "15169",
            "asn_description": "GOOGLE - Google LLC",
            "network": {"name": "GOOGLE"},
            "objects": {"test": "data"},
        }
        mock_ip_whois.return_value = mock_ip_whois_instance

        # Test the method
        result = whois_service._get_ip_whois("8.8.8.8")

        # Assertions
        mock_ip_whois.assert_called_once_with("8.8.8.8")
        mock_ip_whois_instance.lookup_rdap.assert_called_once_with(depth=1)
        assert result["asn"] == "15169"
        assert result["asn_description"] == "GOOGLE - Google LLC"
        assert result["network"] == {"name": "GOOGLE"}
        assert result["objects"] == {"test": "data"}

    @mock.patch("app.IPWhois")
    def test_get_ip_whois_exception(self, mock_ip_whois, whois_service):
        """Test exception handling in IP WHOIS lookup."""
        # Setup mock to raise an exception
        mock_ip_whois_instance = mock.MagicMock()
        mock_ip_whois_instance.lookup_rdap.side_effect = Exception("Test error")
        mock_ip_whois.return_value = mock_ip_whois_instance

        # Test the method
        result = whois_service._get_ip_whois("8.8.8.8")

        # Assertions
        assert "error" in result
        assert "Test error" in result["error"]

    @mock.patch("app.whois.whois")
    def test_get_domain_whois_success(self, mock_whois, whois_service):
        """Test successful domain WHOIS lookup."""
        # Setup mock response - erstelle ein Dictionary, das dem Ergebnis von whois.whois() entspricht
        from datetime import datetime

        # Das neue whois.whois() gibt ein Dictionary zurück, kein Objekt
        whois_data = {
            "domain_name": "EXAMPLE.COM",
            "registrar": "Test Registrar",
            "name_servers": ["ns1.example.com", "ns2.example.com"],
            "creation_date": datetime(1995, 8, 14, 4, 0, 0),
            "expiration_date": datetime(2023, 8, 13, 4, 0, 0),
            "status": "clientDeleteProhibited",
        }
        # Setze das Mock zurück
        mock_whois.return_value = whois_data

        # Test the method
        result = whois_service._get_domain_whois("example.com")

        # Assertions
        mock_whois.assert_called_once_with("example.com")
        assert result["domain_name"] == "EXAMPLE.COM"
        assert result["registrar"] == "Test Registrar"
        assert len(result["name_servers"]) == 2

    @mock.patch("app.whois.whois")
    def test_get_domain_whois_exception(self, mock_whois, whois_service):
        """Test exception handling in domain WHOIS lookup."""
        # Setup mock to raise an exception
        mock_whois.side_effect = Exception("Test error")

        # Test the method
        result = whois_service._get_domain_whois("example.com")

        # Assertions
        assert "error" in result
        assert "Test error" in result["error"]

    @mock.patch("app.socket.gethostbyaddr")
    def test_resolve_ip_to_domain_success(self, mock_gethostbyaddr, whois_service):
        """Test successful reverse DNS lookup."""
        # Setup mock
        mock_gethostbyaddr.return_value = ("example.com", [], ["8.8.8.8"])

        # Test the method
        result = whois_service.resolve_ip_to_domain("8.8.8.8")

        # Assertions
        mock_gethostbyaddr.assert_called_once_with("8.8.8.8")
        assert result == "example.com"

    @mock.patch("app.socket.gethostbyaddr")
    def test_resolve_ip_to_domain_failure(self, mock_gethostbyaddr, whois_service):
        """Test failure handling in reverse DNS lookup."""
        # Setup mock to raise an exception
        mock_gethostbyaddr.side_effect = socket.herror("Host not found")

        # Test the method
        result = whois_service.resolve_ip_to_domain("8.8.8.8")

        # Assertions
        assert result is None

    @mock.patch.object(WhoisService, "_get_ip_whois")
    @mock.patch.object(WhoisService, "_is_ip")
    @mock.patch.object(WhoisService, "resolve_ip_to_domain")
    def test_get_whois_data_for_ip(
        self, mock_resolve, mock_is_ip, mock_get_ip_whois, whois_service
    ):
        """Test WHOIS data retrieval for an IP address."""
        # Setup mocks
        mock_is_ip.return_value = True
        mock_get_ip_whois.return_value = {"asn": "15169"}
        mock_resolve.return_value = "example.com"

        # Test the method
        result = whois_service.get_whois_data("8.8.8.8")

        # Assertions
        assert result["target"] == "8.8.8.8"
        assert "lookup_timestamp" in result
        assert result["ip_whois"] == {"asn": "15169"}
        assert result["reverse_dns"] == "example.com"
        mock_is_ip.assert_called_once_with("8.8.8.8")
        mock_get_ip_whois.assert_called_once_with("8.8.8.8")
        mock_resolve.assert_called_once_with("8.8.8.8")

    @mock.patch.object(WhoisService, "_get_domain_whois")
    @mock.patch.object(WhoisService, "_is_ip")
    def test_get_whois_data_for_domain(
        self, mock_is_ip, mock_get_domain_whois, whois_service
    ):
        """Test WHOIS data retrieval for a domain."""
        # Setup mocks
        mock_is_ip.return_value = False
        mock_get_domain_whois.return_value = {"domain_name": "EXAMPLE.COM"}

        # Test the method
        result = whois_service.get_whois_data("example.com")

        # Assertions
        assert result["target"] == "example.com"
        assert "lookup_timestamp" in result
        assert result["domain_whois"] == {"domain_name": "EXAMPLE.COM"}
        assert "reverse_dns" not in result
        mock_is_ip.assert_called_once_with("example.com")
        mock_get_domain_whois.assert_called_once_with("example.com")
