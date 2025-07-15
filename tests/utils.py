import json
import os
from typing import Any, Dict, cast


def load_fixture(filename: str) -> Dict[str, Any]:
    """
    Load a fixture file from the fixtures directory.

    Args:
        filename: Name of the fixture file to load

    Returns:
        The loaded fixture as a dictionary
    """
    fixture_path = os.path.join(os.path.dirname(__file__), "fixtures", filename)
    with open(fixture_path, "r") as f:
        data = json.load(f)
        return cast(Dict[str, Any], data)


def get_mock_geo_response() -> Dict[str, Any]:
    """
    Get a mock GeoIP response

    Returns:
        A dictionary simulating a GeoLite2 response
    """
    result: Dict[str, Any] = {
        "city": {
            "geoname_id": 5375480,
            "names": {
                "de": "Mountain View",
                "en": "Mountain View",
                "fr": "Mountain View",
                "ja": "マウンテンビュー",
                "ru": "Маунтин-Вью",
            },
        },
        "continent": {
            "code": "NA",
            "geoname_id": 6255149,
            "names": {
                "de": "Nordamerika",
                "en": "North America",
                "es": "Norteamérica",
                "fr": "Amérique du Nord",
                "ja": "北アメリカ",
                "pt-BR": "América do Norte",
                "ru": "Северная Америка",
                "zh-CN": "北美洲",
            },
        },
        "country": {
            "geoname_id": 6252001,
            "iso_code": "US",
            "names": {
                "de": "Vereinigte Staaten",
                "en": "United States",
                "es": "Estados Unidos",
                "fr": "États-Unis",
                "ja": "アメリカ合衆国",
                "pt-BR": "Estados Unidos",
                "ru": "США",
                "zh-CN": "美国",
            },
        },
        "location": {
            "accuracy_radius": 1000,
            "latitude": 37.386,
            "longitude": -122.0838,
            "metro_code": 807,
            "time_zone": "America/Los_Angeles",
        },
        "postal": {"code": "94035"},
        "registered_country": {
            "geoname_id": 6252001,
            "iso_code": "US",
            "names": {
                "de": "Vereinigte Staaten",
                "en": "United States",
                "es": "Estados Unidos",
                "fr": "États-Unis",
                "ja": "アメリカ合衆国",
                "pt-BR": "Estados Unidos",
                "ru": "США",
                "zh-CN": "美国",
            },
        },
        "subdivisions": [
            {
                "geoname_id": 5332921,
                "iso_code": "CA",
                "names": {
                    "de": "Kalifornien",
                    "en": "California",
                    "es": "California",
                    "fr": "Californie",
                    "ja": "カリフォルニア州",
                    "pt-BR": "Califórnia",
                    "ru": "Калифорния",
                    "zh-CN": "加利福尼亚州",
                },
            }
        ],
    }
    return result


def get_mock_whois_domain_response() -> Dict[str, Any]:
    """
    Get a mock WHOIS response for a domain

    Returns:
        A dictionary simulating a WHOIS response for a domain
    """
    result: Dict[str, Any] = {
        "domain_name": "EXAMPLE.COM",
        "registrar": "ICANN",
        "whois_server": "whois.example-registrar.com",
        "referral_url": "http://www.example-registrar.com",
        "updated_date": "2022-01-01T00:00:00",
        "creation_date": "1995-08-14T04:00:00",
        "expiration_date": "2023-08-13T04:00:00",
        "name_servers": ["NS1.EXAMPLE.COM", "NS2.EXAMPLE.COM"],
        "status": [
            "clientDeleteProhibited",
            "clientRenewProhibited",
            "clientTransferProhibited",
            "serverUpdateProhibited",
        ],
        "emails": "domain-admin@example.com",
        "dnssec": "unsigned",
    }
    return result


def get_mock_whois_ip_response() -> Dict[str, Any]:
    """
    Get a mock WHOIS response for an IP address

    Returns:
        A dictionary simulating a WHOIS response for an IP
    """
    result: Dict[str, Any] = {
        "asn": "15169",
        "asn_description": "GOOGLE - Google LLC",
        "network": {
            "cidr": "8.8.8.0/24",
            "name": "GOOGLE",
            "handle": "NET-8-8-8-0-1",
            "range": "8.8.8.0 - 8.8.8.255",
            "start_address": "8.8.8.0",
            "end_address": "8.8.8.255",
            "ip_version": "v4",
        },
        "objects": {
            "GOGL": {
                "handle": "GOGL",
                "name": "Google LLC",
                "roles": ["registrant"],
                "address": [
                    "1600 Amphitheatre Parkway",
                    "Mountain View",
                    "CA",
                    "94043",
                    "United States",
                ],
                "contact": {
                    "phone": "+1-650-253-0000",
                    "email": "dns-admin@google.com",
                },
            }
        },
    }
    return result
