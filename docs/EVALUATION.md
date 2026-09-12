# Prototype evaluation and limitations

## Measured results

The bundled target `sample-027` was processed by the actual local models and read correctly as `KL22L9038`. A warmed run during browser verification took about 1.35 seconds on this laptop's CPU provider. Its vehicle box, plate box, crop, OCR text, and confidence all come from the same image-processing job.

An exploratory post-inference comparison was run on 31 manually transcribed principal plates from the CC0 sample collection. Five images had an exact full-plate result among detected candidates: **16.1% exact accuracy**. Best-candidate character error rate was **24.1%**. This small convenience sample is not a production benchmark, and the annotations have not received independent review.

The official greater-than-90% requirement remains an unproven target. The general global OCR model frequently confuses `0/O`, `1/I`, or drops characters on small and angled Indian plates. The dashboard preserves raw OCR, separates model confidence from heuristic association, and routes uncertain readings to review.

## Verified application behavior

- The target creates one exact watchlist alert episode; later accepted sightings update its last accepted camera.
- Four accepted sightings appear once and in chronological order: Barakhamba Road → Mandi House → ITO → Akshardham approach.
- A one-character uncertain observation is excluded from the accepted route until review.
- Plate normalization, combined filters, descriptive search, replay restart, out-of-order events, duplicate ingestion, expired watchlists, failed inference, offline cameras, and resumable events have automated coverage.
- New demo runs archive earlier observations and evidence, so plate queries can reopen past travel history.
- Browser checks block external requests and exercise the dashboard at 1440×900, 1366×768, and a narrower 1000px view.

## Data truth labels

The Delhi camera network, watchlists, timestamps, traffic population, descriptive make/model/size metadata, and replayed sightings are synthetic. Camera markers are plausible demonstration locations, not verified police installations. The prototype cannot establish a continuous route, true current position, real-world stolen status, or citywide traffic conditions.

Sample publisher metadata, filenames, hashes, source URL, and declared CC0 license are stored under `assets/samples`. The Delhi PMTiles provenance and OpenStreetMap attribution are stored under `assets/map`.
