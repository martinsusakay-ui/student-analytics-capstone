"""
kafka_producer.py - Polling dari FastAPI Railway, kirim ke Kafka lokal
"""

import requests
import json
import time
from datetime import datetime, timezone
from pathlib import Path
from kafka import KafkaProducer
from kafka.errors import KafkaTimeoutError

# ============================================================
# KONFIGURASI
# ============================================================
CONFIG = {
    # ✅ URL RAILWAY YANG BARU
    "api_base_url": "https://big-data-analytics-production.up.railway.app",
    "endpoint_kafka": "/api/activities/kafka-format/since/{last_id}",
    "poll_interval": 5,
    "poll_limit": 100,
    "kafka_bootstrap": "localhost:9092",
    "kafka_topic": "moodle-events",
    "state_file": "pipeline_state.json",
    "max_retries": 3,
    "retry_delay": 2,
    "request_timeout": 30,
}


# ============================================================
# STATE MANAGEMENT
# ============================================================
def load_last_id() -> int:
    state_file = Path(CONFIG["state_file"])
    if state_file.exists():
        try:
            with open(state_file, "r") as f:
                data = json.load(f)
                return data.get("last_id", 0)
        except Exception as e:
            print(f"[WARN] Gagal baca state: {e}")
    return 0


def save_last_id(last_id: int):
    state_file = Path(CONFIG["state_file"])
    with open(state_file, "w") as f:
        json.dump({
            "last_id": last_id,
            "updated_at": datetime.now(timezone.utc).isoformat()
        }, f, indent=2)


# ============================================================
# KAFKA PRODUCER
# ============================================================
def create_kafka_producer(retries=5, delay=5):
    """Buat Kafka producer dengan retry."""
    for attempt in range(retries):
        try:
            producer = KafkaProducer(
                bootstrap_servers=CONFIG["kafka_bootstrap"],
                value_serializer=lambda v: json.dumps(v).encode("utf-8"),
                key_serializer=lambda k: k.encode("utf-8") if k else None,
                acks="all",
                retries=3,
                linger_ms=10,
            )
            print(f"[KAFKA] Connected to {CONFIG['kafka_bootstrap']}")
            return producer
        except KafkaTimeoutError:
            print(f"[KAFKA] Attempt {attempt+1}/{retries} failed. Retry in {delay}s...")
            time.sleep(delay)
        except Exception as e:
            print(f"[KAFKA] Error koneksi: {e}")
            time.sleep(delay)
            
    raise RuntimeError("Tidak dapat connect ke Kafka. Pastikan broker Kafka sudah berjalan.")


# ============================================================
# POLL FROM RAILWAY
# ============================================================
def poll_from_railway(last_id: int) -> dict:
    """Polling event baru dari Railway."""
    url = f"{CONFIG['api_base_url']}{CONFIG['endpoint_kafka'].format(last_id=last_id)}"
    params = {"limit": CONFIG["poll_limit"]}
    
    for attempt in range(CONFIG["max_retries"]):
        try:
            r = requests.get(url, params=params, timeout=CONFIG["request_timeout"])
            if r.status_code == 200:
                return r.json()
            else:
                print(f"[WARN] HTTP {r.status_code}: {r.text[:100]}")
        except Exception as e:
            if attempt < CONFIG["max_retries"] - 1:
                time.sleep(CONFIG["retry_delay"])
            else:
                print(f"[ERROR] Polling gagal: {e}")
    return {"count": 0, "events": [], "next_last_id": last_id}


# ============================================================
# MAIN
# ============================================================
def run():
    print(f"\n{'='*70}")
    print(f"  KAFKA PRODUCER - Polling from Railway")
    print(f"{'='*70}")
    print(f"  API Base   : {CONFIG['api_base_url']}")
    print(f"  Kafka      : {CONFIG['kafka_bootstrap']}")
    print(f"  Topic      : {CONFIG['kafka_topic']}")
    print(f"  Poll every : {CONFIG['poll_interval']}s")
    print(f"  Poll limit : {CONFIG['poll_limit']} events")
    print(f"{'='*70}\n")
    
    # Cek Railway health
    try:
        r = requests.get(f"{CONFIG['api_base_url']}/health", timeout=10)
        print(f"[INFO] Railway health: {r.json()}")
    except Exception as e:
        print(f"[ERROR] Railway tidak dapat dihubungi: {e}")
        return
    
    # Cek Kafka
    producer = create_kafka_producer()
    
    # Load last_id
    last_id = load_last_id()
    print(f"[INFO] Starting from last_id = {last_id}")
    print(f"[INFO] Mulai polling...\n")
    
    total_sent = 0
    poll_count = 0
    start_real = time.time()
    
    try:
        while True:
            poll_count += 1
            
            # Poll dari Railway
            data = poll_from_railway(last_id)
            
            events = data.get("events", [])
            next_last_id = data.get("next_last_id", last_id)
            count = data.get("count", 0)
            
            if count > 0:
                # Kirim ke Kafka
                for event in events:
                    key = str(event.get("user_hash", "unknown"))[:16]
                    producer.send(CONFIG["kafka_topic"], key=key, value=event)
                
                producer.flush()
                total_sent += count
                last_id = next_last_id
                save_last_id(last_id)
                
                elapsed = time.time() - start_real
                rate = total_sent / elapsed if elapsed > 0 else 0
                
                print(f"[POLL #{poll_count:>4}] "
                      f"+{count:>3} events | "
                      f"last_id={last_id:>6} | "
                      f"total={total_sent:>6} | "
                      f"rate={rate:.1f} ev/s")
            else:
                print(f"[POLL #{poll_count:>4}] No new events (last_id={last_id})")
            
            time.sleep(CONFIG["poll_interval"])
    
    except KeyboardInterrupt:
        print(f"\n[STOP] Dihentikan user")
    finally:
        producer.flush()
        producer.close()
        elapsed = time.time() - start_real
        print(f"\n{'='*70}")
        print(f"  SELESAI")
        print(f"{'='*70}")
        print(f"  Total sent   : {total_sent:,}")
        print(f"  Poll count   : {poll_count}")
        print(f"  Durasi       : {elapsed:.1f}s")
        print(f"  Rate         : {total_sent/elapsed:.2f} ev/s")
        print(f"  Last ID      : {last_id}")
        print(f"{'='*70}\n")


if __name__ == "__main__":
    run()