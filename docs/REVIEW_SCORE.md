# Experimental suspicion score

Shown in the interface as **Suspicion score** (previously "theft review score"). API field names (`theft_review`) are unchanged.

This is a transparent rule-based review aid, not a trained theft classifier or a calibrated probability. The warning is displayed on vehicle search results and vehicle investigations. Low or zero scores do not clear a vehicle. No action, alert, association, or priority change is performed by scoring.

## Rules, version 1

| Observed signal | Points |
|---|---:|
| Accepted exact match to an active demo stolen/wanted record, OCR ≥ 0.90 | 70 |
| Accepted exact match to another active flagged record | 45 |
| Uncertain exact/one-character watchlist resemblance | 15 |
| Plate explicitly recorded as visibly absent | 12 |
| Vehicle explicitly recorded as heavily obscured | 8 |
| Conflicting identity association | 15 |
| Accepted camera sequence A → B → A → B within 20 scenario minutes | 20 |

Only one watchlist signal contributes. Scores are capped at 95/100. Unreadable plates are not treated as absent. Missing evidence remains unknown; sufficiently unobserved candidates display “Unknown.” The same passage does not accumulate points repeatedly. Camera patterns use accepted sightings of one identity in the same run, within the previous 20 minutes, and never use future sightings. Appearance-only candidates remain separate. Routine journeys, lawful coverings, OCR mistakes and camera timing can explain these signals.

Description-match scores are separate: the fraction of requested attributes actually matched, on a 0–100 scale. Known contradictions are excluded; unknown attributes do not earn points. Appearance search ranks match quality first, then distinguishing attributes, with theft-review score used only to break equally relevant matches. Plate and ordinary attribute searches put accepted associations and higher OCR scores first. OCR confidence, match quality and theft-review points are not interchangeable.

The weights are hand-selected prototype values. They have no measured theft-prediction accuracy and are not a basis for enforcement. Watchlists, observed Delhi locations and most supporting attributes in this presentation are synthetic. Jev is not called to calculate scores, so scoring consumes no gateway credits.

Regression coverage includes expiry, future-history exclusion, separation across runs, missing-versus-unreadable plates, explanation of each signal, and scoring without new alerts.
