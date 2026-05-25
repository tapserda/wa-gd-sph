# WAGD - WhatsApp Bridge to Google Drive & Google Sheet

Proyek otomasi hibrida untuk mencadangkan (backup) setiap file media (Gambar, Video, Dokumen, Audio/Voice Note) dari WhatsApp secara otomatis ke **Google Drive**, sekaligus berfungsi sebagai **Scheduler Reminder Otomatis** berbasis data dari **Google Sheets**.

## ✨ Fitur Utama
- **Auto-Media Backup**: Mengunduh media dari chat masuk maupun pesan yang dikirim oleh akun Anda sendiri, lalu menyimpannya langsung ke folder Google Drive tertentu.
- **Session Persistence**: File login `neonize.db` otomatis dicadangkan ke Google Drive. Bot kebal terhadap restart server cloud dan tidak akan meminta scan QR ulang.
- **Google Sheet Scheduler**: Mengirim pesan pengingat WhatsApp secara otomatis setiap jam berdasarkan jadwal yang ditentukan pada baris spreadsheet.
- **Timezone Synchronized**: Jam internal scheduler sudah disinkronkan menggunakan Zona Waktu **WIB (GMT+7)** meskipun dijalankan di server luar negeri.

---

## 🛠️ Panduan Langkah Persiapan

### Langkah 1: Persiapan Google Sheets & Google Drive
1. Buat sebuah Spreadsheet baru di Google Sheets.
2. Buat tabel pada **Sheet1** dengan struktur kolom utama pada baris pertama seperti ini:
   - Kolom A: `nama`
   - Kolom B: `no_hp` (Format angka murni diawali kode negara, contoh: `628123456xxx`)
   - Kolom C: `jam` (Format angka 0-23, contoh: `22` untuk jam 10 malam)
   - Kolom D: `pesan`
   - Kolom E: `status`
3. Buat sebuah folder kosong baru di Google Drive Anda untuk menampung file backup media.

### Langkah 2: Deploy Google Apps Script
1. Di dalam Google Sheets Anda, klik menu **Ekstensi** > **Apps Script**.
2. Hapus semua kode bawaan, lalu pasang skrip penanganan API Apps Script milik Anda (skrip yang mengurus penanganan aksi `sync_session`, `upload_media`, `Tasks/Reminders`, dan `update_status`).
3. Isi variabel ID Folder Drive dan ID Spreadsheet di dalam skrip tersebut dengan data milik Anda.
4. Klik tombol **Terapkan (Deploy)** di pojok kanan atas > **Terapkan Baru (New Deployment)**.
5. Setel konfigurasinya:
   - **Jenis elemen**: `Aplikasi Web (Web App)`
   - **Yang menjalankan**: `Diri Anda sendiri`
   - **Siapa yang memiliki akses**: `Siapa saja (Anyone)`
6. Klik **Terapkan**, setujui semua izin akses akun Google, lalu salin **URL Aplikasi Web** yang diberikan (akhiran `/exec`).

---

## 🚀 Cara Menjalankan Aplikasi

Proyek ini dikemas menggunakan Docker sehingga sangat mudah dijalankan di platform mana pun.

### Opsi A: Deployment via Hugging Face Spaces (Direkomendasikan - Gratis 100%)
1. Buat akun di [Hugging Face](https://huggingface.co/).
2. Buat Space baru: Klik Profil > **New Space**.
3. Isi nama Space, pilih SDK berupa **Docker**, lalu pilih template **Blank**.
4. Unggah file `main.py`, `requirements.txt`, dan `Dockerfile` ke dalam Space tersebut.
5. Masuk ke menu **Settings** di Space Anda, gulir ke bawah ke bagian **Variables and secrets**.
6. Tambahkan dua variabel lingkungan (**New variable**):
   - **Name**: `ENVIRONMENT` -> **Value**: `PRODUCTION`
   - **Name**: `APPS_SCRIPT_URL` -> **Value**: *[Tempel URL Google Apps Script Anda disini]*
7. Lakukan **Restart Space** dan pantau log kontainer untuk melakukan scan QR Code pada proses autentikasi pertama kali.

### Opsi B: Menggunakan Docker Lokal
Jalankan perintah berikut di terminal komputer Anda setelah mengklon repositori ini:

```bash
docker build -t whatsapp-bridge .
docker run -d \
  -p 7860:7860 \
  -e ENVIRONMENT=PRODUCTION \
  -e APPS_SCRIPT_URL="URL_APPS_SCRIPT_ANDA_DISINI" \
  --name wa-bot \
  whatsapp-bridge
```
## 🗂️ Struktur Proyek

1. ​main.py - Logika inti bot WhatsApp menggunakan FastAPI, Uvicorn, dan Neonize.
2. ​Dockerfile - Konfigurasi pembuatan image container Docker.
​3. requirements.txt - Daftar dependensi pustaka Python.
