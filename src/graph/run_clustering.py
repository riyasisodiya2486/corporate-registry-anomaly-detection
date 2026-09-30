import os
import networkx as nx
import pandas as pd
from dotenv import load_dotenv
from networkx.algorithms.community import louvain_communities
from sqlalchemy import create_engine, text

load_dotenv()
engine = create_engine(os.getenv("DATABASE_URL"), pool_pre_ping=True)

MAX_CLUSTER_SIZE = 200
MAX_SPLIT_DEPTH = 3


def split_component(G, nodes, depth=0):
    if len(nodes) <= MAX_CLUSTER_SIZE or depth >= MAX_SPLIT_DEPTH:
        return [set(nodes)]
    sub = G.subgraph(nodes)
    parts = louvain_communities(
        sub, weight="weight", resolution=1.0 + depth, seed=42
    )
    if len(parts) <= 1:
        return [set(nodes)]
    out = []
    for part in parts:
        out.extend(split_component(G, part, depth + 1))
    return out


def run():
    print("Pulling matched pairs from Neon...")
    edges = pd.read_sql(
        """SELECT entity_id_a, entity_id_b,
                  GREATEST(address_similarity, name_similarity) AS edge_weight
           FROM scored_pairs WHERE is_match = TRUE""",
        engine,
    )
    edges["entity_id_a"] = pd.to_numeric(edges["entity_id_a"]).astype(int)
    edges["entity_id_b"] = pd.to_numeric(edges["entity_id_b"]).astype(int)
    print(f"Loaded {len(edges):,} matched edges.")

    G = nx.Graph()
    G.add_weighted_edges_from(
        edges[["entity_id_a", "entity_id_b", "edge_weight"]].itertuples(
            index=False, name=None
        )
    )
    components = list(nx.connected_components(G))
    comp_sizes = sorted((len(c) for c in components), reverse=True)
    print(f"Graph: {G.number_of_nodes():,} nodes, {G.number_of_edges():,} edges")
    print(f"Connected components: {len(components):,} | largest 5: {comp_sizes[:5]}")

    clusters, split_count = [], 0
    for comp in components:
        if len(comp) > MAX_CLUSTER_SIZE:
            split_count += 1
        clusters.extend(split_component(G, comp))
    before = sum(len(c) for c in clusters)
    clusters = [c for c in clusters if len(c) >= 2]
    dropped = before - sum(len(c) for c in clusters)
    clusters.sort(key=len, reverse=True)

    print(
        f"Oversized components split with Louvain: {split_count} | singletons dropped: {dropped}"
    )

    assign = pd.DataFrame(
        [
            {"entity_id": int(eid), "cluster_id": cid}
            for cid, members in enumerate(clusters, start=1)
            for eid in members
        ]
    )

    with engine.begin() as conn:
        conn.execute(text("DROP TABLE IF EXISTS entity_clusters CASCADE;"))
        conn.execute(text("DROP TABLE IF EXISTS cluster_assignments CASCADE;"))
        conn.execute(
            text("""
            CREATE TABLE cluster_assignments (
                entity_id INTEGER PRIMARY KEY REFERENCES cleaned_entities(entity_id),
                cluster_id INTEGER NOT NULL,
                assigned_at TIMESTAMP DEFAULT NOW()
            );
        """)
        )

    assign.to_sql(
        "cluster_assignments",
        engine,
        if_exists="append",
        index=False,
        method="multi",
        chunksize=5000,
    )

    sizes = assign.groupby("cluster_id").size()
    print(f"\nSUCCESS: {len(assign):,} entities in {len(sizes):,} clusters")
    print("Ten largest cluster sizes:", sizes.sort_values(ascending=False).head(10).tolist())
    print(
        sizes.value_counts()
        .sort_index()
        .head(12)
        .rename("cluster_count")
        .to_frame()
        .rename_axis("cluster_size")
    )


if __name__ == "__main__":
    run()