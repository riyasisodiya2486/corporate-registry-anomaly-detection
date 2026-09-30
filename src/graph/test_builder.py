import pandas as pd
from builder import build_clusters

edges = pd.DataFrame(
    {
        "entity_id_a": [1, 2, 7],
        "entity_id_b": [2, 3, 8],
        "edge_weight": [0.95, 0.88, 0.91],
    }
)

result = build_clusters(edges)
print("=== Graph Clustering Test Output ===")
print(result.to_string(index=False))