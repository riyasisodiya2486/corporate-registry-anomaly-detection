import jellyfish
import recordlinkage
import pandas as pd

# Fake company records with intentional real-world-style typos
data = pd.DataFrame({
    "entity_id": [1, 2, 3, 4],
    "company_name": [
        "Sharma Traders Pvt Ltd",
        "Sharma Traders Private Limited",
        "Verma Textiles Ltd",
        "Verma Textile Limited",
    ],
    "address": [
        "Plot 14 MIDC Road Pune",
        "Plot-14, M.I.D.C., Pune",
        "12 Shivaji Nagar Pune",
        "12 Shivaji Ngr, Pune",
    ],
})

print("=== Testing jellyfish directly ===")
for i in range(len(data)):
    for j in range(i + 1, len(data)):
        name_score = jellyfish.jaro_winkler_similarity(
            data.company_name[i], data.company_name[j]
        )
        addr_score = jellyfish.jaro_winkler_similarity(
            data.address[i], data.address[j]
        )
        print(f"Pair ({i},{j}): name={name_score:.2f}  address={addr_score:.2f}")

print("\n=== Testing recordlinkage's built-in comparator ===")
indexer = recordlinkage.Index()
indexer.full()
candidate_pairs = indexer.index(data)

compare = recordlinkage.Compare()
compare.string("company_name", "company_name", method="jarowinkler", label="name_sim")
compare.string("address", "address", method="jarowinkler", label="addr_sim")
result = compare.compute(candidate_pairs, data)
print(result)