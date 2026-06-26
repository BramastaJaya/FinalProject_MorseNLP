# ESP32 Morse Decoder with FastAPI NLP Backend

Sistem IoT berbasis ESP32 untuk menerjemahkan input tombol Morse menjadi teks, kalimat dikonversi dikirim menuju ke backend FastAPI melalui Wi-Fi lokal. Backend menampilkan halaman web lokal dan menjalankan dua model koreksi teks bahasa Indonesia:

- **N-gram spell checker**: `model/n_gram/ngram_spell_checker.py`
- **RNN spell checker**: `model/RNN/specil_rnn_spellchecker.py`

Backend menampilkan tiga keluaran utama: teks mentah dari ESP32, hasil koreksi n-gram, dan hasil koreksi RNN.

---

## Arsitektur

```text
ESP32 + tombol Morse
-> MicroPython main.py
-> Wi-Fi lokal
-> FastAPI backend di laptop
-> n-gram + RNN spell checker
-> browser lokal
```

Komponen utama:

- `main.py`: firmware MicroPython untuk ESP32. Membaca tombol Morse dan mengirim kalimat ke backend.
- `app.py`: backend FastAPI dan halaman web.
- `model/model_pipeline.ipynb`: notebook untuk split SPECIL, train n-gram, train RNN, dan verifikasi artifact.
- `model/specil_train.csv`: data latih gabungan dari semua CSV SPECIL.
- `model/specil_test.csv`: data uji SPECIL yang tidak dipakai saat training.
- `model/n_gram/`: model n-gram yang dilatih dari `specil_train.csv`.
- `model/RNN/`: model TensorFlow/Keras RNN yang dilatih dari `specil_train.csv`.
- `test_backend_app.py`: tes sederhana backend.

---

## Hardware

| Komponen | Pin ESP32 | Fungsi |
| :--- | :--- | :--- |
| Push Button 1 | `GPIO 5` | Input Morse dot/dash |
| Push Button 2 | `GPIO 18` | Submit kode Morse / spasi |
| Push Button 3 | `GPIO 19` | Kirim kalimat ke backend |
| Active Buzzer | `GPIO 22` | Feedback suara |
| LED | `GPIO 21` | Feedback visual |

---

## Setup Backend Laptop

Gunakan environment Python lokal `.env`.

Install dependency:

```powershell
.env\python.exe -m pip install -r requirements.txt
```

Jalankan backend dari root project:

```powershell
.env\python.exe -m uvicorn app:app --host 0.0.0.0 --port 8000
```

Buka web lokal:

```text
http://localhost:8000
```

Untuk perangkat lain di Wi-Fi yang sama, pakai IP laptop. Contoh:

```text
http://10.230.213.13:8000
```

Catatan: `0.0.0.0` hanya untuk menjalankan server, bukan alamat browser.

---

## Setup ESP32

Di `main.py`, sesuaikan Wi-Fi dan IP backend laptop:

```python
wifi_name = "Nama_WiFi"
password = "Password_WiFi"
BACKEND_HOST = "Your local IP"
BACKEND_PORT = 8000
```

ESP32 mengirim teks ke backend melalui:

```text
GET /api/esp32?text=...
```

Jika ESP32 masih mengirim versi lama:

```text
POST /api/message
```

backend tetap menerima route tersebut untuk kompatibilitas.

---

## API Backend

Koreksi teks manual:

```powershell
Invoke-RestMethod "http://localhost:8000/api/esp32?text=ak%20mw%20makn"
```

Endpoint yang tersedia:

- `GET /`
- `GET /api/latest`
- `GET /api/status`
- `GET /api/esp32?text=...`
- `POST /api/esp32`
- `POST /api/message`
- `POST /api/correct`

---

## Menjalankan Tes

Tes backend:

```powershell
.env\python.exe test_backend_app.py
```

Tes RNN:

```powershell
.env\python.exe model\RNN\test_specil_rnn_spellchecker.py
```

Tes model langsung:

```powershell
.env\python.exe model\RNN\specil_rnn_spellchecker.py correct "ak mw makn"
```

Bangun ulang split SPECIL dan latih ulang model jika dataset mentah berubah:

Buka dan jalankan semua cell di `model/model_pipeline.ipynb`.

---
