import json
from unittest import mock

import pytest
from flask import Flask

from app import app, db_manager, whois_service


@pytest.fixture
def client():
    """Create a test client for the Flask app."""
    with app.test_client() as client:
        # Set the application context
        with app.app_context():
            yield client


class TestAPIEndpoints:
    @mock.patch.object(db_manager, "mmdb_reader")
    @mock.patch.object(db_manager, "last_db_update_time")
    @mock.patch.object(db_manager, "current_db_version_tag")
    @mock.patch.object(whois_service, "get_whois_data")
    def test_geo_lookup_success(
        self, mock_whois_data, mock_version_tag, mock_last_update, mock_reader, client
    ):
        """Test successful geo lookup."""
        # Setup mocks
        from datetime import datetime

        mock_version_tag.__str__ = mock.MagicMock(return_value="v1.0.0")
        mock_last_update = datetime(2023, 1, 1, 0, 0, 0)  # A real datetime object
        db_manager.last_db_update_time = mock_last_update
        db_manager.current_db_version_tag = "v1.0.0"
        mock_reader.get.return_value = {
            "city": {"names": {"en": "Mountain View", "de": "Mountain View"}},
            "country": {"names": {"en": "United States", "de": "Vereinigte Staaten"}},
        }
        mock_whois_data.return_value = {
            "target": "8.8.8.8",
            "lookup_timestamp": "2023-01-01T00:00:00",
            "ip_whois": {"asn": "15169", "asn_description": "GOOGLE"},
        }

        # Make the request
        response = client.get("/api/geo-lookup/8.8.8.8?lang=de")

        # Assertions
        assert response.status_code == 200
        data = json.loads(response.data)
        assert "city" in data
        assert data["city"].get("name") == "Mountain View"
        assert "country" in data
        assert data["country"].get("name") == "Vereinigte Staaten"
        assert "database_info" in data
        mock_reader.get.assert_called_once_with("8.8.8.8")

    @mock.patch.object(db_manager, "mmdb_reader", None)
    def test_geo_lookup_no_database(self, client):
        """Test geo lookup when database is not available."""
        # Make the request
        response = client.get("/api/geo-lookup/8.8.8.8")

        # Assertions
        assert response.status_code == 503
        data = json.loads(response.data)
        assert "error" in data
        assert "database not available" in data["error"].lower()

    @mock.patch.object(db_manager, "mmdb_reader")
    def test_geo_lookup_ip_not_found(self, mock_reader, client):
        """Test geo lookup when IP is not found in database."""
        # Setup mock
        mock_reader.get.return_value = None

        # Make the request
        response = client.get("/api/geo-lookup/8.8.8.8")

        # Assertions
        assert response.status_code == 404
        data = json.loads(response.data)
        assert "error" in data
        assert "not found" in data["error"].lower()

    @mock.patch.object(db_manager, "mmdb_reader")
    @mock.patch.object(whois_service, "get_whois_data")
    def test_geo_lookup_invalid_ip(self, mock_whois_data, mock_reader, client):
        """Test geo lookup with invalid IP format."""
        # Make sure the reader is not None, so we reach the ValueError part
        # If mock_reader were None, we would immediately return 503
        mock_reader.get.side_effect = ValueError("Invalid IP address")
        # Whois should not be called, but we mock it anyway for safety

        # Make the request with invalid IP
        response = client.get("/api/geo-lookup/invalid-ip")

        # Assertions
        assert response.status_code == 400
        data = json.loads(response.data)
        assert "error" in data
        assert "invalid ip" in data["error"].lower()

        # Whois should not have been called since validation fails earlier
        mock_whois_data.assert_not_called()

    @mock.patch.object(db_manager, "get_status")
    def test_status_endpoint(self, mock_get_status, client):
        """Test status endpoint."""
        # Setup mock
        mock_get_status.return_value = {
            "database_loaded": True,
            "last_database_update_check_utc": "2023-01-01T00:00:00",
            "current_database_version_tag": "v1.0.0",
            "current_database_file": "/path/to/db.mmdb",
        }

        # Make the request
        response = client.get("/api/status")

        # Assertions
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data["database_loaded"] is True
        assert data["last_database_update_check_utc"] == "2023-01-01T00:00:00"
        assert data["current_database_version_tag"] == "v1.0.0"
        assert data["current_database_file"] == "/path/to/db.mmdb"
        mock_get_status.assert_called_once()

    @mock.patch.object(whois_service, "get_whois_data")
    def test_whois_lookup_success(self, mock_get_whois_data, client):
        """Test successful WHOIS lookup."""
        # Setup mock
        mock_get_whois_data.return_value = {
            "target": "example.com",
            "lookup_timestamp": "2023-01-01T00:00:00",
            "domain_whois": {"domain_name": "EXAMPLE.COM"},
        }

        # Make the request
        response = client.get("/api/whois/example.com")

        # Assertions
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data["target"] == "example.com"
        assert data["domain_whois"]["domain_name"] == "EXAMPLE.COM"
        mock_get_whois_data.assert_called_once_with("example.com")

    @mock.patch.object(whois_service, "get_whois_data")
    def test_whois_lookup_exception(self, mock_get_whois_data, client):
        """Test WHOIS lookup with exception."""
        # Setup mock to raise an exception
        mock_get_whois_data.side_effect = Exception("Test error")

        # Make the request
        response = client.get("/api/whois/example.com")

        # Assertions
        assert response.status_code == 500
        data = json.loads(response.data)
        assert "error" in data
        assert "internal server error" in data["error"].lower()
        mock_get_whois_data.assert_called_once_with("example.com")
