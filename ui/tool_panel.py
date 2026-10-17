# HP Browser — by hypermarket
"""Универсальная панель инструментов (OSINT / Leaks / Security / Sniffer / Оценка)."""

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QDockWidget, QPlainTextEdit


class ToolPanel(QDockWidget):
    """Док-панель с заголовком и текстовым выводом результатов."""

    def __init__(self, parent=None):
        super().__init__("Инструменты", parent)
        self.setObjectName("tool_panel")
        self.output = QPlainTextEdit()
        self.output.setReadOnly(True)
        self.output.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap)
        self.setWidget(self.output)
        self.setMinimumWidth(360)

    def show_panel(self, title: str) -> None:
        """Показывает панель с новым заголовком."""
        self.setWindowTitle(title)
        self.show()
        self.raise_()

    def clear(self) -> None:
        self.output.clear()

    def set_text(self, text: str) -> None:
        self.output.setPlainText(text)

    def append(self, line: str) -> None:
        self.output.appendPlainText(line)

    def start(self, title: str, message: str = "выполняется…") -> None:
        """Заголовок + сообщение о начале работы."""
        self.show_panel(title)
        self.set_text(message)
