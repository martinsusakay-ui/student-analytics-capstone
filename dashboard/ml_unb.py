"""
ml_unb.py - K-Means Clustering untuk dataset UnB
Target: Segmentasi perilaku mahasiswa (UNSUPERVISED)
"""

import pandas as pd
import numpy as np
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import (
    silhouette_score, davies_bouldin_score, calinski_harabasz_score
)
import warnings
warnings.filterwarnings("ignore")


def build_unb_features(df_events):
    """Bangun fitur agregat per user_hash dari event logs."""
    if df_events.empty or "user_hash" not in df_events.columns:
        return pd.DataFrame()
    
    grouped = df_events.groupby("user_hash")
    
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


def run_unb_clustering(df_events, n_clusters=3):
    """K-Means Clustering untuk segmentasi perilaku mahasiswa UnB."""
    features = build_unb_features(df_events)
    if features.empty or len(features) < n_clusters:
        return {"error": "Data tidak cukup untuk clustering (min 30 users)"}
    
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
    
    # Metrik
    try:
        silhouette = float(silhouette_score(X_scaled, labels))
    except: silhouette = 0
    try:
        davies = float(davies_bouldin_score(X_scaled, labels))
    except: davies = 0
    try:
        calinski = float(calinski_harabasz_score(X_scaled, labels))
    except: calinski = 0
    
    # Profil cluster
    cluster_stats = []
    for cid in range(n_clusters):
        cd = features[features["cluster"] == cid]
        cluster_stats.append({"cluster_id": cid, "avg_events": cd["total_events"].mean(), "size": len(cd)})
    
    sorted_clusters = sorted(cluster_stats, key=lambda x: -x["avg_events"])
    labels_pool = ["Power User", "Highly Active", "Moderately Active", "Low Activity"]
    label_map = {}
    for rank, stat in enumerate(sorted_clusters):
        if rank < len(labels_pool):
            label_map[stat["cluster_id"]] = labels_pool[rank]
    
    clusters = []
    for cid in range(n_clusters):
        cd = features[features["cluster"] == cid]
        clusters.append({
            "cluster_id": cid,
            "label": label_map.get(cid, f"Cluster {cid}"),
            "size": len(cd),
            "percentage": round(len(cd) / len(features) * 100, 2),
            "avg_total_events": round(cd["total_events"].mean(), 1),
            "avg_unique_courses": round(cd["unique_courses"].mean(), 1),
            "avg_login": round(cd["login_count"].mean(), 1),
            "avg_message": round(cd["message_count"].mean(), 1),
        })
    
    return {
        "dataset": "UnB", "model": "K-Means Clustering", "task": "Segmentasaun",
        "n_clusters": n_clusters, "n_users": len(features),
        "metrics": {
            "inertia": round(float(kmeans.inertia_), 2),
            "silhouette": round(silhouette, 4),
            "davies_bouldin": round(davies, 4),
            "calinski_harabasz": round(calinski, 2),
        },
        "clusters": clusters,
    }