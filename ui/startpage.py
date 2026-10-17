# HP Browser — by hypermarket
"""Стартовая страница (новая вкладка).

Светлые темы получают чистую страницу (поиск + плитки ссылок).
Хакерская тема дополнительно включает «матричный дождь» на фоне.
"""

from html import escape

from PyQt6.QtCore import QUrl

from core.browser import DEFAULT_ENGINE, DEFAULT_QUICK_LINKS, SEARCH_ENGINES
from utils.branding import APP_VERSION, LOGO_ASCII, TAGLINE

START_URL = "https://hp-browser.local/start"

QUICK_LINKS = [(item["name"], item["url"]) for item in DEFAULT_QUICK_LINKS]

_TEMPLATE = """<!doctype html>
<html lang="ru"><head><meta charset="utf-8">
<title>HP Browser — новая вкладка</title>
<style>
  html,body{margin:0;height:100%;background:__BG__;color:__FG__;overflow:hidden;
    font-family:"Noto Sans","DejaVu Sans",system-ui,sans-serif}
  __RAIN_CSS__
  .wrap{position:relative;z-index:1;display:flex;flex-direction:column;align-items:center;
    justify-content:center;min-height:100%;gap:26px;text-align:center;padding:24px}
  .logo{color:__ACCENT__;font-family:"DejaVu Sans Mono","Liberation Mono","Courier New",monospace;
    font-size:clamp(9px,1.65vw,19px);line-height:1.15;white-space:pre;margin:0;
    text-shadow:__GLOW__;max-width:100%;overflow-x:auto}
  h1{font-size:15px;font-weight:600;color:__MUTED__;margin:0;letter-spacing:.4px}
  form{display:flex;width:min(640px,86vw);gap:10px}
  input{flex:1;background:__URLBG__;color:__FG__;border:1px solid __BORDER__;border-radius:22px;
    padding:13px 20px;font:inherit;font-size:15px;outline:none}
  input:focus{border-color:__ACCENT__;box-shadow:0 0 0 3px __RING__}
  button{background:__ACCENT__;color:__ACCENTFG__;border:0;border-radius:22px;padding:13px 22px;
    font:inherit;font-weight:600;cursor:pointer}
  button:hover{filter:brightness(1.08)}
  .links{display:flex;flex-wrap:wrap;gap:14px;justify-content:center;max-width:760px}
  a{display:flex;flex-direction:column;align-items:center;gap:8px;width:100px;padding:12px 6px;
    color:__FG__;text-decoration:none;border-radius:12px;font-size:13px}
  a:hover{background:__PANEL__}
  .tile{width:44px;height:44px;border-radius:12px;display:flex;align-items:center;justify-content:center;
    background:__PANEL__;color:__ACCENT__;font-weight:700;font-size:18px;border:1px solid __BORDER__}
  .foot{color:__MUTED__;font-size:12px;letter-spacing:.5px}
  .banner{background:#6e4aa8;color:#fff;border-radius:16px;padding:6px 16px;font-size:13px;
    font-weight:600;letter-spacing:.3px}
</style></head>
<body>
__RAIN_CANVAS__
<div class="wrap">
  <pre class="logo">__LOGO__</pre>
  __BANNER__
  <h1>__HEADLINE__</h1>
  <form onsubmit="go(event)">
    <input id="q" autofocus placeholder="__PLACEHOLDER__" autocomplete="off">
    <button type="submit">Искать</button>
  </form>
  <div class="links">__LINKS__</div>
  <div class="foot">__FOOTER__</div>
</div>
<script>
var ENGINE = "__ENGINE__";
function go(e){
  e.preventDefault();
  var q = document.getElementById('q').value.trim();
  if(!q) return;
  var isUrl = /^(https?:\\/\\/)|^[\\w-]+(\\.[\\w-]+)+(\\/.*)?$/.test(q) && q.indexOf(' ')<0;
  location.href = isUrl ? (q.indexOf('://')<0 ? 'https://'+q : q)
                        : ENGINE.replace('{query}', encodeURIComponent(q));
}
__RAIN_JS__
</script>
</body></html>
"""

_RAIN_CSS = """
  #rain{position:fixed;inset:0;z-index:0;opacity:.28}
"""
_RAIN_CANVAS = '<canvas id="rain"></canvas>'
_RAIN_JS = """
var c=document.getElementById('rain'),x=c.getContext('2d'),cols,ys,chars='01HP<>{}[]#$%&*';
function size(){c.width=innerWidth;c.height=innerHeight;cols=Math.floor(c.width/16);ys=Array(cols).fill(0);}
size();addEventListener('resize',size);
setInterval(function(){
  if(document.hidden) return;
  x.fillStyle='rgba(0,0,0,.10)';x.fillRect(0,0,c.width,c.height);
  x.fillStyle='#0f6';x.font='13px monospace';
  for(var i=0;i<cols;i++){
    x.fillText(chars[Math.floor(Math.random()*chars.length)],i*16,ys[i]*16);
    ys[i]=ys[i]*16>c.height&&Math.random()>.975?0:ys[i]+1;
  }
},90);
"""

_DEFAULT = {
    "name": "classic", "bg": "#ffffff", "fg": "#15141a", "muted": "#5b5b66",
    "panel": "#f9f9fb", "border": "#cfcfd8", "accent": "#0060df",
    "accent_fg": "#ffffff", "url_bg": "#ffffff",
}


def start_html(theme: dict | None = None, engine: str = DEFAULT_ENGINE,
               private: bool = False, links: list[dict] | None = None) -> str:
    """Собирает HTML стартовой страницы под текущую тему, поисковик и плитки."""
    t = {**_DEFAULT, **(theme or {})}
    hacker = t.get("name") == "hacker"
    label, template = SEARCH_ENGINES.get(engine, SEARCH_ENGINES[DEFAULT_ENGINE])
    quick = links if links else DEFAULT_QUICK_LINKS

    if private:
        headline = "Приватный просмотр"
        banner = '<div class="banner">Вы в приватном режиме — история не сохраняется</div>'
    elif hacker:
        headline = "HP BROWSER // ВВЕДИ АДРЕС ИЛИ ЗАПРОС"
        banner = ""
    else:
        headline = "Новая вкладка"
        banner = ""

    tiles = "".join(
        f'<a href="{escape(item.get("url", ""))}">'
        f'<span class="tile">{escape((item.get("name") or "?")[0])}</span>'
        f'{escape(item.get("name") or item.get("url", ""))}</a>'
        for item in quick
        if item.get("url")
    )
    html = _TEMPLATE
    for token, value in (
        ("__RAIN_CSS__", _RAIN_CSS if hacker else ""),
        ("__RAIN_CANVAS__", _RAIN_CANVAS if hacker else ""),
        ("__RAIN_JS__", _RAIN_JS if hacker else ""),
        ("__BG__", t["bg"]),
        ("__FG__", t["fg"]),
        ("__MUTED__", t["muted"]),
        ("__PANEL__", t["panel"]),
        ("__BORDER__", t["border"]),
        ("__ACCENT__", t["accent"]),
        ("__ACCENTFG__", t["accent_fg"]),
        ("__URLBG__", t.get("url_bg", t["bg"])),
        ("__RING__", f"{t['accent']}33"),
        ("__GLOW__", f"0 0 8px {t['accent']}" if hacker else "none"),
        ("__HEADLINE__", headline),
        ("__BANNER__", banner),
        ("__PLACEHOLDER__", f"Поиск в {label} или адрес" if not hacker else "адрес или запрос"),
        ("__ENGINE__", template),
        ("__LINKS__", tiles),
        ("__LOGO__", escape(LOGO_ASCII.rstrip("\n"))),
        ("__VERSION__", APP_VERSION),
        ("__FOOTER__", f"HP Browser by hypermarket · v{APP_VERSION} · {TAGLINE}"),
    ):
        html = html.replace(token, value)
    return html


def load_start_page(view, theme: dict | None = None, engine: str = DEFAULT_ENGINE,
                    private: bool = False, links: list[dict] | None = None) -> None:
    """Загружает стартовую страницу в переданный веб-вид."""
    view.setHtml(start_html(theme, engine, private, links), QUrl(START_URL))
