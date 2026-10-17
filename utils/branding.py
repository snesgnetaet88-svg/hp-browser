# HP Browser — by hypermarket
"""Брендинг приложения: имя, версия, автор, лого, домашняя страница."""

APP_NAME = "HP Browser"
APP_VERSION = "1.0.0"
APP_AUTHOR = "hypermarket"
APP_YEAR = 2026
APP_TITLE = f"{APP_NAME} — by {APP_AUTHOR}"
FOOTER = f"{APP_NAME} v{APP_VERSION} | by {APP_AUTHOR}"
TAGLINE = "быстрый · приватный · твой"

HOME_URL = "https://www.google.com"
SEARCH_URL = "https://duckduckgo.com/?q={query}"

# Логотип-надпись «HP BROWSER» (чёткий моноширинный шрифт, big).
LOGO_LINES = (
    " _    _ _____    ____  _____   ______          _______ ______ _____",
    "| |  | |  __ \\  |  _ \\|  __ \\ / __ \\ \\        / / ____|  ____|  __ \\",
    "| |__| | |__) | | |_) | |__) | |  | \\ \\  /\\  / / (___ | |__  | |__) |",
    "|  __  |  ___/  |  _ <|  _  /| |  | |\\ \\/  \\/ / \\___ \\|  __| |  _  /",
    "| |  | | |      | |_) | | \\ \\| |__| | \\  /\\  /  ____) | |____| | \\ \\",
    "|_|  |_|_|      |____/|_|  \\_\\\\____/   \\/  \\/  |_____/|______|_|  \\_\\",
)

LOGO_ASCII = "\n".join(LOGO_LINES) + "\n"
