# HP Browser — by hypermarket
"""Построение меню (меню-бар и гамбургер)."""
from __future__ import annotations

from PyQt6.QtGui import QActionGroup
from PyQt6.QtWidgets import QMenu

from ui.themes import THEMES


def build_theme_menu(parent, theme_name: str, apply_theme) -> tuple[QMenu, QActionGroup, dict]:
    menu = QMenu("Тема", parent)
    group = QActionGroup(parent)
    group.setExclusive(False)
    actions: dict[str, list] = {}
    for name, theme in THEMES.items():
        act = menu.addAction(theme["label"])
        act.setCheckable(True)
        act.setChecked(name == theme_name)
        act.triggered.connect(lambda _c=False, n=name: apply_theme(n, persist=True))
        group.addAction(act)
        actions.setdefault(name, []).append(act)
    return menu, group, actions


class MenuBuilder:
    def __init__(self, win):
        self.win = win

    def add_items(self, menu: QMenu, items) -> None:
        for title, hint, slot in items:
            if slot is None:
                menu.addSeparator()
                continue
            text = f"{title}\t{hint}" if hint else title
            menu.addAction(text, slot)
