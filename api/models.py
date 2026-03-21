"""API model definitions for Flask-RESTX."""

from flask_restx import Api, fields


def create_api_models(api: Api) -> dict:
    """
    Create and return all API models for documentation.

    Args:
        api: The Flask-RESTX Api instance.

    Returns:
        Dictionary containing all model definitions.
    """
    database_status_model = api.model(
        "DatabaseStatus",
        {
            "database_loaded": fields.Boolean(
                description="Indicates if the database is loaded"
            ),
            "last_database_update_check_utc": fields.String(
                description="Timestamp of the last database update check"
            ),
            "current_database_version_tag": fields.String(
                description="Current database version"
            ),
            "current_database_file": fields.String(
                description="Currently used database file"
            ),
        },
    )

    whois_data_model = api.model(
        "WhoisData",
        {
            "target": fields.String(
                description="Target of the WHOIS query (IP or domain)"
            ),
            "lookup_timestamp": fields.String(description="Query timestamp"),
            "ip_whois": fields.Raw(description="WHOIS data for IP addresses"),
            "domain_whois": fields.Raw(description="WHOIS data for domains"),
            "reverse_dns": fields.String(
                description="Reverse DNS result (if available)"
            ),
        },
    )

    geo_lookup_model = api.model(
        "GeoLookup",
        {
            "city": fields.Raw(description="City information"),
            "country": fields.Raw(description="Country information"),
            "continent": fields.Raw(description="Continent information"),
            "location": fields.Raw(description="Location information (coordinates)"),
            "latitude": fields.Float(
                description="GPS latitude (WGS84)", example=48.1374
            ),
            "longitude": fields.Float(
                description="GPS longitude (WGS84)", example=11.5755
            ),
            "postal": fields.Raw(description="Postal code information"),
            "subdivisions": fields.Raw(
                description="Subdivisions information (states, provinces)"
            ),
            "registered_country": fields.Raw(
                description="Registered country information"
            ),
            "database_info": fields.Raw(description="Database status information"),
            "whois_data": fields.Nested(
                whois_data_model, description="WHOIS data (optional)"
            ),
        },
    )

    return {
        "database_status": database_status_model,
        "whois_data": whois_data_model,
        "geo_lookup": geo_lookup_model,
    }
