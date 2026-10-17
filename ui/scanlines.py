# HP Browser — by hypermarket
"""CRT-сканлайны: лёгкий полупрозрачный оверлей поверх окна.

Оверлей не перехватывает мышь, поэтому не мешает работе с сайтом.

Производительность: рисунок линий рисуется один раз в кэш-картинку, а при
включённой анимации обновляется только узкая полоса свечения (частичная
перерисовка). По умолчанию анимация выключена — тогда окно вообще не
перерисовывается повторно.
"""

from PyQt6.QtCore import QRect, Qt, QTimer
from PyQt6.QtGui import QColor, QPainter, QPixmap
from PyQt6.QtWidgets import QWidget

BAND_HEIGHT = 3
BAND_STEP = 8
ANIM_MS = 90


class ScanlinesOverlay(QWidget):
    """Горизонтальные сканлайны поверх содержимого окна."""

    def __init__(self, parent=None, line_gap: int = 3, color: str = "#00ff66",
                 animate: bool = False):
        super().__init__(parent)
        self.line_gap = line_gap
        self.color = QColor(color)
        self.band_y = 0
        self._cache = QPixmap()
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        self.setAttribute(Qt.WidgetAttribute.WA_NoSystemBackground, True)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)

        self.timer = QTimer(self)
        self.timer.setInterval(ANIM_MS)
        self.timer.timeout.connect(self._tick)
        self.animate = bool(animate)

    # --- отрисовка --------------------------------------------------------
    def _rebuild_cache(self) -> None:
        """Один раз рисует линии в картинку — дальше только копирует её."""
        if self.width() <= 0 or self.height() <= 0:
            return
        pixmap = QPixmap(self.size())
        pixmap.fill(Qt.GlobalColor.transparent)
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, False)
        line = QColor(self.color)
        line.setAlpha(34)
        painter.setPen(line)
        for y in range(0, self.height(), self.line_gap):
            painter.drawLine(0, y, self.width(), y)
        painter.end()
        self._cache = pixmap

    def resizeEvent(self, event) -> None:  # noqa: N802 — API Qt
        super().resizeEvent(event)
        self._rebuild_cache()

    def _tick(self) -> None:
        """Двигает полосу свечения, обновляя только две узкие области."""
        previous = self.band_y
        self.band_y = (self.band_y + BAND_STEP) % max(self.height(), 1)
        self.update(QRect(0, previous, self.width(), BAND_HEIGHT + 2))
        self.update(QRect(0, self.band_y, self.width(), BAND_HEIGHT + 2))

    def paintEvent(self, _event) -> None:  # noqa: N802 — API Qt
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, False)
        if not self._cache.isNull():
            painter.drawPixmap(0, 0, self._cache)
        if self.animate:
            band = QColor(self.color)
            band.setAlpha(26)
            painter.fillRect(0, self.band_y, self.width(), BAND_HEIGHT, band)
        painter.end()

    # --- управление -------------------------------------------------------
    def set_active(self, active: bool) -> None:
        """Включает/выключает оверлей."""
        if active:
            self._rebuild_cache()
            self.show()
            self.raise_()
            if self.animate:
                self.timer.start()
        else:
            self.timer.stop()
            self.hide()

    def set_animated(self, animated: bool) -> None:
        """Включает/выключает бегущую полосу свечения."""
        self.animate = bool(animated)
        if self.animate and self.isVisible():
            self.timer.start()
        else:
            self.timer.stop()
        self.update()
