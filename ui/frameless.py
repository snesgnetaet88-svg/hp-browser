# HP Browser — by hypermarket
"""Безрамочное окно (CSD).

Убирает системный заголовок (KWin SSD), добавляет свои кнопки окна,
перетаскивание за пустую часть ленты вкладок и изменение размера за края
через compositor (Qt6 `startSystemResize` / `startSystemMove`).
"""

from PyQt6.QtCore import QEvent, Qt
from PyQt6.QtGui import QColor, QPainter
from PyQt6.QtWidgets import (
    QApplication,
    QHBoxLayout,
    QPushButton,
    QSizePolicy,
    QTabBar,
    QToolBar,
    QWidget,
)

RESIZE_MARGIN = 6


class PanelTabBar(QTabBar):
    """Лента вкладок, которая сама заливает фон панели (как тулбар панели).

    Общее правило темы `QWidget { background: ... }` перекрывает QSS-фон
    QTabBar, поэтому фон рисуем вручную.
    """

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._bg = QColor("#2b2b2b")

    def set_background(self, color) -> None:
        self._bg = QColor(color)
        self.update()

    def paintEvent(self, event) -> None:  # noqa: N802 — API Qt
        painter = QPainter(self)
        painter.fillRect(self.rect(), self._bg)
        painter.end()
        super().paintEvent(event)


class WindowButtons(QWidget):
    """Кнопки «свернуть / развернуть / закрыть» справа в ленте вкладок.

    Имеют жёсткий минимум: лента вкладок не может их сожать (иначе в
    безрамочном окне пропадает единственный способ свернуть/закрыть).
    """

    def __init__(self, window) -> None:
        super().__init__(window)
        self._win = window
        self.setObjectName("window_buttons")
        lay = QHBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(4)
        self._lay = lay
        self.min_btn = self._make("–", "Свернуть", window.showMinimized)
        self.max_btn = self._make("□", "Развернуть", self._toggle_max)
        self.close_btn = self._make("✕", "Закрыть", window.close)
        self.close_btn.setObjectName("win_close")
        # Резервируем место: без этого QToolBarLayout ужимает блок до нуля,
        # как только ленте вкладок не хватает ширины.
        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        self.setMinimumSize(self.sizeHint())

    def _make(self, text: str, tip: str, slot) -> QPushButton:
        btn = QPushButton(text)
        btn.setObjectName("win_btn")
        btn.setToolTip(tip)
        btn.setFixedSize(26, 26)
        btn.setFlat(True)
        btn.clicked.connect(slot)
        self._lay.addWidget(btn)  # иначе кнопки не управляются лейаутом и не видны
        return btn

    def _toggle_max(self) -> None:
        if self._win.isMaximized():
            self._win.showNormal()
        else:
            self._win.showMaximized()


class DragToolBar(QToolBar):
    """Тулбар, за пустую часть которого можно тащить всё окно."""

    def mousePressEvent(self, event) -> None:  # noqa: N802 — API Qt
        if event.button() == Qt.MouseButton.LeftButton:
            handle = self.window().windowHandle()
            if handle is not None:
                handle.startSystemMove()
                return
        super().mousePressEvent(event)

    def mouseDoubleClickEvent(self, event) -> None:  # noqa: N802 — API Qt
        win = self.window()
        if win.isMaximized():
            win.showNormal()
        else:
            win.showMaximized()


class FramelessMixin:
    """Подмешивается к QMainWindow: безрамочный режим + ресайз за края."""

    RESIZE_MARGIN = RESIZE_MARGIN

    def enable_frameless(self) -> None:
        self.setWindowFlag(Qt.WindowType.FramelessWindowHint, True)
        QApplication.instance().installEventFilter(self)

    def eventFilter(self, obj, event):  # noqa: N802 — API Qt
        try:
            if (
                event.type() == QEvent.Type.MouseButtonPress
                and event.button() == Qt.MouseButton.LeftButton
                and isinstance(obj, QWidget)
                and self.isAncestorOf(obj)
            ):
                edges = self._edges_at(event.globalPosition().toPoint())
                handle = self.windowHandle()
                if edges is not None and handle is not None:
                    handle.startSystemResize(edges)
                    return True
        except Exception:  # noqa: BLE001 — не мешаем работе окна
            pass
        return super().eventFilter(obj, event)

    def _edges_at(self, gp):
        r = self.frameGeometry()
        if not r.contains(gp):
            return None
        edges = None
        m = self.RESIZE_MARGIN
        if abs(gp.x() - r.left()) <= m:
            edges = Qt.Edge.LeftEdge
        if abs(gp.x() - r.right()) <= m:
            edges = Qt.Edge.RightEdge if edges is None else edges | Qt.Edge.RightEdge
        if abs(gp.y() - r.top()) <= m:
            edges = Qt.Edge.TopEdge if edges is None else edges | Qt.Edge.TopEdge
        if abs(gp.y() - r.bottom()) <= m:
            edges = Qt.Edge.BottomEdge if edges is None else edges | Qt.Edge.BottomEdge
        return edges
