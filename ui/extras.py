# HP Browser — by hypermarket
"""Дополнительные фишки: режим чтения, тёмная тема сайтов, скриншот, PDF, заметки.

Вынесено в миксин, подключаемый к MainWindow.
"""

import os
from datetime import datetime

from PyQt6.QtCore import QStandardPaths
from PyQt6.QtGui import QFontDatabase
from PyQt6.QtWidgets import QFileDialog, QInputDialog, QMessageBox

from core.notes import Notes
from utils.branding import APP_AUTHOR, APP_NAME, APP_VERSION, APP_YEAR, LOGO_ASCII, TAGLINE

READER_JS = """
(function () {
  var sels = ['article', 'main', '[role=main]', '.post-content', '#content', '.content'];
  var node = null;
  for (var i = 0; i < sels.length; i++) {
    var n = document.querySelector(sels[i]);
    if (n && (n.innerText || '').trim().length > 400) { node = n; break; }
  }
  if (!node) { node = document.body; }
  var raw = (node.innerText || '').split('\\n');
  var parts = [];
  for (var j = 0; j < raw.length; j++) {
    var t = raw[j].trim();
    if (t.length > 1) {
      parts.push('<p>' + t.replace(/&/g, '&amp;').replace(/</g, '&lt;') + '</p>');
    }
  }
  var title = document.title || '';
  document.head.innerHTML = '<title>' + title + '</title>';
  document.body.innerHTML = '<div id="hp-reader"><h1>' + title + '</h1>' + parts.join('') + '</div>';
  document.body.style.cssText =
    'background:#0b0f0b !important;color:#d8f0dc !important;margin:0;padding:6vh 12vw;' +
    'font:17px/1.75 Georgia,serif;';
  var box = document.getElementById('hp-reader');
  if (box) { box.style.maxWidth = '760px'; box.style.margin = '0 auto'; }
  return parts.length;
})()
"""

DARK_CSS = """
(function () {
  if (document.getElementById('hp-dark-sites')) { return 'already'; }
  var st = document.createElement('style');
  st.id = 'hp-dark-sites';
  st.textContent = `
    html, body { background:#101214 !important; color:#d6d6d6 !important; }
    body * { background-color: transparent !important; color:#d6d6d6 !important;
             border-color:#3a3f44 !important; }
    a, a * { color:#5fd0ff !important; }
    img, video { filter: brightness(.85) contrast(1.05); }
    input, textarea, select { background:#1a1d20 !important; color:#e6e6e6 !important; }
  `;
  document.documentElement.appendChild(st);
  return 'ok';
})()
"""


class ExtrasActions:
    """Примесь с дополнительными возможностями браузера."""

    # --- режим чтения ----------------------------------------------------
    def toggle_reader(self) -> None:
        """Упрощает текущую страницу до текста статьи."""
        view = self.current_view()
        if view is None:
            return
        view.page().runJavaScript(READER_JS, self._reader_done)

    def _reader_done(self, result) -> None:
        count = result if isinstance(result, int) else 0
        try:
            self.statusBar().showMessage(f"Режим чтения: параграфов {count}", 4000)
        except RuntimeError:
            return  # окно уже закрыто — показывать некуда

    # --- тёмная тема сайтов ---------------------------------------------
    def toggle_dark_sites(self, checked: bool | None = None) -> None:
        """Включает/выключает тёмную CSS-инъекцию на сайтах."""
        if checked is None:
            self.dark_sites = not getattr(self, "dark_sites", False)
        else:
            self.dark_sites = bool(checked)
        self.settings.set("dark_mode_sites", self.dark_sites)
        self.settings.save()
        if self.dark_sites:
            self.apply_dark_sites()
        else:
            view = self.current_view()
            if view is not None:
                view.page().runJavaScript(
                    "(function(){var e=document.getElementById('hp-dark-sites');"
                    "if(e){e.remove();return 'off';}return 'none';})()"
                )

    def apply_dark_sites(self) -> None:
        """Переинжектит тёмную тему, если она включена."""
        if not getattr(self, "dark_sites", False):
            return
        view = self.current_view()
        if view is None:
            return
        url = view.url().toString()
        if view.url().scheme() in ("http", "https") and "hp-browser.local" not in url:
            view.page().runJavaScript(DARK_CSS)

    # --- скриншот --------------------------------------------------------
    def take_screenshot(self, path: str | None = None) -> str | None:
        """Сохраняет снимок страницы в PNG."""
        view = self.current_view()
        if view is None:
            return None
        if not path:
            default = os.path.join(self._pictures_dir(), self._stamp("screenshot", "png"))
            path, _ = QFileDialog.getSaveFileName(self, "Сохранить скриншот", default, "PNG (*.png)")
        if not path:
            return None
        pixmap = view.grab()
        if pixmap.save(path, "PNG"):
            self.statusBar().showMessage(f"Скриншот сохранён: {path}", 5000)
            return path
        self.statusBar().showMessage("Не удалось сохранить скриншот", 5000)
        return None

    # --- PDF -------------------------------------------------------------
    def save_pdf(self, path: str | None = None) -> str | None:
        """Печатает текущую страницу в PDF."""
        view = self.current_view()
        if view is None:
            return None
        if not path:
            default = os.path.join(self._pictures_dir(), self._stamp("page", "pdf"))
            path, _ = QFileDialog.getSaveFileName(self, "Сохранить PDF", default, "PDF (*.pdf)")
        if not path:
            return None
        view.page().printToPdf(path)
        view.page().pdfPrintingFinished.connect(
            lambda f, ok: self.statusBar().showMessage(
                f"PDF {'сохранён: ' + f if ok else 'не сохранён'}", 5000
            )
        )
        return path

    # --- заметки ---------------------------------------------------------
    def add_note(self) -> None:
        """Добавляет заметку с привязкой к текущему URL."""
        view = self.current_view()
        url = view.url().toString() if view is not None else ""
        text, ok = QInputDialog.getMultiLineText(self, "Новая заметка", "Текст:", "")
        if ok and self.notes.add(text, url):
            self.show_notes()

    def show_notes(self) -> None:
        """Показывает все заметки в панели инструментов."""
        lines = ["Заметки", "=" * 48]
        for i, note in enumerate(self.notes.items):
            lines.append(f"[{i}] {note.get('ts')}  {note.get('url', '')}")
            lines.append(f"    {note.get('text', '')}")
        if len(lines) == 2:
            lines.append("  (заметок пока нет)")
        self.tool_panel.show_panel("Заметки")
        self.tool_panel.set_text("\n".join(lines))

    def export_notes(self) -> None:
        """Экспортирует заметки в JSON-файл."""
        import json
        import os

        from PyQt6.QtWidgets import QFileDialog

        default = os.path.join(os.path.expanduser("~"), "hp-notes.json")
        path, _ = QFileDialog.getSaveFileName(
            self, "Экспорт заметок", default, "JSON (*.json)"
        )
        if not path:
            return
        try:
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, "w", encoding="utf-8") as fh:
                json.dump(self.notes.items, fh, ensure_ascii=False, indent=2)
            self.statusBar().showMessage(f"Заметки экспортированы: {path}", 4000)
        except Exception as exc:
            self.statusBar().showMessage(f"Ошибка экспорта заметок: {exc}", 4000)

    # --- служебное -------------------------------------------------------
    def init_extras(self) -> None:
        """Инициализация состояния доп. функций."""
        self.notes = Notes()
        self.dark_sites = bool(self.settings.get("dark_mode_sites", False))

    def show_about(self) -> None:
        """Открывает страницу «О программе» в вкладке."""
        try:
            self.open_page("about")
            return
        except Exception:  # noqa: BLE001
            pass
        box = QMessageBox(self)
        box.setWindowTitle(f"О программе — {APP_NAME}")
        box.setTextFormat(box.textFormat().PlainText)
        box.setFont(QFontDatabase.systemFont(QFontDatabase.SystemFont.FixedFont))
        box.setText(
            f"{LOGO_ASCII}\n"
            f"{APP_NAME} v{APP_VERSION} — {TAGLINE}\n"
            f"by {APP_AUTHOR}, {APP_YEAR}\n\n"
            "Браузер на QtWebEngine: гибкие темы, приватность и OSINT-инструменты.\n"
            "PyQt6 / Qt 6."
        )
        box.setIcon(QMessageBox.Icon.Information)
        box.exec()

    def report_load_error(self, url: str) -> None:
        """Сообщает о неудачной загрузке страницы (без падения)."""
        self.statusBar().showMessage(f"[x] Не удалось загрузить: {url}", 6000)

    def _pictures_dir(self) -> str:
        base = QStandardPaths.writableLocation(QStandardPaths.StandardLocation.PicturesLocation)
        return base or os.path.expanduser("~")

    @staticmethod
    def _stamp(prefix: str, ext: str) -> str:
        return f"hp-{prefix}-{datetime.now().strftime('%Y%m%d_%H%M%S')}.{ext}"
