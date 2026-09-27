import jellyfish
import pandas as pd

MATCH_THRESHOLD = 0.85


def score_candidate_pairs(pairs_df, entities_df):
    """Input:

      pairs_df: DataFrame with [pair_id, entity_id_a, entity_id_b]
      entities_df: DataFrame with [entity_id, company_name_normalized,
      address_normalized]

    Output:
      DataFrame with [pair_id, address_similarity, name_similarity, is_match]
    """
    fields = entities_df.set_index("entity_id")[
        ["company_name_normalized", "address_normalized"]
    ]

    merged = pairs_df.merge(
        fields, left_on="entity_id_a", right_index=True
    ).merge(fields, left_on="entity_id_b", right_index=True, suffixes=("_a", "_b"))

    names_a = merged["company_name_normalized_a"].fillna("")
    names_b = merged["company_name_normalized_b"].fillna("")
    addrs_a = merged["address_normalized_a"].fillna("")
    addrs_b = merged["address_normalized_b"].fillna("")

    name_sims = [
        jellyfish.jaro_winkler_similarity(a, b) if a and b else 0.0
        for a, b in zip(names_a, names_b)
    ]
    addr_sims = [
        jellyfish.jaro_winkler_similarity(a, b) if a and b else 0.0
        for a, b in zip(addrs_a, addrs_b)
    ]

    merged["address_similarity"] = addr_sims
    merged["name_similarity"] = name_sims
    merged["is_match"] = (merged["address_similarity"] >= MATCH_THRESHOLD) | (
        merged["name_similarity"] >= MATCH_THRESHOLD
    )

    return merged[
        ["pair_id", "address_similarity", "name_similarity", "is_match"]
    ]