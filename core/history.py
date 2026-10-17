# HP Browser — by hypermarket
"""История посещений: хранение в JSON, поиск, очистка."""

import json
import os
from datetime import datetime

from core.settings import DATA_DIR

MAX_ITEMS = 2000


class History:
    """История браузера с ограничением размера."""

    def __init__(self, path: str | None = None, limit: int = MAX_ITEMS):
        self.path = path or os.path.join(DATA_DIR, "history.json")
        self.limit = limit
        self.items: list[dict] = []
        self.load()

    def load(self) -> None:
        try:
            with open(self.path, encoding="utf-8") as fh:
                data = json.load(fh)
            if isinstance(data, list):
                self.items = data
        except (OSError, ValueError):
            self.items = []

    def save(self) -> bool:
        try:
            os.makedirs(os.path.dirname(self.path), exist_ok=True)
            with open(self.path, "w", encoding="utf-8") as fh:
                # Компактная запись: файл меньше, сохранение быстрее.
                json.dump(self.items[: self.limit], fh, ensure_ascii=False,
                          separators=(",", ":"))
            return True
        except OSError:
            return False

    def add(self, url: str, title: str = "", save: bool = True) -> None:
        """Добавляет запись (пропускает служебные about: и дубли подряд).

        save=False — только меняет список; запись на диск делает вызывающий
        (окно сохраняет историю отложенно, чтобы не тормозить навигацию).
        """
        if not url or url.startswith("about:"):
            return
        if self.items and self.items[0].get("url") == url:
            return
        self.items.insert(
            0,
            {"url": url, "title": title or url, "ts": datetime.now().isoformat(timespec="seconds")},
        )
        del self.items[self.limit :]
        if save:
            self.save()

    def search(self, query: str) -> list[dict]:
        """Фильтрует историю по подстроке в URL или заголовке."""
        query = (query or "").lower().strip()
        if not query:
            return list(self.items)
        return [
            item
            for item in self.items
            if query in item.get("url", "").lower() or query in item.get("title", "").lower()
        ]

    def remove(self, url: str) -> bool:
        """Удаляет из истории все записи с этим URL."""
        before = len(self.items)
        self.items = [item for item in self.items if item.get("url") != url]
        if len(self.items) != before:
            self.save()
            return True
        return False

    def clear(self) -> None:
        self.items = []
        self.save()
