import os
from dotenv import load_dotenv
from urllib.parse import urlparse

load_dotenv()

MATCH_THRESHOLD = 0.85
HIGH_PRIORITY_SCORE = 60
MODERATE_SCORE = 30
CAPITAL_SIMILARITY_THRESHOLD = 0.95
BRIDGE_MIN_CLUSTER_SIZE = 3
TOP_N_SHAP_FEATURES = 3

_database_url = os.getenv("DATABASE_URL")

if not _database_url:
    raise RuntimeError("DATABASE_URL is not set")

_parsed = urlparse(_database_url)

DB_CONFIG = {
    "host": _parsed.hostname,
    "port": _parsed.port or 5432,
    "dbname": _parsed.path.lstrip("/"),
    "user": _parsed.username,
    "password": _parsed.password,
    "sslmode": "require",
}