# Prototype evaluation and limitations

## Measured results

The bundled target `sample-027` was processed by the release's actual local models and read as raw `KL 22L 9038`, normalized to `KL22L9038`. Its vehicle box, plate box, crop, OCR text, and confidence come from the same image-processing job. Browser verification confirms one alert and four ordered camera sightings. Original CCT readings remain attached as alternatives from the same photograph; they do not count as independent evidence.

The previous 5/31 (16.1%) result selected a candidate using its distance to the answer key. That number is superseded and must not be cited as automatic system accuracy. `scripts/evaluate_samples.py` now chooses the principal prediction deterministically by plate area times detector confidence after application deduplication, before reading the reference transcription.

| Configuration | Exact principal plates / 31 | Character error rate |
|---|---:|---:|
| Original CCT baseline, deterministic selection | 4 (12.9%) | 28.5% |
| CCT with padding/orientation/two-line preprocessing | 1 (3.2%) | 74.2% |
| Paddle English PP-OCRv5 with the same preprocessing | 7 (22.6%) | 35.1% |

The predefined group split gives eight validation images: Paddle scored 3/8 versus CCT's 1/8. Paddle was selected on that validation result; it also passes the separate presentation target. The remaining 23 previously inspected development images scored 4/23 for Paddle. This is an exploratory comparison, **not an untouched final test**. Paddle improves exact matches here but produces more character errors overall than the original CCT baseline. Demonstration groups and duplicate file hashes are excluded. No character substitutions or ground-truth-based candidate choices are applied.

A fresh run of the shipped full pipeline reproduces **7/31**, with one unreadable result and **0.519 seconds mean warmed processing time** on this laptop, excluding initial model loading. Plate detection on the four evaluation images with publisher boxes produced 6 true positives, 1 false positive, and 1 false negative at IoU 0.5 (85.7% precision and recall). On that tiny spatially matched principal-plate subset, full plate recognition was **0/4**; OCR on the four annotated plate crops was also **0/4**. These four images are too few to estimate deployment detection accuracy. Vehicle detection precision/recall are unavailable because vehicle bounding-box labels are absent.

Full prediction rows, failures, versions, timing and limitations: [recognition-results.json](recognition-results.json). Reproduce using `scripts/benchmark_recognition.py` and `scripts/evaluate_release.py`; inputs and model hashes are under `artifacts/recognition-upgrade`. Both scripts select predictions independently of reference text.

The official greater-than-90% requirement remains unmet. A 0.90 model confidence is not 90% measured accuracy. Both models make substantial errors on small, angled and two-line Indian plates. The dashboard preserves raw OCR, separates model confidence from heuristic association, and routes uncertain readings to review. Fine-tuning, an independently reviewed corpus, and at least 200 untouched real test images remain outstanding; see [TRAINING_NEXT.md](TRAINING_NEXT.md).

## Verified application behavior

- The target creates one exact watchlist alert episode; later accepted sightings update its last accepted camera.
- Four accepted sightings appear once and in chronological order: Barakhamba Road → Mandi House → ITO → Akshardham approach.
- A one-character uncertain observation is excluded from the accepted route until review.
- Plate normalization, combined filters, descriptive search, replay restart, out-of-order events, duplicate ingestion, expired watchlists, failed inference, offline cameras, and resumable events have automated coverage.
- New demo runs archive earlier observations and evidence, so plate queries can reopen past travel history.
- Browser checks block external requests and exercise the dashboard at 1440×900, 1366×768, and a narrower 1000px view.
- Per-user mutes, administrator suppression, persistent notification cursors, cooldowns, and muted/dismissed retrieval have regression coverage. Appearance watches can be stopped and repeated identical activation reuses the active rule.
- Registration lookup returns labeled synthetic records independently of sightings and never invents an unregistered status.
- Multicolor and common-car candidates, covered-vehicle uncertainty, comparison, and reversible case review pass browser checks. Known attribute conflicts are excluded from search results.
- Jev's cached real response populates editable search filters. Reloading does not call Jev; simulated service failure leaves manual search working. Only one real gateway request was used during verification.

## Data truth labels

The Delhi camera network, watchlists, timestamps, traffic population, descriptive make/model/size metadata, and replayed sightings are synthetic. Camera markers are plausible demonstration locations, not verified police installations. The prototype cannot establish a continuous route, true current position, real-world stolen status, or citywide traffic conditions.

Sample publisher metadata, filenames, hashes, source URL, and declared CC0 license are stored under `assets/samples`. The Delhi PMTiles provenance and OpenStreetMap attribution are stored under `assets/map`.
