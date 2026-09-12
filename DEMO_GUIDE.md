# SylRak three-minute demonstration

## 1. Query by description — 35 seconds

1. Open **Investigations** and select **Vehicle description**.
2. Click the prepared query: **White · Car · Mid-size · Honda City**.
3. Open registration **DL8CAF2041**.
4. Point out the latest observed location, dashed estimated path, full observation timeline, descriptive metadata, and demonstration watchlist alert.

The make/model and size are explicitly labeled seeded demonstration metadata.

## 2. Real recognition and latest path — 90 seconds

1. Return to **Command** and click **Recognize vehicle**.
2. Keep target sample `sample-027` and camera `C01 · Barakhamba Road`; click **Run recognition**.
3. Show the source photo, detected crop, OCR result **KL22L9038**, confidence, and **Sample inference** label.
4. Close the panel, set replay to `60×`, and press Play. The vehicle appears at Mandi House, ITO, and Akshardham approach. The replay takes about 24 seconds.
5. Open its stolen-vehicle demonstration alert, then the investigation. Explain that only the first recognition is real inference; later sightings reuse that evidence and are labeled **Camera replay**.

## 3. Query by number plate and past history — 45 seconds

1. Open **Investigations → Number plate** and search `KL22L9038`.
2. Open any result. The investigation consolidates all accepted sightings into the route and lists the one uncertain reading separately.
3. Use the date filters to narrow history. Use **Recorded journey** to select an earlier archived run when available.
4. If demonstrating persistence, click **New demo run** in the header, search the plate again, and reopen the archived journey. The old evidence and path remain available.

## 4. Analytics — 10 seconds

Open **Traffic analytics**. Flow, monitored-location intensity, observed origin–destination pairs, and corridor travel estimates all come from the same event stream. These are scenario estimates, not citywide density or enforcement-grade speed measurements.

## Recovery

- If a replay is already complete, click **New demo run**, recognize `sample-027`, set `60×`, and Play.
- If a camera was set offline, return to **Cameras** and set it online before assigning an image.
- The interface works offline at `http://127.0.0.1:8000`.
