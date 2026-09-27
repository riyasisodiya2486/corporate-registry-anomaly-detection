# Methodology: Matching & Graph Construction Layer

## Entity Matching & Pairwise Scoring
Candidate pairs generated from pincode and name-prefix blocking are evaluated using string similarity metrics. Pairwise comparisons assess normalized company names and normalized registered addresses using Jaro-Winkler similarity. Pairs exhibiting similarity scores above a pre-defined threshold ($\ge 0.85$) are classified as confirmed structural matches. In our evaluation on MCA registry data (188,042 entities), [INSERT MATCH COUNT] of [INSERT CANDIDATE PAIRS COUNT] candidate pairs ([INSERT MATCH %]%) were classified as structural matches.

## Graph Cluster Formation
Confirmed matches are converted into weighted edges within an undirected graph $G = (V, E)$, where vertices $V$ represent unique corporate entities and edge weights capture composite similarity metrics. Connected component analysis via NetworkX partitions the graph into distinct corporate clusters. From the evaluated registry dataset, the pipeline identified [INSERT CLUSTER COUNT] unique clusters, with the largest cluster containing [INSERT LARGEST CLUSTER SIZE] interconnected companies.