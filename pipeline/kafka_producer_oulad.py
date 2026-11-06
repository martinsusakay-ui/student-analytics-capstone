"""
kafka_producer_oulad.py - Polling OULAD dari Railway, kirim ke Kafka
Versi: LAMBAT (POLL_INTERVAL=30, POLL_LIMIT=50)
"""

import requests
import json
import time
from pathlib import Path
from kafka import KafkaProducer
from kafka.errors import KafkaTimeoutError

# ✅ URL RAILWAY YANG BARU
API_BASE = "https://big-data-analytics-production.up.railway.app"

# Kafka lokal (pastikan Kafka & ZooKeeper sudah berjalan di Docker/laptop)
KAFKA_BOOTSTRAP = "localhost:9092"
STATE_FILE = "pipeline_state_oulad.json"

SOURCES = [
    {"name": "oulad_vle", "endpoint": "/api/oulad/vle/kafka-format/since/{last_id}", "topic": "oulad-vle"},
    {"name": "oulad_assessment", "endpoint": "/api/oulad/assessment/kafka-format/since/{last_id}", "topic": "oulad-assessment"},
    {"name": "oulad_students", "endpoint": "/api/oulad/students/kafka-format/since/{last_id}", "topic": "oulad-students"},
    {"name": "oulad_courses", "endpoint": "/api/oulad/courses/kafka-format/since/{last_id}", "topic": "oulad-courses"},
    {"name": "oulad_registration", "endpoint": "/api/oulad/registration/kafka-format/since/{last_id}", "topic": "oulad-registration"},
]

# ============================================================
# KONFIGURASI LAJU
# ============================================================
POLL_INTERVAL = 30     # detik antar polling
POLL_LIMIT = 50        # event per poll


def load_state():
    if Path(STATE_FILE).exists():
        with open(STATE_FILE) as f:
            return json.load(f)
    return {s["name"]: 0 for s in SOURCES}


def save_state(state):
    with open(STATE_FILE, "w") as f:
        json.dump(state, f, indent=2)


def create_producer():
    try:
        return KafkaProducer(
            bootstrap_servers=KAFKA_BOOTSTRAP,
            value_serializer=lambda v: json.dumps(v).encode("utf-8"),
            acks="all", 
            retries=3,
            request_timeout_ms=5000,
        )
    except KafkaTimeoutError:
        print(f"[FATAL] Tidak bisa terhubung ke Kafka di {KAFKA_BOOTSTRAP}.")
        print("        Pastikan Kafka & ZooKeeper sudah berjalan.")
        exit(1)
    except Exception as e:
        print(f"[FATAL] Kafka Error: {e}")
        exit(1)


def main():
    print("=" * 70)
    print("  OULAD KAFKA PRODUCER (Versi Lambat)")
    print("=" * 70)
    for s in SOURCES:
        print(f"  {s['name']:20} → {s['topic']}")
    print(f"  {'POLL_INTERVAL':20} → {POLL_INTERVAL} detik")
    print(f"  {'POLL_LIMIT':20} → {POLL_LIMIT} event/poll")
    print("=" * 70 + "\n")
    
    producer = create_producer()
    state = load_state()
    print(f"[INFO] State awal: {state}\n")
    
    poll_count = 0
    total_sent = 0
    start_time = time.time()
    
    try:
        while True:
            poll_count += 1
            print(f"\n[POLL #{poll_count}] {time.strftime('%H:%M:%S')}")
            
            for source in SOURCES:
                name = source["name"]
                last_id = state.get(name, 0)
                url = f"{API_BASE}{source['endpoint'].format(last_id=last_id)}"
                
                try:
                    r = requests.get(url, params={"limit": POLL_LIMIT}, timeout=30)
                    if r.status_code == 200:
                        data = r.json()
                        events = data.get("events", [])
                        count = data.get("count", 0)
                        next_id = data.get("next_last_id", last_id)
                        
                        if count > 0:
                            for event in events:
                                producer.send(source["topic"], value=event)
                            producer.flush()
                            state[name] = next_id
                            total_sent += count
                            print(f"  [{name:20}] +{count:>3} events | last_id={next_id:>7}")
                        else:
                            print(f"  [{name:20}] La iha eventu foun | last_id={last_id:>7}")
                    else:
                        print(f"  [{name:20}] HTTP {r.status_code} — {r.text[:100]}")
                except Exception as e:
                    print(f"  [ERROR] {name}: {e}")
            
            save_state(state)
            
            elapsed = time.time() - start_time
            rate = total_sent / elapsed if elapsed > 0 else 0
            print(f"  Total: {total_sent:,} events | Rate: {rate:.2f} ev/s")
            print(f"  Hein {POLL_INTERVAL} segundos...")
            
            time.sleep(POLL_INTERVAL)
    
    except KeyboardInterrupt:
        print(f"\n[STOP] Dihentikan user")
    finally:
        producer.flush()
        producer.close()
        save_state(state)
        print(f"\n[DONE] Total sent: {total_sent:,} events")
        print(f"[DONE] State saved: {state}")


if __name__ == "__main__":
    main()