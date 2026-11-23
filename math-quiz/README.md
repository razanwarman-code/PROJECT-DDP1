# Latihan Matematika

Web latihan soal: pilih topik, kerjakan 10 soal, layar hijau kalau benar dan merah kalau salah.
Frontend HTML/CSS/JS, backend Python (pustaka standar, tanpa install).

## Menjalankan

    python3 server.py          # lalu buka http://127.0.0.1:8000
    python3 -m unittest -v     # menjalankan test

## Struktur

    generator.py    pembuat soal + pengecek jawaban (inti)
    server.py       server web + API
    static/         index.html, style.css, app.js
    static/assets/  gambar pita & tombol layar hasil
    static/fonts/   BryndanWriteBook.ttf (font tulisan tangan; cek lisensi sebelum dipakai publik)
    test_generator.py

## Menambah topik baru

1. Di `generator.py`, buat fungsi `q_namatopik(rng, level)` yang mengembalikan soal
   (lihat `q_linear` sebagai contoh paling sederhana). `level` 1-3 = mudah ke sulit.
2. Daftarkan di dictionary `TOPICS`. Tombol di web muncul otomatis.
3. Tambahkan cara verifikasi di `test_generator.py` (field `meta` dipakai untuk itu).

Pecahan ditulis di soal sebagai `{1/2}` dan dirender jadi pecahan bersusun oleh `app.js`.
