"""WHOIS lookup service."""

import ipaddress
import socket
from datetime import datetime
from typing import Any, Dict, List, Optional, Union

import whois
from ipwhois import IPWhois

from logging_config import log


class WhoisService:
    """Provides WHOIS lookups for IPs and domains."""

    @staticmethod
    def _is_ip(target: str) -> bool:
        """Check if the target is a valid IP address."""
        try:
            ipaddress.ip_address(target)
            return True
        except ValueError:
            return False

    @staticmethod
    def _get_ip_whois(ip: str) -> Dict[str, Any]:
        """Perform WHOIS lookup for an IP address."""
        try:
            ip_whois = IPWhois(ip)
            result = ip_whois.lookup_rdap(depth=1)
            log.info(f"IP WHOIS lookup for {ip} successful.")
            return {
                "asn": result.get("asn"),
                "asn_description": result.get("asn_description"),
                "network": result.get("network", {}),
                "objects": result.get("objects", {}),
            }
        except Exception as e:
            log.error(f"IP WHOIS lookup for {ip} failed: {e}")
            return {"error": f"IP WHOIS lookup failed: {str(e)}"}

    @staticmethod
    def _get_domain_whois(domain: str) -> Dict[str, Any]:
        """Perform WHOIS lookup for a domain."""
        try:
            domain_info = whois.whois(domain)
            log.info(f"Domain WHOIS lookup for {domain} successful.")

            if not domain_info:
                return {"error": "No WHOIS data found"}

            info_dict: Dict[str, Union[str, List[str], Dict[str, Any], None]] = {}
            for k, v in domain_info.items():
                if isinstance(v, datetime):
                    info_dict[k] = v.isoformat()
                elif isinstance(v, list) and v and isinstance(v[0], datetime):
                    info_dict[k] = [item.isoformat() for item in v]
                elif v is not None:
                    info_dict[k] = v

            return info_dict
        except Exception as e:
            log.error(f"Domain WHOIS lookup for {domain} failed: {e}")
            return {"error": f"Domain WHOIS lookup failed: {str(e)}"}

    @staticmethod
    def resolve_ip_to_domain(ip: str) -> Optional[str]:
        """Attempts to resolve an IP address to a domain name via reverse DNS."""
        try:
            domain_name, _, _ = socket.gethostbyaddr(ip)
            log.info(f"Reverse DNS for {ip} successful: {domain_name}")
            return domain_name
        except (socket.herror, socket.gaierror):
            return None

    def get_whois_data(self, target: str) -> Dict[str, Any]:
        """Performs a WHOIS lookup for an IP address or domain."""
        data: Dict[str, Any] = {
            "target": target,
            "lookup_timestamp": datetime.now().isoformat(),
        }

        if self._is_ip(target):
            data["ip_whois"] = self._get_ip_whois(target)
            data["reverse_dns"] = self.resolve_ip_to_domain(target)
        else:
            data["domain_whois"] = self._get_domain_whois(target)

        return data
