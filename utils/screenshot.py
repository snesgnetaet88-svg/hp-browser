# HP Browser — by hypermarket
"""Скриншоты экрана и окон для HP Browser.

Кроссплатформенный модуль с фолбэками. На KDE Plasma (Wayland) используется
``spectacle`` + вывод геометрии окна через KWin-скрипт; на X11 — ``maim``,
``scrot`` или ImageMagick ``import``.

Публичные функции:
    take_screenshot(path=None) -> Path | None
    take_window_screenshot(window_name, path=None) -> Path | None

Все снимки по умолчанию сохраняются в ``~/projects/hp-browser/screenshots/``.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
import time
from datetime import datetime
from pathlib import Path

SCREENSHOTS_DIR = Path.home() / "projects" / "hp-browser" / "screenshots"
_KWIN_SCRIPT = Path(tempfile.gettempdir()) / "hp_shot_kwin.js"


def _which(*names: str) -> str | None:
    """Возвращает первый найденный в PATH исполняемый файл."""
    for name in names:
        found = shutil.which(name)
        if found:
            return found
    return None


def _timestamp() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def _qt_grab(target: Path, window_name: str | None = None) -> Path | None:
    """Снимок через Qt (кроссплатформенный фолбэк).

    Без ``window_name`` снимает весь экран; иначе — окно приложения с
    подстрокой в заголовке. Работает и на Windows, где нет Linux-утилит.
    """
    try:
        from PyQt6.QtGui import QGuiApplication
        from PyQt6.QtWidgets import QApplication
    except Exception:
        return None
    app = QApplication.instance()
    if app is None:
        return None
    screen = QGuiApplication.primaryScreen()
    if screen is None:
        return None
    pix = None
    if window_name:
        needle = window_name.lower()
        for widget in app.topLevelWidgets():
            if widget.isWindow() and needle in (widget.windowTitle() or "").lower():
                pix = screen.grabWindow(widget.winId())
                break
    else:
        pix = screen.grabWindow(0)
    if pix is None or pix.isNull():
        return None
    return target if pix.save(str(target), "PNG") else None


def _resolve(path: str | os.PathLike[str] | None, prefix: str) -> Path:
    """Готовит путь для сохранения снимка и создаёт каталоги."""
    if path is None:
        target = SCREENSHOTS_DIR / f"{prefix}_{_timestamp()}.png"
    else:
        target = Path(path).expanduser()
    target.parent.mkdir(parents=True, exist_ok=True)
    return target


def _run(cmd: list[str]) -> bool:
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        return proc.returncode == 0
    except (OSError, subprocess.SubprocessError):
        return False


def _kwin_available() -> bool:
    return _which("qdbus6", "qdbus") is not None


def _journal_lines(limit: int = 200) -> str:
    tool = _which("journalctl")
    if not tool:
        return ""
    try:
        proc = subprocess.run(
            [tool, "--user", "-u", "plasma-kwin_wayland", "--no-pager", "-n", str(limit)],
            capture_output=True,
            text=True,
            timeout=15,
        )
        return proc.stdout
    except (OSError, subprocess.SubprocessError):
        return ""


def _kwin_script(code: str) -> None:
    """Загружает и запускает временный KWin-скрипт."""
    _KWIN_SCRIPT.write_text(code, encoding="utf-8")
    dbus = _which("qdbus6", "qdbus")
    if not dbus:
        return
    _run([dbus, "org.kde.KWin", "/Scripting", "org.kde.kwin.Scripting.loadScript", str(_KWIN_SCRIPT)])
    _run([dbus, "org.kde.KWin", "/Scripting", "org.kde.kwin.Scripting.start"])
    time.sleep(1.5)


def _kwin_window_geometry(window_name: str) -> tuple[int, int, int, int] | None:
    """Поднимает окно поверх и возвращает его геометрию (x, y, w, h)."""
    marker = f"HPGEO_{os.getpid()}_{int(time.time() * 1000)}"
    _kwin_script(
        f"""
const target = {window_name!r};
const marker = {marker!r};
const clients = workspace.windowList();
for (let i = 0; i < clients.length; i++) {{
    const c = clients[i];
    if (c.caption && c.caption.indexOf(target) !== -1) {{
        c.keepAbove = true; c.minimized = false;
        const g = c.frameGeometry;
        print(marker + "|" + g.x + "," + g.y + "," + g.width + "," + g.height);
    }}
}}
"""
    )
    line = ""
    for candidate in _journal_lines().splitlines():
        if marker in candidate:
            line = candidate
    if not line:
        return None
    try:
        geo = line.split(marker + "|", 1)[1].strip()
        x, y, w, h = (int(v) for v in geo.split(","))
        return x, y, w, h
    except (ValueError, IndexError):
        return None


def _kwin_unkeep(window_name: str) -> None:
    _kwin_script(
        f"""
const target = {window_name!r};
const clients = workspace.windowList();
for (let i = 0; i < clients.length; i++) {{
    const c = clients[i];
    if (c.caption && c.caption.indexOf(target) !== -1) {{ c.keepAbove = false; }}
}}
"""
    )


def take_screenshot(path: str | os.PathLike[str] | None = None) -> Path | None:
    """Делает снимок всего экрана.

    Порядок попыток: spectacle (KDE/Wayland) → maim → scrot → import (X11).
    Возвращает путь к файлу или ``None`` при неудаче.
    """
    target = _resolve(path, "screen")

    spectacle = _which("spectacle")
    if spectacle and _run([spectacle, "-b", "-n", "-f", "-o", str(target)]):
        if target.exists() and target.stat().st_size > 0:
            return target

    maim = _which("maim")
    if maim and _run([maim, str(target)]):
        if target.exists() and target.stat().st_size > 0:
            return target

    scrot = _which("scrot")
    if scrot and _run([scrot, str(target)]):
        if target.exists() and target.stat().st_size > 0:
            return target

    import_bin = _which("import")
    if import_bin and _run([import_bin, "-window", "root", str(target)]):
        if target.exists() and target.stat().st_size > 0:
            return target

    # Кроссплатформенный фолбэк (Windows и системы без внешних утилит).
    return _qt_grab(target)


def _x11_window_id(window_name: str) -> str | None:
    xdotool = _which("xdotool")
    if not xdotool:
        return None
    try:
        proc = subprocess.run(
            [xdotool, "search", "--name", window_name],
            capture_output=True,
            text=True,
            timeout=10,
        )
        ids = [line.strip() for line in proc.stdout.splitlines() if line.strip()]
        return ids[0] if ids else None
    except (OSError, subprocess.SubprocessError):
        return None


def take_window_screenshot(
    window_name: str, path: str | os.PathLike[str] | None = None
) -> Path | None:
    """Снимок конкретного окна по подстроке заголовка.

    На Wayland (KWin): окно поднимается поверх, снимается весь экран и
    вырезается область окна. На X11: ``maim -i`` / ``import -window``.
    """
    target = _resolve(path, "window")

    # --- Wayland / KDE: KWin geometry + full shot + crop ---
    if _kwin_available():
        geo = _kwin_window_geometry(window_name)
        if geo:
            full = take_screenshot(Path(tempfile.gettempdir()) / "hp_shot_full.png")
            try:
                if full and full.exists():
                    from PIL import Image

                    x, y, w, h = geo
                    with Image.open(full) as img:
                        img.crop((x, y, x + w, y + h)).save(target)
                    return target
            except Exception:
                pass
            finally:
                _kwin_unkeep(window_name)

    # --- X11 fallbacks ---
    win_id = _x11_window_id(window_name)
    if win_id:
        maim = _which("maim")
        if maim and _run([maim, "-i", win_id, str(target)]):
            if target.exists() and target.stat().st_size > 0:
                return target
        import_bin = _which("import")
        if import_bin and _run([import_bin, "-window", win_id, str(target)]):
            if target.exists() and target.stat().st_size > 0:
                return target

    # Кроссплатформенный фолбэк: снимок окна средствами Qt.
    return _qt_grab(target, window_name)


if __name__ == "__main__":  # pragma: no cover - ручная проверка
    import sys

    if len(sys.argv) > 1:
        result = take_window_screenshot(sys.argv[1])
    else:
        result = take_screenshot()
    print(result if result else "не удалось сделать снимок")
