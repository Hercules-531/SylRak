# SylRak — Delhi vehicle intelligence prototype

SylRak is a local SIH26127 demonstration of Indian number-plate recognition, multi-camera vehicle trajectories, watchlist alerts, vehicle-history search, and traffic analytics. It combines real inference on a bundled sample with clearly labeled simulated Delhi camera observations.

## Start the presentation build

Open PowerShell in this folder and run:

```powershell
.\Start-SylRak.ps1
```

The script builds the dashboard, starts the local server, prints the generated administrator and operator passwords, and opens `http://127.0.0.1:8000`. It needs no internet connection after the project dependencies and bundled assets are present.

Use the administrator account for replay, camera-health, and watchlist controls. Use the operator account to demonstrate investigation and alert review. Stop the server with `./Stop-SylRak.ps1`.

## Presentation searches

- Number plate: `KL22L9038` shows the real OCR target and its four-camera replay after the recognition demo.
- Ready-to-use number plate: `DL8CAF2041` shows a seeded multi-camera history and active demonstration watchlist alert.
- Description: open **Investigations → Vehicle description**, then click the demo query for **white / car / mid-size / Honda City**. The result `DL8CAF2041` opens the same complete journey.

Each vehicle investigation shows first and last seen times, latest camera, accepted path, uncertain sightings, evidence, watchlist state, descriptive attributes, and a chronological timeline. Starting a new demo run archives earlier runs rather than deleting their histories.

See [DEMO_GUIDE.md](DEMO_GUIDE.md) for the three-minute walkthrough and [docs/EVALUATION.md](docs/EVALUATION.md) for measured recognition results and honest limitations.

## Verification

```powershell
.\.venv\Scripts\python.exe -m pytest -q
npm run build
npm run test:ui
```

The browser workflow runs with external network requests blocked and checks real OCR, replay controls, one alert episode, four ordered camera sightings, uncertain-match separation, normalized plate search, history preservation, responsive layout, and all primary pages.

## Implementation

- React, TypeScript, Vite, TanStack Query, MapLibre GL, and local PMTiles
- FastAPI, SQLAlchemy, and SQLite in WAL mode
- YOLOv8n vehicle detection plus FastALPR plate detection and OCR
- Local evidence files with hashes, source/license metadata, and immutable OCR records
- Session-cookie roles, controlled evidence endpoints, and an audit log

SQLite is retained because it makes the demonstration reproducible and preserves historical runs. The camera positions, watchlist entries, descriptive vehicle metadata, times, and replay locations are simulated. They do not represent Delhi Police infrastructure or real stolen-vehicle status.
