import os
import pandas as pd
from dotenv import load_dotenv
from sqlalchemy import create_engine

load_dotenv()

prod_engine = create_engine(os.environ["DATABASE_URL"])
test_engine = create_engine(
    "postgresql://testuser:testpass@host.docker.internal:5433/test_registry"
)

def run():
    sample = pd.read_sql(
        "SELECT * FROM cleaned_entities ORDER BY RANDOM() LIMIT 500",
        prod_engine
    )
    sample.to_sql("cleaned_entities", test_engine, if_exists="replace", index=False)
    print(f"SUCCESS: seeded test database with {len(sample)} rows")

if __name__ == "__main__":
    run()