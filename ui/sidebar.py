# HP Browser — by hypermarket
"""Боковая панель: закладки и история с живым фильтром."""

from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import (
    QDockWidget,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)


class Sidebar(QDockWidget):
    """Док-панель с вкладками «Закладки» и «История» и поиском по ним."""

    open_url = pyqtSignal(str)
    delete_requested = pyqtSignal(str)
    history_delete_requested = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__("Панель", parent)

        self._bookmarks_items: list[dict] = []
        self._history_items: list[dict] = []

        self.filter_edit = QLineEdit()
        self.filter_edit.setPlaceholderText("Поиск по закладкам и истории…")
        self.filter_edit.setClearButtonEnabled(True)

        self.bookmarks_list = QListWidget()
        self.history_list = QListWidget()

        self.tabs = QTabWidget()
        self.tabs.addTab(self.bookmarks_list, "Закладки")
        self.tabs.addTab(self.history_list, "История")

        self.delete_btn = QPushButton("Удалить выбранное")
        box = QWidget()
        layout = QVBoxLayout(box)
        layout.setContentsMargins(6, 6, 6, 6)
        layout.addWidget(self.filter_edit)
        layout.addWidget(self.tabs)
        layout.addWidget(self.delete_btn)
        self.setWidget(box)

        self.filter_edit.textChanged.connect(self._refresh_lists)
        self.bookmarks_list.itemDoubleClicked.connect(self._open_item)
        self.history_list.itemDoubleClicked.connect(self._open_item)
        self.delete_btn.clicked.connect(self._delete_selected)

    # --- наполнение ------------------------------------------------------
    def set_bookmarks(self, items: list[dict]) -> None:
        self._bookmarks_items = list(items)
        self._refresh_lists()

    def set_history(self, items: list[dict]) -> None:
        self._history_items = list(items)
        self._refresh_lists()

    def _refresh_lists(self) -> None:
        text = self.filter_edit.text().strip().lower()
        self._fill(self.bookmarks_list, self._match(self._bookmarks_items, text))
        self._fill(self.history_list, self._match(self._history_items, text))

    @staticmethod
    def _match(items: list[dict], text: str) -> list[dict]:
        if not text:
            return items
        return [
            item for item in items
            if text in f"{item.get('title', '')} {item.get('url', '')}".lower()
        ]

    def _fill(self, widget: QListWidget, items: list[dict]) -> None:
        widget.clear()
        for item in items:
            entry = QListWidgetItem(item.get("title") or item.get("url", ""))
            entry.setToolTip(item.get("url", ""))
            entry.setData(256, item.get("url", ""))
            widget.addItem(entry)

    def set_bookmarks_items(self, items: list[dict]) -> None:
        """Совместимость: то же, что set_bookmarks."""
        self.set_bookmarks(items)

    def set_history_items(self, items: list[dict]) -> None:
        """Совместимость: то же, что set_history."""
        self.set_history(items)

    # --- действия --------------------------------------------------------
    def _open_item(self, item: QListWidgetItem) -> None:
        url = item.data(256)
        if url:
            self.open_url.emit(url)

    def _delete_selected(self) -> None:
        if self.tabs.currentWidget() is self.bookmarks_list:
            item = self.bookmarks_list.currentItem()
            if item is not None:
                self.delete_requested.emit(item.data(256) or "")
                self.bookmarks_list.takeItem(self.bookmarks_list.row(item))
            return
        item = self.history_list.currentItem()
        if item is not None:
            self.history_delete_requested.emit(item.data(256) or "")
            self.history_list.takeItem(self.history_list.row(item))
