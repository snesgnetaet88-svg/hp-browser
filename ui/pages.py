# HP Browser — by hypermarket
"""Служебные страницы браузера.

Настройки, загрузки, очистка данных, «О программе» и горячие клавиши
открываются обычной вкладкой (hp://…) вместо отдельного окна — как в
современных браузерах.
"""

import os

from PyQt6.QtCore import PYQT_VERSION_STR, QT_VERSION_STR, Qt, pyqtSignal
from PyQt6.QtGui import QFontDatabase
from PyQt6.QtWebEngineCore import QWebEngineProfile
from PyQt6.QtWidgets import (
    QAbstractItemView,
    QCheckBox,
    QComboBox,
    QFormLayout,
    QFrame,
    QHBoxLayout,
    QGroupBox,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QPlainTextEdit,
    QPushButton,
    QScrollArea,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

from core.browser import (
    DEFAULT_QUICK_LINKS,
    SEARCH_ENGINES,
    format_quick_links,
    parse_quick_links,
)
from core.downloads import human
from ui.themes import THEMES
from ui.viewops import SHORTCUT_HELP
from utils.branding import (
    APP_AUTHOR,
    APP_NAME,
    APP_VERSION,
    APP_YEAR,
    LOGO_ASCII,
    TAGLINE,
)
from utils.sysopen import open_path


class PageBase(QWidget):
    """Каркас страницы-вкладки: заголовок, содержимое, кнопки внизу."""

    def __init__(self, title: str, hint: str = "", parent=None):
        super().__init__(parent)
        self.setObjectName("browser_page")
        outer = QVBoxLayout(self)
        outer.setContentsMargins(24, 16, 24, 16)
        outer.setSpacing(6)

        head = QLabel(title)
        head.setObjectName("page_title")
        outer.addWidget(head)
        if hint:
            note = QLabel(hint)
            note.setObjectName("page_hint")
            note.setWordWrap(True)
            outer.addWidget(note)

        self.body = QVBoxLayout()
        self.body.setSpacing(8)
        outer.addLayout(self.body, 1)

        self.footer = QHBoxLayout()
        self.footer.setSpacing(8)
        self.footer.addStretch(1)
        outer.addLayout(self.footer)

    def scroll(self) -> QVBoxLayout:
        """Область с прокруткой — содержимое возвращается как лейаут."""
        holder = QWidget()
        lay = QVBoxLayout(holder)
        lay.setContentsMargins(0, 4, 6, 0)
        lay.setSpacing(10)
        area = QScrollArea()
        area.setWidgetResizable(True)
        area.setFrameShape(QFrame.Shape.NoFrame)
        area.setWidget(holder)
        self.body.addWidget(area, 1)
        return lay

    def button(self, text: str, slot, primary: bool = False) -> QPushButton:
        """Кнопка в футере страницы."""
        btn = QPushButton(text)
        if primary:
            btn.setDefault(True)
            btn.setAutoDefault(True)
        btn.clicked.connect(slot)
        self.footer.addWidget(btn)
        return btn

    def close_page(self) -> None:
        """Закрывает вкладку этой страницы."""
        tabs = getattr(self.window(), "tabs", None)
        index = tabs.indexOf(self) if tabs is not None else -1
        if index != -1:
            tabs.close_tab(index)
        else:
            self.close()


def _check(settings, label: str, key: str, default: bool) -> QCheckBox:
    box = QCheckBox(label)
    box.setChecked(bool(settings.get(key, default)))
    return box


def _select(combo: QComboBox, value: str) -> None:
    index = combo.findData(value)
    if index >= 0:
        combo.setCurrentIndex(index)


class SettingsPage(PageBase):
    """Настройки браузера (hp://settings)."""

    applied = pyqtSignal()

    def __init__(self, settings, parent=None):
        super().__init__(
            "Настройки",
            "Изменения вступают в силу сразу после кнопки «Применить».",
            parent,
        )
        self.settings = settings
        lay = self.scroll()

        self.theme = QComboBox()
        for name, theme in THEMES.items():
            self.theme.addItem(theme["label"], name)
        _select(self.theme, str(settings.get("theme", "classic")))

        self.engine = QComboBox()
        for name, (label, _template) in SEARCH_ENGINES.items():
            self.engine.addItem(label, name)
        _select(self.engine, str(settings.get("search_engine", "duckduckgo")))

        self.home = QLineEdit(str(settings.get("home_url", "")))
        self.home.setPlaceholderText("пусто — внутренняя стартовая страница")

        self.quick = QPlainTextEdit()
        self.quick.setPlaceholderText("Название | https://адрес — по одной на строку")
        self.quick.setMaximumHeight(110)
        current_links = settings.get("quick_links") or DEFAULT_QUICK_LINKS
        self.quick.setPlainText(format_quick_links(current_links))

        self.user_agent = QLineEdit(str(settings.get("user_agent", "")))
        self.user_agent.setPlaceholderText("пусто — браузерный по умолчанию")

        self.proxy = QLineEdit(str(settings.get("proxy", "")))
        self.proxy.setPlaceholderText("напр. socks5://127.0.0.1:9050 (пусто — без прокси)")

        self.bookmarks_bar = _check(settings, "Панель закладок", "show_bookmarks_bar", True)
        self.tools_bar = _check(settings, "Панель инструментов", "show_tools_bar", False)
        self.menu_bar = _check(settings, "Строка меню", "show_menu_bar", False)
        self.restore = _check(
            settings, "Восстанавливать вкладки при запуске", "restore_session", True
        )
        self.scanlines = _check(settings, "Сканлайны (CRT)", "scanlines", False)
        self.scanlines_anim = _check(settings, "Анимация сканлайнов", "scanlines_anim", False)
        self.dark_sites = _check(settings, "Тёмная тема для сайтов", "dark_mode_sites", False)
        self.privacy = _check(settings, "Блокировать трекеры", "privacy", False)
        self.doh = _check(settings, "DNS-over-HTTPS (нужен перезапуск)", "doh", False)
        self.dnt = _check(settings, "Посылать Do Not Track", "dnt", False)

        look = QGroupBox("Оформление")
        look_form = QFormLayout(look)
        look_form.addRow("Тема", self.theme)
        for box in (self.bookmarks_bar, self.tools_bar, self.menu_bar,
                    self.scanlines, self.scanlines_anim):
            look_form.addRow("", box)
        lay.addWidget(look)

        nav = QGroupBox("Навигация")
        nav_form = QFormLayout(nav)
        nav_form.addRow("Поисковик", self.engine)
        nav_form.addRow("Домашняя страница", self.home)
        nav_form.addRow("Плитки новой вкладки", self.quick)
        for box in (self.restore, self.dark_sites):
            nav_form.addRow("", box)
        lay.addWidget(nav)

        net = QGroupBox("Приватность и сеть")
        net_form = QFormLayout(net)
        for box in (self.privacy, self.doh, self.dnt):
            net_form.addRow("", box)
        net_form.addRow("User-Agent", self.user_agent)
        net_form.addRow("Прокси (нужен перезапуск)", self.proxy)
        lay.addWidget(net)
        lay.addStretch(1)

        self.button("Применить", self._apply_and_report, primary=True)
        self.button("Закрыть", self.close_page)

    def _apply_and_report(self) -> None:
        self.apply()
        self.applied.emit()

    def apply(self) -> None:
        """Записывает значения в настройки, сохраняет и сигналит окну."""
        s = self.settings
        s.set("theme", self.theme.currentData())
        s.set("search_engine", self.engine.currentData())
        s.set("home_url", self.home.text().strip())
        s.set("show_bookmarks_bar", self.bookmarks_bar.isChecked())
        s.set("show_tools_bar", self.tools_bar.isChecked())
        s.set("show_menu_bar", self.menu_bar.isChecked())
        s.set("restore_session", self.restore.isChecked())
        s.set("scanlines", self.scanlines.isChecked())
        s.set("scanlines_anim", self.scanlines_anim.isChecked())
        s.set("dark_mode_sites", self.dark_sites.isChecked())
        s.set("privacy", self.privacy.isChecked())
        s.set("doh", self.doh.isChecked())
        s.set("quick_links", parse_quick_links(self.quick.toPlainText()))
        s.set("user_agent", self.user_agent.text().strip())
        s.set("proxy", self.proxy.text().strip())
        s.set("dnt", self.dnt.isChecked())
        s.save()


class DownloadsPage(PageBase):
    """Загрузки (hp://downloads) — обновляется по сигналу менеджера."""

    def __init__(self, manager, parent=None):
        super().__init__("Загрузки", f"Файлы сохраняются в: {manager.dir}", parent)
        self.manager = manager
        self.list = QListWidget()
        self.list.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.body.addWidget(self.list, 1)

        self.button("Открыть", self._open)
        self.button("Открыть папку", self._open_folder)
        self.button("Отменить", self._cancel)
        self.button("Очистить", self._clear)
        self.button("Закрыть", self.close_page)

        try:
            manager.changed.connect(self.refresh)
        except (RuntimeError, TypeError):
            pass
        self.refresh()

    def refresh(self) -> None:
        self.list.clear()
        if not self.manager.items:
            self.list.addItem("Загрузок пока нет")
            return
        for entry in self.manager.items:
            total, done = entry["total"], entry["received"]
            progress = f"{int(done * 100 / total)}%" if total else human(done)
            text = f"{entry['name']} — {entry['state']} · {progress}\n{entry['path']}"
            item = QListWidgetItem(text)
            item.setData(Qt.ItemDataRole.UserRole, entry)
            self.list.addItem(item)

    def _current(self) -> dict | None:
        item = self.list.currentItem()
        return item.data(Qt.ItemDataRole.UserRole) if item else None

    def _open(self) -> None:
        entry = self._current()
        if entry and os.path.exists(entry["path"]):
            open_path(entry["path"])

    def _open_folder(self) -> None:
        entry = self._current()
        target = os.path.dirname(entry["path"]) if entry else self.manager.dir
        if os.path.isdir(target):
            open_path(target)

    def _cancel(self) -> None:
        entry = self._current()
        if entry:
            self.manager.cancel(entry)

    def _clear(self) -> None:
        self.manager.clear_finished()
        self.refresh()


class ClearDataPage(PageBase):
    """Очистка данных просмотра (hp://clear-data)."""

    cleared = pyqtSignal(str)

    def __init__(self, browser, parent=None):
        super().__init__("Очистить данные просмотра", "Что удалить:", parent)
        self.browser = browser

        self.history = QCheckBox("История посещений")
        self.bookmarks = QCheckBox("Закладки")
        self.downloads = QCheckBox("Список загрузок")
        self.cache = QCheckBox("Кэш и cookies")
        self.history.setChecked(True)
        self.cache.setChecked(True)
        for box in (self.history, self.bookmarks, self.downloads, self.cache):
            self.body.addWidget(box)
        self.body.addStretch(1)

        self.button("Очистить", self._clear_and_report, primary=True)
        self.button("Закрыть", self.close_page)

    def _clear_and_report(self) -> None:
        self.cleared.emit(self.apply())

    def apply(self) -> str:
        """Удаляет выбранное и возвращает текстовый отчёт."""
        removed: list[str] = []
        win = self.browser
        if self.history.isChecked():
            win.history.clear()
            removed.append("история")
        if self.bookmarks.isChecked():
            win.bookmarks.clear()
            removed.append("закладки")
        if self.downloads.isChecked():
            win.downloads.items.clear()
            removed.append("загрузки")
        if self.cache.isChecked():
            profile = win.private_profile or QWebEngineProfile.defaultProfile()
            profile.clearHttpCache()
            profile.cookieStore().deleteAllCookies()
            removed.append("кэш и cookies")
        win._refresh_sidebar()
        return ", ".join(removed) if removed else "ничего"


class AboutPage(PageBase):
    """О программе (hp://about) — логотип рисуется в моноширинном поле."""

    def __init__(self, parent=None):
        super().__init__(f"О программе — {APP_NAME}", "", parent)
        lay = self.scroll()

        logo = QPlainTextEdit()
        logo.setObjectName("about_logo")
        logo.setReadOnly(True)
        logo.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap)
        logo.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        font = QFontDatabase.systemFont(QFontDatabase.SystemFont.FixedFont)
        font.setPointSize(10)
        logo.setFont(font)
        logo.setPlainText(LOGO_ASCII.rstrip("\n"))
        lines = LOGO_ASCII.count("\n") + 1
        logo.setFixedHeight(logo.fontMetrics().lineSpacing() * lines + 14)
        lay.addWidget(logo)

        info = QLabel(
            f"{APP_NAME} v{APP_VERSION} — {TAGLINE}\n"
            f"by {APP_AUTHOR}, {APP_YEAR}\n\n"
            "Браузер на QtWebEngine: гибкие темы, приватность и "
            "OSINT-инструменты, вкладки-страницы вместо лишних окон.\n"
            f"PyQt6 {PYQT_VERSION_STR} · Qt {QT_VERSION_STR}"
        )
        info.setWordWrap(True)
        info.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        lay.addWidget(info)
        lay.addStretch(1)

        self.button("Закрыть", self.close_page)


class ShortcutsPage(PageBase):
    """Горячие клавиши (hp://shortcuts)."""

    def __init__(self, rows=None, parent=None):
        super().__init__(
            "Горячие клавиши",
            "Те же сочетания продублированы подсказками в меню.",
            parent,
        )
        tree = QTreeWidget()
        tree.setHeaderLabels(["Клавиши", "Действие"])
        tree.setRootIsDecorated(False)
        tree.setAlternatingRowColors(True)
        tree.setEditTriggers(QTreeWidget.EditTrigger.NoEditTriggers)
        tree.setSelectionMode(QAbstractItemView.SelectionMode.NoSelection)
        tree.setColumnWidth(0, 250)
        for keys, hint in (rows if rows is not None else SHORTCUT_HELP):
            QTreeWidgetItem(tree, [keys, hint])
        self.body.addWidget(tree, 1)
        self.button("Закрыть", self.close_page)
