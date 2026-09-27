import os
import networkx as nx
import pandas as pd
from dotenv import load_dotenv
from sqlalchemy import create_engine, text

load_dotenv()

db_url = os.getenv("DATABASE_URL")
if not db_url:
    raise ValueError("DATABASE_URL not found in .env file.")

engine = create_engine(db_url)


def run():
    print("Pulling matched pairs from Neon for graph clustering...")
    query = """
        SELECT 
            entity_id_a, 
            entity_id_b,
            GREATEST(address_similarity, name_similarity) AS edge_weight
        FROM scored_pairs
        WHERE is_match = TRUE
    """
    matched = pd.read_sql(query, engine)
    print(f"Loaded {len(matched):,} matched edges into memory.")

    if matched.empty:
        print("No matches found. Exiting.")
        return

    print("Building NetworkX undirected graph from matched edges...")
    G = nx.Graph()

    # Add edges with attributes
    edges = [
        (row["entity_id_a"], row["entity_id_b"], {"weight": row["edge_weight"]})
        for _, row in matched.iterrows()
    ]
    G.add_edges_from(edges)

    print(
        f"Graph constructed: {G.number_of_nodes():,} nodes, {G.number_of_edges():,} edges."
    )

    print("Computing connected components (clusters)...")
    connected_components = list(nx.connected_components(G))
    print(f"Identified {len(connected_components):,} distinct clusters.")

    # Build entity-to-cluster DataFrame
    cluster_records = []
    for cluster_id, component in enumerate(connected_components, start=1):
        for entity_id in component:
            cluster_records.append(
                {
                    "entity_id": str(entity_id),
                    "cluster_id": f"cluster_{cluster_id}",
                    "cluster_size": len(component),
                }
            )

    clusters_df = pd.DataFrame(cluster_records)

    # Re-create clusters table in Neon
    with engine.begin() as conn:
        conn.execute(text("DROP TABLE IF EXISTS entity_clusters CASCADE;"))
        conn.execute(
            text("""
            CREATE TABLE entity_clusters (
                entity_id TEXT PRIMARY KEY,
                cluster_id TEXT,
                cluster_size INTEGER,
                created_at TIMESTAMP DEFAULT NOW()
            );
        """)
        )

    print("Uploading cluster assignments to Neon...")
    clusters_df.to_sql(
        "entity_clusters", engine, if_exists="append", index=False
    )

    print("\n--- Cluster Size Distribution ---")
    size_summary = (
        clusters_df.groupby("cluster_size")["cluster_id"]
        .nunique()
        .reset_index(name="cluster_count")
    )
    print(size_summary.head(10).to_string(index=False))

    print(
        f"\nSUCCESS: Assigned {len(clusters_df):,} entities to {len(connected_components):,} clusters."
    )


if __name__ == "__main__":
    run()