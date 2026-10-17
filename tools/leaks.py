# HP Browser — by hypermarket
"""Проверка email на утечки: HIBP (ключ) или бесплатные источники (без ключа)."""

import os

import requests
from PyQt6.QtCore import QThread, pyqtSignal

from tools import free_leaks

TIMEOUT = 10
API = "https://haveibeenpwned.com/api/v3/breachedaccount/{email}"
UA = "HP-Browser/1.0 (by hypermarket)"


def _check_free(email: str, result: dict) -> dict:
    """Бесплатный путь: LeakCheck public + ProxyNova COMB (ключ не нужен)."""
    result["source"] = "free"
    data = free_leaks.free_lookup(email)
    result["free_sources"] = data["sources"]
    if data["error"]:
        result["error"] = data["error"]
        return result
    result["found"] = data["found"]
    return result


def check_email(email: str) -> dict:
    """Возвращает dict(email, found, breaches, error, source, free_sources).

    С ключом HIBP_API_KEY — HaveIBeenPwned, иначе — бесплатные источники
    (LeakCheck public, ProxyNova COMB), ключ не нужен.
    """
    email = (email or "").strip()
    result = {
        "email": email,
        "found": False,
        "breaches": [],
        "error": None,
        "source": "hibp",
        "free_sources": [],
    }
    if "@" not in email or " " in email:
        result["error"] = "Похоже, это не email."
        return result
    key = os.environ.get("HIBP_API_KEY", "").strip()
    if not key:
        return _check_free(email, result)
    try:
        resp = requests.get(
            API.format(email=email),
            headers={"hibp-api-key": key, "user-agent": UA},
            timeout=TIMEOUT,
        )
    except requests.exceptions.RequestException as exc:
        result["error"] = f"Сеть недоступна: {exc}"
        return result

    if resp.status_code == 404:
        return result
    if resp.status_code in (401, 403):
        result["error"] = "HIBP отклонил ключ (401/403)."
        return result
    if resp.status_code == 429:
        result["error"] = "HIBP: лимит запросов (429), подожди."
        return result
    if resp.status_code != 200:
        result["error"] = f"HIBP вернул код {resp.status_code}."
        return result

    try:
        data = resp.json()
    except ValueError:
        result["error"] = "HIBP вернул не-JSON."
        return result

    result["found"] = bool(data)
    for breach in data:
        result["breaches"].append(
            {
                "title": breach.get("Title"),
                "date": breach.get("BreachDate"),
                "pwned": breach.get("PwnCount"),
                "data": breach.get("DataClasses", []),
            }
        )
    return result


class LeaksWorker(QThread):
    """Фоновая проверка email на утечки."""

    done = pyqtSignal(dict)
    failed = pyqtSignal(str)

    def __init__(self, email: str, parent=None):
        super().__init__(parent)
        self.email = email

    def run(self) -> None:  # noqa: D401
        try:
            self.done.emit(check_email(self.email))
        except Exception as exc:  # noqa: BLE001
            self.failed.emit(str(exc))
