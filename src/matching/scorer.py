import jellyfish
import pandas as pd

# Stricter than the original 0.85 / 0.85 rule. Jaro-Winkler rewards shared prefixes, so names such as
# "devidas estate developers" vs "devidatta woodcraft" score ~0.86 even for unrelated companies.
ADDRESS_MATCH_THRESHOLD = 0.90
NAME_MATCH_THRESHOLD = 0.95
MATCH_THRESHOLD = ADDRESS_MATCH_THRESHOLD  # kept so any older script that imports it doesn't break


def score_candidate_pairs(pairs_df, entities_df):
    """
    Input:
      pairs_df:    [pair_id, entity_id_a, entity_id_b]
      entities_df: [entity_id, company_name_normalized, address_normalized]
    Output:
      [pair_id, address_similarity, name_similarity, is_match]   (signature unchanged)
    """
    fields = entities_df.set_index("entity_id")[["company_name_normalized", "address_normalized"]]

    merged = (
        pairs_df
        .merge(fields, left_on="entity_id_a", right_index=True)
        .merge(fields, left_on="entity_id_b", right_index=True, suffixes=("_a", "_b"))
    )

    names_a = merged["company_name_normalized_a"].fillna("")
    names_b = merged["company_name_normalized_b"].fillna("")
    addrs_a = merged["address_normalized_a"].fillna("")
    addrs_b = merged["address_normalized_b"].fillna("")

    merged["name_similarity"] = [
        jellyfish.jaro_winkler_similarity(a, b) if a and b else 0.0 for a, b in zip(names_a, names_b)
    ]
    merged["address_similarity"] = [
        jellyfish.jaro_winkler_similarity(a, b) if a and b else 0.0 for a, b in zip(addrs_a, addrs_b)
    ]
    merged["is_match"] = (
        (merged["address_similarity"] >= ADDRESS_MATCH_THRESHOLD)
        | (merged["name_similarity"] >= NAME_MATCH_THRESHOLD)
    )
    return merged[["pair_id", "address_similarity", "name_similarity", "is_match"]]