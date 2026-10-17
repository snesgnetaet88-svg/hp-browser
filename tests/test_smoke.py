#!/usr/bin/env python3
# HP Browser — by hypermarket
"""Дымовые тесты интерфейса (offscreen, без сети).

Запуск:  python3 tests/test_smoke.py
Код возврата 0, если все проверки прошли.
"""

import os
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
_tmp = tempfile.mkdtemp(prefix="hp-test-")
os.environ["HP_BROWSER_CONFIG"] = os.path.join(_tmp, "cfg.json")
os.environ["HP_BROWSER_DATA"] = os.path.join(_tmp, "data")
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt6.QtWidgets import QApplication  # noqa: E402

from core.browser import engine_url, normalize_input  # noqa: E402
from core.privacy import apply_env_flags  # noqa: E402
from core.settings import Settings  # noqa: E402
from ui.startpage import start_html  # noqa: E402
from ui.themes import DEFAULT_THEME, THEMES, qss  # noqa: E402
from ui.window import PRIVATE_WINDOWS, MainWindow  # noqa: E402

settings = Settings()
apply_env_flags(settings)  # флаги QtWebEngine — строго до QApplication
app = QApplication(sys.argv)
win = MainWindow(settings=settings)

CHECKS: list[tuple[str, object]] = []


def check(name):
    def deco(fn):
        CHECKS.append((name, fn))
        return fn
    return deco


@check("темы: список, умолчание и таблица стилей")
def _():
    assert len(THEMES) >= 6, list(THEMES)
    assert DEFAULT_THEME == "classic"
    assert {"hacker", "classic", "classic-dark"} <= set(THEMES)
    assert all("QMainWindow" in qss(theme) for theme in THEMES.values())


@check("стартовая страница: цвета темы, матрица только у хакера")
def _():
    light = start_html(THEMES["classic"], "duckduckgo")
    assert "#ffffff" in light and "rain" not in light
    dark = start_html(THEMES["hacker"], "duckduckgo")
    assert 'id="rain"' in dark and "#000000" in dark


@check("стартовая страница: приватный режим")
def _():
    html = start_html(THEMES["classic"], "duckduckgo", private=True)
    assert "Приватный просмотр" in html and "6e4aa8" in html
    assert "Приватный просмотр" not in start_html(THEMES["classic"], "duckduckgo")


@check("логотип: новый, ровный, есть на стартовой")
def _():
    from html import escape

    from utils.branding import LOGO_ASCII, LOGO_LINES, TAGLINE

    assert 4 <= len(LOGO_LINES) <= 8, LOGO_LINES
    widths = {len(line.rstrip()) for line in LOGO_LINES}
    assert max(widths) - min(widths) <= 12, widths  # ровная надпись
    html = start_html(THEMES["classic"], "duckduckgo")
    assert escape(LOGO_ASCII.rstrip("\n")) in html
    assert TAGLINE in html


@check("поисковики: нормализация и выбор движка")
def _():
    url, is_search = normalize_input("привет мир", "google")
    assert is_search and "google.com" in url
    assert "yandex" in engine_url("yandex", "тест")
    direct, is_search = normalize_input("example.com", "google")
    assert not is_search and direct.startswith("https://")


@check("поисковики: быстрые ключи gh/yt/w")
def _():
    url, is_search = normalize_input("gh hypermarket", "google")
    assert is_search and url.startswith("https://github.com/search?q=")
    assert "hypermarket" in url
    url, is_search = normalize_input("yt котики", "google")
    assert is_search and "youtube.com/results" in url
    url, is_search = normalize_input("w linux", "google")
    assert is_search and "wikipedia.org" in url
    # ключ без запроса — обычная навигация/поиск, не падаем
    url, is_search = normalize_input("gh", "google")
    assert is_search and "google.com" in url


@check("вкладки: добавить и закрыть")
def _():
    before = win.tabs.count()
    win.add_tab()
    assert win.tabs.count() == before + 1
    win.tabs.close_tab(win.tabs.count() - 1)
    assert win.tabs.count() == before


@check("панель навигации: кнопки, иконки, состояние загрузки")
def _():
    bar = win.toolbar
    for name in ("back_btn", "forward_btn", "reload_btn", "home_btn",
                 "bookmark_btn", "downloads_btn", "menu_btn"):
        assert getattr(bar, name).toolTip(), name
    bar.set_loading(True)
    assert "становить" in win.toolbar.reload_btn.toolTip()
    win.toolbar.set_loading(False)
    assert "бновить" in win.toolbar.reload_btn.toolTip()


@check("вкладки сверху над панелью навигации")
def _():
    win.show()
    app.processEvents()
    top_tabs = win.tab_bar.mapToGlobal(win.tab_bar.rect().topLeft()).y()
    top_nav = win.toolbar.mapToGlobal(win.toolbar.rect().topLeft()).y()
    assert top_tabs < top_nav, (top_tabs, top_nav)


@check("панель закладок: переключатель")
def _():
    win.show()
    win.bookmarks_bar.setVisible(False)
    win.toggle_bookmarks_bar()
    assert win.bookmarks_bar.isVisible()
    win.toggle_bookmarks_bar()
    assert not win.bookmarks_bar.isVisible()


@check("меню-гамбургер собрано")
def _():
    titles = [a.text().split("\t")[0].replace("&", "") for a in win.main_menu.actions()]
    for want in ("Новая вкладка", "Загрузки", "Найти на странице", "Настройки", "Выход"):
        assert want in titles, titles


@check("загрузки: страница и список")
def _():
    page = win.show_downloads()
    assert page is not None and page.metaObject().className() == "DownloadsPage"
    assert win.tabs.page_url(page) == "hp://downloads"
    page.manager.items.insert(0, {"item": None, "name": "x.iso", "path": "/tmp/x.iso",
                                  "received": 5, "total": 10, "state": "загружается"})
    page.refresh()
    assert page.list.count() == 1
    page.manager.items.clear()
    # повторное открытие — та же вкладка, не новая
    count_before = win.tabs.count()
    again = win.show_downloads()
    assert again is page and win.tabs.count() == count_before
    page.close_page()
    assert win.tabs.count() == count_before - 1


@check("служебные страницы: открываются вкладками hp://")
def _():
    for kind, cls, url in (
        ("settings", "SettingsPage", "hp://settings"),
        ("clear", "ClearDataPage", "hp://clear-data"),
        ("about", "AboutPage", "hp://about"),
        ("shortcuts", "ShortcutsPage", "hp://shortcuts"),
    ):
        before = win.tabs.count()
        page = win.open_page(kind)
        assert page is not None, kind
        assert type(page).__name__ == cls, kind
        assert win.tabs.page_url(page) == url, kind
        assert win.tabs.count() == before + 1, kind
        assert win.tabs.currentIndex() == win.tabs.count() - 1, kind
        assert win.tabs.widget(win.tabs.currentIndex()) is page, kind
        # дедуп: второй вызов — та же вкладка
        assert win.open_page(kind) is page
        assert win.tabs.count() == before + 1, kind
        page.close_page()
        assert win.tabs.count() == before, kind


@check("о программе: логотип моноширинный и целиком")
def _():
    from PyQt6.QtWidgets import QLabel, QPlainTextEdit

    from utils.branding import LOGO_ASCII

    page = win.open_page("about")
    try:
        logo = page.findChild(QPlainTextEdit, "about_logo")
        assert logo is not None
        assert logo.toPlainText() == LOGO_ASCII.rstrip("\n")
        assert logo.isReadOnly()
        assert logo.lineWrapMode() == QPlainTextEdit.LineWrapMode.NoWrap
        family = logo.font().family().lower()
        assert any(w in family for w in ("mono", "fixed", "courier", "consolas")), family
        info = next(l for l in page.findChildren(QLabel) if "PyQt6" in l.text())
        assert "Qt " in info.text()
    finally:
        page.close_page()


@check("настройки: страница и запись значений")
def _():
    page = win.open_page("settings")
    try:
        page.theme.setCurrentIndex(page.theme.findData("hacker"))
        page.engine.setCurrentIndex(page.engine.findData("google"))
        page.apply()
        assert win.settings.get("theme") == "hacker"
        assert win.settings.get("search_engine") == "google"
        # applied-сигнал окно ловит и переключает тему
        win.open_settings()
        win.apply_theme("classic", persist=True)
    finally:
        if win.tabs.indexOf(page) != -1:
            page.close_page()


@check("смена темы и сохранение")
def _():
    win.apply_theme("nord", persist=True)
    assert win.settings.get("theme") == "nord"
    assert win.theme["name"] == "nord"
    win.apply_theme("classic", persist=True)


@check("масштаб: увеличить, уменьшить, сбросить")
def _():
    win.zoom_reset()
    assert win.current_zoom() == 1.0
    win._refresh_status()
    assert win.zoom_button.text() == "100%"
    win.zoom_in()
    assert win.current_zoom() > 1.0
    win._refresh_status()
    assert win.zoom_button.text().endswith("%") and win.zoom_button.text() != "100%"
    win.zoom_out()
    assert win.current_zoom() == 1.0
    win._refresh_status()
    assert win.zoom_button.text() == "100%"


@check("переключение темы по кругу")
def _():
    win.apply_theme("classic", persist=False)
    win.toggle_theme()
    assert win.theme_name != "classic"
    win.apply_theme("classic", persist=True)


@check("горячие клавиши: приватное окно и настройки")
def _():
    from ui.shortcuts import SHORTCUTS

    combos = {keys for keys, _method in SHORTCUTS}
    assert "Ctrl+Shift+P" in combos
    assert "Ctrl+Shift+T" in combos
    assert "Ctrl+," in combos


@check("вернуть закрытую вкладку (Ctrl+Shift+T)")
def _():
    before = win.tabs.count()
    seen: list[str] = []
    win.tabs.tab_closed.connect(seen.append)
    win.add_tab()
    win.tabs.close_tab(win.tabs.count() - 1)
    assert seen, "сигнал tab_closed не сработал"
    from ui.shortcuts import SHORTCUTS

    assert "Ctrl+Shift+T" in {keys for keys, _m in SHORTCUTS}
    win._closed_tabs.clear()
    win._remember_closed_tab("https://example.com/page")
    win.reopen_closed_tab()
    assert win.tabs.count() == before + 1
    win.tabs.close_tab(win.tabs.count() - 1)
    assert win.tabs.count() == before
    win._closed_tabs.clear()


@check("меню вкладки: дублировать, закрыть другие/справа, звук")
def _():
    base = win.tabs.count()
    win.add_tab()
    win.add_tab()
    win.add_tab()
    assert win.tabs.count() == base + 3
    win.duplicate_tab(1)
    assert win.tabs.count() == base + 4
    win.close_tabs_right(0)
    assert win.tabs.count() == 1
    win.add_tab()
    win.add_tab()
    assert win.tabs.count() == 3
    win.close_other_tabs(1)
    assert win.tabs.count() == 1
    view = win.tabs.view(0)
    assert view is not None
    win.toggle_tab_mute(0)
    assert view.page().isAudioMuted() is True
    win.toggle_tab_mute(0)
    assert view.page().isAudioMuted() is False
    while win.tabs.count() < base:
        win.add_tab()
    while win.tabs.count() > base:
        win.tabs.close_tab(win.tabs.count() - 1)
    assert win.tabs.count() == base


@check("сессия: сохранение и восстановление вкладок")
def _():
    s = win.settings
    original = list(s.get("session_tabs", []) or [])
    before = win.tabs.count()
    s.set("restore_session", True)
    s.set("session_tabs", ["https://example.com/a", "https://example.com/b"])
    win._restore_session()
    assert win.tabs.count() == before + 1
    view = win.current_view()
    assert view is not None and "example.com" in view.url().toString()
    win._save_session()
    saved = s.get("session_tabs", [])
    assert any("example.com" in u for u in saved), saved
    while win.tabs.count() > before:
        win.tabs.close_tab(win.tabs.count() - 1)
    s.set("session_tabs", original)


@check("очистка данных просмотра")
def _():
    win.history.add("https://example.com/x", "X", save=False)
    win.bookmarks.add("X", "https://example.com/x")
    win.downloads.items.clear()
    win.downloads.items.append({"item": None, "name": "x.iso", "path": "/tmp/x.iso",
                                "received": 1, "total": 2, "state": "готово"})
    page = win.open_page("clear")
    try:
        page.history.setChecked(True)
        page.bookmarks.setChecked(True)
        page.downloads.setChecked(True)
        page.cache.setChecked(False)
        done = page.apply()
        assert "история" in done and "кэш" not in done, done
        assert win.history.items == []
        assert win.bookmarks.items == []
        assert win.downloads.items == []
        # сигнал cleared от кнопки «Очистить»
        got: list[str] = []
        page.cleared.connect(got.append)
        page._clear_and_report()
        assert got and "история" in got[0], got
    finally:
        page.close_page()


@check("сайдбар: живой фильтр и удаление из истории")
def _():
    win.bookmarks.add("Пример", "https://example.com/one")
    win.history.add("https://history.example.com/x", "Пример истории", save=False)
    win._refresh_sidebar()
    total_b = win.sidebar.bookmarks_list.count()
    total_h = win.sidebar.history_list.count()
    assert total_b >= 1 and total_h >= 1, (total_b, total_h)
    win.sidebar.filter_edit.setText("zzz-ничего-zzz")
    assert win.sidebar.bookmarks_list.count() == 0
    assert win.sidebar.history_list.count() == 0
    win.sidebar.filter_edit.setText("")
    assert win.sidebar.bookmarks_list.count() == total_b
    assert win.sidebar.history_list.count() == total_h
    win._remove_history("https://history.example.com/x")
    assert all(i.get("url") != "https://history.example.com/x" for i in win.history.items)


@check("приватное окно: отдельный профиль, без истории")
def _():
    private = MainWindow(settings=win.settings, private=True)
    try:
        assert private.private is True
        assert private.private_profile is not None
        assert private.tabs.count() == 1
        view = private.current_view()
        assert view is not None
        assert view.page().profile() is private.private_profile
        before = len(private.history.items)
        private._record_history("https://example.com/secret")
        assert len(private.history.items) == before
        private._refresh_sidebar()
        assert private.sidebar.history_list.count() == 0
    finally:
        private.close()
    assert private not in PRIVATE_WINDOWS


@check("плитки: парсинг, форматирование и рендер на стартовой")
def _():
    from core.browser import DEFAULT_QUICK_LINKS, format_quick_links, parse_quick_links

    parsed = parse_quick_links("Мой | mysite.com\n# коммент\n")
    assert parsed[0]["name"] == "Мой" and parsed[0]["url"] == "https://mysite.com"
    assert format_quick_links([{"name": "X", "url": "https://x"}]) == "X | https://x"
    html = start_html(
        THEMES["classic"], "duckduckgo",
        links=[{"name": "Zed", "url": "https://zed.example"}],
    )
    assert "https://zed.example" in html and "Zed" in html
    assert DEFAULT_QUICK_LINKS


@check("настройки: block_trackers удалён, quick_links добавлен")
def _():
    from core.settings import DEFAULTS

    assert "block_trackers" not in DEFAULTS
    assert isinstance(DEFAULTS.get("quick_links"), list) and DEFAULTS["quick_links"]


@check("загрузки: сохранение и восстановление истории")
def _():
    mgr = win.downloads
    original = list(mgr.items)
    mgr.items = [{"item": None, "name": "a.iso", "path": "/tmp/a.iso",
                  "received": 10, "total": 20, "state": "готово"}]
    mgr._save()
    mgr.items = []
    mgr._load()
    assert len(mgr.items) == 1
    assert mgr.items[0]["name"] == "a.iso" and mgr.items[0]["item"] is None
    mgr.items = original
    mgr._save()


@check("меню: недавно закрытые вкладки")
def _():
    win._closed_tabs = ["https://example.com/1", "https://example.com/2"]
    win._rebuild_recent_menu()
    texts = [a.text() for a in win.recent_menu.actions()]
    assert any("example.com/2" in t for t in texts), texts
    assert "Вернуть все" in texts
    win._closed_tabs = []
    win._rebuild_recent_menu()
    assert win.recent_menu.actions()[-1].text() == "(пусто)"
    win._closed_tabs = []


@check("новая вкладка: target=_blank открывается новой вкладкой")
def _():
    from PyQt6.QtWebEngineCore import QWebEnginePage, QWebEngineProfile
    from PyQt6.QtWebEngineWidgets import QWebEngineView

    from ui.tabs import BrowserPage

    holder = {}

    def opener():
        view = QWebEngineView()
        view.setPage(QWebEnginePage(QWebEngineProfile.defaultProfile(), view))
        holder["view"] = view
        return view

    page = BrowserPage(QWebEngineProfile.defaultProfile(), None, opener)
    returned = page.createWindow(None)
    assert returned is holder["view"].page()


@check("шорткаты: перезагрузка без кэша и DevTools")
def _():
    from ui.shortcuts import SHORTCUTS

    combos = {keys for keys, _m in SHORTCUTS}
    assert "Ctrl+Shift+R" in combos
    assert "F12 | Ctrl+Shift+I" in combos
    assert hasattr(win, "reload_no_cache")
    assert hasattr(win, "open_devtools")
    assert hasattr(win, "export_history")
    # вызов не должен падать
    win.reload_no_cache()
    win.open_devtools()


@check("приватность: флаги прокси и Do Not Track")
def _():
    from core.privacy import chromium_flags

    class S:
        def __init__(self, data):
            self.data = data

        def get(self, key, default=None):
            return self.data.get(key, default)

    base = chromium_flags(S({}))
    assert "--no-sandbox" in base and "--proxy-server" not in base
    withproxy = chromium_flags(S({"proxy": "socks5://127.0.0.1:9050", "dnt": True}))
    assert "--proxy-server=socks5://127.0.0.1:9050" in withproxy


@check("поисковики: расширенный список")
def _():
    from core.browser import SEARCH_ENGINES, engine_url

    for name in ("brave", "startpage", "ecosia", "mojeek"):
        assert name in SEARCH_ENGINES, name
        assert "{query}" in SEARCH_ENGINES[name][1]
    assert "brave.com" in engine_url("brave", "test")


@check("User-Agent: применяется и сбрасывается")
def _():
    from PyQt6.QtWebEngineCore import QWebEngineProfile

    win.settings.set("user_agent", "HP-Test/9.9")
    win.apply_user_agent()
    assert QWebEngineProfile.defaultProfile().httpUserAgent() == "HP-Test/9.9"
    win.settings.set("user_agent", "")
    win.apply_user_agent()
    assert QWebEngineProfile.defaultProfile().httpUserAgent() == win._default_ua


@check("контекстное меню: BrowserView открывает ссылку в новой вкладке")
def _():
    from PyQt6.QtCore import QUrl

    from ui.tabs import BrowserView

    view = win.current_view()
    assert isinstance(view, BrowserView)
    before = win.tabs.count()
    view._open_new(QUrl("https://example.com/ctx"))
    assert win.tabs.count() == before + 1
    win.tabs.close_tab(win.tabs.count() - 1)
    assert win.tabs.count() == before


@check("раскладка: вкладки сверху, панель навигации ниже")
def _():
    from PyQt6.QtCore import Qt

    top = Qt.ToolBarArea.TopToolBarArea
    assert win.toolBarArea(win.tabs_toolbar) == top
    assert win.toolBarArea(win.toolbar) == top
    assert win.tabs_toolbar.geometry().top() < win.toolbar.geometry().top()


@check("раскладка: адресная строка растягивается, меню прижато вправо")
def _():
    win.resize(1200, 800)
    app.processEvents()
    tb = win.toolbar
    assert tb.url_edit.width() > 600, tb.url_edit.width()
    from PyQt6.QtCore import QPoint

    menu_x = tb.menu_btn.mapTo(tb, QPoint(0, 0)).x()
    assert menu_x > tb.width() - 120, (menu_x, tb.width())


@check("меню-гамбургер: пункты в порядке")
def _():
    texts = [a.text() for a in win.main_menu.actions()]
    joined = " | ".join(texts)
    for needle in ("Новая вкладка", "Новое приватное окно", "Загрузки", "Настройки", "Выход"):
        assert needle in joined, needle
    subs = [a.menu().title() for a in win.main_menu.actions() if a.menu()]
    assert any("Тема" in t for t in subs), subs
    assert win.toolbar.menu_btn is not None


@check("стиль вкладок: скругление только сверху, без нижней границы")
def _():
    s = qss(THEMES["classic"])
    assert "border-top-left-radius" in s and "border-top-right-radius" in s
    assert "QTabBar::tab:selected" in s
    seg = s[s.index("QTabBar::tab:selected"):]
    assert "border-bottom: 2px" not in seg[:140], seg[:140]


@check("кнопка новой вкладки «+» на ленте вкладок")
def _():
    assert win.new_tab_btn.text() == "+"
    assert win.new_tab_btn.width() <= 32


@check("безрамочный режим: своя лента вкладок и кнопки окна")
def _():
    from PyQt6.QtCore import Qt

    from ui.frameless import DragToolBar, WindowButtons

    assert win.windowFlags() & Qt.WindowType.FramelessWindowHint
    assert isinstance(win.tabs_toolbar, DragToolBar)
    assert isinstance(win.window_buttons, WindowButtons)
    for btn in (win.window_buttons.min_btn, win.window_buttons.max_btn,
                win.window_buttons.close_btn):
        assert btn.isEnabled()


@check("лента вкладок: берётся переданный QTabBar (пустой «ложен»!)")
def _():
    from PyQt6.QtWidgets import QTabBar

    from ui.tabs import BrowserTabs

    bar = QTabBar()
    assert not bool(bar)  # у QTabBar есть __len__ — пустой он «ложный»
    tabs = BrowserTabs(tab_bar=bar)
    assert tabs.tab_bar is bar
    tabs.add_tab()
    assert bar.count() == 1
    tabs.close_tab(0)


@check("лента вкладок окна: это та же лента, что у BrowserTabs, и она видима")
def _():
    assert win.tabs.tab_bar is win.tab_bar
    assert win.tab_bar.count() >= 1
    assert win.tab_bar.height() > 0


@check("темы: галочки синхронны в меню-баре и гамбургере")
def _():
    actions = win._theme_actions
    assert len(actions) >= 6, sorted(actions)
    assert all(len(acts) >= 2 for acts in actions.values()), \
        {k: len(v) for k, v in actions.items()}
    win.apply_theme("nord", persist=True)
    try:
        for theme_name, acts in actions.items():
            for act in acts:
                assert act.isChecked() == (theme_name == "nord"), \
                    (theme_name, act.text(), act.isChecked())
        # смена через пункт гамбургера — меню-бар обновляется
        hamburger = actions["hacker"][-1]
        hamburger.trigger()
        assert win.theme_name == "hacker"
        for acts in actions.values():
            for act in acts:
                assert act.isChecked() == (acts is actions["hacker"]), \
                    (act.text(), act.isChecked())
    finally:
        win.apply_theme("classic", persist=True)
    for theme_name, acts in actions.items():
        for act in acts:
            assert act.isChecked() == (theme_name == "classic"), act.text()


@check("горячие клавиши: Ctrl+1..9 переключают вкладки")
def _():
    from ui.shortcuts import SHORTCUTS

    combos = {keys for keys, _m in SHORTCUTS}
    digits = {f"Ctrl+{n}" for n in range(1, 10)}
    assert not (combos & digits), combos & digits  # цифры — отдельным циклом
    win.focus_tab(0)
    assert win.tabs.currentIndex() == 0
    while win.tabs.count() < 4:
        win.add_tab()
    win.focus_tab(2)
    assert win.tabs.currentIndex() == 2
    win.focus_tab(8)  # 9 — последняя
    assert win.tabs.currentIndex() == win.tabs.count() - 1
    win.focus_tab(99)  # за пределами — без сдвига
    assert win.tabs.currentIndex() == win.tabs.count() - 1
    # шорткаты установлены на окно
    digits = [s for s in win._shortcuts
              if s.key().toString() in {f"Ctrl+{n}" for n in range(1, 10)}]
    assert len(digits) == 9, len(digits)
    while win.tabs.count() > 1:
        win.tabs.close_tab(win.tabs.count() - 1)
    win.focus_tab(0)


@check("статус: счётчик приватности и строка загрузок")
def _():
    win._update_privacy_button()
    btn = win.tools_bar.privacy_btn
    assert btn.text().startswith("Приватность")
    assert "заблокировано" in btn.toolTip()
    assert btn.width() >= 104
    try:
        guard = win.privacy_guard
        old = guard.blocked_count
        guard.blocked_count = old + 5
        win._update_privacy_button()
        assert "· 5" in btn.text() or str(old + 5) in btn.text(), btn.text()
        guard.blocked_count = old
        win._update_privacy_button()
    except AttributeError:
        pass
    # строка загрузок
    win._on_downloads_changed()
    assert isinstance(win._download_status.text(), str)
    mgr = win.downloads
    original = list(mgr.items)
    mgr.items = [{"item": None, "name": "a.iso", "path": "/tmp/a.iso",
                  "received": 5, "total": 10, "state": "загружается"}]
    win._on_downloads_changed()
    assert "50%" in win._download_status.text(), win._download_status.text()
    mgr.items = [{"item": None, "name": "a.iso", "path": "/tmp/a.iso",
                  "received": 10, "total": 10, "state": "готово"}]
    win._on_downloads_changed()
    assert "готово" in win._download_status.text(), win._download_status.text()
    mgr.items = original
    win._on_downloads_changed()


@check("недавние закладки: подменю в гамбургере")
def _():
    win.bookmarks.add("Недавняя", "https://recent.example/page")
    win._rebuild_recent_bookmarks_menu()
    subs = [a.menu() for a in win.main_menu.actions() if a.menu()]
    recent = next((m for m in subs if "Недавние" in m.title()), None)
    assert recent is not None, [m.title() for m in subs]
    texts = [a.text() for a in recent.actions()]
    tips = [a.toolTip() for a in recent.actions()]
    assert any("Недавняя" in t for t in texts), texts
    assert any("recent.example" in t for t in tips), tips


def main() -> int:
    win.show()
    app.processEvents()
    failed = 0
    for name, fn in CHECKS:
        try:
            fn()
            print(f"  OK   {name}")
        except Exception as exc:  # noqa: BLE001
            failed += 1
            print(f"  ФЕЙЛ {name}: {exc}")
    print(f"\nитог: {len(CHECKS) - failed}/{len(CHECKS)} проверок пройдено")
    return 1 if failed else 0


raise SystemExit(main())
