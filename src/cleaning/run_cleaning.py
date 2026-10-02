import os

import pandas as pd
from sqlalchemy import create_engine

from normalize import (
    normalize_address,
    normalize_company_name,
    extract_pincode,
    parse_capital
)


database_url = os.getenv(
    "DATABASE_URL",
    "postgresql://admin:admin123@localhost:5432/registry"
)

engine = create_engine(database_url)


def run():
    df = pd.read_sql("SELECT * FROM raw_companies", engine)

    print(f"Loaded {len(df)} raw rows")

    out = pd.DataFrame({
        "raw_id": df["raw_id"],
        "cin": df["cin"],
        "company_name_raw": df["company_name"],
        "company_name_normalized": df["company_name"].apply(
            normalize_company_name
        ),
        "address_raw": df["registered_address"],
        "address_normalized": df["registered_address"].apply(
            normalize_address
        ),
        "pincode": df["registered_address"].apply(
            extract_pincode
        ),
        "company_status": df["company_status"],
        "company_category": df["company_category"],
        "company_sub_category": df["company_sub_category"],
        "authorized_capital": df["authorized_capital"].apply(
            parse_capital
        ),
        "paidup_capital": df["paidup_capital"].apply(
            parse_capital
        ),
        "date_of_registration": pd.to_datetime(
            df["date_of_registration"],
            errors="coerce",
            dayfirst=True
        ).dt.date,
        "nic_code": df["principal_business_activity"],
    })

    out.to_sql(
        "cleaned_entities",
        engine,
        if_exists="append",
        index=False
    )

    print(f"SUCCESS: wrote {len(out)} cleaned rows")

    print("\n=== Cleaning quality report ===")
    print(
        "Addresses normalized OK:",
        out["address_normalized"].notna().sum()
    )
    print(
        "Addresses failed/empty:",
        out["address_normalized"].isna().sum()
    )
    print(
        "Pincodes extracted:",
        out["pincode"].notna().sum()
    )
    print(
        "Pincodes missing:",
        out["pincode"].isna().sum()
    )
    print(
        "Dates parsed OK:",
        out["date_of_registration"].notna().sum()
    )
    print(
        "Capital parsed OK:",
        out["authorized_capital"].notna().sum()
    )


if __name__ == "__main__":
    run()