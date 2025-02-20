import os
import sys
import sqlite3
import hashlib
import subprocess
from datetime import datetime
from dotenv import load_dotenv
load_dotenv("env.env")

VENV_PATH = os.getenv("VENV_PATH")
activate_script = os.path.join(VENV_PATH, "bin", "activate_this.py")
if os.path.exists(activate_script):
    exec(open(activate_script).read(), {'__file__': activate_script})

SHARED_FOLDER = os.getenv("SHARED_FOLDER")
THUMBNAIL_FOLDER = os.path.join(SHARED_FOLDER, ".thumbnails")
DB_PATH = os.path.join(SHARED_FOLDER, ".metadata.db")
LOG_FILE = os.path.join(SHARED_FOLDER, ".sync_log.txt")

if os.path.exists(os.path.join(SHARED_FOLDER, "sync_log.txt")):
    os.rename(os.path.join(SHARED_FOLDER, "sync_log.txt"), LOG_FILE)

IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".gif", ".heic"}
VIDEO_EXTENSIONS = {".mp4", ".avi", ".mov", ".mkv"}

def log_message(message):
    """ログを記録"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(LOG_FILE, "a") as log_file:
        log_file.write(f"[{timestamp}] {message}\n")
    print(message)

def get_thumbnail_path(file_path):
    """サムネイルのファイルパスを取得"""
    filename_hash = hashlib.md5(file_path.encode()).hexdigest() + ".webp"
    return os.path.join(THUMBNAIL_FOLDER, filename_hash)

def scan_actual_files():
    """実際のフォルダ内のファイル一覧を取得"""
    actual_files = set()
    for root, _, files in os.walk(SHARED_FOLDER):
        for file in files:
            if file.startswith("."):
                continue
            file_path = os.path.join(root, file)
            relative_path = os.path.relpath(file_path, SHARED_FOLDER)
            actual_files.add(relative_path)
    return actual_files

def scan_db_files():
    """DB 内の登録ファイル一覧を取得"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT path FROM metadata")
    db_files = {row[0] for row in cursor.fetchall()}
    conn.close()
    return db_files

def remove_db_entry(file_path):
    """DB からファイルのエントリを削除"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM metadata WHERE path=?", (file_path,))
    cursor.execute("DELETE FROM thumbnails WHERE path=?", (file_path,))
    conn.commit()
    conn.close()
    log_message(f"🗑️ DBエントリ削除: {file_path}")

def remove_thumbnail(file_path):
    """該当サムネイルを削除"""
    thumbnail_path = get_thumbnail_path(file_path)
    if os.path.exists(thumbnail_path):
        os.remove(thumbnail_path)
        log_message(f"🗑️ サムネイル削除: {thumbnail_path}")

def add_file_to_db(file_path):
    """ファイルをDBに追加（メタデータ取得含む）"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    file_name = os.path.basename(file_path)
    date = "不明"
    ext = os.path.splitext(file_name)[1].lower()

    if ext in IMAGE_EXTENSIONS:
        try:
            import exifread
            with open(os.path.join(SHARED_FOLDER, file_path), 'rb') as f:
                tags = exifread.process_file(f)
            date = str(tags.get("EXIF DateTimeOriginal", "不明")).replace(":", "/", 2)
        except Exception:
            pass
    elif ext in VIDEO_EXTENSIONS:
        try:
            cmd = [
                "ffprobe", "-v", "error", "-select_streams", "v:0",
                "-show_entries", "format_tags=creation_time",
                "-of", "default=noprint_wrappers=1:nokey=1",
                os.path.join(SHARED_FOLDER, file_path)
            ]
            result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True)
            date = result.stdout.strip() if result.stdout else "不明"
        except Exception:
            pass

    cursor.execute("INSERT OR REPLACE INTO metadata (path, name, date) VALUES (?, ?, ?)", (file_path, file_name, date))
    conn.commit()
    conn.close()
    log_message(f"✅ DB追加: {file_path} (撮影日: {date})")

def sync_files():
    """DB・サムネを実際のファイルと同期"""
    log_message("🔄 同期処理開始")
    actual_files = scan_actual_files()
    db_files = scan_db_files()
    for file_path in db_files - actual_files:
        remove_db_entry(file_path)
        remove_thumbnail(file_path)
    for file_path in actual_files - db_files:
        add_file_to_db(file_path)
    log_message("✅ 同期完了")

if __name__ == "__main__":
    sync_files()