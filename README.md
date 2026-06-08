# ESP32 Morse Decoder & Web Server with NLP (Soon)

Sistem Internet of Things (IoT) berbasis mikrokontroler ESP32 yang berfungsi untuk menerjemahkan ketukan sandi Morse fisik menjadi teks standar internasional (Alfabet, Angka, dan Simbol) secara *real-time*. Sistem ini beroperasi sebagai *Standalone Web Server*, yang memungkinkan hasil terjemahan ditampilkan langsung ke halaman web peramban (browser) melalui jaringan Wi-Fi lokal tanpa memerlukan server komputer tambahan.

---

## Arsitektur & Tech Stack

Sistem ini dibangun menggunakan arsitektur *Client-Server* terpusat secara mandiri di dalam satu cip mikrokontroler. 

* **Hardware / Mikrokontroler:** Mikrokontroler ESP32 (mendukung Wi-Fi 2.4 GHz).
* **Firmware & Backend:** MicroPython.
* **Protokol Jaringan:** Raw TCP Sockets (menggunakan library `socket` bawaan) berjalan di atas IPv4.
* **Frontend Web UI:** HTML5, CSS3, dan Vanilla JavaScript (di-host langsung di dalam memori ESP32).
* **Metode Komunikasi Web:** Server-Sent Events (SSE) / Async Fetching via JavaScript untuk pembaruan antarmuka *non-blocking*.

---

## Kebutuhan Perangkat Keras (Hardware)

Berikut adalah daftar komponen dan topologi *pinout* (jalur kabel) yang digunakan dalam rangkaian proyek ini:

| Komponen FIsik | Pin ESP32 | Konfigurasi Program | Fungsi Utama |
| :--- | :--- | :--- | :--- |
| **Push Button 1** | `GPIO 5` | `Pin.IN`, `Pin.PULL_UP` | Menginput sandi Morse (Dot `.` & Dash `-`). |
| **Push Button 2** | `GPIO 18` | `Pin.IN`, `Pin.PULL_UP` | Menerjemahkan/Submit kode (1x), Membuat Spasi (2x). |
| **Push Button 3** | `GPIO 19` | `Pin.IN`, `Pin.PULL_UP` | Mempublikasikan (Publish) draf kalimat ke Web UI. |
| **Active Buzzer** | `GPIO 22` | `Pin.OUT` | Indikator *feedback* suara saat tombol ditekan. |
| **LED** | `GPIO 21` | `Pin.OUT` | Indikator *feedback* cahaya visual. |

---

## Alur Pemrosesan (Input ke Output)

Sistem bekerja melalui tahapan pemrosesan biner dari interaksi fisik hingga menjadi data visual di layar peramban:

1.  **Deteksi Input Fisik (Debouncing):** Pengguna menekan Tombol Morse (GP5). Sistem mendeteksi penurunan voltase listrik dan menghitung durasi tahanan tombol menggunakan *stopwatch* milidetik (`time.ticks_ms`). Getaran mekanis di bawah 50ms diabaikan.
2.  **Klasifikasi Biner (Dot/Dash):** Durasi tahanan dikalkulasi. Tekanan kurang dari 0.2 detik dicatat sebagai Titik (`.`), sedangkan tekanan yang lebih lama dicatat sebagai Garis (`-`).
3.  **Pencocokan Kamus (Dictionary Lookup):** Saat Tombol Submit (GP18) ditekan, kumpulan string sandi sementara (misal: `...`) akan dicocokkan dengan *Hash Map / Dictionary* bawaan untuk diubah menjadi karakter tunggal (misal: `S`) dan disimpan ke memori Draf Lokal.
4.  **Publikasi Jaringan (Socket Broadcast):** Saat Tombol Send (GP19) ditekan, kalimat utuh di dalam Draf Lokal dikunci dan dipindahkan ke variabel `status` publik.
5.  **Penyajian Web (Frontend Display):** Skrip JavaScript di peramban pengunjung secara terus-menerus (tiap 1 detik) melakukan *request* HTTP ringan (`fetch`) ke ESP32. Jika ada pembaruan teks, layar langsung menampilkannya secara *real-time* tanpa memuat ulang (refresh) halaman secara penuh.

---

## Panduan Pemasangan IoT & Instalasi

### 1. Perakitan Sirkuit Fisik
* Tancapkan ESP32 pada *breadboard*.
* Hubungkan salah satu kaki dari ketiga *push button* ke pin **GPIO 5, 18, dan 19**. Hubungkan kaki satunya lagi dari masing-masing tombol langsung ke pin **GND (Ground)**.
* Hubungkan kutub positif (kaki panjang) Buzzer ke **GPIO 22** dan LED ke **GPIO 21** (gunakan resistor 220 Ohm untuk LED jika diperlukan). Hubungkan kutub negatif keduanya ke **GND**.

### 2. Konfigurasi Perangkat Lunak
* Buka file `main.py` menggunakan IDE andalan (seperti VS Code dengan ekstensi MicroPico atau Arduino Lab for MicroPython).
* Pada bagian atas kode, ubah variabel koneksi jaringan sesuai dengan Wi-Fi lokal yang tersedia:
    ```python
    WIFI_SSID = "Nama_WiFi_Anda"
    WIFI_PASSWORD = "Password_WiFi_Anda"
    ```
* Simpan dan unggah (Flash/Run) kode `main.py` tersebut ke dalam penyimpanan (storage) internal ESP32.

### 3. Eksekusi Program
* Tekan tombol **EN (Reset)** pada ESP32.
* Buka antarmuka Serial Monitor/Terminal di IDE. Tunggu hingga ESP32 terhubung ke Wi-Fi dan memunculkan alamat IP lokal (Contoh: `192.168.1.15`).
* Buka peramban web di laptop atau *smartphone* yang berada di jaringan Wi-Fi yang sama, lalu ketikkan alamat IP tersebut.
* Sistem Morse mandiri siap digunakan!

---

## Kekurangan

Program ini merupakan fondasi purwarupa transmisi tingkat rendah yang berhasil berjalan stabil. Namun, karena keterbatasan kapabilitas dasar (*raw capabilities*), sistem ini masih memiliki beberapa batasan yang membuka peluang besar untuk pengembangan selanjutnya:

* **No Error Correction:** Saat ini, sistem menerima dan menerjemahkan input sandi Morse secara mutlak (harfiah). Jika pengguna salah mengetuk kode ( *typo* mekanis), sistem akan langsung menghasilkan karakter acak yang salah. Sangat disarankan untuk mengintegrasikan pendekatan **Natural Language Processing (NLP)** di masa mendatang yang dapat menganalisis konteks deretan huruf dan melakukan swakoreksi menjadi kata yang memiliki arti valid.
* **Kapasitas Server Ringan:** Karena menggunakan implementasi `socket` primitif secara *non-blocking* dan bukan *production web server* (seperti microdot), ESP32 dapat mengalami penurunan responsivitas atau *crash* internal jika halaman webnya diakses oleh terlalu banyak perangkat secara bersamaan.
* **Hardcoded:** Kredensial Wi-Fi saat ini ditanamkan langsung (hardcoded) di dalam program. Diperlukan pengembangan fitur *Captive Portal* agar pengguna dapat mengganti jaringan Wi-Fi secara fleksibel tanpa harus menulis ulang kode melalui komputer.