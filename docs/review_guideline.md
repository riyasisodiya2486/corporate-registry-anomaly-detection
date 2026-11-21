# Review guideline (Round 1 and Round 2), fixed before reviewing starts

## 1. What the verdict means
The verdict is NOT "suspicious" or "fraud". It answers one question:
"Is this group worth a human investigator's time?"

## 2. What the reviewer sees
Company names, registered addresses, authorized capital, registration dates,
and how many clusters share each address. No score, flag, SHAP, or status.

## 3. The six checks
| Check | Meaning | Allowed answers |
|---|---|---|
| duplicate_record | Same company entered more than once | yes / no / unsure |
| address_type | What the address looks like | residential / commercial / placeholder / unclear |
| registered_close | Registered within a short window | yes / no / unsure |
| directors_shared | Not visible on screen | yes / no / unknown |
| filings_ok | Not visible on screen | yes / no / unknown |
| office_exists | Needs outside checking | yes / no / unknown |
(Answer unknown when the information is not shown. Do not guess.)

## 4. Verdict rules, in priority order
1. data_artifact: duplicate_record is yes, or the address is a placeholder or too generic to mean anything.
2. worth_review: not an artifact, and at least two independent signs point the same way
   (real shared address, near-identical names, close registration dates) with no harmless explanation.
3. ordinary: a clear harmless explanation exists, or the similarity is only a generic word.
4. need_more_info: cannot decide from what is shown.

## 5. Rules for reviewers
- Work alone. Do not discuss clusters until all three reviewers finish.
- Do not look anything up about any person. Write no personal names, including directors, in notes.
- Use exactly your agreed reviewer name every session.

## 6. Disagreements
After export, disagreements are adjudicated in one call. The final label records both original verdicts.

## 7. Limits
Blindness between reviewers is enforced by the app and by procedure, not by the database.
Reviewers share one passcode and self-declare their names.
Three of the six checks are mostly "unknown" in blind mode.
The app author is also a reviewer and knew the system design.