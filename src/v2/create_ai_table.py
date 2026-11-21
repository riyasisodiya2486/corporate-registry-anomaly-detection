import os
from dotenv import load_dotenv
from sqlalchemy import create_engine, text

load_dotenv()
url = os.environ["V2_DATABASE_URL"]
if url == os.environ.get("DATABASE_URL"):
    raise SystemExit("REFUSED: V2_DATABASE_URL equals DATABASE_URL.")
with create_engine(url).begin() as c:
    c.execute(text("""
        CREATE TABLE IF NOT EXISTS ai_opinions (
            cluster_id       INTEGER PRIMARY KEY REFERENCES cluster_scores(cluster_id),
            model            TEXT NOT NULL,
            prompt_version   TEXT NOT NULL,
            verdict          TEXT NOT NULL CHECK (verdict IN
                             ('worth_review','ordinary','data_artifact','need_more_info')),
            duplicate_record TEXT, address_type TEXT, registered_close TEXT,
            directors_shared TEXT, filings_ok TEXT, office_exists TEXT,
            reason           TEXT,
            created_at       TIMESTAMP NOT NULL DEFAULT now())"""))
    c.execute(text("GRANT SELECT ON ai_opinions TO app_reader, app_reviewer"))
print("ai_opinions ready")