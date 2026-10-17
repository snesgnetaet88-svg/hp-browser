# HP Browser — by hypermarket
"""Настройки приложения: чтение и запись config.json."""

import json
import os

from core.browser import DEFAULT_QUICK_LINKS

def _config_dir() -> str:
    """Каталог настроек: %APPDATA% на Windows, ~/.config на остальных."""
    if os.name == "nt":
        base = os.environ.get("APPDATA") or os.path.expanduser("~")
        return os.path.join(base, "hp-browser")
    return os.path.join(os.path.expanduser("~"), ".config", "hp-browser")


def _data_dir() -> str:
    """Каталог данных: %LOCALAPPDATA% на Windows, ~/.local/share на остальных."""
    if os.name == "nt":
        base = os.environ.get("LOCALAPPDATA") or os.environ.get("APPDATA") or os.path.expanduser("~")
        return os.path.join(base, "hp-browser")
    return os.path.join(os.path.expanduser("~"), ".local", "share", "hp-browser")


APP_DIR = _config_dir()
CONFIG_PATH = os.path.join(APP_DIR, "config.json")
DATA_DIR = os.environ.get("HP_BROWSER_DATA") or _data_dir()

DEFAULTS = {
    "theme": "classic",
    "home_url": "",
    "search_engine": "duckduckgo",
    "show_bookmarks_bar": False,
    "show_tools_bar": False,
    "show_menu_bar": False,
    "scanlines": False,
    "scanlines_anim": False,
    "dark_mode_sites": False,
    "privacy": False,
    "doh": False,
    "zoom": 1.0,
    "restore_session": True,
    "session_tabs": [],
    "quick_links": [dict(item) for item in DEFAULT_QUICK_LINKS],
    "user_agent": "",
    "proxy": "",
    "dnt": False,
}


class Settings:
    """Простое JSON-хранилище настроек."""

    def __init__(self, path: str | None = None):
        self.path = path or os.environ.get("HP_BROWSER_CONFIG") or CONFIG_PATH
        self.data = dict(DEFAULTS)
        self.load()

    def load(self) -> None:
        """Читает настройки с диска, игнорируя ошибки."""
        try:
            with open(self.path, encoding="utf-8") as fh:
                stored = json.load(fh)
            if isinstance(stored, dict):
                self.data.update(stored)
        except (OSError, ValueError):
            pass

    def save(self) -> bool:
        """Сохраняет настройки на диск."""
        try:
            os.makedirs(os.path.dirname(self.path), exist_ok=True)
            with open(self.path, "w", encoding="utf-8") as fh:
                json.dump(self.data, fh, ensure_ascii=False, indent=2)
            return True
        except OSError:
            return False

    def get(self, key: str, default=None):
        return self.data.get(key, DEFAULTS.get(key, default))

    def set(self, key: str, value) -> None:
        self.data[key] = value
