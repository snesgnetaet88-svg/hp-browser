# HP Browser — by hypermarket
"""Импорт и экспорт закладок в формате Netscape Bookmark File (HTML)."""

import html
import os
import re

_ANCHOR_RE = re.compile(r"<a\b(.*?)</a\s*>", re.IGNORECASE | re.DOTALL)
_TAG_RE = re.compile(r"<[^>]*>")


def _is_web_url(url: str) -> bool:
    """Проверяет, что url использует схему http/https/ftp."""
    return url.lower().startswith(("http://", "https://", "ftp://"))


def _attr_value(blob: str, name: str) -> str | None:
    """Возвращает значение атрибута name из фрагмента тега или None."""
    match = re.search(
        rf"""(?<![\w-]){name}\s*=\s*(?:"([^"]*)"|'([^']*)'|([^\s>]+))""",
        blob,
        re.IGNORECASE,
    )
    if not match:
        return None
    for group in match.groups():
        if group is not None:
            return group
    return None


def export_html(path: str, items: list[dict]) -> int:
    """Записывает закладки в HTML-файл (формат Netscape Bookmark File).

    items: список словарей вида {"title": str, "url": str, "added": str|None}.
    Возвращает число записанных закладок.
    Пустые/некорректные url (без http/https/ftp) пропускаются.
    """
    lines = [
        "<!DOCTYPE NETSCAPE-Bookmark-file-1>",
        '<META HTTP-EQUIV="Content-Type" CONTENT="text/html; charset=UTF-8">',
        "<TITLE>Bookmarks</TITLE>",
        "<H1>Bookmarks</H1>",
        "<DL><p>",
    ]
    written = 0
    for item in items:
        url = str(item.get("url") or "").strip()
        if not _is_web_url(url):
            continue
        title = str(item.get("title") or "").strip() or url
        line = f'    <DT><A HREF="{html.escape(url, quote=True)}"'
        added = item.get("added")
        if added:
            line += f' ADD_DATE="{html.escape(str(added), quote=True)}"'
        line += f">{html.escape(title, quote=True)}</A>"
        lines.append(line)
        written += 1
    lines.append("</DL><p>")

    parent = os.path.dirname(os.path.abspath(path))
    os.makedirs(parent, exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines) + "\n")
    return written


def import_html(path: str) -> list[dict]:
    """Читает HTML-файл закладок, возвращает список {"title", "url", "added"}.

    Разбирает теги <A HREF="...">текст</A> регистронезависимо.
    Пропускает javascript: и place:-плейсхолдеры, убирает дубли по url.
    Возвращает [] при ошибке чтения/парсинга.
    """
    try:
        with open(path, encoding="utf-8", errors="replace") as fh:
            text = fh.read()
    except OSError:
        return []

    result: list[dict] = []
    seen: set[str] = set()
    try:
        for match in _ANCHOR_RE.finditer(text):
            blob = match.group(1)
            raw = _attr_value(blob, "href")
            if raw is None:
                continue
            url = html.unescape(raw).strip()
            if not url or url.lower().startswith(("javascript:", "place:")):
                continue
            if url in seen:
                continue
            gt = blob.find(">")
            content = blob[gt + 1:] if gt != -1 else ""
            title = html.unescape(_TAG_RE.sub("", content)).strip() or url
            added = _attr_value(blob, "add_date")
            if added is not None:
                added = html.unescape(added)
            seen.add(url)
            result.append({"title": title, "url": url, "added": added})
    except Exception:  # noqa: BLE001
        return []
    return result
