"""
visualize_3d_clustering.py - Visualisasi 3D K-Means Clustering
Dataset: Moodle Activity
Fitur: total_events, login_count, message_count
"""

import pandas as pd
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D
from pymongo import MongoClient
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler
from pathlib import Path
import warnings
warnings.filterwarnings("ignore")


CONFIG = {
    "mongo_uri": "mongodb://admin:admin123@localhost:27017/?authSource=admin",
    "mongo_db": "moodle_analytics",
    "collection_events": "events",
    "n_clusters": 3,
    "output_dir": "clustering_output",
}


def main():
    print("=" * 70)
    print("  3D K-MEANS CLUSTERING - MOODLE DATASET")
    print("=" * 70)
    
    # ========================================================
    # 1. LOAD DATA
    # ========================================================
    print("\n[1] Connecting to MongoDB...")
    client = MongoClient(CONFIG["mongo_uri"])
    db = client[CONFIG["mongo_db"]]
    collection = db[CONFIG["collection_events"]]
    
    events = list(collection.find({}, {"_id": 0}).limit(50000))
    df = pd.DataFrame(events)
    print(f"    Loaded {len(df):,} events")
    print(f"    Unique users: {df['user_hash'].nunique():,}")
    
    if df.empty:
        print("[ERROR] No data!")
        return
    
    # ========================================================
    # 2. FEATURE ENGINEERING
    # ========================================================
    print("\n[2] Building features...")
    grouped = df.groupby("user_hash")
    
    features = pd.DataFrame({
        "total_events": grouped.size(),
        "login_count": grouped.apply(
            lambda x: x["eventname"].str.contains("loggedin", case=False).sum()
        ),
        "message_count": grouped.apply(
            lambda x: x["eventname"].str.contains("message_sent", case=False).sum()
        ),
        "unique_courses": grouped["courseid"].nunique(),
        "graded_count": grouped.apply(
            lambda x: x["eventname"].str.contains("user_graded", case=False).sum()
        ),
        "quiz_count": grouped.apply(
            lambda x: x["eventname"].str.contains("quiz", case=False).sum()
        ),
    }).fillna(0).reset_index()
    
    print(f"    Features shape: {features.shape}")
    
    # ========================================================
    # 3. CLUSTERING
    # ========================================================
    print("\n[3] Running K-Means...")
    feature_cols = [
        "total_events", "login_count", "message_count",
        "unique_courses", "graded_count", "quiz_count",
    ]
    
    X = features[feature_cols].values
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)
    
    kmeans = KMeans(n_clusters=CONFIG["n_clusters"], random_state=42, n_init=10)
    labels = kmeans.fit_predict(X_scaled)
    features["cluster"] = labels
    
    # Label unik berdasarkan ranking
    cluster_stats = []
    for cid in range(CONFIG["n_clusters"]):
        cd = features[features["cluster"] == cid]
        cluster_stats.append({
            "cluster_id": cid,
            "avg_events": cd["total_events"].mean(),
        })
    
    cluster_stats_sorted = sorted(cluster_stats, key=lambda x: -x["avg_events"])
    labels_pool = ["Power User", "Highly Active", "Moderately Active",
                   "Low Activity", "Very Low Activity", "Minimal Activity"]
    
    label_map = {}
    for rank, stat in enumerate(cluster_stats_sorted):
        if rank < len(labels_pool):
            label_map[stat["cluster_id"]] = labels_pool[rank]
    
    features["cluster_label"] = features["cluster"].map(label_map)
    print(f"    Inertia: {kmeans.inertia_:,.2f}")
    
    # ========================================================
    # 4. VISUALISASI 3D
    # ========================================================
    print("\n[4] Creating 3D visualization...")
    output_path = Path(CONFIG["output_dir"])
    output_path.mkdir(parents=True, exist_ok=True)
    
    # 3 fitur untuk 3D
    x_col = "total_events"
    y_col = "login_count"
    z_col = "message_count"
    
    # Warna per cluster
    colors_map = {
        "Power User": "#FF6B6B",
        "Highly Active": "#4ECDC4",
        "Moderately Active": "#45B7D1",
        "Low Activity": "#96CEB4",
        "Very Low Activity": "#FFEAA7",
        "Minimal Activity": "#DDA0DD",
    }
    
    # ========================================================
    # PLOT 1: 3D SCATTER
    # ========================================================
    fig = plt.figure(figsize=(14, 10))
    ax = fig.add_subplot(111, projection='3d')
    
    for cid in sorted(features["cluster"].unique()):
        cd = features[features["cluster"] == cid]
        label = label_map[cid]
        color = colors_map.get(label, "#888888")
        
        ax.scatter(
            cd[x_col], cd[y_col], cd[z_col],
            c=color, label=f"Cluster {cid}: {label} (n={len(cd)})",
            s=80, alpha=0.6, edgecolors='black', linewidth=0.5
        )
    
    # Plot centroid
    for cid in sorted(features["cluster"].unique()):
        cd = features[features["cluster"] == cid]
        centroid_x = cd[x_col].mean()
        centroid_y = cd[y_col].mean()
        centroid_z = cd[z_col].mean()
        
        ax.scatter(
            centroid_x, centroid_y, centroid_z,
            c='black', marker='X', s=400,
            edgecolors='white', linewidth=3,
            label=f"Centroid #{cid}" if cid == 0 else None
        )
        ax.text(centroid_x, centroid_y, centroid_z,
                f'  C{cid}', fontsize=14, fontweight='bold', color='black')
    
    # Label
    ax.set_xlabel(x_col.replace("_", " ").title(), fontsize=12, labelpad=10)
    ax.set_ylabel(y_col.replace("_", " ").title(), fontsize=12, labelpad=10)
    ax.set_zlabel(z_col.replace("_", " ").title(), fontsize=12, labelpad=10)
    
    ax.set_title(
        f"3D K-Means Clustering — Moodle Activity\n"
        f"Fitur: {x_col}, {y_col}, {z_col} | K={CONFIG['n_clusters']} | "
        f"Inertia: {kmeans.inertia_:,.2f}",
        fontsize=14, fontweight='bold', pad=20
    )
    
    ax.legend(loc='upper left', fontsize=10, framealpha=0.9)
    ax.view_init(elev=20, azim=45)
    ax.grid(True, alpha=0.3)
    
    plt.tight_layout()
    plt.savefig(output_path / "3d_clustering_moodle.png", dpi=300, bbox_inches='tight')
    plt.close()
    print(f"    [SAVED] 3d_clustering_moodle.png")
    
    # ========================================================
    # PLOT 2: 3D SCATTER (VIEW BERBEDA)
    # ========================================================
    fig = plt.figure(figsize=(14, 10))
    ax = fig.add_subplot(111, projection='3d')
    
    for cid in sorted(features["cluster"].unique()):
        cd = features[features["cluster"] == cid]
        label = label_map[cid]
        color = colors_map.get(label, "#888888")
        
        ax.scatter(
            cd[x_col], cd[y_col], cd[z_col],
            c=color, label=label, s=80, alpha=0.6,
            edgecolors='black', linewidth=0.5
        )
    
    # Centroid
    for cid in sorted(features["cluster"].unique()):
        cd = features[features["cluster"] == cid]
        ax.scatter(
            cd[x_col].mean(), cd[y_col].mean(), cd[z_col].mean(),
            c='black', marker='X', s=400,
            edgecolors='white', linewidth=3
        )
    
    ax.set_xlabel(x_col.replace("_", " ").title(), fontsize=12)
    ax.set_ylabel(y_col.replace("_", " ").title(), fontsize=12)
    ax.set_zlabel(z_col.replace("_", " ").title(), fontsize=12)
    ax.set_title(
        f"3D K-Means Clustering — View 2\n"
        f"Moodle Activity Dataset",
        fontsize=14, fontweight='bold', pad=20
    )
    ax.legend(loc='upper right', fontsize=10)
    ax.view_init(elev=30, azim=120)
    ax.grid(True, alpha=0.3)
    
    plt.tight_layout()
    plt.savefig(output_path / "3d_clustering_view2.png", dpi=300, bbox_inches='tight')
    plt.close()
    print(f"    [SAVED] 3d_clustering_view2.png")
    
    # ========================================================
    # PLOT 3: 2D PROJECTIONS (3 SUBPLOT)
    # ========================================================
    fig, axes = plt.subplots(1, 3, figsize=(20, 6))
    
    pairs = [
        (x_col, y_col, "Total Events vs Login Count"),
        (x_col, z_col, "Total Events vs Message Count"),
        (y_col, z_col, "Login Count vs Message Count"),
    ]
    
    for ax, (col1, col2, title) in zip(axes, pairs):
        for cid in sorted(features["cluster"].unique()):
            cd = features[features["cluster"] == cid]
            label = label_map[cid]
            color = colors_map.get(label, "#888888")
            ax.scatter(cd[col1], cd[col2], c=color, label=label,
                       s=60, alpha=0.6, edgecolors='black', linewidth=0.5)
        
        # Centroid
        for cid in sorted(features["cluster"].unique()):
            cd = features[features["cluster"] == cid]
            ax.scatter(cd[col1].mean(), cd[col2].mean(),
                       c='black', marker='X', s=300,
                       edgecolors='white', linewidth=2)
        
        ax.set_xlabel(col1.replace("_", " ").title(), fontsize=11)
        ax.set_ylabel(col2.replace("_", " ").title(), fontsize=11)
        ax.set_title(title, fontsize=12, fontweight='bold')
        ax.legend(fontsize=9)
        ax.grid(True, alpha=0.3)
    
    plt.suptitle("2D Projections of 3D Clustering", fontsize=16, fontweight='bold', y=1.02)
    plt.tight_layout()
    plt.savefig(output_path / "3d_clustering_projections.png", dpi=300, bbox_inches='tight')
    plt.close()
    print(f"    [SAVED] 3d_clustering_projections.png")
    
    # ========================================================
    # 5. SUMMARY
    # ========================================================
    print("\n" + "=" * 70)
    print("  CLUSTER SUMMARY")
    print("=" * 70)
    for cid in sorted(features["cluster"].unique()):
        cd = features[features["cluster"] == cid]
        print(f"\n  Cluster #{cid}: {label_map[cid]}")
        print(f"    Size        : {len(cd):,} users ({len(cd)/len(features)*100:.1f}%)")
        print(f"    Avg Events  : {cd['total_events'].mean():.1f}")
        print(f"    Avg Login   : {cd['login_count'].mean():.1f}")
        print(f"    Avg Msg     : {cd['message_count'].mean():.1f}")
    
    print(f"\n  Inertia: {kmeans.inertia_:,.2f}")
    print(f"  Total Users: {len(features):,}")
    print("=" * 70)
    print(f"\n[INFO] Files saved to: {output_path.resolve()}")
    print("=" * 70)


if __name__ == "__main__":
    main()