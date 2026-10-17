# HP Browser — by hypermarket
"""Логика браузера: нормализация ввода, определение URL, поиск."""

import re
from urllib.parse import quote_plus

# (подпись, шаблон). {query} подставляется закодированным запросом.
SEARCH_ENGINES = {
    "duckduckgo": ("DuckDuckGo", "https://duckduckgo.com/?q={query}"),
    "google": ("Google", "https://www.google.com/search?q={query}"),
    "bing": ("Bing", "https://www.bing.com/search?q={query}"),
    "yandex": ("Яндекс", "https://yandex.ru/search/?text={query}"),
    "wikipedia": ("Wikipedia", "https://ru.wikipedia.org/w/index.php?search={query}"),
    "brave": ("Brave", "https://search.brave.com/search?q={query}"),
    "startpage": ("Startpage", "https://www.startpage.com/sp/search?query={query}"),
    "ecosia": ("Ecosia", "https://www.ecosia.org/search?q={query}"),
    "mojeek": ("Mojeek", "https://www.mojeek.com/search?q={query}"),
}
DEFAULT_ENGINE = "duckduckgo"

# Быстрые «ключи» перед запросом (как смарт-ключи в браузерах):
# «gh hypermarket» ищет на GitHub, «yt котики» — на YouTube и т.д.
KEYWORDS = {
    "g": ("Google", "https://www.google.com/search?q={query}"),
    "google": ("Google", "https://www.google.com/search?q={query}"),
    "ddg": ("DuckDuckGo", "https://duckduckgo.com/?q={query}"),
    "b": ("Bing", "https://www.bing.com/search?q={query}"),
    "y": ("Яндекс", "https://yandex.ru/search/?text={query}"),
    "w": ("Wikipedia", "https://ru.wikipedia.org/w/index.php?search={query}"),
    "gh": ("GitHub", "https://github.com/search?q={query}"),
    "yt": ("YouTube", "https://www.youtube.com/results?search_query={query}"),
    "maps": ("Карты", "https://www.openstreetmap.org/search?query={query}"),
}

# Плитки быстрых ссылок на стартовой странице по умолчанию.
# Редактируются в настройках (см. parse_quick_links/format_quick_links).
DEFAULT_QUICK_LINKS = [
    {"name": "GitHub", "url": "https://github.com"},
    {"name": "Arch Linux", "url": "https://archlinux.org"},
    {"name": "DuckDuckGo", "url": "https://duckduckgo.com"},
    {"name": "Wikipedia", "url": "https://wikipedia.org"},
    {"name": "OpenCode", "url": "https://opencode.ai"},
]

_SCHEME_RE = re.compile(r"^(https?|ftp)://", re.I)
_HOST_RE = re.compile(r"^[\w-]+(\.[\w-]+)+(:\d+)?(/.*)?$", re.I)


def engine_url(engine: str, text: str) -> str:
    """Собирает поисковый адрес для выбранного поисковика."""
    _label, template = SEARCH_ENGINES.get(engine, SEARCH_ENGINES[DEFAULT_ENGINE])
    return template.format(query=quote_plus(text))


def looks_like_url(text: str) -> bool:
    """Эвристика: похоже ли на адрес, а не на поисковый запрос."""
    text = (text or "").strip()
    if not text or " " in text:
        return False
    if _SCHEME_RE.match(text):
        return True
    if text.startswith("localhost") or text.startswith("127."):
        return True
    return bool(_HOST_RE.match(text))


def normalize_input(text: str, engine: str = DEFAULT_ENGINE) -> tuple[str, bool]:
    """Превращает ввод в адрес; иначе — поисковый запрос.

    Поддерживает быстрые ключи: «gh hypermarket», «yt котики», «w linux».
    Возвращает (url, был_ли_поиск).
    """
    text = (text or "").strip()
    if not text:
        return "", False
    if looks_like_url(text):
        return (text if _SCHEME_RE.match(text) else f"https://{text}"), False
    head, _, rest = text.partition(" ")
    entry = KEYWORDS.get(head.lower())
    if entry and rest.strip():
        return entry[1].format(query=quote_plus(rest.strip())), True
    return engine_url(engine, text), True


def parse_quick_links(text: str) -> list[dict]:
    """Разбирает список плиток стартовой страницы.

    Формат строки: «Название | https://адрес» (или через «=»).
    Пустые строки и строки с «#» игнорируются.
    """
    result: list[dict] = []
    for line in (text or "").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if "|" in line:
            name, url = line.split("|", 1)
        elif "=" in line:
            name, url = line.split("=", 1)
        else:
            name, url = line, line
        name, url = name.strip(), url.strip()
        if not url:
            continue
        if not _SCHEME_RE.match(url):
            url = f"https://{url}"
        result.append({"name": name or url, "url": url})
    return result


def format_quick_links(links: list[dict]) -> str:
    """Готовит список плиток к редактированию в настройках."""
    return "\n".join(f"{item.get('name', '')} | {item.get('url', '')}" for item in links)
