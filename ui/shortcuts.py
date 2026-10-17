# HP Browser — by hypermarket
"""Горячие клавиши: одна таблица, чтобы окно не разрасталось.

Несколько комбинаций на одно действие разделяются вертикальной чертой.
"""

from PyQt6.QtGui import QKeySequence, QShortcut

SHORTCUTS = (
    ("Ctrl+L", "focus_url"),
    ("Ctrl+T", "new_tab"),
    ("Ctrl+Shift+T", "reopen_closed_tab"),
    ("Ctrl+Shift+P", "open_private_window"),
    ("Ctrl+W", "close_current_tab"),
    ("Ctrl+Tab", "next_tab"),
    ("Ctrl+Shift+Tab", "prev_tab"),
    ("Ctrl+D", "add_bookmark"),
    ("Ctrl+J", "show_downloads"),
    ("Ctrl+Shift+Delete", "clear_data"),
    ("Ctrl+B", "toggle_sidebar"),
    ("Ctrl+F", "find_on_page"),
    ("Ctrl+,", "open_settings"),
    ("F5 | Ctrl+R", "reload_page"),
    ("Ctrl+Shift+R", "reload_no_cache"),
    ("F12 | Ctrl+Shift+I", "open_devtools"),
    ("Esc", "escape_action"),
    ("Ctrl++ | Ctrl+=", "zoom_in"),
    ("Ctrl+-", "zoom_out"),
    ("Ctrl+0", "zoom_reset"),
    ("F11", "toggle_fullscreen"),
    ("F1", "show_shortcuts"),
    ("Alt+Home", "go_home"),
    ("Ctrl+Shift+O", "run_osint"),
    ("Ctrl+Shift+L", "run_leaks"),
)


def _digit_shortcuts(window, made: list) -> None:
    """Ctrl+1..9: вкладки по номеру, 9 — последняя (не входит в SHORTCUTS)."""
    for digit in range(1, 10):
        shortcut = QShortcut(QKeySequence(f"Ctrl+{digit}"), window)
        shortcut.activated.connect(lambda n=digit - 1: window.focus_tab(n))
        made.append(shortcut)


def install(window) -> list[QShortcut]:
    """Ставит клавиши на окно: методы берутся у окна по имени."""
    made = []
    for keys, method in SHORTCUTS:
        handler = getattr(window, method)
        for combo in keys.split(" | "):
            shortcut = QShortcut(QKeySequence(combo), window)
            shortcut.activated.connect(handler)
            made.append(shortcut)
    _digit_shortcuts(window, made)
    return made
