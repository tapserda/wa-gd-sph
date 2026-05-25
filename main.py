import os
import base64
import requests
import asyncio
import uvicorn
from datetime import datetime, timedelta
from contextlib import asynccontextmanager
from fastapi import FastAPI
from neonize.client import NewClient
from neonize.events import ConnectedEv, MessageEv
from neonize.utils import build_jid

# --- KONFIGURASI UTAMA VIA ENVIRONMENT VARIABLES ⚙️ --- #
APPS_SCRIPT_URL = os.environ.get("APPS_SCRIPT_URL", "")
SESSION_FILE = "neonize.db"

app = FastAPI()

if not APPS_SCRIPT_URL:
    print("⚠️ PERINGATAN: APPS_SCRIPT_URL belum dikonfigurasi di Environment Variables!")

# --- 🔄 FUNGSI BRIDGE GOOGLE DRIVE & SHEET ---
def download_session_from_drive():
    if not APPS_SCRIPT_URL: return False
    print("🔄 Mengecek dan mengunduh session dari Google Drive...")
    try:
        response = requests.get(APPS_SCRIPT_URL, timeout=30)
        if "FILE_NOT_FOUND" in response.text:
            print("⚠️ Session belum ada di Drive. Silakan jalankan di lokal dulu untuk scan QR.")
            return False
        if "<html" in response.text.lower():
            print("❌ ERROR: URL Apps Script salah/terkunci! Google mengembalikan halaman login.")
            return False
            
        file_bytes = base64.b64decode(response.text)
        with open(SESSION_FILE, "wb") as f:
            f.write(file_bytes)
        print("✅ Session berhasil disinkronkan dari Google Drive!")
        return True
    except Exception as e:
        print(f"❌ Gagal sinkronisasi download session: {e}")
        return False

def upload_session_to_drive():
    if not APPS_SCRIPT_URL: return
    print("🔄 Mengunggah session terbaru ke Google Drive...")
    try:
        if not os.path.exists(SESSION_FILE): return
        with open(SESSION_FILE, "rb") as f:
            encoded_string = base64.b64encode(f.read()).decode('utf-8')
        
        payload = {"action": "sync_session", "file": encoded_string}
        res = requests.post(APPS_SCRIPT_URL, json=payload, timeout=30)
        
        if "SUCCESS_SYNC" in res.text:
            print("✅ Session di Google Drive berhasil diperbarui.")
        else:
            print(f"❌ Google Apps Script menolak file session. Respon: {res.text[:100]}")
    except Exception as e:
        print(f"❌ Gagal mengunggah session: {e}")

def save_incoming_media_to_drive(file_bytes, filename, mime_type):
    if not APPS_SCRIPT_URL: return
    print(f"📤 Mengunggah media {filename} ke Google Drive...")
    try:
        encoded_string = base64.b64encode(file_bytes).decode('utf-8')
        payload = {
            "action": "upload_media",
            "file": encoded_string,
            "filename": filename,
            "mime_type": mime_type
        }
        res = requests.post(APPS_SCRIPT_URL, json=payload, timeout=30)
        print(f"📩 [DEBUG MEDIA] Respon Google: [{res.status_code}] -> {res.text}")
    except Exception as e:
        print(f"❌ Gagal mengunggah media: {e}")


# --- LOGIKA BOT WHATSAPP (NEONIZE) ---
if os.environ.get('ENVIRONMENT') == 'PRODUCTION':
    download_session_from_drive()

client = NewClient(SESSION_FILE)

@client.event(ConnectedEv)
def on_connected(client: NewClient, v: ConnectedEv):
    print("🚀 Bot WhatsApp Berhasil Terhubung!")
    upload_session_to_drive()

@client.event(MessageEv)
def on_message(client: NewClient, v: MessageEv):
    msg = v.Message
    if not msg: return

    image_msg = getattr(msg, "imageMessage", None)
    video_msg = getattr(msg, "videoMessage", None)
    document_msg = getattr(msg, "documentMessage", None)
    audio_msg = getattr(msg, "audioMessage", None)

    image_mime = getattr(image_msg, "mimetype", "") or getattr(image_msg, "mimeType", "") if image_msg else ""
    video_mime = getattr(video_msg, "mimetype", "") or getattr(video_msg, "mimeType", "") if video_msg else ""
    doc_mime = getattr(document_msg, "mimetype", "") or getattr(document_msg, "mimeType", "") if document_msg else ""
    audio_mime = getattr(audio_msg, "mimetype", "") or getattr(audio_msg, "mimeType", "") if audio_msg else ""

    # 1. GAMBAR
    if image_mime:
        try:
            print(f"📸 Menangkap pesan gambar baru...")
            file_bytes = client.download_any(msg)
            if file_bytes:
                filename = f"WA_Img_{int(datetime.now().timestamp())}.jpg"
                save_incoming_media_to_drive(file_bytes, filename, image_mime)
                return 
        except Exception as e: print(f"❌ Gagal unduh gambar: {e}")

    # 2. VIDEO
    elif video_mime:
        try:
            print(f"🎥 Menangkap pesan video baru...")
            file_bytes = client.download_any(msg)
            if file_bytes:
                filename = f"WA_Vid_{int(datetime.now().timestamp())}.mp4"
                save_incoming_media_to_drive(file_bytes, filename, video_mime)
                return 
        except Exception as e: print(f"❌ Gagal unduh video: {e}")

    # 3. DOKUMEN
    elif doc_mime:
        try:
            print(f"📄 Menangkap pesan dokumen baru...")
            file_bytes = client.download_any(msg)
            if file_bytes:
                filename = getattr(document_msg, "fileName", None) or getattr(document_msg, "filename", None) or f"WA_Doc_{int(datetime.now().timestamp())}"
                save_incoming_media_to_drive(file_bytes, filename, doc_mime)
                return 
        except Exception as e: print(f"❌ Gagal unduh dokumen: {e}")

    # 4. AUDIO / VOICE NOTE
    elif audio_mime:
        try:
            print(f"🎵 Menangkap pesan audio/voice note baru...")
            file_bytes = client.download_any(msg)
            if file_bytes:
                ext = "mp3" if "mp3" in audio_mime else "ogg"
                filename = f"WA_Audio_{int(datetime.now().timestamp())}.{ext}"
                save_incoming_media_to_drive(file_bytes, filename, audio_mime)
                return 
        except Exception as e: print(f"❌ Gagal unduh audio: {e}")


# --- BACKGROUND TASK: SCHEDULER REMINDER (ZONA WIB) ---
async def cek_dan_kirim_reminder():
    while True:
        if not APPS_SCRIPT_URL:
            await asyncio.sleep(60)
            continue
        try:
            sekarang_wib = datetime.utcnow() + timedelta(hours=7)
            jam_sekarang = sekarang_wib.hour
            print(f"⏰ [DEBUG SCHEDULER] Mengecek Sheet... Jam internal bot saat ini (WIB): {jam_sekarang}:00")
            
            if sekarang_wib.hour == 0 and sekarang_wib.minute == 0:
                requests.post(APPS_SCRIPT_URL, json={"action": "reset_status"}, timeout=30)
            
            res = requests.post(APPS_SCRIPT_URL, json={"action": "get_reminders"}, timeout=30)
            
            if res.status_code == 200:
                try: reminders = res.json()
                except Exception: reminders = []
                
                for r in reminders:
                    if r.get('no_hp'):
                        if int(r['jam']) == jam_sekarang and r['status'] != "Sent":
                            try:
                                target_jid = build_jid(str(int(r['no_hp'])))
                                print(f"     🚀 JAM COCOK! Mengirim reminder ke {r['nama']}...")
                                client.send_message(target_jid, r['pesan'])
                                
                                requests.post(APPS_SCRIPT_URL, json={
                                    "action": "update_status",
                                    "row_index": r['row_index'],
                                    "status": "Sent"
                                }, timeout=30)
                            except Exception as send_err:
                                print(f"     ❌ Gagal mengirim WA: {send_err}")
        except Exception as e:
            print(f"❌ Error pada scheduler reminder: {e}")
            
        await asyncio.sleep(60)


# --- KONFIGURASI LIFESPAN FASTAPI ---
@asynccontextmanager
async def lifespan(app: FastAPI):
    print("🔄 Memulai background tasks...")
    asyncio.create_task(cek_dan_kirim_reminder())
    loop = asyncio.get_event_loop()
    loop.run_in_executor(None, client.connect)
    yield
    print("🛑 Mematikan aplikasi server.")


app = FastAPI(lifespan=lifespan)

@app.get("/")
def home():
    return {"status": "WAGD Public Bot Active"}

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000)
