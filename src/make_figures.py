from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd

S = Path("results/snapshot")
F = Path("results/figures")
F.mkdir(parents=True, exist_ok=True)

sc = pd.read_csv(S / "cluster_scores.csv")
ex = pd.read_csv(S / "cluster_explanations.csv")
hi = sc.loc[sc.flag_category == "high_priority", "composite_score"].min()
mo = sc.loc[sc.flag_category == "moderate", "composite_score"].min()


def save(name):
    plt.tight_layout()
    plt.savefig(F / name, dpi=200)
    plt.close()


# Fig 2: cluster size distribution
plt.figure()
sizes = sc.cluster_size.value_counts().sort_index()
plt.bar(sizes.index.astype(str), sizes.values)
plt.yscale("log")
plt.xlabel("Cluster size (companies)")
plt.ylabel("Number of clusters (log scale)")
plt.title(f"Cluster sizes ({len(sc):,} clusters, max {sc.cluster_size.max()})")
plt.xticks(rotation=90, fontsize=6)
save("fig2_cluster_sizes.png")

# Fig 3: score histogram with thresholds
plt.figure()
plt.hist(sc.composite_score, bins=50)
plt.axvline(mo, color="orange", linestyle="--", label=f"Moderate >= {mo:.2f}")
plt.axvline(hi, color="red", linestyle="--", label=f"High priority >= {hi:.2f}")
plt.xlabel("Composite score")
plt.ylabel("Clusters")
plt.title("Composite Score Distribution & Risk Thresholds")
plt.legend()
save("fig3_score_hist.png")

# Fig 4: flag counts (Reordered: High / Moderate / Baseline)
plt.figure()
order = ["high_priority", "moderate", "baseline"]
display_labels = ["High Priority", "Moderate", "Baseline"]
counts = sc.flag_category.value_counts().reindex(order)
plt.bar(display_labels, counts.values)
for i, v in enumerate(counts.values):
    plt.text(i, v, f"{v:,}", ha="center", va="bottom")
plt.ylabel("Clusters")
plt.title("Cluster Risk Classification Counts")
save("fig4_flag_counts.png")

# Fig 5: which factor is the top reason in high-priority clusters
plt.figure(figsize=(8, 5))
m = ex.merge(sc[["cluster_id", "flag_category"]], on="cluster_id")
top = m[(m["rank"] == 1) & (m.flag_category == "high_priority")]

LABELS = {
    "topology_score": "Topology (how tightly connected)",
    "timing_signal_score": "Registration timing",
    "name_signal_score": "Name similarity",
    "address_signal_score": "Address similarity",
    "capital_similarity_score": "Capital similarity",
    "category_homogeneity_score": "Same business type",
}
top = top.assign(
    feature_name=top.feature_name.map(LABELS).fillna(top.feature_name)
)

top.feature_name.value_counts().sort_values().plot.barh()
plt.xlabel("High-priority clusters where this is the #1 factor")
plt.ylabel("Signal")
plt.title("Primary Driver Factor in High-Priority Clusters")
save("fig5_top_factor.png")

print("Saved figures to", F)