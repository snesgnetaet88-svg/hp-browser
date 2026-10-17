# HP Browser — by hypermarket
"""Панель поиска по странице (Ctrl+F)."""

from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import QLabel, QLineEdit, QPushButton, QToolBar


class FindBar(QToolBar):
    """Панель поиска: поле, счётчик совпадений и кнопки перехода."""

    next_requested = pyqtSignal(str)
    prev_requested = pyqtSignal(str)
    closed = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__("Поиск", parent)
        self.setObjectName("find_bar")
        self.setMovable(False)

        self.edit = QLineEdit()
        self.edit.setPlaceholderText("Найти на странице…")
        self.edit.setMinimumWidth(280)
        self.edit.setClearButtonEnabled(True)

        self.status = QLabel("")
        self.status.setMinimumWidth(130)
        self.prev_btn = QPushButton("Назад")
        self.next_btn = QPushButton("Далее")
        self.close_btn = QPushButton("Закрыть")
        for btn in (self.prev_btn, self.next_btn, self.close_btn):
            btn.setFixedWidth(80)

        for widget in (self.edit, self.status, self.prev_btn, self.next_btn, self.close_btn):
            self.addWidget(widget)

        self.next_btn.clicked.connect(lambda: self.next_requested.emit(self.edit.text()))
        self.prev_btn.clicked.connect(lambda: self.prev_requested.emit(self.edit.text()))
        self.close_btn.clicked.connect(self.closed)
        self.edit.textChanged.connect(lambda text: self.next_requested.emit(text))
        self.edit.returnPressed.connect(lambda: self.next_requested.emit(self.edit.text()))

    def activate(self) -> None:
        """Показывает панель и ставит курсор в поле."""
        self.show()
        self.edit.setFocus()
        self.edit.selectAll()

    def set_status(self, text: str) -> None:
        """Текст счётчика совпадений."""
        self.status.setText(text)
