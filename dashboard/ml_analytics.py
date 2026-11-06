"""
ml_analytics.py - Fungsi ML untuk dashboard
Hanya Clustering (K-Means) dengan label unik per cluster
"""

import pandas as pd
import numpy as np
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler
import warnings
warnings.filterwarnings("ignore")


def build_user_features(df: pd.DataFrame) -> pd.DataFrame:
    """Bangun fitur agregat per user_hash."""
    if df.empty or "user_hash" not in df.columns:
        return pd.DataFrame()
    
    grouped = df.groupby("user_hash")
    
    features = pd.DataFrame({
        "total_events": grouped.size(),
        "unique_events": grouped["eventname"].nunique(),
        "unique_courses": grouped["courseid"].nunique(),
        "unique_actions": grouped["action"].nunique(),
    })
    
    features["login_count"] = grouped.apply(
        lambda x: x["eventname"].str.contains("loggedin", case=False).sum()
    )
    features["message_count"] = grouped.apply(
        lambda x: x["eventname"].str.contains("message_sent", case=False).sum()
    )
    features["graded_count"] = grouped.apply(
        lambda x: x["eventname"].str.contains("user_graded", case=False).sum()
    )
    features["quiz_count"] = grouped.apply(
        lambda x: x["eventname"].str.contains("quiz", case=False).sum()
    )
    features["forum_count"] = grouped.apply(
        lambda x: x["eventname"].str.contains("forum", case=False).sum()
    )
    features["assign_count"] = grouped.apply(
        lambda x: x["eventname"].str.contains("assign", case=False).sum()
    )
    
    return features.fillna(0).reset_index()


def run_clustering(df_events: pd.DataFrame, n_clusters: int = 3) -> dict:
    """K-Means clustering dengan label unik per cluster."""
    features = build_user_features(df_events)
    if features.empty or len(features) < n_clusters:
        return {"error": "Data tidak cukup untuk clustering"}

    feature_cols = [
        "total_events", "unique_events", "unique_courses",
        "login_count", "message_count", "graded_count",
        "quiz_count", "forum_count", "assign_count",
    ]
    feature_cols = [c for c in feature_cols if c in features.columns]

    X = features[feature_cols].values
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)

    kmeans = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
    labels = kmeans.fit_predict(X_scaled)
    features["cluster"] = labels

    # Hitung avg events per cluster
    cluster_stats = []
    for cid in range(n_clusters):
        cd = features[features["cluster"] == cid]
        cluster_stats.append({
            "cluster_id": cid,
            "size": len(cd),
            "avg_events": cd["total_events"].mean(),
        })

    # Sort descending
    cluster_stats_sorted = sorted(cluster_stats, key=lambda x: -x["avg_events"])

    # Label unik berdasarkan ranking
    labels_pool = [
        "Power User",
        "Highly Active",
        "Moderately Active",
        "Low Activity",
        "Very Low Activity",
        "Minimal Activity",
    ]

    label_map = {}
    for rank, stat in enumerate(cluster_stats_sorted):
        if rank < len(labels_pool):
            label_map[stat["cluster_id"]] = labels_pool[rank]
        else:
            label_map[stat["cluster_id"]] = f"Cluster {rank}"

    # Bangun profil cluster
    clusters = []
    for cid in range(n_clusters):
        cd = features[features["cluster"] == cid]
        clusters.append({
            "cluster_id": cid,
            "label": label_map[cid],
            "size": len(cd),
            "percentage": round(len(cd) / len(features) * 100, 2),
            "avg_total_events": round(cd["total_events"].mean(), 1),
            "avg_unique_courses": round(cd["unique_courses"].mean(), 1),
            "avg_login": round(cd["login_count"].mean(), 1),
            "avg_message": round(cd["message_count"].mean(), 1),
            "avg_graded": round(cd["graded_count"].mean(), 1),
            "avg_quiz": round(cd["quiz_count"].mean(), 1),
            "avg_forum": round(cd["forum_count"].mean(), 1),
            "avg_assign": round(cd["assign_count"].mean(), 1),
        })

    return {
        "n_clusters": n_clusters,
        "n_users": len(features),
        "inertia": round(float(kmeans.inertia_), 2),
        "clusters": clusters,
    }