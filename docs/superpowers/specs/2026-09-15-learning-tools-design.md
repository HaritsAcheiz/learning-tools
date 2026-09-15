# learning-tools — Design Spec (2026-09-15)

## 1. Tujuan & konteks
- Aplikasi web lokal untuk mempermudah pembelajaran. Materi apa pun ditaruh di `learning_material/`; user memilih tema lalu app memandu belajar efektif/efisien (README Indonesia).
- Status repo: greenfield. Hanya ada `README.md`, `learning_material/` (kosong), `.gitignore` Python, `LICENSE` GPLv3.
- Keputusan terkonfirmasi: bentuk **web lokal**, materi **PDF/Word campuran**, pendekatan **B: FastAPI + RAG + LLM**.

## 2. Basis riset (ringkas)
- Pola aplikasi sejenis (Studi, Quira, ONCard, ai-study-assistant, Vhalwan/learning-assistant): upload PDF → ekstraksi teks → ringkasan → kuis/MCQ → flashcards + spaced repetition → chat tanya materi → tracking progres.
- Teknik paling didukung bukti: spaced repetition + active recall/testing effect; pelengkap: Feynman/self-explanation, interleaving, elaborative interrogation.
- Stack umum: Streamlit untuk MVP cepat atau FastAPI + embeddings + FAISS + LLM (Ollama lokal atau BYOK Gemini/OpenAI/Claude). SRS: SM-2 sederhana → FSRS.

## 3. Arsitektur (disetujui)
- Monolit Python: **FastAPI** (API + web lokal) + **SQLite** (dokumen, chunk, kartu SRS, riwayat kuis, konsep bingung).
- Lapisan:
  - `ingest`: scan `learning_material/` (tiap file/subdir = satu tema) → ekstrak PDF (pypdf) + DOCX (python-docx) → bersihkan → chunk.
  - `retrieval`: embeddings + **FAISS** per-tema, fallback **NumPy** bila FAISS tak terinstal.
  - `learning`: RAG Q&A grounded + ringkasan + generator kuis + flashcards + SRS.
  - `llm`: abstraksi provider — default **Ollama lokal** (offline), opsional BYOK (Gemini/OpenAI/Claude).
- Batasan lisensi: hanya dependensi GPLv3-kompatibel.
- Host dev: Windows + PowerShell 5.1; perintah via `workdir`, hindari `cd`.

## 4. Komponen & alur data (disetujui)
1. **Theme picker**: scan saat start + tombol rescan; tiap file/subdir `learning_material/` = kartu tema. Jangan hapus folder ini.
2. **Ingest pipeline**: ekstrak → chunk ~500–800 token + overlap → simpan teks bersih ke SQLite → bangun/refresh index FAISS per-tema.
3. **Mode belajar**:
   - Baca: teks bersih + ringkasan AI per-chunk.
   - Tanya: RAG top-k chunk → jawab + sitasi chunk.
   - Kuis: MCQ dari chunk + pembahasan (jawaban benar + kenapa opsi lain salah); salah berulang → catat konsep bingung.
   - Review: flashcards + SRS (mulai **SM-2**, siap naik ke FSRS) + daftar kartu jatuh tempo.
4. **Progres**: skor kuis, kartu jatuh tempo, konsep lemah — semuanya per-tema.
5. Alur baku: pilih tema → ingest sekali → baca/ringkasan → tanya → kuis → review terjadwal.

## 5. Error handling (disetujui)
- File gagal ekstrak → error per-file, tema lain tetap jalan.
- FAISS absen → fallback NumPy otomatis.
- LLM/Ollama mati → **mode SAFE** deterministik (retrieval + template, kuis cloze sederhana) agar app tetap usable.
- Jawaban tanpa konteks cukup → tolak jawab + tunjukkan chunk yang ada; setiap jawaban AI wajib cantumkan sumber chunk.

## 6. Testing (disetujui)
- `pytest -q`: unit untuk chunking, retrieval (mock), SRS/SM-2, skoring kuis; mock LLM; skip tes FAISS bila `faiss-cpu` tak terinstal.
- Verifikasi manual per-fase: 1 tema PDF + 1 tema DOCX end-to-end.

## 7. Fase implementasi
- Fase 0: scaffold FastAPI + SQLite + theme picker + `AGENTS.md` tooling.
- Fase 1: ingest PDF/DOCX + chunk + uji.
- Fase 2: embeddings + retrieval FAISS + fallback NumPy.
- Fase 3: RAG Q&A grounded + ringkasan.
- Fase 4: kuis + pembahasan + konsep bingung.
- Fase 5: flashcards SRS + progres per-tema.
- Fase 6: polish web lokal + mode SAFE + docs.

## 8. Non-goals (YAGNI)
- Tanpa auth multi-user, tanpa deploy cloud, tanpa mobile, tanpa FSRS/Anki-sync di awal, tanpa mind-map video YouTube.
