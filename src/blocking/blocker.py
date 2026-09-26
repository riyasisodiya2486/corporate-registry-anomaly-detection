import pandas as pd


MAX_BLOCK_SIZE = 400


def _pairs_within_group(ids):
    pairs = []
    ids = sorted(ids)

    for i in range(len(ids)):
        for j in range(i + 1, len(ids)):
            pairs.append((ids[i], ids[j]))

    return pairs


def generate_pincode_blocks(entities_df):
    """
    Groups entities by pincode.

    Normal-sized pincode groups are paired directly.
    Oversized groups are sub-blocked using the first 6 characters
    of the normalized company name.
    """

    pairs = []
    oversized_groups_report = []

    valid = entities_df.dropna(subset=["pincode"])

    for pincode, group in valid.groupby("pincode"):
        ids = group["entity_id"].tolist()

        if len(ids) <= MAX_BLOCK_SIZE:
            for a, b in _pairs_within_group(ids):
                pairs.append({
                    "entity_id_a": a,
                    "entity_id_b": b,
                    "blocking_method": "pincode"
                })

        else:
            oversized_groups_report.append((pincode, len(ids)))

            sub = group.assign(
                subkey=group["company_name_normalized"].fillna("").str[:6]
            )

            for _, subgroup in sub.groupby("subkey"):
                sub_ids = subgroup["entity_id"].tolist()

                if len(sub_ids) <= MAX_BLOCK_SIZE:
                    for a, b in _pairs_within_group(sub_ids):
                        pairs.append({
                            "entity_id_a": a,
                            "entity_id_b": b,
                            "blocking_method": "pincode"
                        })

    if oversized_groups_report:
        print(
            f"NOTE: {len(oversized_groups_report)} pincode groups "
            f"exceeded {MAX_BLOCK_SIZE} and were sub-blocked."
        )
        print(
            "Largest oversized groups:",
            sorted(
                oversized_groups_report,
                key=lambda x: -x[1]
            )[:5]
        )

    return pd.DataFrame(pairs)


def generate_name_prefix_blocks(entities_df, prefix_length=6):
    """
    Groups entities using the first 6 characters of the normalized
    company name.

    Groups larger than MAX_BLOCK_SIZE are reported and not fully
    expanded into pair combinations.
    """

    pairs = []

    valid = entities_df.dropna(
        subset=["company_name_normalized"]
    )

    valid = valid.assign(
        prefix=valid["company_name_normalized"].str[:prefix_length]
    )

    for prefix, group in valid.groupby("prefix"):

        if len(prefix) < prefix_length:
            continue

        ids = group["entity_id"].tolist()

        if len(ids) <= MAX_BLOCK_SIZE:
            for a, b in _pairs_within_group(ids):
                pairs.append({
                    "entity_id_a": a,
                    "entity_id_b": b,
                    "blocking_method": "name_prefix"
                })

        else:
            print(
                f"NOTE: name-prefix group '{prefix}' "
                f"has {len(ids)} entities and was not expanded."
            )

    return pd.DataFrame(pairs)


def generate_candidate_pairs(entities_df):
    """
    Combines pincode and name-prefix blocking strategies
    and removes duplicate entity pairs.
    """

    pincode_pairs = generate_pincode_blocks(entities_df)
    name_pairs = generate_name_prefix_blocks(entities_df)

    combined = pd.concat(
        [pincode_pairs, name_pairs],
        ignore_index=True
    )

    combined = combined.drop_duplicates(
        subset=["entity_id_a", "entity_id_b"]
    )

    return combined