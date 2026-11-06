"""
config.py - Konfigurasi dashboard
"""

CONFIG = {
    # MongoDB
    "mongo_uri": "mongodb://admin:admin123@localhost:27017/?authSource=admin",
    "mongo_db": "moodle_analytics",
    "collection_events": "events",
    "collection_metrics_1min": "metrics_1min",
    "collection_metrics_5min": "metrics_5min",
    
    # Dashboard
    "refresh_seconds": 10,
    "max_events_read": 100000,
}