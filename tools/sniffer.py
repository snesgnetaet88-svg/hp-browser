# HP Browser — by hypermarket
"""Сниффер запросов + блокировка трекеров в одном перехватчике.

QtWebEngine допускает только один QWebEngineUrlRequestInterceptor на профиль,
поэтому перехват и блокировка живут вместе.
"""

from PyQt6.QtWebEngineCore import QWebEngineUrlRequestInterceptor

from core.privacy import is_tracker

RESOURCE_TYPES = {
    1: "документ",
    2: "фрейм",
    3: "css",
    4: "скрипт",
    5: "картинка",
    6: "шрифт",
    7: "ресурс",
    9: "медиа",
    10: "worker",
    14: "xhr",
    15: "ping",
    16: "sw",
}


def _to_text(value) -> str:
    """QByteArray/str -> str."""
    try:
        return bytes(value).decode("utf-8", "replace")
    except TypeError:
        return str(value)


class RequestSniffer(QWebEngineUrlRequestInterceptor):
    """Собирает запросы страницы и блокирует трекеры (если включено)."""

    def __init__(self, parent=None, guard=None, sink=None, limit: int = 500):
        super().__init__(parent)
        self.enabled = False
        self.guard = guard
        self.sink = sink
        self.limit = limit
        self.records: list[dict] = []

    def interceptRequest(self, info) -> None:  # noqa: N802 — API Qt
        """Вызывается Chromium для каждого запроса."""
        host = info.requestUrl().host()

        # 1) блокировка трекеров
        if self.guard is not None and self.guard.enabled and is_tracker(host):
            info.block(True)
            self.guard.blocked_count += 1
            if host not in self.guard.last_blocked:
                self.guard.last_blocked.append(host)
                del self.guard.last_blocked[:-20]
            return

        # 2) сниффинг
        if not self.enabled:
            return
        try:
            rtype = int(info.resourceType())
        except (TypeError, ValueError):
            rtype = 0
        record = {
            "method": _to_text(info.requestMethod()),
            "url": info.requestUrl().toString(),
            "host": host,
            "type": RESOURCE_TYPES.get(rtype, f"#{rtype}"),
            "first_party": info.firstPartyUrl().toString(),
        }
        self.records.append(record)
        if len(self.records) > self.limit:
            del self.records[: len(self.records) - self.limit]
        if callable(self.sink):
            self.sink(record)

    def set_enabled(self, enabled: bool) -> None:
        self.enabled = bool(enabled)

    def clear(self) -> None:
        self.records.clear()

    def third_party_hosts(self) -> list[str]:
        """Уникальные сторонние хосты среди запросов."""
        hosts = set()
        for rec in self.records:
            if rec["host"] and rec["host"] not in rec.get("first_party", ""):
                hosts.add(rec["host"])
        return sorted(hosts)
