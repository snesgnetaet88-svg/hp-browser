# HP Browser — by hypermarket
"""Кроссплатформенный запуск файлов и папок в приложении по умолчанию.

Windows: ``os.startfile``; macOS: ``open``; Linux/прочие: ``xdg-open``.
"""

import os
import subprocess
import sys


def open_path(path: str) -> bool:
    """Открывает файл или папку системным приложением.

    Возвращает ``True`` при успешном запуске, ``False`` при ошибке.
    """
    target = os.path.abspath(os.path.expanduser(str(path)))
    try:
        if os.name == "nt":
            os.startfile(target)  # type: ignore[attr-defined]
            return True
        if sys.platform == "darwin":
            subprocess.Popen(["open", target])
            return True
        subprocess.Popen(["xdg-open", target])
        return True
    except OSError:
        return False
