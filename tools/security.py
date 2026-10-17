# HP Browser — by hypermarket
"""Сканер безопасности: анализ HTTP-заголовков и оценка A/B/C/D/F."""

import requests
from PyQt6.QtCore import QThread, pyqtSignal

TIMEOUT = 12
UA = "HP-Browser/1.0 (by hypermarket)"

# Заголовок -> (описание, вес при отсутствии)
CHECKS = {
    "content-security-policy": "CSP (защита от XSS/инъекций)",
    "strict-transport-security": "HSTS (принудительный HTTPS)",
    "x-frame-options": "X-Frame-Options (защита от кликджекинга)",
    "x-content-type-options": "X-Content-Type-Options (сниффинг MIME)",
    "referrer-policy": "Referrer-Policy (утечка referrer)",
    "permissions-policy": "Permissions-Policy (доступ к API браузера)",
}
GRADES = [(6, "A"), (5, "B"), (4, "C"), (2, "D")]


def grade_for(score: int) -> str:
    """Оценка по числу присутствующих заголовков."""
    for threshold, letter in GRADES:
        if score >= threshold:
            return letter
    return "F"


def check_headers(url: str) -> dict:
    """Проверяет заголовки безопасности. Возвращает dict(url, present, missing, grade, server, error)."""
    raw = (url or "").strip()
    if not raw:
        return {"url": raw, "error": "Пустой адрес."}
    if "://" not in raw:
        raw = "https://" + raw
    result = {"url": raw, "present": {}, "missing": [], "grade": "F", "server": None, "error": None}
    try:
        resp = requests.get(raw, headers={"User-Agent": UA}, timeout=TIMEOUT, allow_redirects=True)
    except requests.exceptions.RequestException as exc:
        result["error"] = f"Сеть недоступна: {exc}"
        return result

    headers = {k.lower(): v for k, v in resp.headers.items()}
    for name, desc in CHECKS.items():
        if name in headers:
            result["present"][name] = {"desc": desc, "value": headers[name][:120], "status": "ok"}
        else:
            result["missing"].append({"name": name, "desc": desc, "status": "miss"})
    result["grade"] = grade_for(len(result["present"]))
    result["server"] = headers.get("server")
    result["status_code"] = resp.status_code
    return result


class SecurityWorker(QThread):
    """Фоновый сканер безопасности."""

    done = pyqtSignal(dict)
    failed = pyqtSignal(str)

    def __init__(self, url: str, parent=None):
        super().__init__(parent)
        self.url = url

    def run(self) -> None:  # noqa: D401
        try:
            self.done.emit(check_headers(self.url))
        except Exception as exc:  # noqa: BLE001
            self.failed.emit(str(exc))
