\# Methodology — Data Layer and Blocking



\## Dataset



The study uses 188,042 company records from the ROC Pune subset of the

MCA company master data. The records were cleaned and normalized before

candidate generation.



\## Blocking Strategy



To avoid comparing every company with every other company, blocking was

used to generate a smaller set of candidate pairs.



Two blocking keys were evaluated:



1\. Pincode blocking — companies sharing the same pincode are placed in

&#x20;  the same block.

2\. Name-prefix blocking — companies whose normalized company names share

&#x20;  the same first four characters are placed in the same block.



Candidate pairs were generated with the constraint that

`entity\_id\_a < entity\_id\_b`.



\## Blocking Evaluation



For 188,042 entities, the number of possible naive all-pairs comparisons

is:



17,679,802,861



The pincode blocking strategy produced:



257,867,038 candidate pairs



The four-character name-prefix strategy produced 9,883,244 pair

comparisons. After excluding pairs that were already generated through

pincode blocking, 9,717,826 additional unique candidate pairs remained.



Therefore, the combined unique candidate-pair count was:



267,584,864



The resulting reduction ratio was:



98.4865%



This means that blocking reduced the comparison space from approximately

17.68 billion possible pairs to approximately 267.58 million candidate

pairs before the subsequent matching stage.

