# HP Browser — by hypermarket
"""Операции вида: масштаб, поиск по странице, вкладки, полноэкранный режим.

Вынесено в миксин, чтобы окно (window.py) оставалось компактным.
"""

from PyQt6.QtWebEngineCore import QWebEnginePage
from PyQt6.QtWidgets import QMenu, QMessageBox

from utils.branding import APP_NAME

ZOOM_STEP = 0.1
ZOOM_MIN = 0.3
ZOOM_MAX = 3.0

SHORTCUT_HELP = (
    ("Ctrl+L", "перейти в адресную строку"),
    ("Ctrl+T / Ctrl+W", "новая вкладка / закрыть вкладку"),
    ("Ctrl+Shift+T", "вернуть закрытую вкладку"),
    ("Ctrl+Shift+P", "новое приватное окно"),
    ("Ctrl+Tab / Ctrl+Shift+Tab", "следующая / предыдущая вкладка"),
    ("Ctrl+1 … Ctrl+9", "перейти к вкладке 1-8 (9 — последняя)"),
    ("F5 или Ctrl+R", "обновить страницу"),
    ("Ctrl+Shift+R", "перезагрузить без кэша"),
    ("F12 или Ctrl+Shift+I", "инструменты разработчика"),
    ("Esc", "остановить загрузку, закрыть поиск"),
    ("Ctrl+F", "найти на странице"),
    ("Ctrl+D", "добавить в закладки"),
    ("Ctrl+B", "панель закладок и истории"),
    ("Ctrl+J", "загрузки (вкладка)"),
    ("Ctrl+,", "настройки"),
    ("Ctrl+Shift+Delete", "очистить данные просмотра"),
    ("Ctrl+плюс / Ctrl+минус / Ctrl+0", "масштаб страницы"),
    ("Ctrl+Shift+O", "OSINT по текущему сайту"),
    ("Ctrl+Shift+L", "проверить email на утечки"),
    ("Ctrl+Shift+S", "скриншот страницы"),
    ("Ctrl+P", "сохранить страницу в PDF"),
    ("Ctrl+Shift+Y", "сменить тему оформления"),
    ("Alt+Home", "стартовая страница"),
    ("F11", "полноэкранный режим"),
    ("F1", "эта справка"),
)


class ViewOps:
    """Методы-обработчики вида (примесь к MainWindow)."""

    # --- масштаб ---------------------------------------------------------
    def current_zoom(self) -> float:
        """Текущий масштаб страницы."""
        try:
            return float(self.settings.get("zoom", 1.0))
        except (TypeError, ValueError):
            return 1.0

    def _set_zoom(self, value: float) -> None:
        value = max(ZOOM_MIN, min(ZOOM_MAX, round(value, 2)))
        self.settings.set("zoom", value)
        self.settings.save()
        for view in self.tabs.views():
            view.setZoomFactor(value)
        self._refresh_status()

    def zoom_in(self) -> None:
        self._set_zoom(self.current_zoom() + ZOOM_STEP)

    def zoom_out(self) -> None:
        self._set_zoom(self.current_zoom() - ZOOM_STEP)

    def zoom_reset(self) -> None:
        self._set_zoom(1.0)

    # --- поиск по странице ------------------------------------------------
    def find_on_page(self) -> None:
        """Открывает панель поиска по странице."""
        self.find_bar.activate()

    def _find(self, text: str, backward: bool = False) -> None:
        view = self.current_view()
        if view is None:
            return
        if not text:
            view.findText("")
            self.find_bar.set_status("")
            return
        flags = QWebEnginePage.FindFlag.FindBackward if backward else QWebEnginePage.FindFlag(0)
        view.findText(text, flags, self._report_matches)

    def _report_matches(self, result) -> None:
        """Показывает число совпадений (Qt 6 отдаёт объект QWebEngineFindTextResult)."""
        if hasattr(result, "numberOfMatches"):
            total = result.numberOfMatches()
            current = result.activeMatch()
        else:
            total, current = int(result or 0), 0
        if not total:
            self.find_bar.set_status("не найдено")
        elif current:
            self.find_bar.set_status(f"{current} из {total}")
        else:
            self.find_bar.set_status(f"совпадений: {total}")

    def find_next(self, text: str) -> None:
        self._find(text)

    def find_prev(self, text: str) -> None:
        self._find(text, backward=True)

    def close_find(self) -> None:
        """Закрывает панель поиска и снимает подсветку."""
        view = self.current_view()
        if view is not None:
            view.findText("")
        self.find_bar.set_status("")
        self.find_bar.hide()

    # --- вкладки -----------------------------------------------------------
    def new_tab(self) -> None:
        self.add_tab()

    def close_current_tab(self) -> None:
        index = self.tabs.currentIndex()
        if index != -1:
            self.tabs.close_tab(index)

    def next_tab(self) -> None:
        self._cycle_tab(1)

    def prev_tab(self) -> None:
        self._cycle_tab(-1)

    def _cycle_tab(self, step: int) -> None:
        count = self.tabs.count()
        if count > 1:
            self.tabs.setCurrentIndex((self.tabs.currentIndex() + step) % count)

    def focus_tab(self, index: int) -> None:
        """Ctrl+1..9: переключает вкладку по номеру (9 — последняя)."""
        if index == 8:
            index = self.tabs.count() - 1
        if 0 <= index < self.tabs.count():
            self.tabs.setCurrentIndex(index)
            self._refresh_status()

    # --- контекстное меню вкладки -----------------------------------------
    def show_tab_menu(self, pos) -> None:
        """Правый клик по вкладке: дублировать, закрыть другие/справа, звук."""
        index = self.tab_bar.tabAt(pos)
        if index < 0:
            return
        view = self.tabs.view(index)
        muted = bool(view is not None and view.page().isAudioMuted())
        menu = QMenu(self)
        menu.addAction("Обновить вкладку", lambda: self.reload_tab(index))
        menu.addAction("Дублировать вкладку", lambda: self.duplicate_tab(index))
        menu.addSeparator()
        menu.addAction(
            "Включить звук" if muted else "Выключить звук",
            lambda: self.toggle_tab_mute(index),
        )
        menu.addSeparator()
        menu.addAction("Закрыть вкладку", lambda: self.tabs.close_tab(index))
        menu.addAction("Закрыть другие вкладки", lambda: self.close_other_tabs(index))
        menu.addAction("Закрыть вкладки справа", lambda: self.close_tabs_right(index))
        menu.exec(self.tab_bar.mapToGlobal(pos))

    def reload_tab(self, index: int) -> None:
        view = self.tabs.view(index)
        if view is not None:
            view.reload()

    def duplicate_tab(self, index: int) -> None:
        view = self.tabs.view(index)
        url = view.url().toString() if view is not None else ""
        self.add_tab(url)

    def close_other_tabs(self, index: int) -> None:
        for i in range(self.tabs.count() - 1, -1, -1):
            if i != index:
                self.tabs.close_tab(i)

    def close_tabs_right(self, index: int) -> None:
        for i in range(self.tabs.count() - 1, index, -1):
            self.tabs.close_tab(i)

    def toggle_tab_mute(self, index: int) -> None:
        """Включает/выключает звук вкладки."""
        view = self.tabs.view(index)
        if view is None:
            return
        muted = not view.page().isAudioMuted()
        view.page().setAudioMuted(muted)
        self.statusBar().showMessage(
            "Вкладка без звука" if muted else "Звук вкладки включён", 3000
        )

    def focus_url(self) -> None:
        """Ставит курсор в адресную строку и выделяет текст."""
        self.toolbar.url_edit.setFocus()
        self.toolbar.url_edit.selectAll()

    # --- навигация и режим -------------------------------------------------
    def reload_page(self) -> None:
        view = self.current_view()
        if view is not None:
            view.reload()

    def reload_no_cache(self) -> None:
        """Перезагружает страницу без кэша."""
        view = self.current_view()
        if view is None:
            return
        profile = view.page().profile()
        if hasattr(profile, "clearHttpCache"):
            profile.clearHttpCache()
        view.reload()

    def open_devtools(self) -> None:
        """Открывает инструменты разработчика (F12)."""
        view = self.current_view()
        if view is None:
            return
        page = view.page()
        try:
            page.triggerAction(QWebEnginePage.WebAction.InspectElement)
        except Exception:
            pass

    def stop_page(self) -> None:
        view = self.current_view()
        if view is not None:
            view.stop()

    def escape_action(self) -> None:
        """Esc: закрыть поиск, иначе остановить загрузку."""
        if self.find_bar.isVisible():
            self.close_find()
            return
        self.stop_page()

    def toggle_fullscreen(self) -> None:
        """F11: полный экран."""
        if self.isFullScreen():
            self.showNormal()
        else:
            self.showFullScreen()

    # --- оформление --------------------------------------------------------
    def toggle_scanlines(self) -> None:
        """Включает/выключает сканлайны."""
        state = not self.scanlines.isVisible()
        self.scanlines.set_active(state)
        self.settings.set("scanlines", state)
        self.settings.save()
        self.statusBar().showMessage(f"Сканлайны: {'вкл' if state else 'выкл'}", 3000)

    def toggle_scanline_anim(self) -> None:
        """Включает/выключает бегущую полосу свечения."""
        state = not bool(self.settings.get("scanlines_anim", False))
        self.settings.set("scanlines_anim", state)
        self.settings.save()
        self.scanlines.set_animated(state)
        self.statusBar().showMessage(
            f"Анимация сканлайнов: {'вкл' if state else 'выкл'}", 3000
        )

    def show_shortcuts(self) -> None:
        """F1: список горячих клавиш."""
        try:
            if hasattr(self, "open_page"):
                self.open_page("shortcuts")
                return
        except Exception:  # noqa: BLE001
            pass
        rows = "\n".join(f"{keys:<30} {hint}" for keys, hint in SHORTCUT_HELP)
        QMessageBox.information(self, f"{APP_NAME} — горячие клавиши", rows)
