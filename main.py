# HP Browser — by hypermarket
"""Точка входа HP Browser: запуск главного окна."""

import os
import sys

from PyQt6.QtCore import QTimer
from PyQt6.QtWidgets import QApplication

from ui.window import MainWindow
from core.privacy import apply_env_flags
from core.settings import Settings
from utils.branding import APP_AUTHOR, APP_NAME, APP_VERSION


def main() -> int:
    """Создаёт приложение и показывает главное окно."""
    settings = Settings()
    # DoH/WebRTC-флаги Chromium нужно выставить ДО создания QApplication.
    apply_env_flags(settings)

    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setApplicationVersion(APP_VERSION)
    app.setOrganizationName(APP_AUTHOR)

    window = MainWindow(settings=settings)
    window.show()

    open_url = os.environ.get("HP_OPEN_URL")
    if open_url:
        window.navigate(open_url)

    # Автотест без графики: HP_SELFTEST=1 — по завершении загрузки печатает
    # URL и заголовок, затем закрывает приложение.
    if os.environ.get("HP_SELFTEST"):
        def _report(_ok: bool) -> None:
            view = window.current_view()
            print("SELFTEST_URL", view.url().toString() if view else "?")
            print("SELFTEST_TITLE", view.title() if view else "?")
            print("SELFTEST_TABS", window.tabs.count())
            app.quit()

        view = window.current_view()
        if view is not None:
            view.loadFinished.connect(_report)
        QTimer.singleShot(int(os.environ.get("HP_SELFTEST_MS", "15000")), app.quit)

    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
