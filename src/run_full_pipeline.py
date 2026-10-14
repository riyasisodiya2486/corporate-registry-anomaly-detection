import subprocess
import sys
import time

STAGES = [
    # Ingestion and Cleaning skipped -- unchanged since Day 3/4, already correct in Neon
    ("Matching", "src/matching/run_matching.py"),
    ("Clustering", "src/graph/run_clustering.py"),
    ("Feature Extraction", "src/scoring/run_features.py"),
    ("Isolation Forest", "src/scoring/run_isolation_forest.py"),
    ("SHAP Explanations", "src/scoring/run_shap.py"),
]


def run():
    log = []
    total_start = time.time()
    for name, script in STAGES:
        print(f"\n{'=' * 60}\nSTAGE: {name}\n{'=' * 60}")
        start = time.time()
        # sys.executable = the same venv Python that launched this pipeline
        result = subprocess.run([sys.executable, script], capture_output=False)
        elapsed = time.time() - start
        status = "OK" if result.returncode == 0 else "FAILED"
        log.append({"stage": name, "status": status, "seconds": round(elapsed, 1)})
        if result.returncode != 0:
            print(f"\nSTOPPED: {name} failed. Fix before continuing to later stages.")
            break

    print("\n\nFULL PIPELINE SUMMARY")
    for entry in log:
        print(f"  {entry['stage']:25s} {entry['status']:8s} {entry['seconds']}s")
    print(f"  {'TOTAL':25s} {'':8s} {round(time.time() - total_start, 1)}s")


if __name__ == "__main__":
    run()