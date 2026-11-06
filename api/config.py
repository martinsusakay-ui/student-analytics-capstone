"""
config.py - Environment configuration untuk FastAPI
"""

import os

# ============================================================
# ENVIRONMENT & DATABASE URL
# ============================================================
# 1. Ambil URL dari Railway
_env_url = os.getenv("DATABASE_PRIVATE_URL") or os.getenv("DATABASE_URL", "")

# 2. Bersihkan karakter aneh (newline, spasi, atau teks tak sengaja)
_env_url = _env_url.strip().strip('"').strip("'")

# 3. Validasi: pastikan URL benar-benar dimulai dengan postgresql:// atau postgres://
IS_RAILWAY = os.getenv("RAILWAY_ENVIRONMENT") is not None

if not _env_url or ("postgresql://" not in _env_url and "postgres://" not in _env_url):
    if IS_RAILWAY:
        raise ValueError(f"CRITICAL: URL Database tidak valid di Railway! Terbaca: '{_env_url[:20]}...' (Harus diawali postgres://)")
    else:
        DATABASE_URL = "postgresql://postgres:password@localhost:5432/moodle_analytics"
else:
    # 4. Ubah postgres:// menjadi postgresql:// (wajib untuk SQLAlchemy)
    if _env_url.startswith("postgres://"):
        DATABASE_URL = _env_url.replace("postgres://", "postgresql://", 1)
    else:
        DATABASE_URL = _env_url

# 5. Log untuk memastikan (hanya cetak 30 karakter pertama agar password aman)
safe_url = DATABASE_URL[:30] + "..." if len(DATABASE_URL) > 30 else DATABASE_URL
print(f"[CONFIG] URL terbaca: {safe_url}")

# ============================================================
# APP CONFIG & CORS
# ============================================================
APP_NAME = "Moodle Activity API"
APP_VERSION = "1.0.0"

CORS_ORIGINS = [
    "http://localhost:3000",
    "http://localhost:8501",
    "http://127.0.0.1:8501",
]

RAILWAY_DOMAIN = os.getenv("RAILWAY_PUBLIC_DOMAIN")
if RAILWAY_DOMAIN:
    CORS_ORIGINS.append(f"https://{RAILWAY_DOMAIN}")