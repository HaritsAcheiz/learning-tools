# learning-tools

Aplikasi ini digunakan untuk mempermudah proses pembelajaran. Materinya bisa apapun dan user bisa memilih tema apa yang akan dipelajari berdasarkan learning material yang sudah dimasukan ke folder `learning_material`. Aplikasi juga bisa memandu bagaimana agar proses pembelajaran berjalan efektif dan efisien.

Aplikasi web lokal (FastAPI) yang mengubah materi PDF/DOCX/TXT/MD menjadi alur belajar: ringkasan → tanya jawab berbasis materi (RAG) → kuis → flashcards dengan pengulangan terjadwal (SM-2).

## Fitur

- **Pilih tema** — tiap file/subfolder di `learning_material/` menjadi satu tema.
- **Ringkasan** — poin kunci tiap tema.
- **Tanya materi** — jawaban berdasar potongan materi, lengkap dengan sitasi sumber.
- **Kuis** — pilihan ganda otomatis dari materi, lengkap dengan pembahasan; kesalahan berulang dicatat sebagai konsep yang membingungkan.
- **Review** — flashcards + SM-2 spaced repetition dan daftar kartu jatuh tempo.
- **Progres per tema** — skor kuis, kartu jatuh tempo, konsep lemah.

## Cara pakai

Syarat: Python >= 3.10.

```powershell
pip install -e ".[test]"
python -m uvicorn app.main:app --port 8000
```

Buka http://localhost:8000 untuk meja belajar: daftar tema, halaman baca, form tanya, kuis interaktif, dan review kartu — seluruh alur belajar bisa dipakai dari browser. API JSON-nya tetap tersedia untuk akses terprogram.

1. Taruh materi (PDF/DOCX/TXT/MD) sebagai file atau subfolder di `learning_material/`.
2. Klik **Rescan** (`POST /rescan`).
3. Baca ringkasan: `GET /themes/{id}`.
4. Bertanya: `POST /themes/{id}/ask` dengan `{"question": "..."}`.
5. Kuis: `GET /themes/{id}/quiz` untuk soal, lalu `POST /themes/{id}/quiz` dengan `{"items": [...], "answers": [...]}` untuk nilai.
6. Review: `GET /themes/{id}/review` untuk kartu jatuh tempo, lalu `POST /themes/{id}/review` dengan `{"card_id": "...", "quality": 4}` (0–5).

Dokumentasi API interaktif tersedia di http://localhost:8000/docs. Tes: `pytest -q`. Rute yang sama melayani HTML untuk browser (header `Accept: text/html` atau form) dan JSON untuk API.

## Privasi & offline

Berjalan 100% offline secara default (mode SAFE, tanpa API key; Ollama lokal opsional via `LT_SAFE=0`). Isi `learning_material/` dan database lokal `data/app.db` bersifat pribadi dan tidak ikut ter-commit ke git.

## Model AI lokal (Ollama, opsional)

Tanpa Ollama, ringkasan dan jawaban berupa kutipan potongan materi (mode SAFE). Dengan model lokal, keduanya menjadi penjelasan yang disusun AI namun tetap berdasar pada materi yang dikutip.

1. Pasang Ollama dari https://ollama.com/download (Windows: installer resmi, service jalan otomatis).
2. Unduh model yang muat di laptop — mulai dari yang kecil:
   ```powershell
   ollama pull llama3.2:3b
   ```
   Alternatif: `qwen2.5:3b` (ringan) atau `llama3.1` (8B, butuh ±8 GB RAM).
3. Jalankan aplikasi dengan mode LLM aktif (model bisa diganti via `LT_MODEL`):
   ```powershell
   $env:LT_SAFE = "0"; $env:LT_MODEL = "llama3.2:3b"; python -m uvicorn app.main:app --port 8000
   ```
4. Uji di halaman Tanya: jawaban kini berupa uraian, tetap berdasar potongan materi dan bersitasi.

Catatan: yang dipakai LLM hanya ringkasan dan tanya jawab. Kuis, flashcards, dan penjadwalan SM-2 tetap deterministik (tanpa LLM) agar stabil dan cepat. Jika Ollama mati saat `LT_SAFE=0`, aplikasi otomatis mundur ke mode SAFE. Jawaban pertama bisa lambat (puluhan detik di CPU) karena 5 potongan materi dikirim sebagai konteks.

## Lisensi

GPLv3 — lihat `LICENSE`.
