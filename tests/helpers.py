import ipaddress
from contextlib import contextmanager

import main


@contextmanager
def trust_testclient_proxy():
    """Allow TestClient requests to use X-Forwarded-For during tests."""

    original_checker = main._client_from_trusted_proxy
    original_networks = main.TRUSTED_PROXY_NETWORKS

    def _proxy(client_host: str | None) -> bool:
        if client_host == "testclient":
            return True
        return original_checker(client_host)

    if not original_networks:
        main.TRUSTED_PROXY_NETWORKS = (
            ipaddress.ip_network("0.0.0.0/0"),
            ipaddress.ip_network("::/0"),
        )
    try:
        main._client_from_trusted_proxy = _proxy
        yield
    finally:
        main._client_from_trusted_proxy = original_checker
        main.TRUSTED_PROXY_NETWORKS = original_networks
