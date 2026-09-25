# Related Work Notes — Yashika

## 1. Fellegi–Sunter Record Linkage

- Record linkage is used to determine whether two records refer to the same real-world entity.
- The Fellegi–Sunter framework compares candidate record pairs using evidence from multiple fields and assigns matching weights/probabilities.
- It can classify pairs as matches, non-matches, or uncertain/possible matches.
- In our project, this provides the classical foundation for comparing company records, although our implementation uses name and address similarity rather than directly implementing the Fellegi–Sunter model.

## 2. Finding Shell Company Accounts Using Anomaly Detection — CoDS-COMAD 2018

- The paper investigates the use of anomaly detection for identifying suspicious patterns associated with shell company accounts.
- It is relevant because our project also uses anomaly detection to identify unusual patterns in corporate registry data.
- The paper helped establish the idea of looking for unusual behaviour/patterns rather than relying only on manually defined rules.
- Our project extends this direction to corporate registry data by combining entity matching, graph relationships, structural signals, and anomaly scoring.