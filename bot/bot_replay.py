"""
bot_replay.py - Bot replay dataset Moodle ke FastAPI
Mendukung single event & batch event.
"""

import pandas as pd
import requests
import json
import time
from datetime import datetime, timezone
from pathlib import Path
import sys

# Pastikan file config.py berada di folder yang sama
sys.path.append(".")
from config import CONFIG, validate_config, print_config


# ============================================================
# HEALTH CHECK
# ============================================================
def check_api_health() -> bool:
    """Cek FastAPI online."""
    url = f"{CONFIG['api_base_url']}{CONFIG['endpoint_health']}"
    try:
        r = requests.get(url, timeout=CONFIG["request_timeout"])
        if r.status_code == 200:
            data = r.json()
            print(f"[INFO] Health check OK: {data}")
            return True
        print(f"[WARN] Health status: {r.status_code}")
        return False
    except Exception as e:
        print(f"[ERROR] Health check gagal: {e}")
        return False


# ============================================================
# PARSE EVENT
# ============================================================
def parse_event(row, sequence: int) -> dict:
    """Ubah baris CSV jadi payload JSON."""
    return {
        "sequence": sequence,
        "user_hash": row["user_hash"],
        "courseid": int(row["courseid"]),
        "component": row["component"],
        "eventname": row["eventname"],
        "action": row["action"],
        "target": row["target"],
        "timecreated": int(row["timecreated"]),
        "event_time": datetime.fromtimestamp(
            int(row["timecreated"]), tz=timezone.utc
        ).isoformat(),
        "ingested_at": datetime.now(timezone.utc).isoformat(),
        "bot_name": CONFIG.get("bot_name", "moodle-bot-replay"),
        "source": "moodle-bot-replay",
    }


# ============================================================
# SEND SINGLE
# ============================================================
def send_single(payload: dict, retries: int = None) -> bool:
    """Kirim 1 event ke FastAPI."""
    if retries is None:
        retries = CONFIG["max_retries"]
    
    url = f"{CONFIG['api_base_url']}{CONFIG['endpoint_post']}"
    
    for attempt in range(retries):
        try:
            r = requests.post(
                url,
                json=payload,
                timeout=CONFIG["request_timeout"],
                headers={"Content-Type": "application/json"},
            )
            if r.status_code in [200, 201]:
                return True
            print(f"[WARN] HTTP {r.status_code}: {r.text[:100]}")
        except requests.exceptions.ConnectionError:
            if attempt < retries - 1:
                time.sleep(CONFIG["retry_delay"])
        except Exception as e:
            print(f"[ERROR] {e}")
            return False
    return False


# ============================================================
# SEND BATCH
# ============================================================
def send_batch(events: list, retries: int = None) -> bool:
    """Kirim batch event ke FastAPI dengan auto-fallback format."""
    if retries is None:
        retries = CONFIG["max_retries"]
    
    url = f"{CONFIG['api_base_url']}{CONFIG['endpoint_post']}/batch"
    
    # Coba format 1: {"events": [...]}
    # Jika gagal (422), coba format 2: [...] langsung
    payloads = [
        {"events": events},
        events
    ]
    
    for payload in payloads:
        for attempt in range(retries):
            try:
                r = requests.post(
                    url,
                    json=payload,
                    timeout=CONFIG["request_timeout"],
                    headers={"Content-Type": "application/json"},
                )
                if r.status_code in [200, 201]:
                    return True
                elif r.status_code == 422:
                    # Jika 422 (Unprocessable), putus loop retry, coba format selanjutnya
                    break
                print(f"[WARN] HTTP {r.status_code}: {r.text[:200]}")
            except requests.exceptions.ConnectionError:
                if attempt < retries - 1:
                    time.sleep(CONFIG["retry_delay"])
            except Exception as e:
                print(f"[ERROR] {e}")
                return False
                
    return False


# ============================================================
# MAIN
# ============================================================
def run():
    print_config()
    
    # Validasi
    errors = validate_config()
    if errors:
        print("[ERROR] Konfigurasi tidak valid:")
        for e in errors:
            print(f"  - {e}")
        return
    
    # Cek health
    print("[INFO] Cek FastAPI health...")
    if not check_api_health():
        print(f"[ERROR] FastAPI tidak dapat dihubungi di {CONFIG['api_base_url']}")
        return
    print("[INFO] FastAPI online ✓\n")
    
    # Load dataset
    csv_path = Path(CONFIG["csv_path"]).resolve()
    print(f"[INFO] Membaca {csv_path.name}...")
    df = pd.read_csv(csv_path)
    
    if CONFIG["max_records"]:
        df = df.head(CONFIG["max_records"])
    
    df = df.sort_values("timecreated").reset_index(drop=True)
    total = len(df)
    
    t_min = datetime.fromtimestamp(df["timecreated"].min(), tz=timezone.utc)
    t_max = datetime.fromtimestamp(df["timecreated"].max(), tz=timezone.utc)
    
    batch_size = CONFIG.get("batch_size", 1)
    mode = "BATCH" if batch_size > 1 else "SINGLE"
    
    print(f"[INFO] Total      : {total:,}")
    print(f"[INFO] Rentang    : {t_min} → {t_max}")
    print(f"[INFO] Mode       : {mode} (batch_size={batch_size})")
    print(f"[INFO] Rate       : {CONFIG['events_per_second']} event/detik")
    print(f"[INFO] Mulai replay...\n")
    
    interval = 1.0 / CONFIG["events_per_second"]
    sent = 0
    failed = 0
    start_real = time.time()
    
    try:
        if batch_size == 1:
            # ==================================================
            # MODE SINGLE
            # ==================================================
            for idx, row in df.iterrows():
                payload = parse_event(row, sequence=idx + 1)
                ok = send_single(payload)
                
                if ok:
                    sent += 1
                else:
                    failed += 1
                
                if (idx + 1) % CONFIG["log_every"] == 0:
                    elapsed = time.time() - start_real
                    rate = sent / elapsed if elapsed > 0 else 0
                    print(f"[{idx+1:>7,}/{total:,}] "
                          f"sent={sent:,} failed={failed} "
                          f"| {rate:6.1f} ev/s "
                          f"| {payload['eventname'][:40]}")
                
                time.sleep(interval)
        
        else:
            # ==================================================
            # MODE BATCH
            # ==================================================
            batch = []
            for idx, row in df.iterrows():
                payload = parse_event(row, sequence=idx + 1)
                batch.append(payload)
                
                # Kirim kalau batch penuh
                if len(batch) >= batch_size:
                    ok = send_batch(batch)
                    if ok:
                        sent += len(batch)
                    else:
                        failed += len(batch)
                    
                    if sent % CONFIG["log_every"] < batch_size:
                        elapsed = time.time() - start_real
                        rate = sent / elapsed if elapsed > 0 else 0
                        print(f"[{sent:>7,}/{total:,}] "
                              f"sent={sent:,} failed={failed} "
                              f"| {rate:6.1f} ev/s "
                              f"| batch #{sent//batch_size}")
                    
                    batch = []
                    time.sleep(interval * batch_size / 10)
            
            # Kirim sisa batch
            if batch:
                ok = send_batch(batch)
                if ok:
                    sent += len(batch)
                else:
                    failed += len(batch)
    
    except KeyboardInterrupt:
        print(f"\n[STOP] Dihentikan user")
    
    elapsed = time.time() - start_real
    print(f"\n{'='*70}")
    print(f"  SELESAI")
    print(f"{'='*70}")
    print(f"  Total sent   : {sent:,}")
    print(f"  Total failed : {failed:,}")
    print(f"  Durasi       : {elapsed:.1f}s ({elapsed/60:.1f} menit)")
    print(f"  Rate         : {sent/elapsed:.1f} ev/s")
    print(f"{'='*70}\n")


if __name__ == "__main__":
    run()