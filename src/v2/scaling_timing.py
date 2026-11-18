"""Yashika. Time blocking and scoring on 25/50/75/100% of the records, then plot runtime vs records.
TODO Yashika: read the signatures of generate_candidate_pairs and score_candidate_pairs
(src/blocking/blocker.py, src/matching/scorer.py) and fill in run_blocking / run_scoring.
Run on the v2 Neon branch or from the snapshot CSV, never on production tables."""
import time
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd

ent = pd.read_csv("results/snapshot/cleaned_entities.csv")
OUT = Path("results/v2")
OUT.mkdir(parents=True, exist_ok=True)


def run_blocking(df):
    raise NotImplementedError("call generate_candidate_pairs(df, ...) and return the pairs")


def run_scoring(pairs):
    raise NotImplementedError("call score_candidate_pairs(pairs, ...) and return the matches")


rows = []
for frac in (0.25, 0.5, 0.75, 1.0):
    df = ent.sample(frac=frac, random_state=7) if frac < 1 else ent
    t0 = time.time()
    pairs = run_blocking(df)
    t1 = time.time()
    run_scoring(pairs)
    t2 = time.time()
    rows.append({"fraction": frac, "records": len(df), "pairs": len(pairs),
                 "blocking_s": round(t1 - t0, 1), "scoring_s": round(t2 - t1, 1)})
    print(rows[-1])
res = pd.DataFrame(rows)
res.to_csv(OUT / "scaling.csv", index=False)
plt.plot(res.records, res.blocking_s + res.scoring_s, marker="o")
plt.xlabel("Records")
plt.ylabel("Seconds (blocking + scoring)")
plt.title("Runtime against number of records")
plt.tight_layout()
plt.savefig(OUT / "scaling.png", dpi=200)
