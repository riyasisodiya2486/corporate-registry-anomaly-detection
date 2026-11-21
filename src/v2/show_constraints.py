import os
from dotenv import load_dotenv
from sqlalchemy import create_engine, text

load_dotenv()
url = os.environ["V2_DATABASE_URL"]
if url == os.environ.get("DATABASE_URL"):
    raise SystemExit("V2_DATABASE_URL equals DATABASE_URL. Stop.")
eng = create_engine(url)
with eng.connect() as c:
    print("CONSTRAINTS")
    for r in c.execute(text("""
        SELECT conrelid::regclass, conname, pg_get_constraintdef(oid)
        FROM pg_constraint
        WHERE conrelid IN ('review_queue'::regclass, 'reviewer_reviews'::regclass)""")):
        print("  ", *r)
    print("DEFAULTS")
    for r in c.execute(text("""
        SELECT column_name, column_default, is_identity
        FROM information_schema.columns
        WHERE table_name = 'reviewer_reviews' ORDER BY ordinal_position""")):
        print("  ", *r)
    print("GRANTS (app_* roles)")
    for r in c.execute(text("""
        SELECT grantee, table_name, privilege_type
        FROM information_schema.role_table_grants
        WHERE grantee LIKE 'app_%' ORDER BY grantee, table_name, privilege_type""")):
        print("  ", *r)