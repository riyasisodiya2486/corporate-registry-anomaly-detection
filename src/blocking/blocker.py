import pandas as pd


def generate_pincode_blocks(entities_df):
    """
    Generates candidate pairs within each pincode group.
    Returns a DataFrame.

    This function is intended for smaller datasets/tests.
    """
    pairs = []
    valid = entities_df.dropna(subset=["pincode"])

    for _, group in valid.groupby("pincode"):
        ids = sorted(group["entity_id"].tolist())

        for i in range(len(ids)):
            for j in range(i + 1, len(ids)):
                pairs.append({
                    "entity_id_a": ids[i],
                    "entity_id_b": ids[j],
                    "blocking_method": "pincode"
                })

    return pd.DataFrame(pairs)


def generate_name_prefix_blocks(entities_df, prefix_length=4):
    """
    Groups entities by the first N characters of the normalized company name.
    """
    pairs = []
    valid = entities_df.dropna(subset=["company_name_normalized"])
    valid = valid.assign(
        prefix=valid["company_name_normalized"].str[:prefix_length]
    )

    for prefix, group in valid.groupby("prefix"):
        if len(prefix) < prefix_length:
            continue

        ids = sorted(group["entity_id"].tolist())

        for i in range(len(ids)):
            for j in range(i + 1, len(ids)):
                pairs.append({
                    "entity_id_a": ids[i],
                    "entity_id_b": ids[j],
                    "blocking_method": "name_prefix"
                })

    return pd.DataFrame(pairs)


def generate_candidate_pairs(entities_df):
    """
    Combines pincode and name-prefix blocking.
    Intended for smaller datasets.
    """
    pincode_pairs = generate_pincode_blocks(entities_df)
    name_pairs = generate_name_prefix_blocks(entities_df)

    return pd.concat(
        [pincode_pairs, name_pairs],
        ignore_index=True
    )