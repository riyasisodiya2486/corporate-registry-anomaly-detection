import pandas as pd
from sqlalchemy import create_engine

engine = create_engine("postgresql://admin:admin123@localhost:5432/registry")

df = pd.read_sql(
    "SELECT registered_address, company_name FROM raw_companies LIMIT 500",
    engine
)

print("=== 30 sample addresses ===")
for addr in df["registered_address"].head(30):
    print(repr(addr))

print("\n=== 30 sample company names ===")
for name in df["company_name"].head(30):
    print(repr(name))

print("\n=== How many addresses are null or blank? ===")
print("Null:", df["registered_address"].isna().sum())
print(
    "Blank:",
    (df["registered_address"].fillna("").str.strip() == "").sum()
)