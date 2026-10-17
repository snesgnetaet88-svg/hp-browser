# HP Browser — by hypermarket
"""Панели окна.

Навигация: слева кнопки «назад/вперёд/обновить/домой», по центру адресная
строка, справа — закладка, загрузки и меню. Пиктограммы берутся из
стандартных иконок Qt (не эмодзи), поэтому не зависят от шрифтов.
"""

from PyQt6.QtCore import QStringListModel, Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QCompleter,
    QLineEdit,
    QMenu,
    QPushButton,
    QSizePolicy,
    QStyle,
    QToolBar,
)

SP = QStyle.StandardPixmap

# (атрибут, подсказка, иконка)
NAV_BUTTONS = (
    ("back_btn", "Назад (Alt+Стрелка влево)", SP.SP_ArrowBack),
    ("forward_btn", "Вперёд (Alt+Стрелка вправо)", SP.SP_ArrowForward),
    ("reload_btn", "Обновить (F5 / Ctrl+R)", SP.SP_BrowserReload),
    ("home_btn", "Домашняя страница (Alt+Home)", SP.SP_DirHomeIcon),
)
RIGHT_BUTTONS = (
    ("bookmark_btn", "Добавить в закладки (Ctrl+D)", SP.SP_DialogSaveButton),
    ("downloads_btn", "Загрузки (Ctrl+J)", SP.SP_ArrowDown),
    ("menu_btn", "Меню", SP.SP_TitleBarMenuButton),
)

TOOL_BUTTONS = (
    ("osint_btn", "OSINT", "OSINT по текущему сайту (Ctrl+Shift+O)", 74),
    ("leaks_btn", "Утечки", "Проверить email на утечки (Ctrl+Shift+L)", 74),
    ("security_btn", "Безопасность", "Оценка безопасности сайта", 100),
    ("sniffer_btn", "Сниффер", "Сниффер запросов", 84),
    ("privacy_btn", "Приватность", "Приватность: трекеры, DoH, WebRTC", 104),
)


class NavToolBar(QToolBar):
    """Верхняя панель навигации и адресная строка."""

    go_requested = pyqtSignal(str)
    back_requested = pyqtSignal()
    forward_requested = pyqtSignal()
    reload_requested = pyqtSignal()
    home_requested = pyqtSignal()
    bookmark_requested = pyqtSignal()
    downloads_requested = pyqtSignal()
    menu_requested = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__("Навигация", parent)
        self.setObjectName("nav_toolbar")
        self.setMovable(False)
        self.setIconSize(self.iconSize().scaled(16, 16, Qt.AspectRatioMode.KeepAspectRatio))

        for name, tip, icon in NAV_BUTTONS:
            btn = self._icon_button(tip, icon)
            setattr(self, name, btn)
            self.addWidget(btn)

        self.url_edit = QLineEdit()
        self.url_edit.setObjectName("url_edit")
        self.url_edit.setPlaceholderText("Поиск или адрес")
        self.url_edit.setClearButtonEnabled(True)
        self.url_edit.setMinimumWidth(260)
        self.url_edit.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self._completion_model = QStringListModel([], self)
        completer = QCompleter(self._completion_model, self)
        completer.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        completer.setFilterMode(Qt.MatchFlag.MatchContains)
        completer.setMaxVisibleItems(12)
        completer.setCompletionMode(QCompleter.CompletionMode.PopupCompletion)
        self.url_edit.setCompleter(completer)
        self.addWidget(self.url_edit)

        for name, tip, icon in RIGHT_BUTTONS:
            btn = self._icon_button(tip, icon)
            setattr(self, name, btn)
            self.addWidget(btn)

        self.back_btn.clicked.connect(self.back_requested)
        self.forward_btn.clicked.connect(self.forward_requested)
        self.reload_btn.clicked.connect(self.reload_requested)
        self.home_btn.clicked.connect(self.home_requested)
        self.bookmark_btn.clicked.connect(self.bookmark_requested)
        self.downloads_btn.clicked.connect(self.downloads_requested)
        self.menu_btn.clicked.connect(self.menu_requested)
        self.url_edit.returnPressed.connect(self._emit_go)

        # ПКМ по стрелке — список недавних переходов в эту сторону.
        for btn in (self.back_btn, self.forward_btn):
            btn.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.back_btn.customContextMenuRequested.connect(self._show_back_history)
        self.forward_btn.customContextMenuRequested.connect(self._show_forward_history)

    # --- история переходов по стрелкам ---------------------------------
    def _show_back_history(self) -> None:
        self._show_nav_history(back=True)

    def _show_forward_history(self) -> None:
        self._show_nav_history(back=False)

    def _show_nav_history(self, back: bool) -> None:
        """Выпадающий список истории: −1/−2 — назад, 1/2 — вперёд."""
        window = self.window()
        view = window.current_view() if hasattr(window, "current_view") else None
        if view is None:
            return
        history = view.history()
        current = history.currentItem()
        items = [it for it in history.items() if it is not current]
        if back:
            # ближайший назад — offset −1
            items = sorted((i for i in items if i.offset() < 0), key=lambda i: i.offset(), reverse=True)
            arrow = "←"
        else:
            items = sorted((i for i in items if i.offset() > 0), key=lambda i: i.offset())
            arrow = "→"
        menu = QMenu(self)
        if not items:
            empty = menu.addAction("(истории нет)")
            empty.setEnabled(False)
        for item in items[:15]:
            title = (item.title() or "").strip() or item.url().toString()
            action = menu.addAction(f"{arrow} {title[:70]}")
            action.setToolTip(item.url().toString())
            action.triggered.connect(
                lambda _checked=False, i=item: self._goto_history_item(i)
            )
        btn = self.back_btn if back else self.forward_btn
        menu.exec(btn.mapToGlobal(btn.rect().bottomLeft()))

    def _goto_history_item(self, item) -> None:
        window = self.window()
        view = window.current_view() if hasattr(window, "current_view") else None
        if view is None:
            return
        view.history().goToItem(item)
        if hasattr(window, "_refresh_status"):
            window._refresh_status()

    def _icon_button(self, tip: str, icon) -> QPushButton:
        btn = QPushButton()
        btn.setToolTip(tip)
        btn.setIcon(self.style().standardIcon(icon))
        btn.setFixedSize(32, 30)
        btn.setFlat(True)
        return btn

    def _emit_go(self) -> None:
        self.go_requested.emit(self.url_edit.text())

    def set_completions(self, values: list[str]) -> None:
        """Обновляет подсказки адресной строки (история и закладки)."""
        self._completion_model.setStringList(values)

    def set_url(self, url: str) -> None:
        """Обновляет адресную строку, если она не в фокусе."""
        if not self.url_edit.hasFocus():
            self.url_edit.setText(url)

    def set_loading(self, loading: bool) -> None:
        """Меняет иконку «обновить» на «стоп», пока идёт загрузка."""
        icon = SP.SP_BrowserStop if loading else SP.SP_BrowserReload
        self.reload_btn.setIcon(self.style().standardIcon(icon))
        self.reload_btn.setToolTip("Остановить" if loading else "Обновить (F5 / Ctrl+R)")

    def set_nav_state(self, can_back: bool, can_forward: bool) -> None:
        """Включает/выключает кнопки навигации."""
        self.back_btn.setEnabled(can_back)
        self.forward_btn.setEnabled(can_forward)


class ToolsBar(QToolBar):
    """Нижняя панель: инструменты (OSINT, утечки, безопасность, сниффер, приватность)."""

    osint_requested = pyqtSignal()
    leaks_requested = pyqtSignal()
    security_requested = pyqtSignal()
    # переключаемые кнопки: обработчику нужен признак «нажата»
    sniffer_requested = pyqtSignal(bool)
    privacy_requested = pyqtSignal(bool)

    def __init__(self, parent=None):
        super().__init__("Инструменты", parent)
        self.setObjectName("tools_toolbar")
        self.setMovable(False)

        for name, text, tip, width in TOOL_BUTTONS:
            btn = QPushButton(text)
            btn.setToolTip(tip)
            btn.setFixedWidth(width)
            btn.setCheckable(name in ("sniffer_btn", "privacy_btn"))
            setattr(self, name, btn)
            self.addWidget(btn)

        self.osint_btn.clicked.connect(self.osint_requested)
        self.leaks_btn.clicked.connect(self.leaks_requested)
        self.security_btn.clicked.connect(self.security_requested)
        self.sniffer_btn.clicked.connect(self.sniffer_requested)
        self.privacy_btn.clicked.connect(self.privacy_requested)
