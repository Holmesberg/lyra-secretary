import socket

import httpx
import pytest

from app.utils.provider_url_safety import (
    ProviderUrlSafetyError,
    safe_provider_get,
    validate_provider_url,
)


@pytest.mark.parametrize(
    "url",
    [
        "http://127.0.0.1/calendar/export_execute.php?authtoken=x",
        "http://localhost/calendar/export_execute.php?authtoken=x",
        "http://10.0.0.5/calendar/export_execute.php?authtoken=x",
        "http://192.168.1.10/calendar/export_execute.php?authtoken=x",
        "http://172.16.0.2/calendar/export_execute.php?authtoken=x",
        "http://169.254.169.254/latest/meta-data",
        "http://[::1]/calendar/export_execute.php?authtoken=x",
    ],
)
def test_validate_provider_url_rejects_private_literal_targets(url):
    with pytest.raises(ProviderUrlSafetyError) as exc:
        validate_provider_url(url)
    assert exc.value.code == "url_private_network"


def test_validate_provider_url_rejects_dns_to_private(monkeypatch):
    def _fake_getaddrinfo(host, port, *args, **kwargs):
        return [
            (
                socket.AF_INET,
                socket.SOCK_STREAM,
                6,
                "",
                ("10.1.2.3", port),
            )
        ]

    monkeypatch.setattr(socket, "getaddrinfo", _fake_getaddrinfo)

    with pytest.raises(ProviderUrlSafetyError) as exc:
        validate_provider_url("https://lms.example.edu/calendar/export_execute.php")
    assert exc.value.code == "url_private_network"


def test_safe_provider_get_rejects_redirect_to_private(monkeypatch):
    def _fake_getaddrinfo(host, port, *args, **kwargs):
        ip = "93.184.216.34" if host == "public.example.edu" else "127.0.0.1"
        return [
            (
                socket.AF_INET,
                socket.SOCK_STREAM,
                6,
                "",
                (ip, port),
            )
        ]

    class FakeClient:
        def __init__(self, *args, **kwargs):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def get(self, url, params=None):
            return httpx.Response(
                302,
                headers={"location": "http://127.0.0.1/admin"},
                request=httpx.Request("GET", url, params=params),
            )

    monkeypatch.setattr(socket, "getaddrinfo", _fake_getaddrinfo)
    monkeypatch.setattr("app.utils.provider_url_safety.httpx.Client", FakeClient)

    with pytest.raises(ProviderUrlSafetyError) as exc:
        safe_provider_get("https://public.example.edu/feed", timeout=1)
    assert exc.value.code == "url_private_network"
