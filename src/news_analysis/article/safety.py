from __future__ import annotations

import ipaddress
import socket
from urllib.parse import urlparse

from news_analysis.pipeline.errors import AnalysisError, AnalysisStatus

CLOUD_METADATA_IPS = {
    ipaddress.ip_address("169.254.169.254"),
}


def validate_http_url(url: str):
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise AnalysisError(
            AnalysisStatus.INVALID_URL,
            "URL must be an absolute HTTP or HTTPS URL.",
            retryable=False,
        )
    return parsed


def assert_url_is_safe(url: str, resolver=socket.getaddrinfo) -> None:
    parsed = validate_http_url(url)
    hostname = parsed.hostname
    if not hostname:
        raise AnalysisError(AnalysisStatus.INVALID_URL, "URL host is missing.", retryable=False)
    lowered = hostname.lower()
    if lowered in {"localhost", "localhost.localdomain"}:
        _blocked(hostname)

    addresses = _resolve_addresses(hostname, resolver)
    for address in addresses:
        if _is_blocked_address(address):
            _blocked(hostname, str(address))


def _resolve_addresses(hostname: str, resolver) -> list[ipaddress._BaseAddress]:
    try:
        literal = ipaddress.ip_address(hostname)
        return [literal]
    except ValueError:
        pass

    try:
        infos = resolver(hostname, None, proto=socket.IPPROTO_TCP)
    except socket.gaierror as exc:
        raise AnalysisError(
            AnalysisStatus.NEWS_FETCH_FAILED,
            f"Could not resolve URL host: {hostname}.",
            retryable=True,
            details={"host": hostname},
        ) from exc

    addresses = []
    for info in infos:
        sockaddr = info[4]
        try:
            addresses.append(ipaddress.ip_address(sockaddr[0]))
        except ValueError:
            continue
    return addresses


def _is_blocked_address(address: ipaddress._BaseAddress) -> bool:
    return (
        address.is_loopback
        or address.is_private
        or address.is_link_local
        or address.is_multicast
        or address.is_reserved
        or address in CLOUD_METADATA_IPS
    )


def _blocked(hostname: str, address: str | None = None) -> None:
    details = {"host": hostname}
    if address:
        details["address"] = address
    raise AnalysisError(
        AnalysisStatus.BLOCKED_INTERNAL_URL,
        "URL was blocked for security because it resolves to an internal or restricted network address.",
        retryable=False,
        details=details,
    )
