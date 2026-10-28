"""Собирает страницу «Мои приложения» в ~/apps и регистрирует одно приложение.

python ph-apps-build.py                      — только пересобрать страницу
python ph-apps-build.py trenirovki Тренировки — записать app.json, манифест и пересобрать
"""
import html
import json
import struct
import sys
import time
import zlib
from pathlib import Path

APPS = Path.home() / "apps"
BG, FG = "#000000", "#ffffff"


def png_icon(size):
    # чёрный квадрат с белым кругом — простая иконка без библиотек
    r = size * 0.22
    c = size / 2
    rows = []
    for y in range(size):
        row = bytearray(b"\x00")
        for x in range(size):
            row += b"\xff\xff\xff" if (x - c) ** 2 + (y - c) ** 2 <= r * r else b"\x00\x00\x00"
        rows.append(bytes(row))

    def chunk(tag, data):
        return struct.pack(">I", len(data)) + tag + data + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)

    return (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", size, size, 8, 2, 0, 0, 0))
            + chunk(b"IDAT", zlib.compress(b"".join(rows), 9)) + chunk(b"IEND", b""))


def ensure_icons():
    for size in (192, 512):
        f = APPS / f"icon-{size}.png"
        if not f.exists():
            f.write_bytes(png_icon(size))


def manifest(name, start, scope):
    return {
        "id": start, "name": name, "short_name": name, "start_url": start, "scope": scope, "display": "standalone",
        "background_color": BG, "theme_color": BG,
        "icons": [{"src": f"/icon-{s}.png", "sizes": f"{s}x{s}", "type": "image/png"} for s in (192, 512)],
    }


def link_manifest(page):
    text = page.read_text(encoding="utf-8")
    if 'rel="manifest"' in text or "rel='manifest'" in text:
        return
    tag = '<link rel="manifest" href="manifest.webmanifest">\n'
    text = text.replace("</head>", tag + "</head>", 1) if "</head>" in text else tag + text
    page.write_text(text, encoding="utf-8")


def register(slug, name):
    d = APPS / slug
    page = d / "index.html"
    if not page.exists():
        sys.exit(f"нет {page}")
    (d / "app.json").write_text(json.dumps({"name": name, "slug": slug, "updated": int(time.time())},
                                           ensure_ascii=False), encoding="utf-8")
    (d / "manifest.webmanifest").write_text(json.dumps(manifest(name, f"/{slug}/", f"/{slug}/"),
                                                       ensure_ascii=False, indent=1), encoding="utf-8")
    link_manifest(page)


SW = """// Кэш на случай, если сервер на телефоне ещё не поднялся: сначала сеть, потом сохранённое
self.addEventListener('install', () => self.skipWaiting());
self.addEventListener('activate', e => e.waitUntil(self.clients.claim()));
self.addEventListener('fetch', e => {
  if (e.request.method !== 'GET') return;
  e.respondWith(fetch(e.request).then(r => {
    const copy = r.clone();
    caches.open('apps').then(c => c.put(e.request, copy));
    return r;
  }).catch(() => caches.match(e.request)));
});
"""

PAGE = """<!doctype html>
<html lang="ru">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<meta name="theme-color" content="#000000">
<title>Мои приложения</title>
<link rel="manifest" href="/home/manifest.webmanifest">
<style>
  html, body {{ margin: 0; background: #000; color: #fff; }}
  body {{ min-height: 100vh; display: flex; flex-direction: column; justify-content: center; align-items: center;
         font: 400 30px/1.25 system-ui, -apple-system, "Inter", sans-serif; padding: 48px 16px; box-sizing: border-box; }}
  a {{ color: #fff; text-decoration: none; display: block; padding: 10px 0; text-align: center; }}
  a:active {{ opacity: .5; }}
  .empty {{ color: #8a8a8a; font-size: 18px; text-align: center; max-width: 18em; }}
</style>
</head>
<body>
{items}
<script>
if ('serviceWorker' in navigator) navigator.serviceWorker.register('/sw.js');
// Список остаётся открытым между свайпами — при каждом возвращении перечитываем его, чтобы видеть новые приложения
document.addEventListener('visibilitychange', () => {{ if (document.visibilityState === 'visible') location.reload(); }});
// Приложение открывается в обычном Chrome, а список остаётся списком; не вышло — открываем здесь
document.querySelectorAll('a[data-slug]').forEach(a => a.addEventListener('click', e => {{
  e.preventDefault();
  fetch('/open/' + a.dataset.slug, {{cache: 'no-store', redirect: 'manual'}})
    .then(r => {{ if (r.status !== 204) location.href = a.href; }})
    .catch(() => {{ location.href = a.href; }});
}}));
</script>
</body>
</html>
"""


REDIRECT = '<!doctype html><meta charset="utf-8"><meta http-equiv="refresh" content="0; url=/home/">\n'


def build_index():
    # Список живёт в /home/ со своей областью: приложения из /<slug>/ лежат вне её и открываются
    # поверх списка во вкладке Chrome, а установленный список при каждом открытии остаётся списком.
    home = APPS / "home"
    home.mkdir(parents=True, exist_ok=True)
    ensure_icons()
    (APPS / "sw.js").write_text(SW, encoding="utf-8")
    (APPS / "index.html").write_text(REDIRECT, encoding="utf-8")
    (APPS / "manifest.webmanifest").unlink(missing_ok=True)
    (home / "manifest.webmanifest").write_text(json.dumps(manifest("Мои приложения", "/home/", "/home/"),
                                                          ensure_ascii=False, indent=1), encoding="utf-8")
    apps = []
    for meta in APPS.glob("*/app.json"):
        try:
            apps.append(json.loads(meta.read_text(encoding="utf-8")))
        except ValueError:
            continue
    apps.sort(key=lambda a: a["name"].lower())
    if apps:
        # data-slug: скрипт ниже просит сервер открыть приложение в обычном Chrome (см. ph-apps-serve.py)
        items = "\n".join(f'<a href="/{html.escape(a["slug"])}/" data-slug="{html.escape(a["slug"])}">'
                          f'{html.escape(a["name"])}</a>' for a in apps)
    else:
        items = '<p class="empty">Пока пусто. Напиши Claude: «сделай мне приложение…»</p>'
    (home / "index.html").write_text(PAGE.format(items=items), encoding="utf-8")


if __name__ == "__main__":
    if len(sys.argv) == 3:
        register(sys.argv[1], sys.argv[2])
    build_index()
