# HP Browser — by hypermarket
"""Вкладки браузера.

Каждая вкладка — свой QWebEngineView в QStackedWidget, а сама лента вкладок
(QTabBar) живёт отдельно: окно кладёт её в верхнюю панель.
"""

from PyQt6.QtCore import QUrl, pyqtSignal
from PyQt6.QtWebEngineCore import (
    QWebEngineContextMenuRequest,
    QWebEnginePage,
    QWebEngineProfile,
)
from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.QtWidgets import (
    QApplication,
    QMenu,
    QStackedWidget,
    QTabBar,
    QVBoxLayout,
    QWidget,
)


class BrowserView(QWebEngineView):
    """Веб-вид с локализованным контекстным меню."""

    def contextMenuEvent(self, event) -> None:  # noqa: N802 — API Qt
        req = self.lastContextMenuRequest()
        menu = QMenu(self)
        link = req.linkUrl() if req is not None else QUrl()
        media = req.mediaUrl() if req is not None else QUrl()
        is_image = (
            req is not None
            and req.mediaType() == QWebEngineContextMenuRequest.MediaType.MediaImage
            and media.isValid()
            and not media.isEmpty()
        )
        if is_image:
            menu.addAction("Открыть изображение в новой вкладке", lambda: self._open_new(media))
            menu.addAction("Сохранить изображение в «Загрузки»", lambda: self._download(media))
            menu.addAction(
                "Копировать изображение",
                lambda: self.page().triggerAction(QWebEnginePage.WebAction.CopyImageToClipboard),
            )
            menu.addAction(
                "Копировать адрес изображения",
                lambda: QApplication.clipboard().setText(media.toString()),
            )
            menu.addSeparator()
        if req is not None and link.isValid() and not link.isEmpty():
            menu.addAction("Открыть ссылку в новой вкладке", lambda: self._open_new(link))
            menu.addAction(
                "Копировать адрес ссылки",
                lambda: QApplication.clipboard().setText(link.toString()),
            )
            menu.addSeparator()
        if req is not None and req.selectedText():
            menu.addAction(
                "Копировать", lambda: self.page().triggerAction(QWebEnginePage.WebAction.Copy)
            )
            menu.addSeparator()
        history = self.history()
        back = menu.addAction("Назад", self.back)
        back.setEnabled(history.canGoBack())
        forward = menu.addAction("Вперёд", self.forward)
        forward.setEnabled(history.canGoForward())
        menu.addAction("Обновить", self.reload)
        url = self.url()
        if url.isValid() and not url.isEmpty() and url.scheme() in ("http", "https"):
            menu.addAction("Исходный код страницы", lambda: self._open_new(QUrl("view-source:" + url.toString())))
            menu.addAction(
                "Копировать адрес страницы",
                lambda: QApplication.clipboard().setText(url.toString()),
            )
        menu.addSeparator()
        menu.addAction(
            "Инструменты разработчика",
            lambda: self.page().triggerAction(QWebEnginePage.WebAction.InspectElement),
        )
        menu.exec(event.globalPos())

    def _download(self, url: QUrl) -> None:
        """Сохраняет ресурс (изображение и т.п.) через менеджер загрузок."""
        self.page().download(url)
        window = self.window()
        if hasattr(window, "statusBar"):
            window.statusBar().showMessage("Сохранение в «Загрузки»…", 4000)

    def _open_new(self, url: QUrl) -> None:
        """Открывает URL в новой вкладке окна."""
        window = self.window()
        if hasattr(window, "add_tab"):
            window.add_tab(url.toString())


class BrowserPage(QWebEnginePage):
    """Страница вкладки: окна (target=_blank) открывает новой вкладкой."""

    def __init__(self, profile, parent, open_new_tab=None):
        super().__init__(profile, parent)
        self._open_new_tab = open_new_tab

    def createWindow(self, _window_type):  # noqa: N802 — API Qt
        """Возвращает страницу новой вкладки вместо отдельного окна."""
        if not callable(self._open_new_tab):
            return None
        view = self._open_new_tab()
        return view.page() if view is not None else None


class BrowserTabs(QWidget):
    """Стек веб-видов + внешняя лента вкладок QTabBar."""

    url_changed = pyqtSignal(str)
    title_changed = pyqtSignal(str)
    currentChanged = pyqtSignal(int)
    tab_closed = pyqtSignal(str)
    last_tab_closed = pyqtSignal()

    def __init__(self, parent=None, tab_bar: QTabBar | None = None, profile=None):
        super().__init__(parent)
        self.profile = profile
        # Важно: проверяем именно None — пустой QTabBar «ложен» (у него есть
        # __len__), поэтому `tab_bar or QTabBar()` ошибочно создавал бы новую
        # невидимую ленту вместо переданной.
        self.tab_bar = tab_bar if tab_bar is not None else QTabBar()
        self.tab_bar.setTabsClosable(True)
        try:
            import os
            from PyQt6.QtGui import QIcon
            icons_dir = os.path.join(os.path.dirname(__file__), 'icons')
            # default: classic style
            icon_path = os.path.join(icons_dir, 'close_classic.png')
            if os.path.exists(icon_path):
                self._close_icon = QIcon(icon_path)
                self.tab_bar.setStyleSheet(
                    "QTabBar::close-button { image: none; }"
                )
        except Exception:
            self._close_icon = None
        self.tab_bar.setMovable(True)
        self.tab_bar.setExpanding(False)
        self.tab_bar.setUsesScrollButtons(True)

        self.stack = QStackedWidget(self)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        if tab_bar is None:
            layout.addWidget(self.tab_bar)
        layout.addWidget(self.stack)

        self.tab_bar.tabCloseRequested.connect(self.close_tab)
        self.tab_bar.currentChanged.connect(self._on_current_changed)
        self.stack.currentChanged.connect(self.currentChanged)

    # --- вкладки ---------------------------------------------------------
    def create_view(self) -> QWebEngineView:
        """Создаёт веб-вид с локальной страницей, но НЕ кладёт его в стек."""
        view = BrowserView(self)
        profile = self.profile or QWebEngineProfile.defaultProfile()
        page = BrowserPage(profile, view, self._open_new_tab)
        view.setPage(page)
        view.urlChanged.connect(lambda u, v=view: self._relay_url(v, u))
        view.titleChanged.connect(lambda t, v=view: self._set_title(v, t))
        if hasattr(view, "iconChanged"):
            view.iconChanged.connect(lambda icon, v=view: self._set_icon(v, icon))
        return view

    def add_tab(self, url: str | None = None, background: bool = False) -> QWebEngineView:
        """Создаёт новую вкладку и возвращает её веб-вид."""
        view = self.create_view()
        self.stack.addWidget(view)
        index = self.tab_bar.addTab("Новая вкладка")
        self.tab_bar.setTabToolTip(index, "Загрузка…")
        try:
            if hasattr(self, '_close_icon') and self._close_icon is not None:
                btn = self.tab_bar.tabButton(index, QTabBar.ButtonPosition.RightSide)
                if btn is None:
                    btn = self.tab_bar.tabButton(index, QTabBar.ButtonPosition.LeftSide)
                if btn is not None:
                    btn.setIcon(self._close_icon)
        except Exception:
            pass
        view.setUrl(QUrl(url) if url else QUrl("about:blank"))
        if not background:
            self.tab_bar.setCurrentIndex(index)
        return view

    def replace_widget(self, index: int, widget: QWidget, url: str = "") -> None:
        """Меняет содержимое вкладки (например, страница → веб-вид)."""
        old = self.stack.widget(index)
        if old is None:
            return
        self.stack.removeWidget(old)
        old.deleteLater()
        self.stack.insertWidget(index, widget)
        self.stack.setCurrentIndex(index)
        self.tab_bar.setCurrentIndex(index)
        self.tab_bar.setTabText(index, "Загрузка…" if not url else url[:22])
        self.tab_bar.setTabToolTip(index, url)

    def _open_new_tab(self):
        """Создаёт вкладку для нового окна (target=_blank); возвращает вид."""
        window = self.window()
        if hasattr(window, "add_tab"):
            try:
                return window.add_tab()
            except TypeError:
                pass
        return self.add_tab()

    # --- служебные страницы (не веб) --------------------------------------
    def add_page(self, widget: QWidget, title: str, url: str, icon=None) -> int:
        """Кладёт служебную страницу (настройки, загрузки, справка) в стек."""
        widget.setProperty("hp_page_url", url)
        self.stack.addWidget(widget)
        index = self.tab_bar.addTab(title)
        self.tab_bar.setTabToolTip(index, url)
        if icon is not None:
            self.tab_bar.setTabIcon(index, icon)
        return index

    @staticmethod
    def page_url(widget) -> str | None:
        """Адрес служебной страницы (hp://…) либо None, если это веб-вид."""
        if widget is None or isinstance(widget, QWebEngineView):
            return None
        value = widget.property("hp_page_url")
        return str(value) if value else None

    def current_page(self) -> QWidget | None:
        """Служебная страница текущей вкладки (или None, если веб-вид)."""
        widget = self.stack.currentWidget()
        return widget if self.page_url(widget) else None

    def close_tab(self, index: int) -> None:
        """Закрывает вкладку; если была последней — сообщает окну."""
        view = self.stack.widget(index)
        if isinstance(view, QWebEngineView):
            self.tab_closed.emit(view.url().toString())
        self.tab_bar.removeTab(index)
        if view is not None:
            self.stack.removeWidget(view)
            view.deleteLater()
        if self.count() == 0:
            self.last_tab_closed.emit()


    def current_view(self) -> QWebEngineView | None:
        """Возвращает веб-вид активной вкладки."""
        widget = self.stack.currentWidget()
        return widget if isinstance(widget, QWebEngineView) else None

    def view(self, index: int) -> QWebEngineView | None:
        widget = self.stack.widget(index)
        return widget if isinstance(widget, QWebEngineView) else None

    def views(self) -> list[QWebEngineView]:
        """Все веб-виды (служебные страницы вкладок сюда не входят)."""
        return [
            self.stack.widget(i)
            for i in range(self.stack.count())
            if isinstance(self.stack.widget(i), QWebEngineView)
        ]

    # --- совместимость с QTabWidget -------------------------------------
    def count(self) -> int:
        return self.stack.count()

    def currentIndex(self) -> int:  # noqa: N802 — API Qt
        return self.stack.currentIndex()

    def setCurrentIndex(self, index: int) -> None:  # noqa: N802 — API Qt
        self.stack.setCurrentIndex(index)
        self.tab_bar.setCurrentIndex(index)

    def indexOf(self, view) -> int:  # noqa: N802 — API Qt
        return self.stack.indexOf(view)

    def widget(self, index: int):  # noqa: N802 — API Qt
        return self.stack.widget(index)

    def setTabText(self, index: int, text: str) -> None:  # noqa: N802 — API Qt
        self.tab_bar.setTabText(index, text)

    def setTabToolTip(self, index: int, tip: str) -> None:  # noqa: N802 — API Qt
        self.tab_bar.setTabToolTip(index, tip)

    # --- обработчики -----------------------------------------------------
    def _relay_url(self, view: QWebEngineView, url: QUrl) -> None:
        if view is self.stack.currentWidget():
            self.url_changed.emit(url.toString())

    def _set_title(self, view: QWebEngineView, title: str) -> None:
        index = self.stack.indexOf(view)
        if index != -1:
            short = (title or "Новая вкладка")[:22]
            self.tab_bar.setTabText(index, short)
            self.tab_bar.setTabToolTip(index, title or "")
        if view is self.stack.currentWidget():
            self.title_changed.emit(title)

    def _set_icon(self, view: QWebEngineView, icon) -> None:
        """Ставит фавикон сайта на вкладку."""
        if icon is None or icon.isNull():
            return
        index = self.stack.indexOf(view)
        if index != -1:
            self.tab_bar.setTabIcon(index, icon)


    def set_close_icon(self, icon: 'QIcon' | None = None) -> None:
        """Устанавливает иконку закрытия вкладки для текущих вкладок."""
        self._close_icon = icon
        if icon is None:
            return
        for i in range(self.tab_bar.count()):
            btn = self.tab_bar.tabButton(i, QTabBar.ButtonPosition.RightSide)
            if btn is None:
                btn = self.tab_bar.tabButton(i, QTabBar.ButtonPosition.LeftSide)
            if btn is not None:
                btn.setIcon(icon)

    def _on_current_changed(self, index: int) -> None:
        self.stack.setCurrentIndex(index)
        view = self.stack.currentWidget()
        if isinstance(view, QWebEngineView):
            self.url_changed.emit(view.url().toString())
            self.title_changed.emit(view.title())
