import networkx as nx
import pandas as pd


def build_clusters(edges_df):
    """
    Input: DataFrame with [entity_id_a, entity_id_b, edge_weight]
    Output: DataFrame with [entity_id, cluster_id] — one row per entity
    """
    G = nx.Graph()
    for _, row in edges_df.iterrows():
        G.add_edge(row["entity_id_a"], row["entity_id_b"], weight=row["edge_weight"])

    rows = []
    for cluster_id, component in enumerate(nx.connected_components(G), start=1):
        for entity_id in component:
            rows.append({"entity_id": entity_id, "cluster_id": cluster_id})

    return pd.DataFrame(rows).sort_values("entity_id").reset_index(drop=True)