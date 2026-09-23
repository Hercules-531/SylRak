# SylRak — Delhi vehicle intelligence prototype

SylRak is a local SIH26127 demonstration of Indian number-plate recognition, multi-camera vehicle trajectories, watchlist alerts, vehicle-history search, and traffic analytics. It combines real inference on a bundled sample with clearly labeled simulated Delhi camera observations.

## Start the presentation build

Open PowerShell in this folder and run:

```powershell
.\Start-SylRak.ps1
```

The script builds the dashboard, starts the local server, and opens `http://127.0.0.1:8010` directly. No login or password is required. The core application works offline after setup. The optional Jev description assistant needs internet for new descriptions; previously evaluated descriptions are cached locally.

The local workspace has access to replay, camera-health, watchlist, investigation, and alert controls. Stop the server with `./Stop-SylRak.ps1`.

## Presentation searches

- Number plate: `KL22L9038` shows the real OCR target and its four-camera replay after the recognition demo.
- Ready-to-use number plate: `DL8CAF2041` shows a seeded multi-camera history and active demonstration watchlist alert.
- Description: open **Investigations → Vehicle description**, then click the demo query for **white / car / mid-size / Honda City**. The result `DL8CAF2041` opens the same complete journey.

Each vehicle investigation shows first and last seen times, latest camera, accepted path, uncertain sightings, evidence, watchlist state, descriptive attributes, and a chronological timeline. Starting a new demo run archives earlier runs rather than deleting their histories.

See [DEMO_GUIDE.md](DEMO_GUIDE.md) for the three-minute walkthrough and [docs/EVALUATION.md](docs/EVALUATION.md) for measured recognition results and honest limitations.

## Verification

```powershell
.\.venv313\Scripts\python.exe -m pytest -q
npm run build
npm run test:ui
npm run test:upgrades
```

The browser workflow runs with external network requests blocked and checks real OCR, replay controls, one alert episode, four ordered camera sightings, uncertain-match separation, normalized plate search, history preservation, responsive layout, and all primary pages.

## Implementation

- React, TypeScript, Vite, TanStack Query, MapLibre GL, and local PMTiles
- FastAPI, SQLAlchemy, and SQLite in WAL mode
- YOLOv8n vehicle detection, FastALPR plate detection, and PaddleOCR English recognition; the original CCT model is retained as a recorded alternative and rollback
- Local evidence files with hashes, source/license metadata, and immutable OCR records
- Direct local administrator access, evidence endpoints, and an audit log

SQLite is retained because it makes the demonstration reproducible and preserves historical runs. The camera positions, watchlist entries, descriptive vehicle metadata, times, and replay locations are simulated. They do not represent Delhi Police infrastructure or real stolen-vehicle status.

## Added presentation workflows

- **Investigations → Distinctive appearance:** multicolor cars, regional colors, accessories, damage, covered vehicles, and separate candidates for common white Dzires. Select up to four candidates to compare, then add them to a case. Reviewed case connections remain separate from exact plate histories.
- **Jev description assistant:** expand “Describe a vehicle in your own words.” Click “Search with Jev” to apply the extracted filters and display matching candidates automatically. You can refine the populated fields afterward. A real response for the example in the demo guide is already cached.
- **Alerts:** critical/high/medium ordering, acknowledgement, per-vehicle mute, dismissed history, and administrator stop/re-enable. Repeated sightings update one episode. Banner delivery has persistent cursors and cooldowns; sound defaults off.
- **Registration lookup:** `DL10CZ7788` returns a labeled demonstration record with no sightings. Unknown numbers show that live lookup is unavailable. The official Parivahan link opens separately.

See [docs/JEV.md](docs/JEV.md) for credit controls. The Jev API key remains in `API_KEYS/vercelkey.txt`, excluded from source control. Optional settings remain in `.env`. Dashboard password settings have been removed.

Recognition is **not 90% accurate**. The release measured **7/31 exact principal plates (22.6%)** on a small exploratory set; the correctly read demo target is excluded from that set. Fine-tuning and a sufficiently large untouched test set remain unfinished. See the evaluation report before making accuracy claims.

The interface uses a pure-black background, the current IST date in the header, and navigation that opens from the left edge on hover, focus, or tap. The replay clock retains its scenario date. Search results include an explainable experimental theft review score; it is not a calibrated probability or proof of theft. See [the scoring rules](docs/REVIEW_SCORE.md).
