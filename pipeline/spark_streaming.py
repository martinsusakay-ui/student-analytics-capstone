"""
spark_streaming.py - Baca dari Kafka (UnB + OULAD), tulis ke MongoDB
6 Kafka topic → 6 MongoDB collection (Raw)
+ Window Aggregation (1min, 5min) dengan Watermark untuk UnB
"""

import json
from pyspark.sql import SparkSession
from pyspark.sql.functions import (
    col, from_json, to_timestamp, window, count,
    approx_count_distinct, lit, current_timestamp
)
from pyspark.sql.types import (
    StructType, StructField, StringType, IntegerType, LongType, FloatType
)

# ============================================================
# KONFIGURASI
# ============================================================
CONFIG = {
    "kafka_bootstrap": "localhost:9092",
    "mongo_uri": "mongodb://admin:admin123@localhost:27017/?authSource=admin",
    "mongo_db": "moodle_analytics",
    "checkpoint_dir": "C:/Users/User/student-analytics/pipeline/checkpoints_v6",
    "trigger_interval": "30 seconds",
    "max_offsets_per_trigger": 2000,
    "watermark_delay": "2 minutes",  # Watermark 2 menit
}

# ============================================================
# SCHEMA UnB
# ============================================================
UNB_EVENTS_SCHEMA = StructType([
    StructField("sequence", LongType(), True),
    StructField("user_hash", StringType(), True),
    StructField("courseid", IntegerType(), True),
    StructField("component", StringType(), True),
    StructField("eventname", StringType(), True),
    StructField("action", StringType(), True),
    StructField("target", StringType(), True),
    StructField("timecreated", LongType(), True),
    StructField("event_time", StringType(), True),
    StructField("ingested_at", StringType(), True),
    StructField("bot_name", StringType(), True),
    StructField("source", StringType(), True),
])

# ============================================================
# SCHEMA OULAD
# ============================================================
OULAD_VLE_SCHEMA = StructType([
    StructField("sequence", LongType(), True),
    StructField("code_module", StringType(), True),
    StructField("code_presentation", StringType(), True),
    StructField("id_student", IntegerType(), True),
    StructField("id_site", IntegerType(), True),
    StructField("date", IntegerType(), True),
    StructField("sum_click", IntegerType(), True),
    StructField("ingested_at", StringType(), True),
    StructField("bot_name", StringType(), True),
    StructField("source", StringType(), True),
])

OULAD_ASSESSMENT_SCHEMA = StructType([
    StructField("sequence", LongType(), True),
    StructField("id_assessment", IntegerType(), True),
    StructField("id_student", IntegerType(), True),
    StructField("date_submitted", IntegerType(), True),
    StructField("is_banked", IntegerType(), True),
    StructField("score", FloatType(), True),
    StructField("ingested_at", StringType(), True),
    StructField("bot_name", StringType(), True),
    StructField("source", StringType(), True),
])

OULAD_STUDENTS_SCHEMA = StructType([
    StructField("sequence", LongType(), True),
    StructField("code_module", StringType(), True),
    StructField("code_presentation", StringType(), True),
    StructField("id_student", IntegerType(), True),
    StructField("gender", StringType(), True),
    StructField("region", StringType(), True),
    StructField("highest_education", StringType(), True),
    StructField("imd_band", StringType(), True),
    StructField("age_band", StringType(), True),
    StructField("num_of_prev_attempts", IntegerType(), True),
    StructField("studied_credits", IntegerType(), True),
    StructField("disability", StringType(), True),
    StructField("final_result", StringType(), True),
    StructField("ingested_at", StringType(), True),
    StructField("bot_name", StringType(), True),
    StructField("source", StringType(), True),
])

OULAD_COURSES_SCHEMA = StructType([
    StructField("sequence", LongType(), True),
    StructField("code_module", StringType(), True),
    StructField("code_presentation", StringType(), True),
    StructField("module_presentation_length", IntegerType(), True),
    StructField("ingested_at", StringType(), True),
    StructField("bot_name", StringType(), True),
    StructField("source", StringType(), True),
])

OULAD_REGISTRATION_SCHEMA = StructType([
    StructField("sequence", LongType(), True),
    StructField("code_module", StringType(), True),
    StructField("code_presentation", StringType(), True),
    StructField("id_student", IntegerType(), True),
    StructField("date_registration", IntegerType(), True),
    StructField("date_unregistration", IntegerType(), True),
    StructField("ingested_at", StringType(), True),
    StructField("bot_name", StringType(), True),
    StructField("source", StringType(), True),
])

# ============================================================
# SPARK SESSION
# ============================================================
def create_spark_session():
    spark = (
        SparkSession.builder
        .appName("MoodleStreamingAnalytics")
        .config("spark.jars.packages",
                "org.apache.spark:spark-sql-kafka-0-10_2.12:3.4.1")
        .config("spark.sql.streaming.checkpointLocation", CONFIG["checkpoint_dir"])
        .config("spark.sql.shuffle.partitions", "6")
        .getOrCreate()
    )
    spark.sparkContext.setLogLevel("WARN")
    return spark

# ============================================================
# WRITE TO MONGODB
# ============================================================
def write_to_mongodb(df, collection_name, checkpoint_name):
    """Tulis streaming DataFrame ke MongoDB via PyMongo."""
    
    def write_batch(batch_df, batch_id):
        try:
            count_val = batch_df.count()
            if count_val > 0:
                records = batch_df.toJSON().collect()
                docs = [json.loads(r) for r in records]
                
                from pymongo import MongoClient
                client = MongoClient(CONFIG["mongo_uri"])
                db = client[CONFIG["mongo_db"]]
                collection = db[collection_name]
                
                if docs:
                    collection.insert_many(docs, ordered=False)
                    print(f"[MONGO] Batch {batch_id}: {len(docs)} docs → {collection_name}")
                
                client.close()
        except Exception as e:
            print(f"[MONGO ERROR] {collection_name} batch {batch_id}: {e}")
    
    return (
        df.writeStream
        .foreachBatch(write_batch)
        .outputMode("append")  # WAJIB 'append' untuk watermark & window
        .option("checkpointLocation", f"{CONFIG['checkpoint_dir']}/{checkpoint_name}")
        .trigger(processingTime=CONFIG["trigger_interval"])
        .start()
    )

# ============================================================
# PROCESS STREAM (RAW DATA)
# ============================================================
def process_stream(spark, topic, schema, collection, checkpoint):
    """Baca Kafka topic → parse JSON → tulis MongoDB (Raw)."""
    kafka_df = (
        spark.readStream
        .format("kafka")
        .option("kafka.bootstrap.servers", CONFIG["kafka_bootstrap"])
        .option("subscribe", topic)
        .option("startingOffsets", "latest")
        .option("failOnDataLoss", "false")
        .option("maxOffsetsPerTrigger", CONFIG["max_offsets_per_trigger"])
        .load()
    )
    
    parsed_df = (
        kafka_df
        .selectExpr("CAST(value AS STRING) as json_str")
        .select(from_json(col("json_str"), schema).alias("data"))
        .select("data.*")
        .withColumn("processing_time", current_timestamp())
    )
    
    return write_to_mongodb(parsed_df, collection, checkpoint)

# ============================================================
# PROCESS METRICS STREAM (WINDOW AGGREGATION)
# ============================================================
def process_metrics_stream(spark, topic, schema, collection, checkpoint, window_duration):
    """Baca Kafka → Window Aggregation + Watermark → MongoDB."""
    
    kafka_df = (
        spark.readStream
        .format("kafka")
        .option("kafka.bootstrap.servers", CONFIG["kafka_bootstrap"])
        .option("subscribe", topic)
        .option("startingOffsets", "latest")
        .option("failOnDataLoss", "false")
        .option("maxOffsetsPerTrigger", CONFIG["max_offsets_per_trigger"])
        .load()
    )
    
    parsed_df = (
        kafka_df
        .selectExpr("CAST(value AS STRING) as json_str")
        .select(from_json(col("json_str"), schema).alias("data"))
        .select("data.*")
        .withColumn("processing_time", current_timestamp())
    )

    # LOGIKA WINDOW & WATERMARK
    metrics_df = (
        parsed_df
        .withWatermark("processing_time", CONFIG["watermark_delay"])
        .groupBy(
            window(col("processing_time"), window_duration).alias("time_window"),
            col("courseid")
        )
        .agg(
            count("*").alias("total_events"),
            approx_count_distinct("user_hash").alias("unique_users")
        )
        # Ratakan struct 'time_window' agar mudah dibaca di MongoDB
        .select(
            col("time_window.start").alias("window_start"),
            col("time_window.end").alias("window_end"),
            col("courseid"),
            col("total_events"),
            col("unique_users")
        )
        .withColumn("window_type", lit(window_duration))
    )
    
    return write_to_mongodb(metrics_df, collection, checkpoint)

# ============================================================
# MAIN
# ============================================================
def run():
    print("=" * 70)
    print("  SPARK STREAMING - UnB + OULAD → MongoDB")
    print("=" * 70)
    print(f"  Kafka      : {CONFIG['kafka_bootstrap']}")
    print(f"  MongoDB    : {CONFIG['mongo_db']}")
    print(f"  Trigger    : {CONFIG['trigger_interval']}")
    print(f"  Watermark  : {CONFIG['watermark_delay']}")
    print(f"  Checkpoint : {CONFIG['checkpoint_dir']}")
    print("=" * 70 + "\n")
    
    spark = create_spark_session()
    queries = []
    
    # 1. RAW DATA STREAMS
    topics_raw = [
        ("moodle-events", UNB_EVENTS_SCHEMA, "events", "unb_events"),
        ("oulad-vle", OULAD_VLE_SCHEMA, "oulad_vle", "oulad_vle"),
        ("oulad-assessment", OULAD_ASSESSMENT_SCHEMA, "oulad_assessment", "oulad_assessment"),
        ("oulad-students", OULAD_STUDENTS_SCHEMA, "oulad_students", "oulad_students"),
        ("oulad-courses", OULAD_COURSES_SCHEMA, "oulad_courses", "oulad_courses"),
        ("oulad-registration", OULAD_REGISTRATION_SCHEMA, "oulad_registration", "oulad_registration"),
    ]
    
    for topic, schema, coll, chk in topics_raw:
        print(f"[SPARK] Setup RAW {topic}...")
        q = process_stream(spark, topic, schema, coll, chk)
        queries.append(q)
        
    # 2. METRICS STREAMS (WINDOW AGGREGATION)
    # Menghitung metrics dari topik 'moodle-events' (UnB)
    print("[SPARK] Setup METRICS (1 menit) dari moodle-events...")
    q_1min = process_metrics_stream(
        spark, "moodle-events", UNB_EVENTS_SCHEMA, 
        "metrics_1min", "unb_metrics_1min", "1 minute"
    )
    queries.append(q_1min)

    print("[SPARK] Setup METRICS (5 menit) dari moodle-events...")
    q_5min = process_metrics_stream(
        spark, "moodle-events", UNB_EVENTS_SCHEMA, 
        "metrics_5min", "unb_metrics_5min", "5 minutes"
    )
    queries.append(q_5min)
    
    print(f"\n{'='*70}")
    print(f"  {len(queries)} STREAM AKTIF")
    print(f"{'='*70}")
    print(f"  Tekan Ctrl+C untuk stop\n")
    
    try:
        spark.streams.awaitAnyTermination()
    except KeyboardInterrupt:
        print(f"\n[STOP] Dihentikan user")
    finally:
        for q in queries:
            try:
                q.stop()
            except:
                pass
        spark.stop()
        print(f"[DONE] Spark session dihentikan")

if __name__ == "__main__":
    run()