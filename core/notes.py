# HP Browser — by hypermarket
"""Заметки пользователя: хранение в JSON."""

import json
import os
from datetime import datetime

from core.settings import DATA_DIR


class Notes:
    """Список заметок с сохранением на диск."""

    def __init__(self, path: str | None = None):
        self.path = path or os.path.join(DATA_DIR, "notes.json")
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

    def add(self, text: str, url: str = "") -> bool:
        """Добавляет заметку. Пустой текст игнорируется."""
        text = (text or "").strip()
        if not text:
            return False
        self.items.insert(
            0,
            {
                "text": text,
                "url": url,
                "ts": datetime.now().isoformat(timespec="seconds"),
            },
        )
        self.save()
        return True

    def remove(self, index: int) -> bool:
        if 0 <= index < len(self.items):
            del self.items[index]
            self.save()
            return True
        return False
