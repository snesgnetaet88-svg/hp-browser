# HP Browser — by hypermarket
"""Бесплатные источники утечек без ключа: LeakCheck (public) и ProxyNova COMB.

Фолбэк для модуля Leaks, когда нет платного HIBP_API_KEY.
Пароли маскируются.
"""

import requests

TIMEOUT = 12
UA = "HP-Browser/1.0 (by hypermarket)"
HEADERS = {"User-Agent": UA, "Accept": "application/json"}

LEAKCHECK_URL = "https://leakcheck.io/api/public?check={email}"
COMB_URL = "https://api.proxynova.com/comb?query={email}"
SAMPLE_LIMIT = 8


def mask(secret: str) -> str:
    """Маскирует пароль, оставляя первые 2 символа."""
    secret = secret or ""
    if len(secret) <= 2:
        return "***"
    return secret[:2] + "*" * min(len(secret) - 2, 8)


def _get(url: str):
    """GET с обработкой ошибок. Возвращает (data, error)."""
    try:
        resp = requests.get(url, headers=HEADERS, timeout=TIMEOUT)
    except requests.exceptions.Timeout:
        return None, "таймаут"
    except requests.exceptions.ConnectionError:
        return None, "нет соединения (DNS/сеть)"
    except requests.exceptions.RequestException as exc:
        return None, f"ошибка запроса: {exc}"
    if resp.status_code != 200:
        return None, f"HTTP {resp.status_code}"
    try:
        return resp.json(), None
    except ValueError:
        return None, "ответ не JSON"


def leakcheck(email: str) -> dict:
    """LeakCheck public API: количество записей и список утечек."""
    entry = {"name": "LeakCheck (public)", "found": False, "count": 0, "details": [], "error": None}
    data, error = _get(LEAKCHECK_URL.format(email=email))
    if error:
        entry["error"] = error
        return entry
    found = int(data.get("found") or 0)
    entry["found"] = found > 0
    entry["count"] = found
    if data.get("fields"):
        entry["details"].append("поля: " + ", ".join(list(data["fields"])[:10]))
    for src in (data.get("sources") or [])[:SAMPLE_LIMIT]:
        entry["details"].append(f"{src.get('name') or '?'} ({src.get('date') or '?'})")
    return entry


def comb(email: str) -> dict:
    """ProxyNova COMB: связки email:пароль из дампа COMB."""
    entry = {"name": "ProxyNova COMB", "found": False, "count": 0, "details": [], "error": None}
    data, error = _get(COMB_URL.format(email=email))
    if error:
        entry["error"] = error
        return entry
    count = int(data.get("count") or 0)
    entry["count"] = count
    entry["found"] = count > 0
    for line in (data.get("lines") or [])[:SAMPLE_LIMIT]:
        login, _, password = line.partition(":")
        entry["details"].append(f"{login}:{mask(password)}")
    return entry


def free_lookup(email: str) -> dict:
    """Опросить все бесплатные источники.

    Возвращает {found, sources: [...], error}.
    """
    sources = [leakcheck(email), comb(email)]
    alive = [s for s in sources if not s["error"]]
    return {
        "found": any(s["found"] for s in sources),
        "sources": sources,
        "error": None if alive else "Бесплатные источники недоступны (проверь интернет).",
    }
