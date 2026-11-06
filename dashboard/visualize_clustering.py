"""
visualize_clustering.py - Visualisasi hasil K-Means Clustering
Simpan hasil sebagai PNG
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from pymongo import MongoClient
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler
from sklearn.decomposition import PCA
from pathlib import Path
import sys
import warnings
warnings.filterwarnings("ignore")

# ============================================================
# KONFIGURASI
# ============================================================
CONFIG = {
    "mongo_uri": "mongodb://admin:admin123@localhost:27017/?authSource=admin",
    "mongo_db": "moodle_analytics",
    "collection_events": "events",
    "n_clusters": 3,
    "output_dir": "clustering_output",
}


# ============================================================
# LOAD DATA
# ============================================================
def load_events():
    """Load events dari MongoDB."""
    print("[INFO] Connecting to MongoDB...")
    client = MongoClient(CONFIG["mongo_uri"])
    db = client[CONFIG["mongo_db"]]
    collection = db[CONFIG["collection_events"]]
    
    events = list(collection.find({}, {"_id": 0}).limit(50000))
    df = pd.DataFrame(events)
    print(f"[INFO] Loaded {len(df):,} events")
    print(f"[INFO] Unique users: {df['user_hash'].nunique():,}")
    return df


# ============================================================
# FEATURE ENGINEERING
# ============================================================
def build_features(df):
    """Bangun fitur agregat per user."""
    print("[INFO] Building features...")
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
    
    features = features.fillna(0).reset_index()
    print(f"[INFO] Features shape: {features.shape}")
    return features


# ============================================================
# CLUSTERING
# ============================================================
def run_clustering(features, n_clusters=3):
    """Run K-Means clustering."""
    print(f"[INFO] Running K-Means with {n_clusters} clusters...")
    
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
    
    # Label unik berdasarkan ranking
    cluster_stats = []
    for cid in range(n_clusters):
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
        label_map[stat["cluster_id"]] = labels_pool[rank]
    
    features["cluster_label"] = features["cluster"].map(label_map)
    
    inertia = kmeans.inertia_
    print(f"[INFO] Inertia: {inertia:,.2f}")
    
    return features, X_scaled, inertia, label_map


# ============================================================
# VISUALISASI
# ============================================================
def visualize_all(features, X_scaled, inertia, label_map, output_dir):
    """Buat semua visualisasi dan simpan sebagai PNG."""
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    
    sns.set_style("whitegrid")
    colors = ["#FF6B6B", "#4ECDC4", "#45B7D1", "#96CEB4", "#FFEAA7", "#DDA0DD"]
    
    # ========================================================
    # 1. CLUSTER DISTRIBUTION (BAR CHART)
    # ========================================================
    fig, ax = plt.subplots(figsize=(10, 6))
    cluster_counts = features["cluster_label"].value_counts()
    bars = ax.bar(cluster_counts.index, cluster_counts.values, 
                  color=colors[:len(cluster_counts)], edgecolor="black")
    
    for bar in bars:
        height = bar.get_height()
        ax.text(bar.get_x() + bar.get_width()/2., height,
                f'{int(height)}\n({height/len(features)*100:.1f}%)',
                ha='center', va='bottom', fontsize=11, fontweight='bold')
    
    ax.set_title("Distribusi Cluster", fontsize=16, fontweight='bold')
    ax.set_xlabel("Cluster Label", fontsize=12)
    ax.set_ylabel("Jumlah User", fontsize=12)
    plt.tight_layout()
    plt.savefig(output_path / "01_cluster_distribution.png", dpi=300, bbox_inches='tight')
    plt.close()
    print(f"[SAVED] 01_cluster_distribution.png")
    
    # ========================================================
    # 2. PCA SCATTER PLOT (2D)
    # ========================================================
    pca = PCA(n_components=2)
    X_pca = pca.fit_transform(X_scaled)
    
    fig, ax = plt.subplots(figsize=(10, 8))
    for cid in sorted(features["cluster"].unique()):
        mask = features["cluster"] == cid
        label = label_map[cid]
        ax.scatter(X_pca[mask, 0], X_pca[mask, 1],
                   c=colors[cid], label=f"Cluster {cid}: {label}",
                   alpha=0.6, s=50, edgecolors='black', linewidth=0.5)
    
    ax.set_title("K-Means Clustering (PCA 2D)", fontsize=16, fontweight='bold')
    ax.set_xlabel(f"PC1 ({pca.explained_variance_ratio_[0]*100:.1f}%)", fontsize=12)
    ax.set_ylabel(f"PC2 ({pca.explained_variance_ratio_[1]*100:.1f}%)", fontsize=12)
    ax.legend(loc='best', fontsize=10)
    plt.tight_layout()
    plt.savefig(output_path / "02_pca_scatter.png", dpi=300, bbox_inches='tight')
    plt.close()
    print(f"[SAVED] 02_pca_scatter.png")
    
    # ========================================================
    # 3. FEATURE COMPARISON (GROUPED BAR)
    # ========================================================
    feature_cols = [
        "total_events", "unique_events", "unique_courses",
        "login_count", "message_count", "graded_count",
        "quiz_count", "forum_count", "assign_count",
    ]
    feature_cols = [c for c in feature_cols if c in features.columns]
    
    cluster_means = features.groupby("cluster_label")[feature_cols].mean()
    
    fig, ax = plt.subplots(figsize=(14, 7))
    cluster_means.T.plot(kind='bar', ax=ax, color=colors[:len(cluster_means)], 
                         edgecolor='black', width=0.8)
    
    ax.set_title("Perbandingan Fitur per Cluster", fontsize=16, fontweight='bold')
    ax.set_xlabel("Fitur", fontsize=12)
    ax.set_ylabel("Rata-rata Nilai", fontsize=12)
    ax.legend(title="Cluster", fontsize=10, loc='best')
    plt.xticks(rotation=45, ha='right')
    plt.tight_layout()
    plt.savefig(output_path / "03_feature_comparison.png", dpi=300, bbox_inches='tight')
    plt.close()
    print(f"[SAVED] 03_feature_comparison.png")
    
    # ========================================================
    # 4. HEATMAP CLUSTER PROFILE
    # ========================================================
    fig, ax = plt.subplots(figsize=(12, 6))
    sns.heatmap(cluster_means, annot=True, fmt=".1f", cmap="YlOrRd",
                ax=ax, cbar_kws={"label": "Rata-rata"}, linewidths=0.5)
    ax.set_title("Heatmap Profil Cluster", fontsize=16, fontweight='bold')
    ax.set_xlabel("Fitur", fontsize=12)
    ax.set_ylabel("Cluster", fontsize=12)
    plt.xticks(rotation=45, ha='right')
    plt.tight_layout()
    plt.savefig(output_path / "04_cluster_heatmap.png", dpi=300, bbox_inches='tight')
    plt.close()
    print(f"[SAVED] 04_cluster_heatmap.png")
    
    # ========================================================
    # 5. ELBOW METHOD
    # ========================================================
    print("[INFO] Running elbow method...")
    inertias = []
    K_range = range(2, 8)
    for k in K_range:
        km = KMeans(n_clusters=k, random_state=42, n_init=10)
        km.fit(X_scaled)
        inertias.append(km.inertia_)
    
    fig, ax = plt.subplots(figsize=(10, 6))
    ax.plot(K_range, inertias, 'bo-', linewidth=2, markersize=10)
    ax.axvline(x=3, color='red', linestyle='--', alpha=0.7, label='Elbow (k=3)')
    ax.set_title("Elbow Method", fontsize=16, fontweight='bold')
    ax.set_xlabel("Jumlah Cluster (k)", fontsize=12)
    ax.set_ylabel("Inertia", fontsize=12)
    ax.legend(fontsize=10)
    ax.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.savefig(output_path / "05_elbow_method.png", dpi=300, bbox_inches='tight')
    plt.close()
    print(f"[SAVED] 05_elbow_method.png")
    
    # ========================================================
    # 6. SUMMARY TABLE
    # ========================================================
    fig, ax = plt.subplots(figsize=(14, 4))
    ax.axis('tight')
    ax.axis('off')
    
    summary_data = []
    for cid in sorted(features["cluster"].unique()):
        cd = features[features["cluster"] == cid]
        summary_data.append([
            f"#{cid}",
            label_map[cid],
            f"{len(cd):,}",
            f"{len(cd)/len(features)*100:.1f}%",
            f"{cd['total_events'].mean():.1f}",
            f"{cd['login_count'].mean():.1f}",
            f"{cd['message_count'].mean():.1f}",
        ])
    
    table = ax.table(
        cellText=summary_data,
        colLabels=["Cluster", "Label", "Size", "%", "Avg Events", "Avg Login", "Avg Msg"],
        cellLoc='center',
        loc='center',
        colColours=['#4ECDC4']*7
    )
    table.auto_set_font_size(False)
    table.set_fontsize(11)
    table.scale(1, 2)
    
    ax.set_title(f"Ringkasan Cluster (Inertia: {inertia:,.2f})", 
                 fontsize=16, fontweight='bold', pad=20)
    plt.tight_layout()
    plt.savefig(output_path / "06_summary_table.png", dpi=300, bbox_inches='tight')
    plt.close()
    print(f"[SAVED] 06_summary_table.png")
    
    print(f"\n[INFO] Semua visualisasi disimpan di: {output_path.resolve()}")


# ============================================================
# MAIN
# ============================================================
def main():
    print("=" * 70)
    print("  K-MEANS CLUSTERING VISUALIZATION")
    print("=" * 70)
    print(f"  MongoDB     : {CONFIG['mongo_db']}.{CONFIG['collection_events']}")
    print(f"  Clusters    : {CONFIG['n_clusters']}")
    print(f"  Output      : {CONFIG['output_dir']}/")
    print("=" * 70 + "\n")
    
    # Load data
    df = load_events()
    if df.empty:
        print("[ERROR] No data in MongoDB")
        return
    
    # Build features
    features = build_features(df)
    if features.empty:
        print("[ERROR] No features")
        return
    
    # Clustering
    features, X_scaled, inertia, label_map = run_clustering(
        features, CONFIG["n_clusters"]
    )
    
    # Visualisasi
    visualize_all(features, X_scaled, inertia, label_map, CONFIG["output_dir"])
    
    # Print summary
    print("\n" + "=" * 70)
    print("  CLUSTER SUMMARY")
    print("=" * 70)
    for cid in sorted(features["cluster"].unique()):
        cd = features[features["cluster"] == cid]
        print(f"  Cluster #{cid}: {label_map[cid]}")
        print(f"    - Size      : {len(cd):,} users ({len(cd)/len(features)*100:.1f}%)")
        print(f"    - Avg Events: {cd['total_events'].mean():.1f}")
        print(f"    - Avg Login : {cd['login_count'].mean():.1f}")
        print(f"    - Avg Msg   : {cd['message_count'].mean():.1f}")
    print("=" * 70)


if __name__ == "__main__":
    main()