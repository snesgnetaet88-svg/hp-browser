# HP Browser — by hypermarket
"""Приватность: блокировка трекеров, DNS-over-HTTPS, отключение WebRTC."""

import os

from PyQt6.QtWebEngineCore import QWebEngineUrlRequestInterceptor

# Известные трекеры/рекламные домены (подстрока хоста).
TRACKER_HOSTS = (
    "google-analytics.com",
    "googletagmanager.com",
    "doubleclick.net",
    "googlesyndication.com",
    "googleadservices.com",
    "facebook.net",
    "connect.facebook.net",
    "scorecardresearch.com",
    "hotjar.com",
    "criteo.com",
    "adnxs.com",
    "quantserve.com",
    "taboola.com",
    "outbrain.com",
    "yandex.ru/metrika",
    "mc.yandex.ru",
    "top-fwz1.mail.ru",
)

DOH_TEMPLATE = "https://cloudflare-dns.com/dns-query"


def is_tracker(host: str) -> bool:
    """Относится ли хост к известным трекерам."""
    host = (host or "").lower()
    return any(marker in host for marker in TRACKER_HOSTS)


class PrivacyGuard(QWebEngineUrlRequestInterceptor):
    """Блокирует запросы к трекерам, когда защита включена."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.enabled = False
        self.blocked_count = 0
        self.last_blocked: list[str] = []

    def interceptRequest(self, info) -> None:  # noqa: N802 — API Qt
        """Блокирует трекерные запросы."""
        if not self.enabled:
            return
        host = info.requestUrl().host()
        if is_tracker(host):
            info.block(True)
            self.blocked_count += 1
            if host not in self.last_blocked:
                self.last_blocked.append(host)
                del self.last_blocked[:-20]

    def set_enabled(self, enabled: bool) -> None:
        self.enabled = bool(enabled)

    def reset_stats(self) -> None:
        self.blocked_count = 0
        self.last_blocked = []


def gpu_enabled() -> bool:
    """Аппаратное ускорение: явно через HP_GPU, иначе по платформе.

    ``HP_GPU=1`` / ``HP_GPU=0`` включают и выключают ускорение принудительно.
    Без переменной на Linux рендеринг программный: на машинах, где GBM
    недоступен, Chromium падает в Vulkan и роняет процесс (сегфолт). На Windows
    аппаратное ускорение обычно работает, поэтому включено по умолчанию.
    """
    value = os.environ.get("HP_GPU", "").strip().lower()
    if value in ("1", "true", "yes", "on"):
        return True
    if value in ("0", "false", "no", "off"):
        return False
    return os.name == "nt"


def chromium_flags(settings) -> str:
    """Собирает Chromium-флаги для рендеринга, DoH и отключения WebRTC.

    Должны быть установлены в QTWEBENGINE_CHROMIUM_FLAGS ДО создания QApplication.
    """
    flags_set: set[str] = set()
    # Chromium-песочница несовместима с частью окружений (контейнеры), поэтому
    # вне Windows она отключена. На Windows песочница работает штатно.
    if os.name != "nt":
        flags_set.add("--no-sandbox")
    if not gpu_enabled():
        flags_set.add("--disable-gpu")
        # безопасный программный фолбэк
        flags_set.add("--disable-software-rasterizer")
    if settings.get("doh"):
        flags_set.add(f"--dns-over-https-templates={DOH_TEMPLATE}")
        flags_set.add("--dns-over-https-mode=secure")
    if settings.get("privacy"):
        flags_set.add("--force-webrtc-ip-handling-policy=disable_non_proxied_udp")
    proxy = str(settings.get("proxy", "") or "").strip()
    if proxy:
        flags_set.add(f"--proxy-server={proxy}")
    return " ".join(sorted(flags_set))
def apply_env_flags(settings) -> None:
    """Прописывает флаги в окружение (вызывать до QApplication)."""
    extra = chromium_flags(settings)
    current = os.environ.get("QTWEBENGINE_CHROMIUM_FLAGS", "")
    os.environ["QTWEBENGINE_CHROMIUM_FLAGS"] = f"{current} {extra}".strip()
