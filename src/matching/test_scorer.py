import pandas as pd
from scorer import score_candidate_pairs

# Sample data shaped exactly like cleaned_entities will be
entities = pd.DataFrame({
    "entity_id": [1, 2, 3, 4, 5],
    "company_name_normalized": [
        "sharma traders",
        "sharma traders",         # same name, different-looking address
        "verma textiles",
        "verma textile",          # near-identical name
        "gupta exports",          # unrelated
    ],
    "address_normalized": [
        "plot 14 midc road pune",
        "plot 14 midc road pune",
        "12 shivaji nagar pune",
        "12 shivaji nagar pune",
        "45 koregaon park pune",
    ],
})

pairs = pd.DataFrame({
    "pair_id": [1, 2, 3, 4],
    "entity_id_a": [1, 3, 1, 2],
    "entity_id_b": [2, 4, 5, 3],
})

result = score_candidate_pairs(pairs, entities)
print(result.to_string(index=False))

print("\nExpected: pairs 1 and 2 should be matches, pairs 3 and 4 should not.")