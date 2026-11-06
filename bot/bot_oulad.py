"""
bot_oulad.py - Bot yang mengirim OULAD dataset ke FastAPI Railway
Handle '?' sebagai missing value
"""

import pandas as pd
import requests
import time
from datetime import datetime, timezone
from pathlib import Path
import threading

# ============================================================
# KONFIGURASI
# ============================================================
API_BASE = "https://big-data-analytics-production.up.railway.app"
OULAD_DIR = "C:/Users/User/student-analytics/data/oulad"

CONFIG = {
    "batch_size": 100,
    "events_per_second": 50,
    "max_records": 50000,
    "request_timeout": 60,
}


# ============================================================
# HELPER
# ============================================================
def send_batch(endpoint: str, events: list) -> bool:
    url = f"{API_BASE}{endpoint}"
    # KOREKSI UTAMA: Bungkus list dengan {"events": ...}
    payload = {"events": events}
    
    try:
        r = requests.post(url, json=payload, timeout=CONFIG["request_timeout"])
        if r.status_code in [200, 201]:
            return True
        print(f"[WARN] {endpoint}: HTTP {r.status_code} — {r.text[:100]}")
        return False
    except Exception as e:
        print(f"[ERROR] {endpoint}: {e}")
        return False


def now_iso():
    return datetime.now(timezone.utc).isoformat()


def safe_int(val, default=0):
    if pd.isna(val):
        return default
    s = str(val).strip()
    if s == "?" or s == "" or s.lower() == "nan":
        return default
    try:
        return int(float(s))
    except (ValueError, TypeError):
        return default


def safe_float(val, default=0.0):
    if pd.isna(val):
        return default
    s = str(val).strip()
    if s == "?" or s == "" or s.lower() == "nan":
        return default
    try:
        return float(s)
    except (ValueError, TypeError):
        return default


def safe_str(val, default=""):
    if pd.isna(val):
        return default
    s = str(val).strip()
    if s == "?" or s.lower() == "nan":
        return default
    return s


# ============================================================
# BOT 1: VLE (studentVle.csv)
# ============================================================
def bot_vle():
    print("[OULAD-VLE] Started...")
    path = Path(OULAD_DIR) / "studentVle.csv"
    df = pd.read_csv(path)
    if CONFIG["max_records"]:
        df = df.head(CONFIG["max_records"])
    total = len(df)
    print(f"[OULAD-VLE] Total: {total:,}")
    
    batch = []
    sent = 0
    
    for idx, row in df.iterrows():
        batch.append({
            "sequence": idx + 1,
            "code_module": safe_str(row["code_module"]),
            "code_presentation": safe_str(row["code_presentation"]),
            "id_student": safe_int(row["id_student"]),
            "id_site": safe_int(row["id_site"]),
            "date": safe_int(row["date"]),
            "sum_click": safe_int(row["sum_click"]),
            "ingested_at": now_iso(),
            "bot_name": "bot-oulad-vle",
            "source": "studentVle.csv",
        })
        
        if len(batch) >= CONFIG["batch_size"]:
            if send_batch("/api/oulad/vle/batch", batch):
                sent += len(batch)
                if sent % 1000 == 0:
                    print(f"[OULAD-VLE] Sent: {sent:,}/{total:,}")
            batch = []
            time.sleep(CONFIG["batch_size"] / CONFIG["events_per_second"])
    
    if batch:
        send_batch("/api/oulad/vle/batch", batch)
    print(f"[OULAD-VLE] DONE. Total: {sent:,}")


# ============================================================
# BOT 2: ASSESSMENT
# ============================================================
def bot_assessment():
    print("[OULAD-ASSESS] Started...")
    path = Path(OULAD_DIR) / "studentAssessment.csv"
    df = pd.read_csv(path)
    if CONFIG["max_records"]:
        df = df.head(CONFIG["max_records"])
    total = len(df)
    print(f"[OULAD-ASSESS] Total: {total:,}")
    
    batch = []
    sent = 0
    skipped = 0
    
    for idx, row in df.iterrows():
        id_student = safe_int(row["id_student"])
        if id_student == 0:
            skipped += 1
            continue
        
        batch.append({
            "sequence": idx + 1,
            "id_assessment": safe_int(row["id_assessment"]),
            "id_student": id_student,
            "date_submitted": safe_int(row["date_submitted"]),
            "is_banked": safe_int(row["is_banked"]), 
            "score": safe_float(row["score"]),
            "ingested_at": now_iso(),
            "bot_name": "bot-oulad-assessment",
            "source": "studentAssessment.csv",
        })
        
        if len(batch) >= CONFIG["batch_size"]:
            if send_batch("/api/oulad/assessment/batch", batch):
                sent += len(batch)
                if sent % 1000 == 0:
                    print(f"[OULAD-ASSESS] Sent: {sent:,}/{total:,}")
            batch = []
            time.sleep(CONFIG["batch_size"] / CONFIG["events_per_second"])
    
    if batch:
        send_batch("/api/oulad/assessment/batch", batch)
    print(f"[OULAD-ASSESS] DONE. Total: {sent:,} (skipped: {skipped})")


# ============================================================
# BOT 3: STUDENTS
# ============================================================
def bot_students():
    print("[OULAD-STUDENTS] Started...")
    path = Path(OULAD_DIR) / "studentInfo.csv"
    df = pd.read_csv(path)
    if CONFIG["max_records"]:
        df = df.head(CONFIG["max_records"])
    total = len(df)
    print(f"[OULAD-STUDENTS] Total: {total:,}")
    
    batch = []
    sent = 0
    
    for idx, row in df.iterrows():
        id_student = safe_int(row["id_student"])
        if id_student == 0:
            continue
        
        batch.append({
            "sequence": idx + 1,
            "code_module": safe_str(row["code_module"]),
            "code_presentation": safe_str(row["code_presentation"]),
            "id_student": id_student,
            "gender": safe_str(row["gender"]),
            "region": safe_str(row["region"]),
            "highest_education": safe_str(row["highest_education"]),
            "imd_band": safe_str(row["imd_band"]),
            "age_band": safe_str(row["age_band"]),
            "num_of_prev_attempts": safe_int(row["num_of_prev_attempts"]),
            "studied_credits": safe_int(row["studied_credits"]),
            "disability": safe_str(row["disability"]),
            "final_result": safe_str(row["final_result"]),
            "ingested_at": now_iso(),
            "bot_name": "bot-oulad-students",
            "source": "studentInfo.csv",
        })
        
        if len(batch) >= CONFIG["batch_size"]:
            if send_batch("/api/oulad/students/batch", batch):
                sent += len(batch)
                if sent % 1000 == 0:
                    print(f"[OULAD-STUDENTS] Sent: {sent:,}/{total:,}")
            batch = []
            time.sleep(CONFIG["batch_size"] / CONFIG["events_per_second"])
    
    if batch:
        send_batch("/api/oulad/students/batch", batch)
    print(f"[OULAD-STUDENTS] DONE. Total: {sent:,}")


# ============================================================
# BOT 4: COURSES
# ============================================================
def bot_courses():
    print("[OULAD-COURSES] Started...")
    path = Path(OULAD_DIR) / "courses.csv"
    df = pd.read_csv(path)
    total = len(df)
    print(f"[OULAD-COURSES] Total: {total:,}")
    
    batch = []
    sent = 0
    
    for idx, row in df.iterrows():
        batch.append({
            "sequence": idx + 1,
            "code_module": safe_str(row["code_module"]),
            "code_presentation": safe_str(row["code_presentation"]),
            "module_presentation_length": safe_int(row["module_presentation_length"]),
            "ingested_at": now_iso(),
            "bot_name": "bot-oulad-courses",
            "source": "courses.csv",
        })
        
        if len(batch) >= CONFIG["batch_size"]:
            if send_batch("/api/oulad/courses/batch", batch):
                sent += len(batch)
            batch = []
            time.sleep(0.5)
    
    if batch:
        send_batch("/api/oulad/courses/batch", batch)
    print(f"[OULAD-COURSES] DONE. Total: {sent:,}")


# ============================================================
# BOT 5: REGISTRATION
# ============================================================
def bot_registration():
    print("[OULAD-REG] Started...")
    path = Path(OULAD_DIR) / "studentRegistration.csv"
    df = pd.read_csv(path)
    if CONFIG["max_records"]:
        df = df.head(CONFIG["max_records"])
    total = len(df)
    print(f"[OULAD-REG] Total: {total:,}")
    
    batch = []
    sent = 0
    
    for idx, row in df.iterrows():
        id_student = safe_int(row["id_student"])
        if id_student == 0:
            continue
        
        batch.append({
            "sequence": idx + 1,
            "code_module": safe_str(row["code_module"]),
            "code_presentation": safe_str(row["code_presentation"]),
            "id_student": id_student,
            "date_registration": safe_int(row["date_registration"]),
            "date_unregistration": safe_int(row["date_unregistration"]),
            "ingested_at": now_iso(),
            "bot_name": "bot-oulad-registration",
            "source": "studentRegistration.csv",
        })
        
        if len(batch) >= CONFIG["batch_size"]:
            if send_batch("/api/oulad/registration/batch", batch):
                sent += len(batch)
                if sent % 1000 == 0:
                    print(f"[OULAD-REG] Sent: {sent:,}/{total:,}")
            batch = []
            time.sleep(CONFIG["batch_size"] / CONFIG["events_per_second"])
    
    if batch:
        send_batch("/api/oulad/registration/batch", batch)
    print(f"[OULAD-REG] DONE. Total: {sent:,}")


# ============================================================
# MAIN
# ============================================================
if __name__ == "__main__":
    print("=" * 70)
    print("  OULAD MULTI-SOURCE BOT")
    print("=" * 70)
    print(f"  API      : {API_BASE}")
    print(f"  Data     : {OULAD_DIR}")
    print(f"  Batch    : {CONFIG['batch_size']}")
    print(f"  Max/File : {CONFIG['max_records']:,}")
    print("=" * 70 + "\n")
    
    # Cek health dulu
    try:
        r = requests.get(f"{API_BASE}/health", timeout=10)
        print(f"[INFO] Railway health: {r.json()}\n")
    except Exception as e:
        print(f"[ERROR] Railway tidak dapat dihubungi: {e}")
        exit(1)
    
    # Jalankan paralel
    threads = [
        threading.Thread(target=bot_vle, name="vle"),
        threading.Thread(target=bot_assessment, name="assessment"),
        threading.Thread(target=bot_students, name="students"),
        threading.Thread(target=bot_courses, name="courses"),
        threading.Thread(target=bot_registration, name="registration"),
    ]
    
    for t in threads:
        t.start()
        time.sleep(2)
    
    for t in threads:
        t.join()
    
    print("\n" + "=" * 70)
    print("  ALL OULAD BOTS DONE!")
    print("=" * 70)