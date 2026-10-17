# HP Browser — by hypermarket
"""Главное окно HP Browser: вкладки, панель навигации, тема."""

import os

from PyQt6.QtCore import Qt, QTimer, QUrl
from PyQt6.QtGui import QActionGroup, QKeySequence, QShortcut
from PyQt6.QtWebEngineCore import QWebEngineProfile
from PyQt6.QtWidgets import (
    QApplication,
    QFileDialog,
    QLabel,
    QMainWindow,
    QMenu,
    QProgressBar,
    QPushButton,
    QSizePolicy,
    QStyle,
    QToolBar,
    QToolButton,
    QWidget,
)

from core import bookmarks_io
from core.bookmarks import Bookmarks
from core.browser import DEFAULT_QUICK_LINKS, normalize_input
from core.downloads import DownloadManager
from core.history import History
from core.settings import Settings
from ui.actions import ToolsActions
from ui.extras import ExtrasActions
from ui.findbar import FindBar
from ui.frameless import DragToolBar, PanelTabBar, FramelessMixin, WindowButtons
from ui.pages import (
    AboutPage,
    ClearDataPage,
    DownloadsPage,
    SettingsPage,
    ShortcutsPage,
)
from ui.scanlines import ScanlinesOverlay
from ui.shortcuts import install as install_shortcuts
from ui.sidebar import Sidebar
from ui.startpage import START_URL, load_start_page
from ui.tabs import BrowserTabs
from ui.themes import DEFAULT_THEME, THEMES, qss
from ui.menu import MenuBuilder, build_theme_menu
from ui.tool_panel import ToolPanel
from ui.toolbar import NavToolBar, ToolsBar
from ui.viewops import ViewOps
from utils.branding import APP_TITLE, FOOTER, HOME_URL

THEME_MAP = THEMES
HISTORY_SAVE_MS = 1500
PRIVACY_POLL_MS = 800

# Служебные страницы-вкладки: kind → (заголовок вкладки, адрес hp://…)
PAGE_META = {
    "settings": ("Настройки", "hp://settings"),
    "downloads": ("Загрузки", "hp://downloads"),
    "clear": ("Очистить данные", "hp://clear-data"),
    "about": ("О программе", "hp://about"),
    "shortcuts": ("Горячие клавиши", "hp://shortcuts"),
}

# Открытые приватные окна держим тут, иначе Qt их соберёт сборщик мусора.
PRIVATE_WINDOWS: list["MainWindow"] = []


class MainWindow(FramelessMixin, ViewOps, ToolsActions, ExtrasActions, QMainWindow):
    """Главное окно приложения."""

    def __init__(self, theme_name: str | None = None, settings: Settings | None = None,
                 private: bool = False):
        super().__init__()
        self.enable_frameless()
        self.private = private
        self.settings = settings or Settings()
        self.bookmarks = Bookmarks()
        self.history = History()
        self.theme_name = theme_name or self.settings.get("theme", DEFAULT_THEME)
        self.theme = THEME_MAP.get(self.theme_name, THEME_MAP[DEFAULT_THEME])
        # Приватное окно: отдельный off-the-record профиль, история не пишется.
        # Профиль живёт дольше окна (родитель — приложение), чтобы страницы
        # успели удалиться раньше него.
        self.private_profile = (
            QWebEngineProfile(QApplication.instance()) if private else None
        )
        self._closed_tabs: list[str] = []  # стек для «вернуть закрытую вкладку»

        self.setWindowTitle(f"{APP_TITLE} — приватное окно" if private else APP_TITLE)
        # Минимум по ширине: лента вкладок, панель навигации и кнопки окна
        # обязаны помещаться целиком — ничего не вылезает за рамки.
        self.setMinimumWidth(620)
        self.resize(1200, 800)

        # Лента вкладок — сверху.
        self.tab_bar = PanelTabBar()
        self.tab_bar.setObjectName("main_tab_bar")
        self.tabs_toolbar = DragToolBar("Вкладки", self)
        self.tabs_toolbar.setObjectName("tabs_toolbar")
        self.tabs_toolbar.setMovable(False)
        self.addToolBar(self.tabs_toolbar)
        self.addToolBarBreak()

        self.tabs = BrowserTabs(self, tab_bar=self.tab_bar, profile=self.private_profile)
        self.setCentralWidget(self.tabs)
        self.tabs_toolbar.addWidget(self.tab_bar)

        self.downloads = DownloadManager(QWebEngineProfile.defaultProfile(), self)
        self._download_states: dict[tuple[str, str], str] = {}
        self._default_ua = QWebEngineProfile.defaultProfile().httpUserAgent()
        self.apply_user_agent()

        self.new_tab_btn = QPushButton("+")
        self.new_tab_btn.setObjectName("new_tab_btn")
        self.new_tab_btn.setToolTip("Новая вкладка (Ctrl+T)")
        self.new_tab_btn.setFixedWidth(28)
        self.new_tab_btn.clicked.connect(lambda: self.add_tab())
        self.tabs_toolbar.addWidget(self.new_tab_btn)

        # Растяжка, затем кнопки окна (справа в ленте вкладок).
        spacer = QWidget()
        spacer.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        self.tabs_toolbar.addWidget(spacer)
        self.window_buttons = WindowButtons(self)
        self.tabs_toolbar.addWidget(self.window_buttons)

        self.sidebar = Sidebar(self)
        self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, self.sidebar)
        self.sidebar.hide()  # боковая панель скрыта до Ctrl+B

        self.tool_panel = ToolPanel(self)
        self.addDockWidget(Qt.DockWidgetArea.BottomDockWidgetArea, self.tool_panel)
        self.tool_panel.hide()

        self._install_interceptors()
        self.init_extras()

        self.toolbar = NavToolBar(self)
        self.addToolBar(self.toolbar)
        self.addToolBarBreak()

        self.bookmarks_bar = QToolBar("Панель закладок", self)
        self.bookmarks_bar.setObjectName("bookmarks_bar")
        self.bookmarks_bar.setMovable(False)
        self.addToolBar(self.bookmarks_bar)

        self.addToolBarBreak()
        self.tools_bar = ToolsBar(self)
        self.addToolBar(self.tools_bar)
        self.tools_bar.privacy_btn.setChecked(bool(self.settings.get("privacy", False)))
        self.bookmarks_bar.setVisible(bool(self.settings.get("show_bookmarks_bar", True)))
        self.tools_bar.setVisible(bool(self.settings.get("show_tools_bar", False)))

        self.addToolBarBreak()
        self.find_bar = FindBar(self)
        self.addToolBar(self.find_bar)
        self.find_bar.hide()

        self._build_statusbar()
        self._connect_signals()
        self._build_menu()
        self.menuBar().setVisible(bool(self.settings.get("show_menu_bar", False)))
        self._shortcuts = install_shortcuts(self)

        self.apply_theme(self.theme_name)
        self._refresh_sidebar()
        self.add_tab()
        self._restore_session()
        self._start_privacy_poll()
        self._update_privacy_button()

        self.scanlines = ScanlinesOverlay(
            self, animate=bool(self.settings.get("scanlines_anim", False))
        )
        self.scanlines.setGeometry(self.rect())
        self.scanlines.set_active(bool(self.settings.get("scanlines", False)))

    def resizeEvent(self, event) -> None:  # noqa: N802 — API Qt
        """Растягивает оверлей сканлайнов на всё окно."""
        super().resizeEvent(event)
        if hasattr(self, "scanlines"):
            self.scanlines.setGeometry(self.rect())
            self.scanlines.raise_()

    # --- сигналы ---------------------------------------------------------
    def _connect_signals(self) -> None:
        bar = self.toolbar
        bar.go_requested.connect(self.navigate)
        bar.back_requested.connect(self._with_view("back"))
        bar.forward_requested.connect(self._with_view("forward"))
        bar.reload_requested.connect(self._reload_or_stop)
        bar.home_requested.connect(self.go_home)
        bar.bookmark_requested.connect(self.add_bookmark)
        bar.downloads_requested.connect(self.show_downloads)
        bar.menu_requested.connect(self.show_main_menu)

        tools = self.tools_bar
        tools.osint_requested.connect(self.run_osint)
        tools.leaks_requested.connect(self.run_leaks)
        tools.security_requested.connect(self.run_security)
        tools.sniffer_requested.connect(self.toggle_sniffer)
        tools.privacy_requested.connect(self.toggle_privacy)

        self.tabs.url_changed.connect(bar.set_url)
        self.tabs.url_changed.connect(self._record_history)
        self.tabs.tab_closed.connect(self._remember_closed_tab)
        self.tabs.last_tab_closed.connect(self.close)
        self.tabs.currentChanged.connect(lambda _i: self._refresh_status())

        self.tab_bar.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.tab_bar.customContextMenuRequested.connect(self.show_tab_menu)

        self.sidebar.open_url.connect(self.navigate)
        self.sidebar.delete_requested.connect(self._remove_bookmark)
        self.sidebar.history_delete_requested.connect(self._remove_history)

        self.find_bar.next_requested.connect(self.find_next)
        self.find_bar.prev_requested.connect(self.find_prev)
        self.find_bar.closed.connect(self.close_find)

        # История пишется на диск отложенно: навигация не ждёт диск.
        self._history_timer = QTimer(self)
        self._history_timer.setSingleShot(True)
        self._history_timer.setInterval(HISTORY_SAVE_MS)
        self._history_timer.timeout.connect(self._save_history)

        # Обновление счётчика трекеров на кнопке приватности.
        self._privacy_timer = QTimer(self)
        self._privacy_timer.setInterval(PRIVACY_POLL_MS)
        self._privacy_timer.timeout.connect(self._update_privacy_button)

        # Ctrl+Shift+Y — переключение темы (Ctrl+Shift+T — вернуть вкладку)
        self.theme_shortcut = QShortcut(QKeySequence("Ctrl+Shift+Y"), self)
        self.theme_shortcut.activated.connect(self.toggle_theme)

    def _with_view(self, method: str):
        """Возвращает обработчик, вызывающий method у активного вида."""
        def handler() -> None:
            view = self.current_view()
            if view is not None:
                getattr(view, method)()
        return handler

    def _build_statusbar(self) -> None:
        """Статус-бар: индикатор загрузки и текущий масштаб."""
        self.progress = QProgressBar()
        self.progress.setFixedWidth(140)
        self.progress.setTextVisible(False)
        self.progress.setVisible(False)
        self.zoom_button = QToolButton()
        self.zoom_button.setText("100%")
        self.zoom_button.setAutoRaise(True)
        self.zoom_button.setToolTip(
            "Масштаб страницы. Нажмите, чтобы вернуть 100% (Ctrl+плюс / Ctrl+минус / Ctrl+0)"
        )
        self.zoom_button.clicked.connect(self.zoom_reset)
        if self.private:
            self.private_label = QLabel("Приватное окно")
            self.private_label.setObjectName("private_badge")
            self.statusBar().addWidget(self.private_label)
        self.statusBar().addPermanentWidget(self.progress)
        self.statusBar().addPermanentWidget(self.zoom_button)
        self.downloads.changed.connect(self._on_downloads_changed)
        self._download_status = QLabel("")
        self.statusBar().addWidget(self._download_status)

    def _build_menu(self) -> None:
        """Меню: Файл, Вид, Инструменты, Справка.

        Клавиши указаны подсказкой (после \\t) — сами комбинации живут в
        ui/shortcuts.py, чтобы не было двойных (неоднозначных) шорткатов.
        """
        bar = self.menuBar()

        file_menu = bar.addMenu("Файл")
        self._add_items(file_menu, (
            ("Новая вкладка", "Ctrl+T", self.new_tab),
            ("Новое приватное окно", "Ctrl+Shift+P", self.open_private_window),
            ("Закрыть вкладку", "Ctrl+W", self.close_current_tab),
            ("Вернуть закрытую вкладку", "Ctrl+Shift+T", self.reopen_closed_tab),
            ("-", "", None),
            ("Сохранить страницу в PDF", "Ctrl+P", self.save_pdf),
            ("Скриншот страницы", "Ctrl+Shift+S", self.take_screenshot),
            ("-", "", None),
            ("Импорт закладок (HTML)…", "", self.import_bookmarks),
            ("Экспорт закладок (HTML)…", "", self.export_bookmarks),
            ("Экспорт истории (HTML)…", "", self.export_history),
            ("-", "", None),
            ("Очистить данные просмотра", "Ctrl+Shift+Delete", self.clear_data),
            ("-", "", None),
            ("Выход", "Ctrl+Q", self.close),
        ))

        view_menu = bar.addMenu("Вид")
        self._add_items(view_menu, (
            ("Найти на странице", "Ctrl+F", self.find_on_page),
            ("-", "", None),
            ("Крупнее", "Ctrl+плюс", self.zoom_in),
            ("Мельче", "Ctrl+минус", self.zoom_out),
            ("Обычный масштаб", "Ctrl+0", self.zoom_reset),
            ("-", "", None),
            ("Сканлайны", "", self.toggle_scanlines),
            ("Анимация сканлайнов", "", self.toggle_scanline_anim),
            ("-", "", None),
            ("Панель закладок", "", self.toggle_bookmarks_bar),
            ("-", "", None),
        ))

        theme_menu = view_menu.addMenu("Тема")
        # одна группа на два меню (меню-бар и гамбургер): галочки держит
        # _sync_theme_actions, иначе exclusive-группа гасит вторую галочку
        self._theme_group = QActionGroup(self)
        self._theme_group.setExclusive(False)
        self._theme_actions = {}
        for name, theme in THEME_MAP.items():
            act = theme_menu.addAction(theme["label"])
            act.setCheckable(True)
            act.setChecked(name == self.theme_name)
            act.triggered.connect(lambda _checked=False, n=name: self.apply_theme(n, persist=True))
            self._theme_group.addAction(act)
            self._theme_actions.setdefault(name, []).append(act)

        self._add_items(view_menu, (
            ("Тёмная тема сайтов", "", self._menu_toggle_dark),
            ("Полноэкранный режим", "F11", self.toggle_fullscreen),
            ("-", "", None),
            ("Панель закладок и истории", "Ctrl+B", self.toggle_sidebar),
            ("Панель инструментов", "", self.toggle_tools_bar),
            ("Панель результатов", "", self._toggle_tool_panel),
            ("Настройки", "Ctrl+,", self.open_settings),
        ))

        tools_menu = bar.addMenu("Инструменты")
        self._add_items(tools_menu, (
            ("OSINT по текущему сайту", "Ctrl+Shift+O", self.run_osint),
            ("Проверить email на утечки", "Ctrl+Shift+L", self.run_leaks),
            ("Оценка безопасности сайта", "", self.run_security),
            ("Сниффер запросов", "", lambda: self.tools_bar.sniffer_btn.toggle()),
            ("Приватность (трекеры, DoH, WebRTC)", "", lambda: self.tools_bar.privacy_btn.toggle()),
            ("Статистика приватности", "", self.show_privacy_stats),
            ("-", "", None),
            ("Режим чтения", "Ctrl+Shift+R", self.toggle_reader),
            ("Новая заметка", "Ctrl+Shift+N", self.add_note),
            ("Показать заметки", "", self.show_notes),
            ("Экспорт заметок (JSON)…", "", self.export_notes),
        ))

        help_menu = bar.addMenu("Справка")
        self._add_items(help_menu, (
            ("Горячие клавиши", "F1", self.show_shortcuts),
            ("О программе", "", self.show_about),
        ))

        self._build_main_menu()

    @staticmethod
    def _add_items(menu, items) -> None:
        """Наполняет меню: («-», ...) — разделитель, иначе пункт с подсказкой."""
        for title, hint, slot in items:
            if slot is None:
                menu.addSeparator()
                continue
            text = f"{title}\t{hint}" if hint else title
            menu.addAction(text, slot)

    def _toggle_tool_panel(self) -> None:
        """Показывает/скрывает панель результатов."""
        self.tool_panel.setVisible(not self.tool_panel.isVisible())

    def _build_main_menu(self) -> None:
        """Собирает меню-«гамбургер»."""
        menu = QMenu(self)
        self._add_items(menu, (
            ("Новая вкладка", "Ctrl+T", self.new_tab),
            ("Новое приватное окно", "Ctrl+Shift+P", self.open_private_window),
            ("Вернуть закрытую вкладку", "Ctrl+Shift+T", self.reopen_closed_tab),
            ("Новая заметка", "Ctrl+Shift+N", self.add_note),
            ("-", "", None),
            ("Загрузки", "Ctrl+J", self.show_downloads),
            ("Закладки и история", "Ctrl+B", self.toggle_sidebar),
            ("Очистить данные просмотра", "Ctrl+Shift+Delete", self.clear_data),
            ("Найти на странице", "Ctrl+F", self.find_on_page),
            ("Режим чтения", "Ctrl+Shift+R", self.toggle_reader),
            ("-", "", None),
        ))
        theme_menu = menu.addMenu("Тема")
        for name, theme in THEME_MAP.items():
            act = theme_menu.addAction(theme["label"])
            act.setCheckable(True)
            act.setChecked(name == self.theme_name)
            act.triggered.connect(lambda _c=False, n=name: self.apply_theme(n, persist=True))
            self._theme_actions.setdefault(name, []).append(act)
            self._theme_group.addAction(act)
        tools_menu = menu.addMenu("Инструменты")
        self._add_items(tools_menu, (
            ("OSINT по текущему сайту", "Ctrl+Shift+O", self.run_osint),
            ("Проверить email на утечки", "Ctrl+Shift+L", self.run_leaks),
            ("Оценка безопасности сайта", "", self.run_security),
            ("Статистика приватности", "", self.show_privacy_stats),
        ))
        self._add_items(menu, (
            ("-", "", None),
            ("Полноэкранный режим", "F11", self.toggle_fullscreen),
            ("Панель инструментов", "", self.toggle_tools_bar),
            ("Строка меню", "", self.toggle_menu_bar),
            ("Горячие клавиши", "F1", self.show_shortcuts),
            ("О программе", "", self.show_about),
            ("Настройки", "Ctrl+,", self.open_settings),
            ("-", "", None),
            ("Выход", "Ctrl+Q", self.close),
        ))
        self.recent_menu = menu.addMenu("Недавно закрытые вкладки")
        self.recent_bookmarks_menu = menu.addMenu("Недавние закладки")
        self._rebuild_recent_menu()
        self._rebuild_recent_bookmarks_menu()
        self.main_menu = menu

    def _rebuild_recent_menu(self) -> None:
        """Наполняет подменю последними закрытыми вкладками."""
        self.recent_menu.clear()
        if not self._closed_tabs:
            act = self.recent_menu.addAction("(пусто)")
            act.setEnabled(False)
            return
        for url in reversed(self._closed_tabs[-10:]):
            self.recent_menu.addAction(url, lambda _c=False, u=url: self.add_tab(u))
        self.recent_menu.addSeparator()
        self.recent_menu.addAction("Вернуть все", self._reopen_all_closed)

    def _reopen_all_closed(self) -> None:
        """Открывает все недавно закрытые вкладки заново."""
        urls = list(self._closed_tabs)
        self._closed_tabs.clear()
        for url in urls:
            self.add_tab(url, background=True)

    def show_main_menu(self) -> None:
        """Открывает меню под кнопкой-гамбургером."""
        self._rebuild_recent_menu()
        # наполнить недавние закладки
        self._rebuild_recent_bookmarks_menu()
        btn = self.toolbar.menu_btn
        self.main_menu.popup(btn.mapToGlobal(btn.rect().bottomLeft()))

    def show_downloads(self):
        """Показывает страницу загрузок (вкладка)."""
        return self.open_page("downloads")

    def clear_data(self):
        """Ctrl+Shift+Delete: очистка данных просмотра."""
        return self.open_page("clear")

    def open_settings(self):
        """Открывает страницу настроек."""
        return self.open_page("settings")

    def open_page(self, kind: str):
        """Открывает служебную страницу-вкладку hp://…"""
        if kind not in PAGE_META:
            return
        title, url = PAGE_META[kind]
        # ищем уже открытую
        for i in range(self.tabs.count()):
            w = self.tabs.widget(i)
            pu = self.tabs.page_url(w)
            if pu == url:
                self.tabs.setCurrentIndex(i)
                self._refresh_status()
                return w
        if kind == "settings":
            page = SettingsPage(self.settings)
            page.applied.connect(self._on_settings_applied)
        elif kind == "downloads":
            page = DownloadsPage(self.downloads)
        elif kind == "clear":
            page = ClearDataPage(self)
            page.cleared.connect(self._on_cleared)
        elif kind == "about":
            page = AboutPage()
        elif kind == "shortcuts":
            from ui.viewops import SHORTCUT_HELP
            page = ShortcutsPage(SHORTCUT_HELP)
        else:
            return
        icon = None
        try:
            from PyQt6.QtWidgets import QStyle
            if kind == "downloads":
                icon = self.style().standardIcon(QStyle.StandardPixmap.SP_ArrowDown)
            elif kind == "settings":
                icon = self.style().standardIcon(QStyle.StandardPixmap.SP_FileDialogDetailedView)
            elif kind == "clear":
                icon = self.style().standardIcon(QStyle.StandardPixmap.SP_DialogResetButton)
            elif kind == "about":
                icon = self.style().standardIcon(QStyle.StandardPixmap.SP_MessageBoxInformation)
            elif kind == "shortcuts":
                icon = self.style().standardIcon(QStyle.StandardPixmap.SP_DialogHelpButton)
        except Exception:
            pass
        idx = self.tabs.add_page(page, title, url, icon)
        self.tabs.setCurrentIndex(idx)
        self._refresh_status()
        return page

    def _on_settings_applied(self) -> None:
        self.apply_theme(str(self.settings.get("theme", DEFAULT_THEME)))
        self.bookmarks_bar.setVisible(bool(self.settings.get("show_bookmarks_bar", True)))
        self.tools_bar.setVisible(bool(self.settings.get("show_tools_bar", False)))
        self.menuBar().setVisible(bool(self.settings.get("show_menu_bar", False)))
        if hasattr(self, "scanlines"):
            self.scanlines.set_active(bool(self.settings.get("scanlines", False)))
            self.scanlines.set_animated(bool(self.settings.get("scanlines_anim", False)))
        self.tools_bar.privacy_btn.setChecked(bool(self.settings.get("privacy", False)))
        try:
            self.privacy_guard.set_enabled(bool(self.settings.get("privacy", False)))
        except Exception:
            pass
        self.apply_dark_sites()
        self.apply_user_agent()
        self.reload_page()
        self._sync_theme_actions(self.theme_name)
        self._refresh_status()
        self._update_privacy_button()
        self.statusBar().showMessage("Настройки сохранены", 3000)

    def _on_cleared(self, done: str) -> None:
        self.statusBar().showMessage(f"Очищено: {done}", 5000)

    def _menu_toggle_dark(self) -> None:
        self.toggle_dark_sites(None)
        state = "вкл" if self.dark_sites else "выкл"
        self.statusBar().showMessage(f"Тёмная тема сайтов: {state}", 4000)

    # --- публичные методы ------------------------------------------------
    def current_view(self):
        """Веб-вид активной вкладки."""
        return self.tabs.current_view()

    def add_tab(self, url: str | None = None, background: bool = False):
        """Открывает новую вкладку: URL, либо стартовую страницу."""
        view = self.tabs.add_tab(None, background)
        self._wire_view(view)
        if url:
            view.setUrl(QUrl(url))
        else:
            load_start_page(view, self.theme, self._engine(), self.private, self._quick_links())
        self._refresh_status()
        return view

    def _wire_view(self, view) -> None:
        view.loadFinished.connect(lambda ok, v=view: self._on_load_finished(ok, v))
        view.loadStarted.connect(self._on_load_started)
        view.loadProgress.connect(self._on_load_progress)
        try:
            view.setZoomFactor(self.current_zoom())
        except Exception:  # noqa: BLE001
            pass

    def _reload_or_stop(self) -> None:
        """Кнопка «Обновить» во время загрузки работает как «Стоп»."""
        if self.progress.isVisible():
            self.stop_page()
        else:
            self.reload_page()

    def _on_load_started(self) -> None:
        self.progress.setValue(0)
        self.progress.setVisible(True)
        self.toolbar.set_loading(True)

    def _on_load_progress(self, value: int) -> None:
        self.progress.setValue(value)
        if value >= 100:
            self.progress.setVisible(False)

    def _on_load_finished(self, ok: bool, view) -> None:
        """Обрабатывает завершение загрузки: тёмная тема и ошибки."""
        self.progress.setVisible(False)
        self.toolbar.set_loading(False)
        self.apply_dark_sites()
        if not ok and view.url().scheme() in ("http", "https"):
            self.report_load_error(view.url().toString())

    def _engine(self) -> str:
        """Имя выбранного поисковика из настроек."""
        return str(self.settings.get("search_engine", "duckduckgo"))

    def _quick_links(self) -> list[dict]:
        """Плитки стартовой страницы из настроек (или встроенные)."""
        return self.settings.get("quick_links") or DEFAULT_QUICK_LINKS

    def apply_user_agent(self) -> None:
        """Применяет User-Agent из настроек ко всем профилям."""
        ua = str(self.settings.get("user_agent", "") or "").strip()
        if not ua:
            ua = getattr(self, "_default_ua", "")
        QWebEngineProfile.defaultProfile().setHttpUserAgent(ua)
        if self.private_profile is not None:
            self.private_profile.setHttpUserAgent(ua)

    def go_home(self) -> None:
        """Открывает домашнюю страницу (или стартовую, если она не задана)."""
        view = self.current_view()
        home = str(self.settings.get("home_url", "") or "").strip()
        if view is not None:
            if home:
                url, _was_search = normalize_input(home, self._engine())
                if url:
                    view.setUrl(QUrl(url))
                    self._refresh_status()
                    return
            load_start_page(view, self.theme, self._engine(), self.private, self._quick_links())
            self._refresh_status()
            return
        page = self.tabs.current_page()
        if page is not None:
            index = self.tabs.currentIndex()
            wv = self.tabs.create_view()
            self._wire_view(wv)
            if home:
                url, _was_search = normalize_input(home, self._engine())
                if url:
                    wv.setUrl(QUrl(url))
                    self.tabs.replace_widget(index, wv, url)
                    self._refresh_status()
                    return
            load_start_page(wv, self.theme, self._engine(), self.private, self._quick_links())
            self.tabs.replace_widget(index, wv, wv.url().toString())
            self._refresh_status()
            return

    def navigate(self, text: str) -> None:
        """Переходит по адресу или ищет в выбранном поисковике."""
        url, _was_search = normalize_input(text, self._engine())
        view = self.current_view()
        if url and view is not None:
            view.setUrl(QUrl(url))
            self._refresh_status()
            return
        page = self.tabs.current_page()
        if page is not None and url:
            index = self.tabs.currentIndex()
            wv = self.tabs.create_view()
            self._wire_view(wv)
            wv.setUrl(QUrl(url))
            self.tabs.replace_widget(index, wv, url)
            self._refresh_status()

    # --- закладки и история ---------------------------------------------
    def add_bookmark(self) -> None:
        """Добавляет текущую страницу в закладки."""
        view = self.current_view()
        if view is None:
            return
        url = view.url().toString()
        if self.bookmarks.add(view.title(), url):
            self._refresh_sidebar()
            self._rebuild_recent_bookmarks_menu()

    def import_bookmarks(self) -> None:
        """Импортирует закладки из HTML-файла (формат HTML-закладок)."""
        path, _ = QFileDialog.getOpenFileName(
            self, "Импорт закладок", "", "Закладки HTML (*.html *.htm);;Все файлы (*)"
        )
        if not path:
            return
        items = bookmarks_io.import_html(path)
        added = sum(
            1 for item in items
            if self.bookmarks.add(item.get("title", ""), item.get("url", ""))
        )
        self._refresh_sidebar()
        self.statusBar().showMessage(
            f"Импортировано закладок: {added} (в файле: {len(items)})", 5000
        )

    def export_history(self) -> None:
        """Экспортирует историю в HTML-файл (Netscape)."""
        default = os.path.join(os.path.expanduser("~"), "hp-history.html")
        path, _ = QFileDialog.getSaveFileName(
            self, "Экспорт истории", default, "Закладки/история HTML (*.html)"
        )
        if not path:
            return
        count = bookmarks_io.export_html(path, self.history.items)
        self.statusBar().showMessage(f"Экспортировано из истории: {count}", 5000)

    def export_bookmarks(self) -> None:
        """Экспортирует закладки в HTML-файл."""
        default = os.path.join(os.path.expanduser("~"), "hp-bookmarks.html")
        path, _ = QFileDialog.getSaveFileName(
            self, "Экспорт закладок", default, "Закладки HTML (*.html)"
        )
        if not path:
            return
        count = bookmarks_io.export_html(path, self.bookmarks.items)
        self.statusBar().showMessage(f"Экспортировано закладок: {count}", 5000)

    def _remove_bookmark(self, url: str) -> None:
        if self.bookmarks.remove(url):
            self._refresh_sidebar()

    def _remove_history(self, url: str) -> None:
        """Удаляет запись из истории (кнопка в боковой панели)."""
        if url and self.history.remove(url):
            self._refresh_sidebar()

    def _record_history(self, url: str) -> None:
        """Пишет переход в историю; приватное окно — не пишет."""
        if self.private:
            return
        view = self.current_view()
        title = view.title() if view is not None else ""
        self.history.add(url, title, save=False)
        self._history_timer.start()

    def _save_history(self) -> None:
        """Отложенная запись истории на диск."""
        self.history.save()
        self._refresh_sidebar()

    def _restore_session(self) -> None:
        """Открывает вкладки прошлой сессии («Восстановить сессию»)."""
        if self.private or not self.settings.get("restore_session", True):
            return
        saved = self.settings.get("session_tabs", []) or []
        urls = [u for u in saved if u and u not in ("about:blank", START_URL)]
        if not urls:
            return
        view = self.current_view()
        if view is not None:
            view.setUrl(QUrl(urls[0]))
        for url in urls[1:]:
            self.add_tab(url, background=True)

    def _save_session(self) -> None:
        """Запоминает открытые вкладки для следующего запуска."""
        if self.private:
            return
        urls = []
        for view in self.tabs.views():
            url = view.url().toString()
            if url and url not in ("about:blank", START_URL):
                urls.append(url)
        self.settings.set("session_tabs", urls)

    def closeEvent(self, event) -> None:  # noqa: N802 — API Qt
        """Сохраняет историю, сессию и настройки при выходе."""
        if self.private and self in PRIVATE_WINDOWS:
            PRIVATE_WINDOWS.remove(self)
        self._save_session()
        self.settings.save()
        if not self.private:
            self.history.save()
        super().closeEvent(event)

    def open_private_window(self) -> None:
        """Открывает приватное окно (Ctrl+Shift+P)."""
        win = MainWindow(settings=self.settings, private=True)
        PRIVATE_WINDOWS.append(win)
        win.show()

    def _remember_closed_tab(self, url: str) -> None:
        """Запоминает адрес закрытой вкладки (для Ctrl+Shift+T)."""
        if not url or url in ("about:blank", START_URL):
            return
        self._closed_tabs.append(url)
        del self._closed_tabs[:-20]

    def _rebuild_recent_bookmarks_menu(self) -> None:
        """Подменю последних добавленных закладок (первые 10)."""
        if not hasattr(self, "recent_bookmarks_menu"):
            return
        self.recent_bookmarks_menu.clear()
        items = list(self.bookmarks.items)[:10]
        if not items:
            act = self.recent_bookmarks_menu.addAction("(пусто)")
            act.setEnabled(False)
            return
        for item in items:
            title = (item.get("title") or "").strip() or item.get("url", "")
            url = item.get("url", "")
            action = self.recent_bookmarks_menu.addAction(title[:70])
            action.setToolTip(url)
            action.triggered.connect(lambda _c=False, u=url: self.navigate(u))

    def reopen_closed_tab(self) -> None:
        """Возвращает последнюю закрытую вкладку (Ctrl+Shift+T)."""
        while self._closed_tabs:
            url = self._closed_tabs.pop()
            self.add_tab(url)
            return
        self.statusBar().showMessage("Нет закрытых вкладок", 3000)

    def _refresh_sidebar(self) -> None:
        self.sidebar.set_bookmarks(self.bookmarks.items)
        self.sidebar.set_history([] if self.private else self.history.items)
        self._refresh_completions()
        self._refresh_bookmarks_bar()

    def _refresh_bookmarks_bar(self) -> None:
        """Пересобирает панель закладок: кнопка на каждую закладку."""
        self.bookmarks_bar.clear()
        for item in self.bookmarks.items:
            url = item.get("url", "")
            title = item.get("title") or url
            btn = QPushButton(title[:28])
            btn.setToolTip(f"{title}\n{url}")
            btn.setFlat(True)
            btn.clicked.connect(lambda _checked=False, u=url: self.navigate(u))
            btn.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
            btn.customContextMenuRequested.connect(
                lambda _pos, u=url: self._remove_bookmark(u)
            )
            btn.clicked.connect(lambda _checked=False, u=url: self.navigate(u))
            btn.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
            btn.customContextMenuRequested.connect(
                lambda _pos, u=url: self._remove_bookmark(u)
            )
            self.bookmarks_bar.addWidget(btn)
        self._rebuild_recent_bookmarks_menu()

    def toggle_bookmarks_bar(self) -> None:
        """Показывает/скрывает панель закладок и запоминает выбор."""
        visible = not self.bookmarks_bar.isVisible()
        self.bookmarks_bar.setVisible(visible)
        self.settings.set("show_bookmarks_bar", visible)
        self.settings.save()

    def _refresh_completions(self) -> None:
        """Подсказки в адресной строке: недавняя история + закладки."""
        seen: list[str] = []
        recent = [] if self.private else self.history.items[:150]
        for item in recent + self.bookmarks.items:
            url = item.get("url", "")
            if not url or url in seen or url.startswith("about:"):
                continue
            if "hp-browser.local" in url:
                continue  # внутренние страницы в подсказках не нужны
            seen.append(url)
        self.toolbar.set_completions(seen)

    def toggle_sidebar(self) -> None:
        self.sidebar.setVisible(not self.sidebar.isVisible())

    def toggle_menu_bar(self) -> None:
        """Показывает/скрывает строку меню (скрыта по умолчанию)."""
        visible = not self.menuBar().isVisible()
        self.menuBar().setVisible(visible)
        self.settings.set("show_menu_bar", visible)
        self.settings.save()

    def toggle_tools_bar(self) -> None:
        """Показывает/скрывает панель инструментов (OSINT и прочее)."""
        visible = not self.tools_bar.isVisible()
        self.tools_bar.setVisible(visible)
        self.settings.set("show_tools_bar", visible)
        self.settings.save()

    # --- тема и статус ---------------------------------------------------
    def _start_privacy_poll(self) -> None:
        if hasattr(self, "_privacy_timer"):
            self._privacy_timer.start()

    def _update_privacy_button(self) -> None:
        try:
            guard = self.privacy_guard
            count = getattr(guard, "blocked_count", 0)
        except Exception:  # noqa: BLE001
            count = 0
        btn = self.tools_bar.privacy_btn
        if count > 0:
            btn.setText(f"Приватность · {count}")
        else:
            btn.setText("Приватность")
        btn.setToolTip(f"Приватность: трекеры, DoH, WebRTC (заблокировано: {count})")
        fm = btn.fontMetrics()
        w = fm.horizontalAdvance(btn.text()) + 26
        btn.setFixedWidth(max(104, w))

    def _on_downloads_changed(self) -> None:
        items = self.downloads.items
        active = [e for e in items if e.get("state") == "загружается"]
        done = [e for e in items if e.get("state") == "готово"]
        if active:
            total = sum(e.get("total", 0) or 0 for e in active)
            received = sum(e.get("received", 0) or 0 for e in active)
            if total:
                prog = int(received * 100 / total)
                text = f"Загрузки: {prog}% ({len(active)} активн.)"
            else:
                text = f"Загрузки: {len(active)} активн."
        elif done:
            text = f"Загрузки: готово ({len(done)})"
        else:
            text = ""
        self._download_status.setText(text)

    def _sync_theme_actions(self, name: str) -> None:
        actions = getattr(self, "_theme_actions", {})
        for theme_name, acts in actions.items():
            wanted = theme_name == name
            for act in acts:
                try:
                    act.setChecked(wanted)
                except Exception:  # noqa: BLE001
                    pass

    def _refresh_status(self) -> None:
        view = self.current_view()
        current_page = self.tabs.current_page()
        if current_page is not None:
            # служебная страница-вкладка
            url = self.tabs.page_url(current_page) or HOME_URL
        elif view is not None:
            history = view.history()
            self.toolbar.set_nav_state(history.canGoBack(), history.canGoForward())
            url = view.url().toString() or HOME_URL
        else:
            url = HOME_URL
        self.zoom_button.setText(f"{int(self.current_zoom() * 100)}%")
        marker = "Приватное окно · " if self.private else ""
        tabs_count = self.tabs.count()
        self.statusBar().showMessage(
            marker
            + f"{FOOTER} | тема: {self.theme['label']} | вкладок: {tabs_count} | {url}"
        )

    def apply_theme(self, theme_name: str, persist: bool = False) -> None:
        """Применяет тему по имени; при persist — сохраняет в настройки."""
        self.theme_name = theme_name if theme_name in THEME_MAP else DEFAULT_THEME
        self.theme = THEME_MAP[self.theme_name]
        self.setStyleSheet(qss(self.theme))
        # QTabBar рисует тело из палитры/QWidget-фона — подкласс заливает фон
        # сам, выравнивая ленту вкладок с панелью инструментов.
        self.tab_bar.set_background(self.theme["panel"])
        self._sync_theme_actions(self.theme_name)
        # обновить иконку закрытия вкладок по теме
        try:
            import os
            from PyQt6.QtGui import QIcon
            icons_dir = os.path.join(os.path.dirname(__file__), 'icons')
            fname = {
                'hacker': 'close_hacker.png',
                'comfort': 'close_comfort.png',
                'light': 'close_light.png',
                'classic': 'close_classic.png',
                'classic-dark': 'close_classic_dark.png',
                'nord': 'close_nord.png',
                'solarized': 'close_solarized.png',
                'dark': 'close_dark.png',
            }.get(self.theme_name, 'close_classic.png')
            p = os.path.join(icons_dir, fname)
            if os.path.exists(p):
                self.tabs.set_close_icon(QIcon(p))
            else:
                self.tabs.set_close_icon(None)
        except Exception:
            pass
        if persist:
            self.settings.set("theme", self.theme_name)
            self.settings.save()
        # Стартовая страница нарисована в цветах темы — перерисуем её.
        view = self.current_view()
        if view is not None and view.url().toString().startswith(START_URL):
            load_start_page(view, self.theme, self._engine(), self.private, self._quick_links())
        self._refresh_status()

    def toggle_theme(self) -> None:
        """Переключает тему по кругу через список доступных тем."""
        names = list(THEME_MAP)
        index = (names.index(self.theme_name) + 1) % len(names) if self.theme_name in names else 0
        self.apply_theme(names[index], persist=True)
