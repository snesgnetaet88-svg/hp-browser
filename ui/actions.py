# HP Browser — by hypermarket
"""Инструменты окна: OSINT, Leaks, Security, Sniffer, Privacy.

Вынесено в миксин, чтобы окно (window.py) оставалось компактным.
"""

from PyQt6.QtCore import QTimer
from PyQt6.QtWebEngineCore import QWebEngineProfile
from PyQt6.QtWidgets import QInputDialog

from core.privacy import PrivacyGuard
from tools.leaks import LeaksWorker
from tools.osint import OsintWorker
from tools.security import SecurityWorker
from tools.sniffer import RequestSniffer

SNIFF_FLUSH_MS = 500


class ToolsActions:
    """Методы-обработчики для панели инструментов (примесь к MainWindow)."""

    # --- перехватчики ----------------------------------------------------
    def _install_interceptors(self) -> None:
        """Ставит единый перехватчик: сниффер + блокировка трекеров."""
        self.privacy_guard = PrivacyGuard(self)
        self.privacy_guard.set_enabled(bool(self.settings.get("privacy", False)))
        self.sniffer = RequestSniffer(self, guard=self.privacy_guard, sink=self._sniff_sink)
        self._sniff_lines: list[str] = []
        self._sniff_shown = 0
        self._sniff_timer = QTimer(self)
        self._sniff_timer.setInterval(SNIFF_FLUSH_MS)
        self._sniff_timer.timeout.connect(self._flush_sniffer)
        profile = getattr(self, "private_profile", None) or QWebEngineProfile.defaultProfile()
        profile.setUrlRequestInterceptor(self.sniffer)

    # --- OSINT -----------------------------------------------------------
    def run_osint(self) -> None:
        """OSINT-разведка по текущему сайту (в фоне)."""
        view = self.current_view()
        if view is None:
            return
        url = view.url().toString()
        self.tool_panel.start("OSINT", f"Разведка по {url} …")
        self._osint_worker = OsintWorker(url, self)
        self._osint_worker.done.connect(self._show_osint)
        self._osint_worker.failed.connect(self._show_error)
        self._osint_worker.start()

    def _show_osint(self, data: dict) -> None:
        lines = [f"OSINT — {data.get('host', '?')}", "=" * 48]
        if data.get("error"):
            lines.append(f"[!] {data['error']}")
            self.tool_panel.set_text("\n".join(lines))
            return
        whois = data.get("whois", {})
        lines.append("WHOIS")
        if whois.get("error"):
            lines.append(f"  [!] {whois['error']}")
        else:
            lines += [
                f"  регистратор : {whois.get('registrar')}",
                f"  создан      : {whois.get('created')}",
                f"  истекает    : {whois.get('expires')}",
            ]
        lines.append("DNS")
        for rtype, values in (data.get("dns") or {}).items():
            lines.append(f"  {rtype:<5}: {'; '.join(values)}")
        ssl_info = data.get("ssl", {})
        lines.append("SSL")
        if ssl_info.get("error"):
            lines.append(f"  [!] {ssl_info['error']}")
        else:
            lines += [
                f"  издатель    : {ssl_info.get('issuer')}",
                f"  действует до: {ssl_info.get('not_after')}",
            ]
        subs = data.get("subdomains") or []
        lines.append(f"Поддомены ({len(subs)}):")
        lines += [f"  · {name}" for name in subs] or ["  (нет данных)"]
        self.tool_panel.set_text("\n".join(lines))

    # --- Leaks -----------------------------------------------------------
    def run_leaks(self) -> None:
        """Спрашивает email и проверяет его на утечки (в фоне)."""
        email, ok = QInputDialog.getText(self, "Проверка утечек", "Email:")
        if not ok or not email.strip():
            return
        self.tool_panel.start("Leaks", f"Проверка {email.strip()} …")
        self._leaks_worker = LeaksWorker(email.strip(), self)
        self._leaks_worker.done.connect(self._show_leaks)
        self._leaks_worker.failed.connect(self._show_error)
        self._leaks_worker.start()

    def _show_leaks(self, data: dict) -> None:
        lines = [f"Leaks — {data.get('email')}", "=" * 48]
        if data.get("error"):
            lines.append(f"[!] {data['error']}")
        elif data.get("source") == "free":
            lines.append("[i] HIBP_API_KEY не задан — бесплатные источники (без ключа).")
            for item in data.get("free_sources", []):
                if item.get("error"):
                    lines.append(f"[!] {item['name']}: {item['error']}")
                    continue
                mark = f"найдено записей: {item['count']}" if item["found"] else "не найдено"
                lines.append(f"[{'x' if item['found'] else '+'}] {item['name']}: {mark}")
                lines += [f"  · {d}" for d in item.get("details", [])]
        elif not data.get("found"):
            lines.append("[+] Утечек не найдено.")
        else:
            lines.append(f"[x] Найдено утечек: {len(data['breaches'])}")
            for breach in data["breaches"]:
                lines.append(
                    f"  · {breach.get('title')} ({breach.get('date')}) — "
                    f"{breach.get('pwned')} аккаунтов"
                )
                lines.append(f"      данные: {', '.join(breach.get('data') or [])}")
        self.tool_panel.set_text("\n".join(lines))

    # --- Security --------------------------------------------------------
    def run_security(self) -> None:
        """Проверяет заголовки безопасности текущего сайта (в фоне)."""
        view = self.current_view()
        if view is None:
            return
        url = view.url().toString()
        self.tool_panel.start("Security", f"Анализ заголовков {url} …")
        self._security_worker = SecurityWorker(url, self)
        self._security_worker.done.connect(self._show_security)
        self._security_worker.failed.connect(self._show_error)
        self._security_worker.start()

    def _show_security(self, data: dict) -> None:
        lines = [f"Security — {data.get('url')}", "=" * 48]
        if data.get("error"):
            lines.append(f"[!] {data['error']}")
            self.tool_panel.set_text("\n".join(lines))
            return
        lines.append(f"Код ответа: {data.get('status_code')} | Сервер: {data.get('server') or '—'}")
        lines.append(f"ОЦЕНКА: {data.get('grade')}")
        lines.append("")
        lines.append("Присутствуют:")
        for name, info in (data.get("present") or {}).items():
            lines.append(f"  [+] {name}: {info['desc']}")
        lines.append("Отсутствуют:")
        for item in data.get("missing") or []:
            lines.append(f"  [!] {item['name']}: {item['desc']}")
        self.tool_panel.set_text("\n".join(lines))

    # --- Sniffer ---------------------------------------------------------
    def toggle_sniffer(self, checked: bool) -> None:
        """Включает/выключает перехват запросов."""
        self.sniffer.set_enabled(checked)
        if checked:
            self._sniff_lines = []
            self._sniff_shown = 0
            self.tool_panel.show_panel("Sniffer")
            self.tool_panel.set_text("Перехват включён. Открой сайт — запросы появятся здесь.")
            self._sniff_timer.start()
        else:
            self._sniff_timer.stop()
            self._flush_sniffer(force=True)

    def _sniff_sink(self, record: dict) -> None:
        """Копит записи, чтобы не дёргать интерфейс на каждый запрос."""
        self._sniff_lines.append(
            f"{record['method']:<4} {record['type']:<9} {record['host']}"
        )

    def _flush_sniffer(self, force: bool = False) -> None:
        """Дописывает только новые строки — панель не перерисовывается целиком."""
        new = self._sniff_lines[self._sniff_shown :]
        if not new and not force:
            return
        for line in new[-300:]:
            self.tool_panel.append(f"  {line}")
        self._sniff_shown = len(self._sniff_lines)
        thirds = self.sniffer.third_party_hosts()
        self.tool_panel.setWindowTitle(
            f"Sniffer — запросов: {len(self.sniffer.records)}, сторонних хостов: {len(thirds)}"
        )

    # --- Privacy ---------------------------------------------------------
    def toggle_privacy(self, checked: bool) -> None:
        """Включает/выключает блокировку трекеров."""
        self.privacy_guard.set_enabled(checked)
        self.settings.set("privacy", bool(checked))
        self.settings.save()
        if checked:
            self.privacy_guard.reset_stats()
        self._refresh_status()

    def show_privacy_stats(self) -> None:
        """Показывает статистику блокировок."""
        guard = self.privacy_guard
        lines = [
            "Privacy — блокировка трекеров",
            "=" * 48,
            f"Статус: {'ВКЛ' if guard.enabled else 'выкл'}",
            f"Заблокировано запросов: {guard.blocked_count}",
            "Хосты:",
        ]
        lines += [f"  [x] {host}" for host in guard.last_blocked] or ["  (пока пусто)"]
        self.tool_panel.show_panel("Privacy")
        self.tool_panel.set_text("\n".join(lines))

    # --- общее -----------------------------------------------------------
    def _show_error(self, message: str) -> None:
        self.tool_panel.set_text(f"[x] Ошибка: {message}")
