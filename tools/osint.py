# HP Browser — by hypermarket
"""Встроенный OSINT: WHOIS, DNS, SSL и поддомены (crt.sh) для текущего сайта."""

import socket
import ssl
from urllib.parse import urlparse

import dns.exception
import dns.resolver
import requests
import whois as whois_lib
from PyQt6.QtCore import QThread, pyqtSignal

TIMEOUT = 10
DNS_TYPES = ("A", "AAAA", "MX", "NS", "TXT")
SILENT = (dns.resolver.NoAnswer, dns.resolver.NXDOMAIN, dns.resolver.NoNameservers, dns.exception.Timeout)


def host_of(url: str) -> str:
    """Извлекает хост из URL или ввода."""
    raw = (url or "").strip()
    if not raw:
        return ""
    if "://" not in raw:
        raw = "http://" + raw
    return (urlparse(raw).hostname or "").lower()


def _whois(host: str) -> dict:
    try:
        w = whois_lib.whois(host)
    except Exception as exc:  # noqa: BLE001
        return {"error": f"WHOIS недоступен: {exc}"}
    if not w:
        return {"error": "WHOIS: нет данных"}
    def first(v):
        if isinstance(v, (list, tuple)):
            return v[0] if v else None
        return v
    return {
        "registrar": first(w.get("registrar")),
        "created": str(first(w.get("creation_date")) or "?"),
        "expires": str(first(w.get("expiration_date")) or "?"),
    }


def _dns(host: str) -> dict:
    data: dict = {}
    resolver = dns.resolver.Resolver()
    resolver.timeout = resolver.lifetime = TIMEOUT
    for rtype in DNS_TYPES:
        try:
            data[rtype] = [str(r).strip('"') for r in resolver.resolve(host, rtype)][:5]
        except SILENT:
            continue
        except Exception:  # noqa: BLE001
            continue
    return data


def _ssl(host: str) -> dict:
    ctx = ssl.create_default_context()
    try:
        with socket.create_connection((host, 443), timeout=TIMEOUT) as sock:
            with ctx.wrap_socket(sock, server_hostname=host) as tls:
                cert = tls.getpeercert()
    except (OSError, ssl.SSLError) as exc:
        return {"error": f"SSL недоступен: {exc}"}
    issuer = dict(x[0] for x in cert.get("issuer", []))
    return {
        "issuer": issuer.get("organizationName", issuer.get("commonName", "?")),
        "not_after": cert.get("notAfter", "?"),
        "san": [v for _, v in cert.get("subjectAltName", [])][:10],
    }


def _subdomains(host: str) -> list[str]:
    try:
        resp = requests.get(f"https://crt.sh/?q=%25.{host}&output=json", timeout=TIMEOUT)
        if resp.status_code != 200:
            return []
        names = set()
        for row in resp.json():
            for name in str(row.get("name_value", "")).splitlines():
                name = name.strip().lstrip("*.").lower()
                if name.endswith(host):
                    names.add(name)
        return sorted(names)[:30]
    except Exception:  # noqa: BLE001
        return []


def check_site(url: str) -> dict:
    """Собирает WHOIS, DNS, SSL и поддомены. Возвращает dict(host, whois, dns, ssl, subdomains, error)."""
    host = host_of(url)
    if not host or "." not in host:
        return {"host": host, "error": "Не удалось определить домен из адреса."}
    return {
        "host": host,
        "whois": _whois(host),
        "dns": _dns(host),
        "ssl": _ssl(host),
        "subdomains": _subdomains(host),
    }


class OsintWorker(QThread):
    """Выполняет check_site в фоне, чтобы не морозить интерфейс."""

    done = pyqtSignal(dict)
    failed = pyqtSignal(str)

    def __init__(self, url: str, parent=None):
        super().__init__(parent)
        self.url = url

    def run(self) -> None:  # noqa: D401
        try:
            self.done.emit(check_site(self.url))
        except Exception as exc:  # noqa: BLE001
            self.failed.emit(str(exc))
