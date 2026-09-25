import pandas as pd
from sqlalchemy import create_engine


CSV_PATH = "data/raw/roc_maharashtra.csv"

COLUMN_MAPPING = {
    "CIN": "cin",
    "CompanyName": "company_name",
    "CompanyStatus": "company_status",
    "CompanyCategory": "company_category",
    "CompanySubCategory": "company_sub_category",
    "CompanyROCcode": "roc_code",
    "Registered_Office_Address": "registered_address",
    "CompanyRegistrationdate_date": "date_of_registration",
    "AuthorizedCapital": "authorized_capital",
    "PaidupCapital": "paidup_capital",
    "CompanyIndustrialClassification": "principal_business_activity",
}


def load():
    print("Reading CSV...")

    df = pd.read_csv(
        CSV_PATH,
        dtype=str,
        keep_default_na=False
    )

    print(f"Total rows in source CSV: {len(df)}")
    print("Columns found in CSV:", list(df.columns))

    # Keep only the selected project jurisdiction.
    df = df[df["CompanyROCcode"].str.strip() == "ROC Pune"].copy()

    print(f"ROC Pune rows selected: {len(df)}")

    available = {
        source: target
        for source, target in COLUMN_MAPPING.items()
        if source in df.columns
    }

    missing = [
        source
        for source in COLUMN_MAPPING
        if source not in df.columns
    ]

    if missing:
        print("WARNING — expected columns not found:", missing)

    df = df[list(available.keys())].rename(columns=available)

    engine = create_engine(
        "postgresql://admin:admin123@localhost:5432/registry"
    )

    df.to_sql(
        "raw_companies",
        engine,
        if_exists="append",
        index=False
    )

    print(f"SUCCESS: loaded {len(df)} ROC Pune rows into raw_companies")


if __name__ == "__main__":
    load()