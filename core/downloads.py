# HP Browser — by hypermarket
"""Менеджер загрузок: перехватывает скачивания QWebEngine и ведёт список."""

import json
import os

from PyQt6.QtCore import QObject, QStandardPaths, pyqtSignal
from PyQt6.QtWebEngineCore import QWebEngineDownloadRequest as Download

from core.settings import DATA_DIR

COMPLETED = Download.DownloadState.DownloadCompleted
CANCELLED = Download.DownloadState.DownloadCancelled
INTERRUPTED = Download.DownloadState.DownloadInterrupted


def human(size: float) -> str:
    """Человекочитаемый размер файла."""
    for unit in ("Б", "КБ", "МБ", "ГБ"):
        if size < 1024:
            return f"{size:.0f} {unit}"
        size /= 1024
    return f"{size:.1f} ТБ"


class DownloadManager(QObject):
    """Хранит список загрузок и следит за их прогрессом."""

    changed = pyqtSignal()

    def __init__(self, profile, parent=None):
        super().__init__(parent)
        self.path = os.path.join(DATA_DIR, "downloads.json")
        self.items: list[dict] = []
        self.dir = self._default_dir()
        self._load()
        profile.downloadRequested.connect(self._on_requested)

    def _load(self) -> None:
        """Читает историю загрузок с диска (без живых объектов Qt)."""
        try:
            with open(self.path, encoding="utf-8") as fh:
                data = json.load(fh)
            if isinstance(data, list):
                self.items = [
                    {
                        "item": None,
                        "name": e.get("name", ""),
                        "path": e.get("path", ""),
                        "received": e.get("received", 0),
                        "total": e.get("total", 0),
                        "state": e.get("state", "готово"),
                    }
                    for e in data
                ]
        except (OSError, ValueError):
            self.items = []

    def _save(self) -> None:
        """Пишет историю загрузок на диск (без QWebEngineDownloadRequest)."""
        try:
            os.makedirs(os.path.dirname(self.path), exist_ok=True)
            serializable = [{k: v for k, v in e.items() if k != "item"} for e in self.items]
            with open(self.path, "w", encoding="utf-8") as fh:
                json.dump(serializable, fh, ensure_ascii=False, indent=2)
        except OSError:
            pass

    @staticmethod
    def _default_dir() -> str:
        path = QStandardPaths.writableLocation(
            QStandardPaths.StandardLocation.DownloadLocation
        )
        return path or os.path.expanduser("~/Downloads")

    def _unique_name(self, name: str) -> str:
        """Не даёт новой загрузке затереть уже существующий файл."""
        base, ext = os.path.splitext(name)
        candidate, n = name, 1
        while os.path.exists(os.path.join(self.dir, candidate)):
            n += 1
            candidate = f"{base} ({n}){ext}"
        return candidate

    def _on_requested(self, item) -> None:
        os.makedirs(self.dir, exist_ok=True)
        name = item.downloadFileName() or item.suggestedFileName() or "download"
        item.setDownloadDirectory(self.dir)
        item.setDownloadFileName(self._unique_name(name))
        entry = {
            "item": item,
            "name": item.downloadFileName(),
            "path": os.path.join(self.dir, item.downloadFileName()),
            "received": 0,
            "total": 0,
            "state": "загружается",
        }
        item.receivedBytesChanged.connect(lambda e=entry, i=item: self._on_progress(e, i))
        item.stateChanged.connect(lambda _s, e=entry, i=item: self._on_state(e, i))
        item.accept()
        self.items.insert(0, entry)
        self._save()
        self.changed.emit()

    def _on_progress(self, entry, item) -> None:
        entry["received"] = item.receivedBytes()
        entry["total"] = item.totalBytes()
        self.changed.emit()

    def _on_state(self, entry, item) -> None:
        state = item.state()
        entry["state"] = {
            COMPLETED: "готово",
            CANCELLED: "отменено",
            INTERRUPTED: "ошибка",
        }.get(state, "загружается")
        self._save()
        self.changed.emit()

    def cancel(self, entry: dict) -> None:
        """Отменяет загрузку."""
        item = entry.get("item")
        if item is not None:
            item.cancel()

    def clear_finished(self) -> None:
        """Убирает из списка всё, кроме активных загрузок."""
        self.items = [e for e in self.items if e.get("state") == "загружается"]
        self._save()
        self.changed.emit()
