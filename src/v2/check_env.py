"""Riya or Yashika. Shows WHICH database each .env key points to (host and database name only, no passwords)
and the row counts, so a script can never silently write to production."""
import os
from urllib.parse import urlparse

from dotenv import load_dotenv
from sqlalchemy import create_engine, text

load_dotenv()
KEYS = ["DATABASE_URL", "V2_DATABASE_URL", "APP_DATABASE_URL", "REVIEWER_DATABASE_URL"]
TABLES = ["cleaned_entities", "cluster_assignments", "cluster_scores", "cluster_explanations",
          "review_queue", "reviewer_reviews"]

for k in KEYS:
    url = os.environ.get(k)
    if not url:
        print(f"{k:22s} not set")
        continue
    u = urlparse(url)
    print(f"{k:22s} host={u.hostname}  db={u.path.lstrip('/')}  user={u.username}")
    if k == "REVIEWER_DATABASE_URL":
        continue
    try:
        with create_engine(url).connect() as conn:
            parts = []
            for t in TABLES:
                try:
                    parts.append(f"{t}={conn.execute(text(f'SELECT COUNT(*) FROM {t}')).scalar()}")
                except Exception:
                    conn.rollback()
                    parts.append(f"{t}=missing/no access")
            print("    " + ", ".join(parts))
    except Exception as e:
        print("    could not connect:", str(e)[:100])