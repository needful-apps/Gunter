"""API resource definitions for Flask-RESTX."""

import ipaddress
from typing import Any, Dict, cast

from flask import jsonify, request
from flask_restx import Namespace, Resource

from config import Config
from logging_config import log
from services.geo_db_manager import GeoDBManager
from services.whois_service import WhoisService
from utils import filter_names_by_lang


def register_resources(
    geo_ns: Namespace,
    whois_ns: Namespace,
    status_ns: Namespace | None,
    models: dict,
    db_manager: GeoDBManager,
    whois_service: WhoisService,
    config: Config,
) -> None:
    """
    Register all API resources with their namespaces.

    Args:
        geo_ns: Geolocation namespace.
        whois_ns: WHOIS namespace.
        status_ns: Status namespace (optional).
        models: Dictionary of API models.
        db_manager: GeoDBManager instance.
        whois_service: WhoisService instance.
        config: Application configuration.
    """

    @geo_ns.route("/<string:ip>")
    @geo_ns.doc(
        params={"ip": "IP address for geolocation"},
        responses={
            200: "Success",
            400: "Invalid IP address",
            404: "IP address not found",
            503: "GeoLite2 database not available",
        },
    )
    class GeoLookup(Resource):
        @geo_ns.doc(
            params={
                "lang": "Language code for the response (e.g., de, en, fr)",
                "exclude_whois": "If true, WHOIS data will be excluded from the response",
            }
        )
        @geo_ns.marshal_with(models["geo_lookup"], skip_none=True, code=200)
        def get(self, ip: str):
            if not db_manager.mmdb_reader:
                return geo_ns.abort(
                    503,
                    error="GeoLite2 database not available. Please try again later.",
                )

            try:
                ipaddress.ip_address(ip)
            except ValueError:
                return geo_ns.abort(400, error="Invalid IP address format.")

            record = db_manager.mmdb_reader.get(ip)
            if not record:
                log.info(f"IP address not found in database: {ip}")
                return geo_ns.abort(404, error="IP address not found in the database.")

            try:
                lang = request.args.get("lang", config.DEFAULT_LANG).lower()

                record_dict: Dict[str, Any] = {}
                if record and isinstance(record, dict):
                    for key, value in record.items():
                        record_dict[key] = value

                processed_record = filter_names_by_lang(record_dict, lang)
                processed_record = cast(Dict[str, Any], processed_record)

                location = processed_record.get("location", {})
                if isinstance(location, dict):
                    if "latitude" in location:
                        processed_record["latitude"] = location["latitude"]
                    if "longitude" in location:
                        processed_record["longitude"] = location["longitude"]

                processed_record["database_info"] = {
                    "last_updated_utc": (
                        db_manager.last_db_update_time.isoformat()
                        if db_manager.last_db_update_time
                        else "N/A"
                    ),
                    "version_tag": db_manager.current_db_version_tag,
                }

                if request.args.get("exclude_whois", "false").lower() != "true":
                    log.info(f"Including WHOIS data for IP: {ip}")
                    processed_record["whois_data"] = whois_service.get_whois_data(ip)

                log.info(f"Lookup for IP: {ip}, Lang: {lang} successful.")
                return processed_record
            except Exception as e:
                log.error(f"Error during IP lookup for {ip}: {e}")
                response = jsonify({"error": "An internal server error occurred."})
                response.status_code = 500
                return response

    @whois_ns.route("/<string:target>")
    @whois_ns.doc(
        params={"target": "IP address or domain name for the WHOIS query"},
        responses={200: "Success", 500: "Internal server error"},
    )
    class WhoisLookup(Resource):
        @whois_ns.marshal_with(models["whois_data"], skip_none=True)
        def get(self, target: str):
            try:
                whois_data = whois_service.get_whois_data(target)
                return whois_data
            except Exception as e:
                log.error(f"Error during WHOIS lookup for {target}: {e}")
                whois_ns.abort(500, error="An internal server error occurred.")

    if status_ns:

        @status_ns.route("")
        class Status(Resource):
            @status_ns.marshal_with(models["database_status"])
            def get(self):
                return db_manager.get_status()
