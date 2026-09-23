import pandas as pd
import jellyfish   # swap to recordlinkage if that was your Day 2 decision

# Import from shared config once it exists; hardcode for now if not yet created
MATCH_THRESHOLD = 0.85


def score_candidate_pairs(pairs_df, entities_df):
    """
    Input:
      pairs_df: DataFrame with [pair_id, entity_id_a, entity_id_b]
      entities_df: DataFrame with [entity_id, company_name_normalized, address_normalized]
    Output:
      DataFrame with [pair_id, address_similarity, name_similarity, is_match]
      (matches the scored_pairs table schema in the interface contract)
    """
    lookup = entities_df.set_index("entity_id")

    results = []
    for _, row in pairs_df.iterrows():
        a = lookup.loc[row["entity_id_a"]]
        b = lookup.loc[row["entity_id_b"]]

        name_a = a["company_name_normalized"] or ""
        name_b = b["company_name_normalized"] or ""
        addr_a = a["address_normalized"] or ""
        addr_b = b["address_normalized"] or ""

        name_sim = jellyfish.jaro_winkler_similarity(name_a, name_b) if name_a and name_b else 0.0
        addr_sim = jellyfish.jaro_winkler_similarity(addr_a, addr_b) if addr_a and addr_b else 0.0

        results.append({
            "pair_id": row["pair_id"],
            "address_similarity": round(addr_sim, 4),
            "name_similarity": round(name_sim, 4),
            "is_match": bool(addr_sim >= MATCH_THRESHOLD or name_sim >= MATCH_THRESHOLD),
        })

    return pd.DataFrame(results)