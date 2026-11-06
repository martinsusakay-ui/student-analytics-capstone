"""
app.py - Dashboard Prediksaun Dezempenhu Estudante
Pipeline Big Data Real-Time | UnB + OULAD
"""

import streamlit as st
import pandas as pd
import numpy as np
import time
from datetime import datetime, timezone
from pymongo import MongoClient
import sys

sys.path.append(".")
from config import CONFIG
from ml_unb import run_unb_clustering
from ml_oulad import run_oulad_classification


# ============================================================
# KONFIGURASAUN PÁJINA
# ============================================================
st.set_page_config(
    page_title="Prediksaun Dezempenhu Estudante",
    page_icon="🎓",
    layout="wide"
)


# ============================================================
# KONEKSAUN MONGODB
# ============================================================
@st.cache_resource
def get_mongo_client():
    return MongoClient(CONFIG["mongo_uri"])


def get_collection(name):
    client = get_mongo_client()
    db = client[CONFIG["mongo_db"]]
    return db[name]


@st.cache_data(ttl=CONFIG["refresh_seconds"])
def load_events(limit: int = 50000) -> pd.DataFrame:
    try:
        collection = get_collection(CONFIG["collection_events"])
        cursor = collection.find({}, {"_id": 0}).limit(limit)
        records = list(cursor)
        if not records:
            return pd.DataFrame()
        df = pd.DataFrame(records)
        if "event_time" in df.columns:
            df["event_time"] = pd.to_datetime(df["event_time"], errors="coerce")
        return df
    except Exception as e:
        st.error(f"Erru load events: {e}")
        return pd.DataFrame()


@st.cache_data(ttl=CONFIG["refresh_seconds"])
def load_oulad_collection(name: str, limit: int = 50000) -> pd.DataFrame:
    try:
        collection = get_collection(name)
        cursor = collection.find({}, {"_id": 0}).limit(limit)
        records = list(cursor)
        if not records:
            return pd.DataFrame()
        return pd.DataFrame(records)
    except Exception as e:
        st.error(f"Erru load {name}: {e}")
        return pd.DataFrame()


def get_collection_count(name: str) -> int:
    try:
        return get_collection(name).count_documents({})
    except:
        return 0


# ============================================================
# HEADER
# ============================================================
st.title("🎓 Sistema Prediksaun Dezempenhu Estudante")
st.caption(
    f"Pipeline Big Data Real-Time | UnB + OULAD | "
    f"MongoDB konektadu | Refresh: {CONFIG['refresh_seconds']}s | "
    f"Atualiza: {datetime.now().strftime('%H:%M:%S')}"
)

try:
    client = get_mongo_client()
    client.admin.command("ping")
    st.success("✅ MongoDB konektadu")
except Exception as e:
    st.error(f"❌ MongoDB la konektadu: {e}")
    st.stop()


# ============================================================
# LOAD DATA
# ============================================================
events_count = get_collection_count(CONFIG["collection_events"])
df_events = load_events()

oulad_vle_count = get_collection_count("oulad_vle")
oulad_students_count = get_collection_count("oulad_students")
oulad_assessment_count = get_collection_count("oulad_assessment")
oulad_registration_count = get_collection_count("oulad_registration")

df_oulad_students = load_oulad_collection("oulad_students")
df_oulad_vle = load_oulad_collection("oulad_vle")
df_oulad_assessment = load_oulad_collection("oulad_assessment")


# ============================================================
# 1. ALERTA / NOTIFIKASAUN
# ============================================================
st.header("🚨 Alerta / Notifikasaun")

# Cek Clustering UnB
unb_result = None
if not df_events.empty:
    try:
        unb_result = run_unb_clustering(df_events, n_clusters=3)
    except:
        unb_result = None

# Cek prediksaun OULAD — estudante Withdrawn
oulad_result = None
if not df_oulad_students.empty:
    try:
        oulad_result = run_oulad_classification(
            df_oulad_vle, df_oulad_assessment, df_oulad_students
        )
    except:
        oulad_result = None

col_alert1, col_alert2 = st.columns(2)

with col_alert1:
    if unb_result and "error" not in unb_result:
        # Cek klaster Low Activity / Moderately Active
        clusters = unb_result.get("clusters", [])
        low_activity = [c for c in clusters if c["label"] in ["Low Activity", "Moderately Active"]]
        total_low = sum(c["size"] for c in low_activity)
        
        if total_low > 0:
            st.warning(f"⚠️ {total_low} estudante iha cluster Low/Moderately Active — UnB")
        else:
            st.success("✅ La iha estudante iha cluster risku — UnB")
    else:
        st.info("⏳ Seidauk iha clustering UnB")

with col_alert2:
    if oulad_result and "error" not in oulad_result:
        samples = oulad_result.get("sample_predictions", [])
        withdrawn = [s for s in samples if s.get("predicted") == "Withdrawn"]
        if withdrawn:
            st.warning(f"⚠️ {len(withdrawn)} estudante prediksaun Withdrawn — OULAD")
        else:
            st.success("✅ La iha estudante Withdrawn — OULAD")
    else:
        st.info("⏳ Seidauk iha prediksaun OULAD")


# ============================================================
# 2. ANÁLITIKA DESKRITIVA
# ============================================================
st.header("📊 Análitika Deskritiva")

total_records = (
    events_count + oulad_vle_count + oulad_students_count
    + oulad_assessment_count + oulad_registration_count
)

col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric("📥 Eventu", f"{events_count:,}")
with col2:
    if not df_events.empty and "user_hash" in df_events.columns:
        st.metric("👥 Uzuáriu", f"{df_events['user_hash'].nunique():,}")
    else:
        st.metric("👥 Uzuáriu", "0")
with col3:
    if not df_events.empty and "courseid" in df_events.columns:
        st.metric("📚 Kursu", f"{df_events['courseid'].nunique():,}")
    else:
        st.metric("📚 Kursu", "0")
with col4:
    st.metric("📋 Rejistu", f"{total_records:,}")


# ============================================================
# 3. ANÁLIZE TENDÉNSIA
# ============================================================
st.header("📈 Análize Tendénsia")
st.caption("Timeline eventu kada minutu")

if not df_events.empty and "event_time" in df_events.columns:
    df_time = df_events.dropna(subset=["event_time"]).copy()
    if not df_time.empty:
        timeline = df_time.set_index("event_time").resample("1min").size()
        if not timeline.empty:
            st.line_chart(timeline)
        else:
            st.info("La iha dadus timeline")
    else:
        st.info("La iha timestamp válidu")
else:
    st.info("⏳ Hein dadus...")


# ============================================================
# 4. ANÁLIZE ESTATÍSTIKA
# ============================================================
st.header("📊 Análize Estatístika")
st.caption("Distribuisaun tipu eventu")

if not df_events.empty and "eventname" in df_events.columns:
    event_counts = df_events["eventname"].value_counts().head(10)
    event_counts.index = [
        e.split("\\")[-1] if "\\" in e else e
        for e in event_counts.index
    ]
    st.bar_chart(event_counts)
else:
    st.info("⏳ Hein dadus...")


# ============================================================
# 5. DATASET UnB — MONITORIZASAUN + CLUSTERING
# ============================================================
st.header("Monitorizasaun + Segmentasaun")

col_u1, col_u2, col_u3, col_u4 = st.columns(4)

with col_u1:
    st.metric("📥 Eventu", f"{events_count:,}")
with col_u2:
    if not df_events.empty and "user_hash" in df_events.columns:
        st.metric("👥 Uzuáriu", f"{df_events['user_hash'].nunique():,}")
    else:
        st.metric("👥 Uzuáriu", "0")
with col_u3:
    if not df_events.empty and "courseid" in df_events.columns:
        st.metric("📚 Kursu", f"{df_events['courseid'].nunique():,}")
    else:
        st.metric("📚 Kursu", "0")
with col_u4:
    if not df_events.empty and "eventname" in df_events.columns:
        st.metric("⚡ Tipu Eventu", f"{df_events['eventname'].nunique():,}")
    else:
        st.metric("⚡ Tipu Eventu", "0")

st.divider()

st.subheader("🎯 Segmentasaun Dezempenhu Estudante (K-Means)")
st.caption("Modelu: K-Means Clustering | Target: Segmentasaun (Unsupervised)")

if unb_result and "error" not in unb_result:
    # Metrik
    col_p1, col_p2, col_p3, col_p4 = st.columns(4)
    with col_p1:
        st.metric("Inertia", f"{unb_result['metrics']['inertia']:,.2f}")
    with col_p2:
        st.metric("Silhouette", f"{unb_result['metrics']['silhouette']:.4f}")
    with col_p3:
        st.metric("Davies-Bouldin", f"{unb_result['metrics']['davies_bouldin']:.4f}")
    with col_p4:
        st.metric("Uzuáriu", f"{unb_result['n_users']:,}")

    st.divider()

    # Distribusi
    st.write("**📊 Distribuisaun Cluster**")
    df_clusters = pd.DataFrame(unb_result["clusters"])
    df_pie = df_clusters.set_index("label")["size"]
    st.bar_chart(df_pie)

    # Profil
    st.write("**📋 Profil Cluster**")
    profiles = []
    for c in unb_result["clusters"]:
        profiles.append({
            "Cluster": f"#{c['cluster_id']}", "Label": c["label"],
            "Size": c["size"], "%": f"{c['percentage']}%",
            "Avg Events": c["avg_total_events"], "Avg Courses": c["avg_unique_courses"],
            "Avg Login": c["avg_login"], "Avg Msg": c["avg_message"],
        })
    st.dataframe(pd.DataFrame(profiles), use_container_width=True, hide_index=True)

elif unb_result and "error" in unb_result:
    st.warning(unb_result["error"])
else:
    st.info("⏳ Hein dadus UnB...")


# ============================================================
# 6. DATASET OULAD — MONITORIZASAUN + KLASIFIKASAUN
# ============================================================
st.header("Monitorizasaun + Klasifikasaun")

col_o1, col_o2, col_o3, col_o4 = st.columns(4)

with col_o1:
    st.metric("📥 VLE", f"{oulad_vle_count:,}")
with col_o2:
    st.metric("🎓 Estudante", f"{oulad_students_count:,}")
with col_o3:
    st.metric("📝 Assessment", f"{oulad_assessment_count:,}")
with col_o4:
    st.metric("📋 Rejistu", f"{oulad_registration_count:,}")

st.divider()

st.subheader("Distribuisaun Rezultadu Final")
if not df_oulad_students.empty and "final_result" in df_oulad_students.columns:
    result_counts = df_oulad_students["final_result"].value_counts()
    st.bar_chart(result_counts)
else:
    st.info("⏳ Hein dadus OULAD...")

st.divider()

st.subheader("🎯 Klasifikasaun Graduasaun (Classification)")
st.caption("Modelu: Random Forest Classifier | Target: final_result")

if oulad_result and "error" not in oulad_result:
    st.info(f"🎯 Klase: {', '.join(oulad_result.get('classes', []))}")

    col_c1, col_c2, col_c3, col_c4 = st.columns(4)
    with col_c1:
        st.metric("Akurasa", f"{oulad_result['metrics']['accuracy']:.2%}")
    with col_c2:
        st.metric("Presizaun", f"{oulad_result['metrics']['precision']:.2%}")
    with col_c3:
        st.metric("Rekall", f"{oulad_result['metrics']['recall']:.2%}")
    with col_c4:
        st.metric("Skor F1", f"{oulad_result['metrics']['f1_score']:.2%}")

    st.divider()

    st.write("**Importánsia Fitur**")
    if oulad_result.get("feature_importance"):
        df_imp = pd.DataFrame(oulad_result["feature_importance"])
        df_imp = df_imp.set_index("feature")["importance"].sort_values(ascending=True)
        st.bar_chart(df_imp)

    st.write("**Matriz Konfusaun**")
    if oulad_result.get("confusion_matrix"):
        cm = np.array(oulad_result["confusion_matrix"])
        df_cm = pd.DataFrame(
            cm,
            index=[f"Atuál: {c}" for c in oulad_result["classes"]],
            columns=[f"Prediksaun: {c}" for c in oulad_result["classes"]],
        )
        st.dataframe(df_cm, use_container_width=True)

    st.write("**Ezemplu Prediksaun**")
    df_pred_oulad = pd.DataFrame(oulad_result.get("sample_predictions", []))
    if not df_pred_oulad.empty:
        st.dataframe(df_pred_oulad, use_container_width=True, hide_index=True)
elif oulad_result and "error" in oulad_result:
    st.warning(oulad_result["error"])
else:
    st.info("⏳ Hein dadus OULAD...")


# ============================================================
# 7. MONITORIZASAUN REAL-TIME
# ============================================================
st.header("🔄 Monitorizasaun Real-Time")
st.caption("Atividade estudante ne'ebé tama ona ba MongoDB")

if not df_events.empty:
    recent_cols = [c for c in [
        "event_time", "user_hash", "courseid", "eventname", "action"
    ] if c in df_events.columns]

    df_recent = df_events[recent_cols].head(20).copy()
    if "user_hash" in df_recent.columns:
        df_recent["user_hash"] = df_recent["user_hash"].str[:12] + "..."
    if "eventname" in df_recent.columns:
        df_recent["eventname"] = df_recent["eventname"].apply(
            lambda x: x.split("\\")[-1] if "\\" in x else x
        )

    df_recent = df_recent.rename(columns={
        "event_time": "Tempu",
        "user_hash": "Uzuáriu",
        "courseid": "Kursu",
        "eventname": "Eventu",
        "action": "Aksaun",
    })

    st.write("**Atividade Foun (20 ikus)**")
    st.dataframe(df_recent, use_container_width=True, hide_index=True)
else:
    st.info("⏳ Hein dadus...")


# ============================================================
# AUTO REFRESH
# ============================================================
time.sleep(CONFIG["refresh_seconds"])
st.rerun()