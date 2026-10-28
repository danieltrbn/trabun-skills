"""Сервер ~/apps на 127.0.0.1:8765.

Кроме файлов отвечает на /open/<slug>: открывает приложение в обычном Chrome отдельной задачей
(через adb на самого себя), чтобы список «Мои приложения» оставался списком. 204 — открыл,
302 на /<slug>/ — не вышло (нет отладки), тогда страница откроет приложение сама.
"""
import re
import subprocess
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

APPS = Path.home() / "apps"
PORT = 8765


class Handler(SimpleHTTPRequestHandler):
    def do_GET(self):
        m = re.fullmatch(r"/open/([a-z0-9-]+)/?", self.path.split("?")[0])
        if not m:
            return super().do_GET()
        slug = m.group(1)
        if not (APPS / slug / "index.html").exists():
            return self.send_error(404)
        url = f"http://127.0.0.1:{PORT}/{slug}/"
        try:
            ok = subprocess.run(
                [str(Path.home() / ".local/bin/ph"), "am", "start", "-a", "android.intent.action.VIEW", "-d", url,
                 "-n", "com.android.chrome/com.google.android.apps.chrome.Main"],
                capture_output=True, timeout=25).returncode == 0
        except (OSError, subprocess.TimeoutExpired):
            ok = False
        if ok:
            self.send_response(204)
        else:
            self.send_response(302)
            self.send_header("Location", f"/{slug}/")
        self.end_headers()

    def log_message(self, *args):
        pass


if __name__ == "__main__":
    ThreadingHTTPServer(("127.0.0.1", PORT), partial(Handler, directory=str(APPS))).serve_forever()
