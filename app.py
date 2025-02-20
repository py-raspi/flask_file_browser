from flask import Flask, render_template, send_from_directory, make_response, request
import os
import subprocess
import hashlib
import threading
import time
import sqlite3
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
import exifread
from datetime import datetime
from flask import jsonify
import psutil
from dotenv import load_dotenv

load_dotenv("env.env")
SSD_UUID = os.getenv("SSD_UUID")
SHARED_FOLDER = os.getenv("SHARED_FOLDER")
VENV_PATH = os.getenv("VENV_PATH") + "/bin/python"
SYNC_DB_AND_THUMBNAILS = os.getenv("SYNC_DB_AND_THUMBNAILS")
PORT = os.getenv("PORT")

app = Flask(__name__)
THUMBNAIL_FOLDER = os.path.join(SHARED_FOLDER, ".thumbnails")
os.makedirs(THUMBNAIL_FOLDER, exist_ok=True)
DB_PATH = os.path.join(SHARED_FOLDER, ".metadata.db")

def get_smart_status():
    cmd = f"lsblk -o UUID,NAME | grep {SSD_UUID}"
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    if not result.stdout:
        return {"status": "不明", "details": "デバイスが見つかりません"}
    dev_name = result.stdout.split()[1]
    dev_path = f"/dev/{dev_name}"
    cmd = f"sudo smartctl -A {dev_path}"
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    smart_data = result.stdout.split("\n") if result.stdout else []
    temp = "不明"
    reallocated = 0
    pending = 0
    for line in smart_data:
        if "Temperature_Celsius" in line:
            temp = line.split()[-1] + "°C"
        if "Reallocated_Sector_Ct" in line:
            reallocated = int(line.split()[9])
        if "Current_Pending_Sector" in line:
            pending = int(line.split()[9])
    if temp == "不明":
        cmd = f"sudo nvme smart-log /dev/{dev_name}| grep 'temperature'"
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        if result.stdout:
            try:
                for line in result.stdout.split("\n"):
                    if "temperature" in line.lower():
                        temp = line.split(":")[1].split("(")[0].strip()
                        break
            except ValueError:
                temp = "不明"
    if reallocated == 0 and pending == 0:
        status = '<i class="fa-solid fa-check-circle" style="color: green;"></i> 正常'
    elif reallocated > 0 or pending > 0:
        status = '<i class="fa-solid fa-exclamation-circle" style="color: yellow;"></i> 注意'
    if reallocated >= 10 or pending >= 10:
        status = '<i class="fa-solid fa-times-circle" style="color: red;"></i> 危険'
    return {
        "status": status,
        "temperature": temp,
        "reallocated": reallocated,
        "pending": pending
    }

def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS thumbnails (
            path TEXT PRIMARY KEY,
            thumbnail_path TEXT,
            is_video INTEGER
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS metadata (
            path TEXT PRIMARY KEY,
            name TEXT,
            date TEXT
        )
    """)
    conn.commit()
    conn.close()

init_db()

def get_thumbnail_path(original_path):
    filename_hash = hashlib.md5(original_path.encode()).hexdigest() + ".webp"
    return os.path.join(THUMBNAIL_FOLDER, filename_hash)

def save_thumbnail_info(file_path, thumbnail_path, is_video):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("INSERT OR REPLACE INTO thumbnails (path, thumbnail_path, is_video) VALUES (?, ?, ?)",
                   (file_path, thumbnail_path, int(is_video)))
    conn.commit()
    conn.close()

def generate_and_save_thumbnail(input_path, output_path, is_video=False):
    if os.path.exists(output_path):
        return True
    try:
        if input_path.lower().endswith(".heic"):
            converted_path = input_path + ".jpg"
            subprocess.run(["convert", input_path, converted_path], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            input_path = converted_path
        cmd = [
            "ffmpeg", "-noaccurate_seek", "-i", input_path, "-ss", "00:00:01", "-vframes", "1",
            "-vf", "crop=in_w:in_h,scale=150:150:force_original_aspect_ratio=1", 
            "-q:v", "30", "-y", output_path
        ] if is_video else [
            "ffmpeg", "-i", input_path, "-vf", "scale=150:150:force_original_aspect_ratio=1", 
            "-q:v", "30", "-y", output_path
        ]
        subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        if os.path.exists(output_path):
            save_thumbnail_info(input_path, output_path, is_video)
        return os.path.exists(output_path)
    except Exception as e:
        print(f"サムネイル作成エラー: {e}")
        return False

def get_directory_contents(path):
    directories = []
    images = []
    videos = []
    if os.path.exists(path):
        for item in sorted(os.listdir(path)):
            full_path = os.path.join(path, item)
            if os.path.isdir(full_path) and not item.startswith('.') and item != "lost+found":
                directories.append(item)
            else:
                ext = os.path.splitext(item)[1].lower()
                if ext in {'.png', '.jpg', '.jpeg', '.gif', '.heic'}:
                    images.append(item)
                elif ext in {'.mp4', '.avi', '.mov', '.mkv'}:
                    videos.append(item)
    return directories, images, videos

def get_metadata(file_path):
    ext = os.path.splitext(file_path)[1].lower()
    if ext in {'.jpg', '.jpeg', '.png', '.gif', '.heic'}:
        try:
            with open(file_path, 'rb') as f:
                tags = exifread.process_file(f)
            date = tags.get("EXIF DateTimeOriginal", None)
            if date:
                return str(date).replace(":", "/", 2)
            return "不明"
        except Exception:
            return "不明"
    elif ext in {'.mp4', '.avi', '.mov', '.mkv'}:
        try:
            cmd = [
                "ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries",
                "format_tags=creation_time", "-of", "default=noprint_wrappers=1:nokey=1", file_path
            ]
            result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True)
            date_str = result.stdout.strip()
            if date_str:
                try:
                    dt = datetime.strptime(date_str, "%Y-%m-%dT%H:%M:%S.%fZ")
                except ValueError:
                    try:
                        dt = datetime.strptime(date_str, "%Y-%m-%dT%H:%M:%SZ")
                    except ValueError:
                        return "不明"
                return dt.strftime("%Y/%m/%d %H:%M:%S")
            return "不明"
        except Exception:
            return "不明"
    return "不明"

def save_metadata(file_path):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    file_name = os.path.basename(file_path)
    date = get_metadata(file_path)
    cursor.execute("INSERT OR REPLACE INTO metadata (path, name, date) VALUES (?, ?, ?)",
                   (file_path, file_name, date))
    conn.commit()
    conn.close()

def get_files_with_metadata(directory, file_list):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    files = []
    for file in file_list:
        file_path = os.path.join(directory, file)
        cursor.execute("SELECT name, date FROM metadata WHERE path=?", (file_path,))
        row = cursor.fetchone()
        if not row:
            save_metadata(file_path)
            cursor.execute("SELECT name, date FROM metadata WHERE path=?", (file_path,))
            row = cursor.fetchone()
        try:
            file_date = datetime.strptime(row[1], "%Y/%m/%d %H:%M:%S") if row[1] != "不明" else datetime.min
        except ValueError:
            file_date = datetime.min
        files.append({
            "path": file,
            "name": row[0],
            "date": row[1],
            "file_date": file_date,
            "isVideo": file.endswith(('.mp4', '.avi', '.mov', '.mkv'))
        })
    conn.close()
    return sorted(files, key=lambda x: x["file_date"], reverse=True)

@app.route('/')
@app.route('/<path:subpath>')
def index(subpath=''):
    current_path = os.path.join(SHARED_FOLDER, subpath)
    if not os.path.exists(current_path):
        return "Directory not found", 404
    directories, images, videos = get_directory_contents(current_path)
    image_data = get_files_with_metadata(current_path, images)
    video_data = get_files_with_metadata(current_path, videos)
    breadcrumbs = [{'name': 'ルート', 'path': ''}]
    path_parts = subpath.split('/') if subpath else []
    for i in range(len(path_parts)):
        breadcrumbs.append({'name': path_parts[i], 'path': '/'.join(path_parts[:i+1])})
    return render_template('index.html', directories=directories, images=image_data, videos=video_data, breadcrumbs=breadcrumbs, subpath=subpath)

@app.route('/files/<path:filepath>')
def get_file(filepath):
    directory = os.path.join(SHARED_FOLDER, os.path.dirname(filepath))
    filename = os.path.basename(filepath)
    response = make_response(send_from_directory(directory, filename))
    response.headers['Cache-Control'] = 'public, max-age=86400'
    return response

@app.route('/thumbnail/<path:filepath>')
def get_thumbnail(filepath):
    original_path = os.path.join(SHARED_FOLDER, filepath)
    thumbnail_path = get_thumbnail_path(original_path)
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT thumbnail_path FROM thumbnails WHERE path=?", (original_path,))
    row = cursor.fetchone()
    conn.close()
    if row and os.path.exists(row[0]):
        return send_from_directory(THUMBNAIL_FOLDER, os.path.basename(row[0]))
    ext = os.path.splitext(filepath)[1].lower()
    is_video = ext in {'.mp4', '.avi', '.mov', '.mkv'}
    generate_and_save_thumbnail(original_path, thumbnail_path, is_video)
    return send_from_directory(THUMBNAIL_FOLDER, os.path.basename(thumbnail_path))

@app.route('/delete/<path:filepath>', methods=['DELETE'])
def delete_file(filepath):
    full_path = os.path.join(SHARED_FOLDER, filepath)
    thumbnail_path = get_thumbnail_path(full_path)
    try:
        if os.path.exists(full_path):
            os.remove(full_path)
        if os.path.exists(thumbnail_path):
            os.remove(thumbnail_path)
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("DELETE FROM metadata WHERE path=?", (full_path,))
        cursor.execute("DELETE FROM thumbnails WHERE path=?", (full_path,))
        conn.commit()
        conn.close()
        return {"success": True}
    except Exception as e:
        print(f"削除エラー: {e}")
        return {"success": False}, 500

@app.route('/shutdown', methods=['POST'])
def shutdown():
    try:
        subprocess.run(["sudo", "shutdown", "-h", "now"])
        return jsonify({"success": True})
    except Exception as e:
        print(f"シャットダウンエラー: {e}")
        return jsonify({"success": False}), 500

@app.route('/smart')
def smart_info():
    return jsonify(get_smart_status())

@app.route('/storage_info')
def storage_info():
    try:
        cmd = f"lsblk -o UUID,MOUNTPOINT | grep {SSD_UUID}"
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        if not result.stdout:
            return jsonify({"success": False, "error": "ストレージが見つかりません"})
        mount_point = result.stdout.split()[1]
        statvfs = os.statvfs(mount_point)
        total_size = statvfs.f_frsize * statvfs.f_blocks 
        free_size = statvfs.f_frsize * statvfs.f_bfree
        used_size = total_size - free_size 
        usage_percent = (used_size / total_size) * 100 
        return jsonify({
            "success": True,
            "total": total_size,
            "used": used_size,
            "free": free_size,
            "percent": usage_percent
        })
    except Exception as e:
        print(f"ストレージ情報取得エラー: {e}")
        return jsonify({"success": False, "error": "情報取得に失敗しました"})

@app.route('/reset_db', methods=['POST'])
def reset_db():
    try:
        if os.path.exists(DB_PATH):
            os.remove(DB_PATH)
        init_db()
        return jsonify({"success": True})
    except Exception as e:
        print(f"DBリセットエラー: {e}")
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/run_sync', methods=['POST'])
def run_sync():
    try:
        subprocess.Popen([VENV_PATH, SYNC_DB_AND_THUMBNAILS])
        return jsonify({"success": True})
    except Exception as e:
        print(f"同期エラー: {e}")
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/system_info')
def system_info():
    try:
        cpu_usage = psutil.cpu_percent(interval=1)
        temp_cmd = "vcgencmd measure_temp"
        temp_output = subprocess.run(temp_cmd, shell=True, capture_output=True, text=True).stdout.strip()
        cpu_temp = temp_output.replace("temp=", "").replace("'C", "°C")
        mem = psutil.virtual_memory()
        mem_usage = f"{mem.percent}%"
        return jsonify({
            "cpu_usage": f"{cpu_usage}%",
            "cpu_temp": cpu_temp,
            "mem_usage": mem_usage
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=PORT, debug=False)