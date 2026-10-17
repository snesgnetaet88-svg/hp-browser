# HP Browser — by hypermarket
"""Закладки: хранение в JSON и доступ."""

import json
import os
from datetime import datetime

from core.settings import DATA_DIR


class Bookmarks:
    """Список закладок с сохранением в JSON."""

    def __init__(self, path: str | None = None):
        self.path = path or os.path.join(DATA_DIR, "bookmarks.json")
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
                json.dump(self.items, fh, ensure_ascii=False, indent=2)
            return True
        except OSError:
            return False

    def contains(self, url: str) -> bool:
        return any(item.get("url") == url for item in self.items)

    def add(self, title: str, url: str) -> bool:
        """Добавляет закладку (без дублей). Возвращает True, если добавлена."""
        if not url or self.contains(url):
            return False
        self.items.insert(
            0,
            {"title": title or url, "url": url, "added": datetime.now().isoformat(timespec="seconds")},
        )
        self.save()
        return True

    def remove(self, url: str) -> bool:
        before = len(self.items)
        self.items = [item for item in self.items if item.get("url") != url]
        if len(self.items) != before:
            self.save()
            return True
        return False

    def clear(self) -> None:
        """Удаляет все закладки."""
        self.items = []
        self.save()
