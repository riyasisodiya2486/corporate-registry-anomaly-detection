# Fuzzy Matching Library Standard

## Decision
We will standardize on **`recordlinkage`** for pair generation and structured indexing, while utilizing **`jellyfish`** for lightweight inline string evaluations.

## Justification
- Both libraries yield consistent Jaro-Winkler similarity scores across company names and addresses (e.g., ~0.95 Jaro-Winkler for near-identical company names).
- `recordlinkage` provides built-in indexing and blocking capabilities, which will be essential to avoid full cross-product performance bottlenecks when scaling similarity matching across large blocks of corporate registry records.
- `jellyfish` provides fast C-optimized string comparisons for direct pairwise scoring without requiring index management.