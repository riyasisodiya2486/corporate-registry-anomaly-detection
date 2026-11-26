"""RIYA. AI opinion via Groq, cached in ai_opinions (owner connection, V2 only).
Input to the model: names, addresses, capital, dates. NEVER score, SHAP, status or personal names.
Clusters that already have a row are skipped, so the API is never called twice for one cluster.
Usage:
  python src/v2/llm_prescreen.py --batch r1                      # the 70 Round 1 clusters
  python src/v2/llm_prescreen.py --flag high_priority --limit 50  # top clusters of a flag
Untested: run with --limit 3 first."""
import argparse
import json
import os
import time

import pandas as pd
from dotenv import load_dotenv
from groq import Groq
from sqlalchemy import create_engine, text

load_dotenv()
url = os.environ["V2_DATABASE_URL"]
if url == os.environ.get("DATABASE_URL"):
    raise SystemExit("REFUSED: V2_DATABASE_URL equals DATABASE_URL.")
MODEL = os.environ["GROQ_MODEL"]
PROMPT_VERSION = "p1"
MAX_MEMBERS = 30

ap = argparse.ArgumentParser()
ap.add_argument("--batch")
ap.add_argument("--flag")
ap.add_argument("--limit", type=int, default=50)
args = ap.parse_args()
if not args.batch and not args.flag:
    raise SystemExit("Give --batch r1 or --flag high_priority|moderate|baseline")

ALLOWED = {
    "duplicate_record": {"yes", "no", "unsure"},
    "address_type": {"residential", "commercial", "placeholder", "unclear"},
    "registered_close": {"yes", "no", "unsure"},
}
VERDICTS = {"worth_review", "ordinary", "data_artifact", "need_more_info"}
SYSTEM = (
    "You screen a group of registered companies and decide whether a human investigator "
    "should spend time on it. You see only names, addresses, authorized capital and "
    "registration dates. Reply with JSON only, with these keys:\n"
    '"duplicate_record": "yes" | "no" | "unsure" (same company entered more than once)\n'
    '"address_type": "residential" | "commercial" | "placeholder" | "unclear"\n'
    '"registered_close": "yes" | "no" | "unsure" (registered within a short window)\n'
    '"verdict": "worth_review" | "ordinary" | "data_artifact" | "need_more_info"\n'
    '"reason": one short sentence.\n'
    "data_artifact = duplicate records or placeholder or too-generic addresses. "
    "worth_review = not an artifact and at least two independent signs point the same way "
    "with no harmless explanation. ordinary = a clear harmless explanation or only a generic "
    "word in common. need_more_info = cannot decide. Never accuse anyone of wrongdoing. "
    "Do not name any person."
)

eng = create_engine(url, pool_pre_ping=True, pool_recycle=300)
client = Groq(api_key=os.environ["GROQ_API_KEY"])

with eng.connect() as c:
    if args.batch:
        ids = [r[0] for r in c.execute(text(
            "SELECT cluster_id FROM review_queue WHERE batch = :b ORDER BY cluster_id"),
            {"b": args.batch})]
    else:
        ids = [r[0] for r in c.execute(text(
            "SELECT cluster_id FROM cluster_scores WHERE flag_category = :f "
            "ORDER BY composite_score DESC, cluster_id LIMIT :n"),
            {"f": args.flag, "n": args.limit})]
    done = {r[0] for r in c.execute(text("SELECT cluster_id FROM ai_opinions"))}

todo = [i for i in ids if i not in done]
print(f"{len(ids)} selected, {len(ids) - len(todo)} already cached, {len(todo)} to call")


def valid(d):
    if d.get("verdict") not in VERDICTS:
        return False
    return all(d.get(k) in vals for k, vals in ALLOWED.items())


ok = bad = 0
for cid in todo:
    with eng.connect() as c:
        m = pd.read_sql(text("""
            SELECT e.company_name_raw AS name, e.address_raw AS address,
                   e.authorized_capital AS capital, e.date_of_registration AS registered
            FROM cleaned_entities e JOIN cluster_assignments ca ON e.entity_id = ca.entity_id
            WHERE ca.cluster_id = :c ORDER BY e.entity_id"""), c, params={"c": int(cid)})
    note = f"\n(first {MAX_MEMBERS} of {len(m)} companies shown)" if len(m) > MAX_MEMBERS else ""
    user = m.head(MAX_MEMBERS).to_csv(index=False) + note
    data = None
    stop_all = False
    for attempt in range(1, 4):
        try:
            r = client.chat.completions.create(
                model=MODEL, temperature=0, max_tokens=1500, reasoning_effort="low",
                response_format={"type": "json_object"},
                messages=[{"role": "system", "content": SYSTEM},
                          {"role": "user", "content": user}])
            content = r.choices[0].message.content
            if not content:
                print(f"  cluster {cid} attempt {attempt}: empty answer")
                continue
            d = json.loads(content)
            if valid(d):
                data = d
                break
            print(f"  cluster {cid} attempt {attempt}: answer not in the allowed format")
        except Exception as e:
            msg = str(e)
            print(f"  cluster {cid} attempt {attempt}: {type(e).__name__}: {msg[:200]}")
            if "tokens per day" in msg or "(TPD)" in msg:
                stop_all = True
                break
            time.sleep(10 * attempt)
    if stop_all:
        print("Daily token limit reached. Rows stored so far are kept. Rerun tomorrow.")
        break
    if data is None:
        bad += 1
        print(f"  cluster {cid}: no valid answer, NOT stored (rerun later)")
        continue
    with eng.begin() as c:
        c.execute(text("""
            INSERT INTO ai_opinions (cluster_id, model, prompt_version, verdict,
                duplicate_record, address_type, registered_close,
                directors_shared, filings_ok, office_exists, reason)
            VALUES (:c, :m, :pv, :v, :d, :a, :r, 'unknown', 'unknown', 'unknown', :why)
            ON CONFLICT (cluster_id) DO NOTHING"""),
            {"c": int(cid), "m": MODEL, "pv": PROMPT_VERSION, "v": data["verdict"],
             "d": data["duplicate_record"], "a": data["address_type"],
             "r": data["registered_close"], "why": str(data.get("reason", ""))[:300]})
    ok += 1
    time.sleep(2)   # stay under free-tier rate limits
print(f"stored {ok}, failed {bad}")