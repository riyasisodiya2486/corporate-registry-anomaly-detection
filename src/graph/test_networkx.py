import networkx as nx

G = nx.Graph()
G.add_edge(1, 2, weight=0.9)
G.add_edge(2, 3, weight=0.85)
G.add_edge(4, 5, weight=0.95)  # separate cluster, unconnected to 1-2-3

clusters = list(nx.connected_components(G))
print("Clusters found:", clusters)
print("SUCCESS: NetworkX connected-components working")