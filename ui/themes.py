# HP Browser — by hypermarket
"""Темы оформления.

Тема — это словарь с палитрой. Все темы лежат в THEMES и доступны
пользователю из меню «Вид → Тема». Тема по умолчанию — светлая
классическая. Хакерская (чёрный+зелёный) — просто одна из доступных тем.
"""

_BASE = {
    "dark": False,
    "bg": "#ffffff",
    "panel": "#f9f9fb",
    "fg": "#15141a",
    "muted": "#5b5b66",
    "border": "#cfcfd8",
    "accent": "#0060df",
    "accent_fg": "#ffffff",
    "url_bg": "#ffffff",
    "tab_bg": "#f0f0f4",
    "tab_active_bg": "#ffffff",
    "tab_active_fg": "#15141a",
    "tab_hover": "#e6e6ec",
    "status_bg": "#f9f9fb",
}


def make_theme(name: str, label: str, **palette) -> dict:
    """Собирает тему: базовые значения + переопределения палитры."""
    theme = dict(_BASE)
    theme.update(palette)
    theme["name"] = name
    theme["label"] = label
    return theme


CLASSIC = make_theme(
    "classic", "Классическая (светлая)",
    dark=False,
    bg="#ffffff", panel="#f9f9fb", fg="#15141a", muted="#5b5b66",
    border="#cfcfd8", accent="#0060df", accent_fg="#ffffff",
    url_bg="#ffffff", tab_bg="#f9f9fb", tab_active_bg="#ffffff",
    tab_active_fg="#15141a", tab_hover="#e6e6ec", status_bg="#f9f9fb",
)

CLASSIC_DARK = make_theme(
    "classic-dark", "Классическая (тёмная)",
    dark=True,
    bg="#1c1b22", panel="#2b2a33", fg="#fbfbfe", muted="#bfbfc9",
    border="#52525e", accent="#00ddff", accent_fg="#1c1b22",
    url_bg="#2b2a33", tab_bg="#2b2a33", tab_active_bg="#42414d",
    tab_active_fg="#fbfbfe", tab_hover="#3a3944", status_bg="#2b2a33",
)

HACKER = make_theme(
    "hacker", "Хакерская",
    dark=True,
    bg="#000000", panel="#050a06", fg="#00ff66", muted="#0a9a4f",
    border="#00994d", accent="#00ff66", accent_fg="#001a0d",
    url_bg="#030804", tab_bg="#04120a", tab_active_bg="#072a15",
    tab_active_fg="#00ff66", tab_hover="#062114", status_bg="#050a06",
)

COMFORT = make_theme(
    "comfort", "Комфортная",
    dark=True,
    bg="#1e1e1e", panel="#2a2a2a", fg="#e8e8e8", muted="#9a9a9a",
    border="#3c3c3c", accent="#ff8c1a", accent_fg="#1e1e1e",
    url_bg="#262626", tab_bg="#2a2a2a", tab_active_bg="#3a3a3a",
    tab_active_fg="#ffb066", tab_hover="#333333", status_bg="#2a2a2a",
)

NORD = make_theme(
    "nord", "Nord",
    dark=True,
    bg="#2e3440", panel="#3b4252", fg="#eceff4", muted="#a7b1c2",
    border="#4c566a", accent="#88c0d0", accent_fg="#2e3440",
    url_bg="#333b48", tab_bg="#343c4a", tab_active_bg="#434c5e",
    tab_active_fg="#eceff4", tab_hover="#3f4857", status_bg="#3b4252",
)

SOLARIZED = make_theme(
    "solarized", "Solarized (светлая)",
    dark=False,
    bg="#fdf6e3", panel="#eee8d5", fg="#073642", muted="#657b83",
    border="#d9d2bd", accent="#268bd2", accent_fg="#ffffff",
    url_bg="#fffdf5", tab_bg="#eee8d5", tab_active_bg="#fdf6e3",
    tab_active_fg="#073642", tab_hover="#e4ddc8", status_bg="#eee8d5",
)

DARK = make_theme(
    "classic-dark", "Классическая (тёмная)",
    dark=True,
    bg="#1c1b22", panel="#2b2a33", fg="#fbfbfe", muted="#bfbfc9",
    border="#52525e", accent="#00ddff", accent_fg="#1c1b22",
    url_bg="#2b2a33", tab_bg="#2b2a33", tab_active_bg="#42414d",
    tab_active_fg="#fbfbfe", tab_hover="#3a3944", status_bg="#2b2a33",
)

HACKER = make_theme(
    "hacker", "Хакерская",
    dark=True,
    bg="#000000", panel="#050a06", fg="#00ff66", muted="#0a9a4f",
    border="#00994d", accent="#00ff66", accent_fg="#001a0d",
    url_bg="#030804", tab_bg="#04120a", tab_active_bg="#072a15",
    tab_active_fg="#00ff66", tab_hover="#062114", status_bg="#050a06",
)

COMFORT = make_theme(
    "comfort", "Комфортная",
    dark=True,
    bg="#1e1e1e", panel="#2a2a2a", fg="#e8e8e8", muted="#9a9a9a",
    border="#3c3c3c", accent="#ff8c1a", accent_fg="#1e1e1e",
    url_bg="#262626", tab_bg="#2a2a2a", tab_active_bg="#3a3a3a",
    tab_active_fg="#ffb066", tab_hover="#333333", status_bg="#2a2a2a",
)

NORD = make_theme(
    "nord", "Nord",
    dark=True,
    bg="#2e3440", panel="#3b4252", fg="#eceff4", muted="#a7b1c2",
    border="#4c566a", accent="#88c0d0", accent_fg="#2e3440",
    url_bg="#333b48", tab_bg="#343c4a", tab_active_bg="#434c5e",
    tab_active_fg="#eceff4", tab_hover="#3f4857", status_bg="#3b4252",
)

SOLARIZED = make_theme(
    "solarized", "Solarized (светлая)",
    dark=False,
    bg="#fdf6e3", panel="#eee8d5", fg="#073642", muted="#657b83",
    border="#d9d2bd", accent="#268bd2", accent_fg="#ffffff",
    url_bg="#fffdf5", tab_bg="#eee8d5", tab_active_bg="#fdf6e3",
    tab_active_fg="#073642", tab_hover="#e4ddc8", status_bg="#eee8d5",
)

DARK = make_theme(
    "dark", "Тёмная",
    dark=True,
    bg="#1c1c1c", panel="#2b2b2b", fg="#f0f0f0", muted="#a0a0aa",
    border="#4a4a52", accent="#0a84ff", accent_fg="#ffffff",
    url_bg="#212121", tab_bg="#2b2b2b", tab_active_bg="#3f3f46",
    tab_active_fg="#ffffff", tab_hover="#35353a", status_bg="#2b2b2b",
)

DARK = make_theme(
    "dark", "Тёмная",
    dark=True,
    bg="#1c1c1c", panel="#2b2b2b", fg="#f0f0f0", muted="#a0a0aa",
    border="#4a4a52", accent="#0a84ff", accent_fg="#ffffff",
    url_bg="#212121", tab_bg="#2b2b2b", tab_active_bg="#3f3f46",
    tab_active_fg="#ffffff", tab_hover="#35353a", status_bg="#2b2b2b",
)

THEMES = {
    t["name"]: t
    for t in (CLASSIC, CLASSIC_DARK, HACKER, COMFORT, NORD, SOLARIZED, DARK)
}
DEFAULT_THEME = "classic"


def qss(theme: dict) -> str:
    """Собирает таблицу стилей Qt из палитры темы (плоский классический стиль)."""
    c = theme
    return f"""
    QMainWindow, QDialog {{ background: {c['bg']}; color: {c['fg']}; }}
    QWidget {{ color: {c['fg']}; }}
    QToolBar {{ background: {c['panel']}; border: 0; spacing: 2px; padding: 3px 6px; }}
    QToolBar#tabs_toolbar {{ padding: 5px 8px 0 8px; spacing: 2px; }}
    QToolBar#bookmarks_bar {{ padding: 2px 6px; }}
    QToolBar::separator {{ background: {c['border']}; width: 1px; margin: 5px 4px; }}
    QLineEdit {{ background: {c['url_bg']}; color: {c['fg']}; border: 1px solid {c['border']};
                 border-radius: 8px; padding: 6px 12px; min-height: 20px;
                 selection-background-color: {c['accent']};
                 selection-color: {c['accent_fg']}; }}
    QLineEdit:hover {{ border: 1px solid {c['muted']}; }}
    QLineEdit:focus {{ border: 1px solid {c['accent']}; }}
    QPushButton {{ background: transparent; color: {c['fg']}; border: 1px solid transparent;
                   border-radius: 6px; padding: 4px 8px; }}
    QPushButton:hover {{ background: {c['tab_hover']}; }}
    QPushButton:pressed {{ background: {c['border']}; }}
    QPushButton:checked {{ background: {c['accent']}; color: {c['accent_fg']}; }}
    QToolButton {{ background: transparent; color: {c['fg']}; border: 0; border-radius: 6px;
                   padding: 5px 7px; }}
    QToolButton:hover {{ background: {c['tab_hover']}; }}
    QToolButton:pressed, QToolButton:checked {{ background: {c['border']}; }}
    QTabWidget::pane {{ border: 0; }}
    QTabBar {{ background: {c['panel']}; }}
    QTabBar::tab {{ background: {c['tab_bg']}; color: {c['muted']}; padding: 7px 10px;
                    margin: 3px 1px 0 1px; border: 0;
                    border-top-left-radius: 7px; border-top-right-radius: 7px;
                    border-bottom-left-radius: 0; border-bottom-right-radius: 0;
                    min-width: 76px; max-width: 225px; }}
    QTabBar::tab:hover {{ background: {c['tab_hover']}; color: {c['fg']}; }}
    QTabBar::tab:selected {{ background: {c['tab_active_bg']}; color: {c['tab_active_fg']}; }}
    QTabBar::close-button {{ background: transparent; }}
    QTabBar::close-button:hover {{ background: {c['tab_hover']}; }}

    QPushButton#new_tab_btn:hover {{ background: {c['tab_hover']}; }}
    QPushButton#win_btn {{ background: transparent; color: {c['muted']}; border: 0;
                           border-radius: 6px; padding: 0; font-size: 12px; }}
    QPushButton#win_btn:hover {{ background: {c['tab_hover']}; color: {c['fg']}; }}
    QPushButton#win_close {{ background: transparent; color: {c['muted']}; border: 0;
                             border-radius: 6px; padding: 0; font-size: 12px; }}
    QPushButton#win_close:hover {{ background: #e81123; color: #ffffff; }}
    QListWidget, QTreeWidget, QTableWidget, QPlainTextEdit {{
        background: {c['bg']}; color: {c['fg']}; border: 1px solid {c['border']}; border-radius: 4px; }}
    QStatusBar {{ background: {c['status_bg']}; color: {c['muted']}; }}
    QMenuBar, QMenu {{ background: {c['panel']}; color: {c['fg']}; border: 1px solid {c['border']}; }}
    QMenuBar::item:selected, QMenu::item:selected {{ background: {c['accent']}; color: {c['accent_fg']}; }}
    QSplitter::handle {{ background: {c['border']}; }}
    QProgressBar {{ border: 1px solid {c['border']}; background: {c['panel']}; text-align: center;
                    color: {c['fg']}; border-radius: 3px; }}
    QProgressBar::chunk {{ background: {c['accent']}; border-radius: 2px; }}
    QScrollBar:vertical {{ background: {c['panel']}; width: 12px; margin: 0; }}
    QScrollBar::handle:vertical {{ background: {c['border']}; border-radius: 5px; min-height: 24px; }}
    QScrollBar::handle:vertical:hover {{ background: {c['muted']}; }}
    QScrollBar::add-line, QScrollBar::sub-line {{ height: 0; }}
    QLabel#private_badge {{ background: #6e4aa8; color: #ffffff; border-radius: 8px;
                            padding: 1px 8px; margin: 2px; font-weight: bold; }}
    QLabel#page_title {{ font-size: 18px; font-weight: 600; }}
    QLabel#page_hint {{ color: {c['muted']}; }}
    QLabel#page_label {{ color: {c['muted']}; }}
    QWidget#page_box {{ border: 1px solid {c['border']}; border-radius: 8px; }}
    QGroupBox {{ border: 1px solid {c['border']}; border-radius: 6px; margin-top: 12px;
                 padding-top: 6px; }}
    QGroupBox::title {{ subcontrol-origin: margin; left: 8px; padding: 0 4px;
                        color: {c['muted']}; }}
    QCheckBox {{ spacing: 6px; }}
    QCheckBox:disabled, QLabel:disabled, QPushButton:disabled {{ color: {c['muted']}; }}
    """
