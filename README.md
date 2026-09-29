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
- **Visible features (stickers, damage, broken parts):** open **Investigations → Vehicle description**. Below the type/color/model fields, filter by feature type, location on the vehicle, and feature description; the demo query **White car · Sticker on rear glass** narrows white cars to two candidates. Features are stored in an indexed `vehicle_marks` table (type, location, description, approximate size, detectability, review status), and every sighting of a vehicle matches once a feature is logged on any of its sightings; unplated sightings match on their own features. Log a feature from any sighting's **Inspect evidence** dialog or with **Log on selected sighting** on a vehicle's page. Size is converted to pixels at a 1080p lane camera (≈3.4 mm/px); the **Camera feasibility guide** shows what is realistically visible. Model suggestions stay amber until an operator confirms or rejects them with a reason. No detector runs; the 14 seeded features are labeled demo fixtures.
- **Search area and time:** both Investigations modes have a **Search area & time** section. Limit a search to all cameras, a named region (Connaught Place; Mandi House · ITO · Tilak Bridge; India Gate · Pragati Maidan · Ring Road; East Delhi), cameras within 0.5–5 km of a chosen camera, or a single camera, and to a From/Until window with quick presets for the last 15 minutes, hour, or 3 hours of scenario time. The cameras actually searched are listed under the controls.
- **Registration lookup:** `DL10CZ7788` returns a labeled demonstration record with no sightings. Unknown numbers show that live lookup is unavailable. The official Parivahan link opens separately.

See [docs/JEV.md](docs/JEV.md) for credit controls. The Jev API key remains in `API_KEYS/vercelkey.txt`, excluded from source control. Optional settings remain in `.env`. Dashboard password settings have been removed.

Recognition is **not 90% accurate**. The release measured **7/31 exact principal plates (22.6%)** on a small exploratory set; the correctly read demo target is excluded from that set. Fine-tuning and a sufficiently large untouched test set remain unfinished. See the evaluation report before making accuracy claims.

The interface uses an OLED-black atlas with a scroll-driven perspective change, a focused recorded-journey scene, and one-at-a-time operations tabs. Sobha Privy Collection informed the scroll pacing; DAQ Consulting informed the thin/bold typography and restrained data diagrams. All map and diagram content remains local and data-derived. Detailed tables are in **Activity log**; investigation, appearance/Jev search, alerts, and administration remain in sidebar workspaces. Strong solid lines link numbered observed-camera positions, with an explicit estimated-route disclaimer. Reduced-motion mode removes scroll-linked camera motion and long pinned scenes. No new runtime service or paid API call is required by the redesign.
