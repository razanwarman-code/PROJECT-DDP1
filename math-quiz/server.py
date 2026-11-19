"""Server web sederhana (pustaka standar Python, tanpa install apa pun).

    python3 server.py            -> buka http://127.0.0.1:8000

API:
    GET  /api/topics
    GET  /api/questions?topic=pecahan&count=10
    POST /api/check   {"id": "...", "answer": "1/2"}   (pilihan ganda: answer = nomor opsi)

Kunci jawaban disimpan di server (memori), tidak pernah dikirim ke browser
sebelum siswa menjawab.
"""
import json
import os
import random
import secrets
import threading
from collections import OrderedDict
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

import generator

STATIC_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static")
STORE = OrderedDict()  # id soal -> soal lengkap (dengan kunci jawaban)
LOCK = threading.Lock()
MAX_STORE = 5000


def remember(q):
    qid = secrets.token_hex(8)
    with LOCK:
        STORE[qid] = q
        while len(STORE) > MAX_STORE:
            STORE.popitem(last=False)
    return qid


class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=STATIC_DIR, **kwargs)

    def _json(self, data, status=200):
        body = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        url = urlparse(self.path)
        if url.path == "/api/topics":
            return self._json({"topics": generator.list_topics()})

        if url.path == "/api/questions":
            params = parse_qs(url.query)
            topic = params.get("topic", [""])[0]
            if topic not in generator.TOPICS:
                return self._json({"error": "Topik tidak ditemukan"}, 404)
            try:
                count = max(1, min(20, int(params.get("count", ["10"])[0])))
            except ValueError:
                count = 10
            questions = generator.generate_set(topic, count, random.Random())
            return self._json({
                "topic": topic,
                "questions": [generator.public_view(q, remember(q)) for q in questions],
            })

        return super().do_GET()  # file statis (index.html, style.css, app.js)

    def do_POST(self):
        if urlparse(self.path).path != "/api/check":
            return self._json({"error": "Tidak ditemukan"}, 404)
        try:
            length = int(self.headers.get("Content-Length", 0))
            if not 0 < length <= 10_000:
                raise ValueError
            payload = json.loads(self.rfile.read(length))
            qid, answer = payload["id"], payload["answer"]
        except (ValueError, KeyError, TypeError):
            return self._json({"error": "Permintaan tidak valid"}, 400)

        with LOCK:
            q = STORE.get(qid)
        if q is None:
            return self._json({"error": "Soal sudah kedaluwarsa, muat ulang halaman."}, 404)

        status = generator.check_answer(q, answer)
        resp = {"status": status, "correct": status == "correct"}
        if status in ("correct", "wrong"):
            resp["answer_text"] = q["answer_text"]
            resp["steps"] = q["steps"]
        return self._json(resp)


def main():
    host = os.environ.get("HOST", "127.0.0.1")
    port = int(os.environ.get("PORT", "8000"))
    server = ThreadingHTTPServer((host, port), Handler)
    print(f"Server jalan di http://{host}:{port}  (Ctrl+C untuk berhenti)")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nBerhenti.")


if __name__ == "__main__":
    main()
