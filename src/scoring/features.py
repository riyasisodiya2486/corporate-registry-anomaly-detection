"""Pure feature functions -- no database access. Everything takes/returns DataFrames."""
import numpy as np
import pandas as pd

BRIDGE_ADDRESS_MIN = 0.80   # cross-cluster pair counts as a "tie" if address similarity >= this...
BRIDGE_NAME_MIN = 0.85      # ...or name similarity >= this


def _industry_division(nic_series):
    """First 2 digits of the NIC code = industry division. Blank/missing values are dropped."""
    s = nic_series.dropna().astype(str).str.strip()
    s = s[s != ""]
    return s.str[:2]


def _unit_prefix(addr, n=18):
    return addr[:n] if isinstance(addr, str) else ""


def address_signal_score(cluster_entities, avg_address_similarity):
    """
    0-30. avg_address_similarity: mean pairwise address_similarity from the matched edges
    that formed this cluster (same basis as name_signal_score -- fixes a bug where this
    function previously only rewarded byte-identical address strings, scoring near zero for
    clusters that were actually formed BECAUSE of high address similarity).

    Dampened in two cases:
      (a) shared professional-service address: many unrelated industries at one address
      (b) shared estate/area: similar address strings but distinct unit/plot numbers
          (discovered in real data: MIDC industrial estate companies at different plots
          score ~0.90+ on full-string similarity purely from shared boilerplate text)
    """
    n = len(cluster_entities)
    if n < 2:
        return 0.0
    base = avg_address_similarity * 30

    addrs = cluster_entities["address_normalized"].dropna()
    prefixes = addrs.apply(_unit_prefix)
    distinct_unit_ratio = prefixes.nunique() / len(prefixes) if len(prefixes) else 0.0

    divisions = _industry_division(cluster_entities["nic_code"])
    industry_diversity = divisions.nunique() / n if len(divisions) else 0.0

    if n >= 8 and industry_diversity > 0.5:
        base *= 0.4
    if distinct_unit_ratio > 0.6:
        base *= 0.35
    return round(min(base, 30.0), 2)


def timing_signal_score(cluster_entities):
    """0-20. High when members were registered within a short window."""
    dates = pd.to_datetime(cluster_entities["date_of_registration"], errors="coerce").dropna()
    if len(dates) < 2:
        return 0.0
    span = (dates.max() - dates.min()).days
    if span <= 30:
        return 20.0
    if span <= 90:
        return 12.0
    if span <= 365:
        return 5.0
    return 0.0


def capital_similarity_score(cluster_entities):
    """0-15. High when authorized capital is (nearly) identical across members."""
    values = pd.to_numeric(cluster_entities["authorized_capital"], errors="coerce").dropna()
    if len(values) < 2:
        return 0.0
    mean = values.mean()
    cv = values.std(ddof=0) / mean if mean > 0 else 1.0
    return round(max(0.0, 1.0 - cv) * 15, 2)


def topology_score(n, edge_count, max_degree):
    """0-15. High for hub-and-spoke shapes: one entity linked to most others (hub_ratio near 1)
    while the cluster overall is sparse (density near 0). Chains and full meshes both score low."""
    if n < 3:
        return 0.0
    mesh_edges = n * (n - 1) / 2
    density = min(edge_count / mesh_edges, 1.0)
    hub_ratio = min(max_degree / (n - 1), 1.0)
    return round(15 * hub_ratio * (1 - density), 2)


def category_homogeneity_score(cluster_entities):
    """0-10. High when members concentrate in few industry divisions (NIC first 2 digits)."""
    divisions = _industry_division(cluster_entities["nic_code"])
    n = len(divisions)
    if n < 2:
        return 0.0
    return round(10 * (n - divisions.nunique()) / (n - 1), 2)


def status_signal_score(cluster_entities):
    """0-10. DESCRIPTIVE ONLY: share of members whose status is not 'Active'.
    Stored for the weak-signal validation experiment. Must NOT be an Isolation Forest input."""
    statuses = cluster_entities["company_status"].dropna().astype(str).str.strip().str.lower()
    if len(statuses) == 0:
        return 0.0
    return round(float((statuses != "active").mean()) * 10, 2)


def compute_cluster_features(entities, assignments, edges, bridge_clusters):
    """
    entities:    [entity_id, address_normalized, nic_code, date_of_registration,
                  authorized_capital, company_status]
    assignments: [entity_id, cluster_id]
    edges:       confirmed matches [entity_id_a, entity_id_b, name_similarity]
    bridge_clusters: set of cluster_ids that have a cross-cluster tie
    Returns one row per cluster.
    """
    df = entities.merge(assignments, on="entity_id", how="inner")

    cl = assignments.set_index("entity_id")["cluster_id"]
    e = edges.copy()
    e["cluster_a"] = e["entity_id_a"].map(cl)
    e["cluster_b"] = e["entity_id_b"].map(cl)
    intra = e[(e["cluster_a"] == e["cluster_b"]) & e["cluster_a"].notna()].copy()
    intra["cluster_id"] = intra["cluster_a"].astype(int)

    edge_stats = intra.groupby("cluster_id").agg(
        edge_count=("name_similarity", "size"),
        avg_name_sim=("name_similarity", "mean"),
        avg_addr_sim=("address_similarity", "mean"),
    )

    ends = pd.concat([
        intra[["cluster_id", "entity_id_a"]].rename(columns={"entity_id_a": "entity_id"}),
        intra[["cluster_id", "entity_id_b"]].rename(columns={"entity_id_b": "entity_id"}),
    ])
    max_degree = (
        ends.groupby(["cluster_id", "entity_id"]).size()
        .groupby(level="cluster_id").max()
    )

    rows = []
    for cid, grp in df.groupby("cluster_id"):
        cid = int(cid)
        n = len(grp)
        ec = int(edge_stats["edge_count"].get(cid, 0))
        avg_sim = float(edge_stats["avg_name_sim"].get(cid, 0.0))
        avg_addr = float(edge_stats["avg_addr_sim"].get(cid, 0.0))
        md = int(max_degree.get(cid, 0))
        rows.append({
            "cluster_id": cid,
            "cluster_size": n,
            "address_signal_score": address_signal_score(grp, avg_addr),
            "name_signal_score": round(avg_sim * 25, 2),
            "timing_signal_score": timing_signal_score(grp),
            "status_signal_score": status_signal_score(grp),
            "capital_similarity_score": capital_similarity_score(grp),
            "topology_score": topology_score(n, ec, md),
            "bridge_flag": cid in bridge_clusters,
            "category_homogeneity_score": category_homogeneity_score(grp),
        })
    return pd.DataFrame(rows)


def find_bridge_clusters(entities, assignments, generate_pairs_fn, score_fn):
    """
    Regenerates candidate pairs locally (never stored), scores them, and returns the set of
    cluster_ids that have at least one moderately-similar tie to a DIFFERENT cluster.
    entities needs: entity_id, pincode, company_name_normalized, address_normalized
    """
    pairs = generate_pairs_fn(entities[["entity_id", "pincode", "company_name_normalized"]])
    pairs = pairs.reset_index(drop=True)
    pairs["pair_id"] = np.arange(1, len(pairs) + 1)

    scored = score_fn(pairs, entities[["entity_id", "company_name_normalized", "address_normalized"]])
    scored = scored.merge(pairs[["pair_id", "entity_id_a", "entity_id_b"]], on="pair_id")

    ties = scored[(scored["address_similarity"] >= BRIDGE_ADDRESS_MIN) |
                  (scored["name_similarity"] >= BRIDGE_NAME_MIN)]

    cl = assignments.set_index("entity_id")["cluster_id"]
    ca = ties["entity_id_a"].map(cl)
    cb = ties["entity_id_b"].map(cl)
    cross = ca.notna() & cb.notna() & (ca != cb)
    return set(ca[cross].astype(int)) | set(cb[cross].astype(int))