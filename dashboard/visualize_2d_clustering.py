"""
visualize_2d_clustering.py - Visualisasi 2D K-Means Clustering
Dataset: Moodle Activity
"""

import pandas as pd
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import seaborn as sns
from pymongo import MongoClient
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler
from sklearn.decomposition import PCA
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
    print("  2D K-MEANS CLUSTERING - MOODLE DATASET")
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
        "forum_count": grouped.apply(
            lambda x: x["eventname"].str.contains("forum", case=False).sum()
        ),
    }).fillna(0).reset_index()
    
    print(f"    Features shape: {features.shape}")
    
    # ========================================================
    # 3. CLUSTERING
    # ========================================================
    print("\n[3] Running K-Means...")
    feature_cols = [
        "total_events", "login_count", "message_count",
        "unique_courses", "graded_count", "quiz_count", "forum_count",
    ]
    
    X = features[feature_cols].values
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)
    
    kmeans = KMeans(n_clusters=CONFIG["n_clusters"], random_state=42, n_init=10)
    labels = kmeans.fit_predict(X_scaled)
    features["cluster"] = labels
    
    # Label unik
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
    # 4. VISUALISASI 2D
    # ========================================================
    print("\n[4] Creating 2D visualizations...")
    output_path = Path(CONFIG["output_dir"])
    output_path.mkdir(parents=True, exist_ok=True)
    
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
    # PLOT 1: PCA 2D SCATTER
    # ========================================================
    print("    [1/6] PCA 2D Scatter...")
    pca = PCA(n_components=2)
    X_pca = pca.fit_transform(X_scaled)
    
    fig, ax = plt.subplots(figsize=(12, 8))
    for cid in sorted(features["cluster"].unique()):
        mask = features["cluster"] == cid
        label = label_map[cid]
        color = colors_map.get(label, "#888888")
        ax.scatter(X_pca[mask, 0], X_pca[mask, 1],
                   c=color, label=f"Cluster {cid}: {label} (n={mask.sum()})",
                   alpha=0.6, s=80, edgecolors='black', linewidth=0.5)
    
    # Centroid PCA
    for cid in sorted(features["cluster"].unique()):
        mask = features["cluster"] == cid
        centroid = X_pca[mask].mean(axis=0)
        ax.scatter(centroid[0], centroid[1],
                   c='black', marker='X', s=400,
                   edgecolors='white', linewidth=3, zorder=10)
        ax.text(centroid[0], centroid[1], f'  C{cid}',
                fontsize=14, fontweight='bold', color='black', zorder=11)
    
    ax.set_xlabel(f"PC1 ({pca.explained_variance_ratio_[0]*100:.1f}%)", fontsize=12)
    ax.set_ylabel(f"PC2 ({pca.explained_variance_ratio_[1]*100:.1f}%)", fontsize=12)
    ax.set_title(f"2D K-Means Clustering (PCA)\nInertia: {kmeans.inertia_:,.2f}",
                 fontsize=14, fontweight='bold', pad=15)
    ax.legend(loc='best', fontsize=10)
    ax.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.savefig(output_path / "2d_pca_scatter.png", dpi=300, bbox_inches='tight')
    plt.close()
    print("        [SAVED] 2d_pca_scatter.png")
    
    # ========================================================
    # PLOT 2: TOTAL EVENTS vs LOGIN COUNT
    # ========================================================
    print("    [2/6] Total Events vs Login Count...")
    fig, ax = plt.subplots(figsize=(12, 8))
    for cid in sorted(features["cluster"].unique()):
        cd = features[features["cluster"] == cid]
        label = label_map[cid]
        color = colors_map.get(label, "#888888")
        ax.scatter(cd["total_events"], cd["login_count"],
                   c=color, label=label, alpha=0.6, s=80,
                   edgecolors='black', linewidth=0.5)
    
    # Centroid
    for cid in sorted(features["cluster"].unique()):
        cd = features[features["cluster"] == cid]
        ax.scatter(cd["total_events"].mean(), cd["login_count"].mean(),
                   c='black', marker='X', s=400,
                   edgecolors='white', linewidth=3, zorder=10)
    
    ax.set_xlabel("Total Events", fontsize=12)
    ax.set_ylabel("Login Count", fontsize=12)
    ax.set_title("2D Clustering: Total Events vs Login Count",
                 fontsize=14, fontweight='bold')
    ax.legend(loc='best', fontsize=10)
    ax.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.savefig(output_path / "2d_events_vs_login.png", dpi=300, bbox_inches='tight')
    plt.close()
    print("        [SAVED] 2d_events_vs_login.png")
    
    # ========================================================
    # PLOT 3: TOTAL EVENTS vs MESSAGE COUNT
    # ========================================================
    print("    [3/6] Total Events vs Message Count...")
    fig, ax = plt.subplots(figsize=(12, 8))
    for cid in sorted(features["cluster"].unique()):
        cd = features[features["cluster"] == cid]
        label = label_map[cid]
        color = colors_map.get(label, "#888888")
        ax.scatter(cd["total_events"], cd["message_count"],
                   c=color, label=label, alpha=0.6, s=80,
                   edgecolors='black', linewidth=0.5)
    
    # Centroid
    for cid in sorted(features["cluster"].unique()):
        cd = features[features["cluster"] == cid]
        ax.scatter(cd["total_events"].mean(), cd["message_count"].mean(),
                   c='black', marker='X', s=400,
                   edgecolors='white', linewidth=3, zorder=10)
    
    ax.set_xlabel("Total Events", fontsize=12)
    ax.set_ylabel("Message Count", fontsize=12)
    ax.set_title("2D Clustering: Total Events vs Message Count",
                 fontsize=14, fontweight='bold')
    ax.legend(loc='best', fontsize=10)
    ax.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.savefig(output_path / "2d_events_vs_message.png", dpi=300, bbox_inches='tight')
    plt.close()
    print("        [SAVED] 2d_events_vs_message.png")
    
    # ========================================================
    # PLOT 4: LOGIN COUNT vs MESSAGE COUNT
    # ========================================================
    print("    [4/6] Login Count vs Message Count...")
    fig, ax = plt.subplots(figsize=(12, 8))
    for cid in sorted(features["cluster"].unique()):
        cd = features[features["cluster"] == cid]
        label = label_map[cid]
        color = colors_map.get(label, "#888888")
        ax.scatter(cd["login_count"], cd["message_count"],
                   c=color, label=label, alpha=0.6, s=80,
                   edgecolors='black', linewidth=0.5)
    
    # Centroid
    for cid in sorted(features["cluster"].unique()):
        cd = features[features["cluster"] == cid]
        ax.scatter(cd["login_count"].mean(), cd["message_count"].mean(),
                   c='black', marker='X', s=400,
                   edgecolors='white', linewidth=3, zorder=10)
    
    ax.set_xlabel("Login Count", fontsize=12)
    ax.set_ylabel("Message Count", fontsize=12)
    ax.set_title("2D Clustering: Login Count vs Message Count",
                 fontsize=14, fontweight='bold')
    ax.legend(loc='best', fontsize=10)
    ax.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.savefig(output_path / "2d_login_vs_message.png", dpi=300, bbox_inches='tight')
    plt.close()
    print("        [SAVED] 2d_login_vs_message.png")
    
    # ========================================================
    # PLOT 5: 3 PROJECTIONS DALAM 1 FIGURE
    # ========================================================
    print("    [5/6] 3 Projections...")
    fig, axes = plt.subplots(1, 3, figsize=(20, 6))
    
    pairs = [
        ("total_events", "login_count", "Total Events vs Login Count"),
        ("total_events", "message_count", "Total Events vs Message Count"),
        ("login_count", "message_count", "Login Count vs Message Count"),
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
                       edgecolors='white', linewidth=2, zorder=10)
        
        ax.set_xlabel(col1.replace("_", " ").title(), fontsize=11)
        ax.set_ylabel(col2.replace("_", " ").title(), fontsize=11)
        ax.set_title(title, fontsize=12, fontweight='bold')
        ax.legend(fontsize=9)
        ax.grid(True, alpha=0.3)
    
    plt.suptitle("2D Projections of Clustering", fontsize=16, fontweight='bold', y=1.02)
    plt.tight_layout()
    plt.savefig(output_path / "2d_projections.png", dpi=300, bbox_inches='tight')
    plt.close()
    print("        [SAVED] 2d_projections.png")
    
    # ========================================================
    # PLOT 6: CLUSTER DISTRIBUTION + FEATURE MEANS
    # ========================================================
    print("    [6/6] Distribution & Feature Means...")
    fig, axes = plt.subplots(1, 2, figsize=(18, 7))
    
    # Bar chart distribusi
    ax1 = axes[0]
    cluster_counts = features["cluster_label"].value_counts()
    bar_colors = [colors_map.get(l, "#888888") for l in cluster_counts.index]
    bars = ax1.bar(cluster_counts.index, cluster_counts.values,
                   color=bar_colors, edgecolor="black", linewidth=2)
    
    for bar in bars:
        height = bar.get_height()
        ax1.text(bar.get_x() + bar.get_width()/2., height,
                 f'{int(height)}\n({height/len(features)*100:.1f}%)',
                 ha='center', va='bottom', fontsize=11, fontweight='bold')
    
    ax1.set_title("Distribusi Cluster", fontsize=14, fontweight='bold')
    ax1.set_xlabel("Cluster", fontsize=12)
    ax1.set_ylabel("Jumlah User", fontsize=12)
    ax1.grid(True, alpha=0.3, axis='y')
    
    # Heatmap fitur means
    ax2 = axes[1]
    cluster_means = features.groupby("cluster_label")[feature_cols].mean()
    sns.heatmap(cluster_means, annot=True, fmt=".1f", cmap="YlOrRd",
                ax=ax2, cbar_kws={"label": "Rata-rata"}, linewidths=0.5)
    ax2.set_title("Heatmap Profil Cluster", fontsize=14, fontweight='bold')
    ax2.set_xlabel("Fitur", fontsize=12)
    ax2.set_ylabel("Cluster", fontsize=12)
    plt.xticks(rotation=45, ha='right')
    
    plt.tight_layout()
    plt.savefig(output_path / "2d_distribution_heatmap.png", dpi=300, bbox_inches='tight')
    plt.close()
    print("        [SAVED] 2d_distribution_heatmap.png")
    
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
    print(f"  PCA Variance Explained: PC1={pca.explained_variance_ratio_[0]*100:.1f}%, "
          f"PC2={pca.explained_variance_ratio_[1]*100:.1f}%")
    print("=" * 70)
    print(f"\n[INFO] Files saved to: {output_path.resolve()}")
    print("=" * 70)


if __name__ == "__main__":
    main()