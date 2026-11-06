"""
config.py - Konfigurasi bot replay
"""

import os
from pathlib import Path

# ============================================================
# BASE PATH
# ============================================================
BASE_DIR = Path(__file__).parent.resolve()

# ============================================================
# KONFIGURASI BOT
# ============================================================
CONFIG = {
    # --------------------------------------------------------
    # TARGET API
    # --------------------------------------------------------
    "api_base_url": os.getenv(
        "API_BASE_URL",
        "https://big-data-analytics-production.up.railway.app"  # ✅ URL BARU
    ).strip(),
    
    # --------------------------------------------------------
    # ENDPOINT
    # --------------------------------------------------------
    "endpoint_post": "/api/activities",
    "endpoint_health": "/health",
    "endpoint_stats": "/api/stats",
    
    # --------------------------------------------------------
    # DATASET
    # --------------------------------------------------------
    # Pastikan file CSV benar-benar ada di path ini.
    # Jika file ada di folder "data", ubah menjadi: BASE_DIR / "data" / "logs_interacoes_anon.csv"
    "csv_path": str(BASE_DIR / "logs_interacoes_anon.csv"),
    
    # --------------------------------------------------------
    # RATE LIMITING
    # --------------------------------------------------------
    # 7 event per 5 detik = 1.4 event/detik
    "events_per_second": 1.4,
    "max_records": None,
    
    # --------------------------------------------------------
    # BATCH
    # --------------------------------------------------------
    "batch_size": 7,                 # 7 event per batch = 1 request
                                     # Setiap 5 detik kirim 1 batch
    
    # --------------------------------------------------------
    # RETRY
    # --------------------------------------------------------
    "max_retries": 3,
    "retry_delay": 2,
    
    # --------------------------------------------------------
    # TIMEOUT
    # --------------------------------------------------------
    "request_timeout": 30,
    
    # --------------------------------------------------------
    # LOGGING
    # --------------------------------------------------------
    "log_every": 7,                  # log tiap 7 event (1 batch)
    
    # --------------------------------------------------------
    # MODE
    # --------------------------------------------------------
    "dry_run": False,
    "verbose": True,
    
    # --------------------------------------------------------
    # IDENTITAS BOT
    # --------------------------------------------------------
    "bot_name": "moodle-bot-replay",
    "bot_version": "1.0.0",
}


# ============================================================
# VALIDASI
# ============================================================
def validate_config():
    """Validasi konfigurasi sebelum dijalankan."""
    errors = []
    
    csv_path = Path(CONFIG["csv_path"])
    if not csv_path.exists():
        errors.append(f"CSV tidak ditemukan: {csv_path}")
    
    if CONFIG["events_per_second"] <= 0:
        errors.append("events_per_second harus > 0")
    
    if not CONFIG["api_base_url"].startswith("http"):
        errors.append("api_base_url harus dimulai dengan http:// atau https://")
    
    return errors


# ============================================================
# PRINT CONFIG
# ============================================================
def print_config():
    """Print konfigurasi ke console."""
    print(f"\n{'='*70}")
    print(f"  BOT CONFIGURATION")
    print(f"{'='*70}")
    print(f"  Bot Name      : {CONFIG['bot_name']} v{CONFIG['bot_version']}")
    print(f"  Target API    : {repr(CONFIG['api_base_url'])}")
    print(f"  Endpoint      : {CONFIG['endpoint_post']}")
    print(f"  Dataset       : {CONFIG['csv_path']}")
    print(f"  Rate          : {CONFIG['events_per_second']} event/detik")
    print(f"  Batch Size    : {CONFIG['batch_size']}")
    print(f"  Interval      : {CONFIG['batch_size'] / CONFIG['events_per_second']:.1f}s per batch")
    print(f"  Max Records   : {CONFIG['max_records'] or 'ALL'}")
    print(f"  Dry Run       : {CONFIG['dry_run']}")
    print(f"  Timeout       : {CONFIG['request_timeout']}s")
    print(f"{'='*70}\n")


if __name__ == "__main__":
    print_config()
    errors = validate_config()
    if errors:
        print("[ERROR] Konfigurasi tidak valid:")
        for e in errors:
            print(f"  - {e}")
    else:
        print("[OK] Konfigurasi valid")