#!/usr/bin/env python3
# HP Browser — by hypermarket
"""Тесты импорта/экспорта закладок (Netscape Bookmark File).

Запуск:  python3 tests/test_bookmarks_io.py
Код возврата 0, если все проверки прошли.
"""

import os
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from core.bookmarks_io import export_html, import_html  # noqa: E402

TMP = tempfile.mkdtemp(prefix="hp-bookmarks-")
CHECKS: list[tuple[str, object]] = []


def check(name):
    def deco(fn):
        CHECKS.append((name, fn))
        return fn
    return deco


def _path(name: str) -> str:
    return os.path.join(TMP, name)


@check("экспорт → импорт: данные совпадают")
def _():
    items = [
        {"title": "Example", "url": "https://example.com", "added": "1700000000"},
        {"title": "Почта", "url": "https://mail.example.com/inbox", "added": None},
    ]
    assert export_html(_path("round.html"), items) == 2
    back = import_html(_path("round.html"))
    assert len(back) == 2, back
    assert back[0]["title"] == "Example" and back[0]["url"] == "https://example.com"
    assert back[0]["added"] == "1700000000"
    assert back[1]["title"] == "Почта" and back[1]["url"] == "https://mail.example.com/inbox"
    assert back[1]["added"] is None


@check("экранирование спецсимволов в title")
def _():
    title = 'a < b & c "d" \'e\''
    export_html(_path("escape.html"), [{"title": title, "url": "https://e.com/?a=1&b=2"}])
    with open(_path("escape.html"), encoding="utf-8") as fh:
        raw = fh.read()
    assert "&lt;" in raw and "&amp;" in raw and "&quot;" in raw and "&#x27;" in raw
    back = import_html(_path("escape.html"))
    assert back[0]["title"] == title, back
    assert back[0]["url"] == "https://e.com/?a=1&b=2"


@check("пропуск некорректных url и дублей")
def _():
    items = [
        {"title": "ok", "url": "https://ok.com", "added": None},
        {"title": "bad", "url": "", "added": None},
        {"title": "js", "url": "javascript:alert(1)", "added": None},
        {"title": "plain", "url": "example.com", "added": None},
        {"title": "dup", "url": "https://ok.com", "added": None},
        {"title": "ftp", "url": "ftp://files.com/x", "added": None},
    ]
    assert export_html(_path("filter.html"), items) == 3
    back = import_html(_path("filter.html"))
    assert [i["url"] for i in back] == ["https://ok.com", "ftp://files.com/x"], back


@check("импорт несуществующего файла → []")
def _():
    assert import_html(_path("нет-такого.html")) == []


@check("импорт сущностей: &amp; → &, регистр тега и ADD_DATE")
def _():
    content = (
        "<html><body><DL><p>\n"
        '<DT><a href="https://a.com/?x=1&amp;y=2" add_date="1600000000">Tom &amp; Jerry</a>\n'
        '<DT><A ADD_DATE="1600000001" HREF="https://b.com">B &lt;b&gt;</A>\n'
        '<DT><A HREF="place:sort=8&maxResults=10">Recent</A>\n'
        '<DT><A HREF="javascript:void(0)">JS</A>\n'
        "</DL><p></body></html>\n"
    )
    path = _path("entities.html")
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(content)
    back = import_html(path)
    assert len(back) == 2, back
    assert back[0]["title"] == "Tom & Jerry"
    assert back[0]["url"] == "https://a.com/?x=1&y=2"
    assert back[0]["added"] == "1600000000"
    assert back[1]["title"] == "B <b>" and back[1]["url"] == "https://b.com"
    assert back[1]["added"] == "1600000001"


@check("title пустой → подставляется url")
def _():
    path = _path("empty-title.html")
    with open(path, "w", encoding="utf-8") as fh:
        fh.write('<A HREF="https://only-url.com"></A>')
    back = import_html(path)
    assert back[0]["title"] == "https://only-url.com", back


@check("экспорт создаёт родительские каталоги")
def _():
    path = os.path.join(TMP, "глубоко", "вложено", "b.html")
    assert export_html(path, [{"title": "X", "url": "https://x.com", "added": None}]) == 1
    assert os.path.isfile(path)


def main() -> int:
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
