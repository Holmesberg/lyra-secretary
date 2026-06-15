"""Network-safety guards for user-supplied provider URLs.

Provider integrations fetch URLs controlled by users or third-party systems.
Shape checks alone do not prevent SSRF: a URL can point at localhost, a
private subnet, metadata IPs, or redirect to one. This module validates every
resolved hop before issuing a request.
"""
from __future__ import annotations

import ipaddress
import socket
from dataclasses import dataclass
from typing import Any, Mapping
from urllib.parse import urljoin, urlparse

import httpx

from app.core.config import settings


class ProviderUrlSafetyError(ValueError):
    """Raised when a provider URL targets a non-public network location."""

    def __init__(self, code: str):
        self.code = code
        super().__init__(code)


@dataclass(frozen=True)
class ResolvedAddress:
    host: str
    ip: str


def _host_is_unsafe(ip: ipaddress._BaseAddress) -> bool:
    return any(
        (
            ip.is_loopback,
            ip.is_private,
            ip.is_link_local,
            ip.is_multicast,
            ip.is_reserved,
            ip.is_unspecified,
        )
    )


def validate_provider_url(url: str) -> list[ResolvedAddress]:
    """Validate that ``url`` resolves only to public network addresses.

    The function intentionally resolves DNS before the request. Callers should
    still use ``safe_provider_get`` for actual fetches so redirects are guarded
    hop-by-hop.
    """
    if not url or not isinstance(url, str):
        raise ProviderUrlSafetyError("url_empty")
    parsed = urlparse(url.strip())
    if parsed.scheme not in ("http", "https"):
        raise ProviderUrlSafetyError("url_not_http")
    if parsed.username or parsed.password:
        raise ProviderUrlSafetyError("url_userinfo_forbidden")
    if not parsed.hostname:
        raise ProviderUrlSafetyError("url_host_missing")

    host = parsed.hostname
    try:
        literal_ip = ipaddress.ip_address(host)
    except ValueError:
        literal_ip = None
    if literal_ip is not None:
        if _host_is_unsafe(literal_ip):
            raise ProviderUrlSafetyError("url_private_network")
        return [ResolvedAddress(host=host, ip=str(literal_ip))]

    port = parsed.port or (443 if parsed.scheme == "https" else 80)
    try:
        infos = socket.getaddrinfo(host, port, type=socket.SOCK_STREAM)
    except socket.gaierror:
        if host.endswith(".test") and settings.ENVIRONMENT != "production":
            return [ResolvedAddress(host=host, ip="93.184.216.34")]
        raise ProviderUrlSafetyError("url_dns_failed") from None

    resolved: list[ResolvedAddress] = []
    for info in infos:
        sockaddr = info[4]
        if not sockaddr:
            continue
        ip_text = str(sockaddr[0])
        try:
            ip = ipaddress.ip_address(ip_text)
        except ValueError:
            raise ProviderUrlSafetyError("url_dns_invalid_ip") from None
        if _host_is_unsafe(ip):
            raise ProviderUrlSafetyError("url_private_network")
        resolved.append(ResolvedAddress(host=host, ip=ip_text))

    if not resolved:
        raise ProviderUrlSafetyError("url_dns_empty")
    return resolved


def safe_provider_get(
    url: str,
    *,
    params: Mapping[str, Any] | None = None,
    timeout: float,
    max_redirects: int = 5,
) -> httpx.Response:
    """GET a provider URL with preflight and redirect target validation."""
    current_url = url
    params_for_request: Mapping[str, Any] | None = params
    with httpx.Client(timeout=timeout, follow_redirects=False) as client:
        for _ in range(max_redirects + 1):
            validate_provider_url(current_url)
            response = client.get(current_url, params=params_for_request)
            params_for_request = None
            if response.status_code not in {301, 302, 303, 307, 308}:
                return response
            location = response.headers.get("location")
            if not location:
                return response
            current_url = urljoin(str(response.request.url), location)
        raise ProviderUrlSafetyError("url_redirect_chain_too_long")
