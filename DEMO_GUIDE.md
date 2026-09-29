# SylRak three-minute demonstration

The opening view is the dimensional Delhi atlas. Scroll to reveal the network, then follow the recorded journey. Search registrations in the top-right corner. Hover over the left edge (or tap the navigation button) for operational workspaces. **Operations** opens the overview tabs and recognition/replay controls. Full recent sightings and priority-alert tables are now in **Activity log**. Solid trajectory lines are explicitly estimated connections, not verified road routes. Use the map +/− controls to zoom; the wheel scrolls the page. Reduced-motion mode and mobile use a shorter, direct flow.

## 1. Query by description — 35 seconds

1. Open **Investigations** and select **Vehicle description**.
2. Click the prepared query: **White · Car · Mid-size · Honda City**.
3. Open registration **DL8CAF2041**.
4. Point out the latest observed location, solid estimated connections, full observation timeline, descriptive metadata, and demonstration watchlist alert.

The make/model and size are explicitly labeled seeded demonstration metadata.

## 2. Real recognition and latest path — 90 seconds

1. Return to **Command**, select **Operations**, and click **Recognize vehicle**.
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
- The core interface works offline at `http://127.0.0.1:8010`.

## Optional additions for judges

**Jev, without spending another request:** Investigations → Distinctive appearance → expand “Describe a vehicle in your own words.” Enter exactly:

> A white Creta with a black roof, a red door panel and a roof rack

Click **Search with Jev**. Its filters are applied automatically and the matching results appear. The cached real response works offline and is labeled “Search complete using saved Jev filters”. The first result is `DL4CAB6672`; open **History (4)**. Explain that Jev classifies written descriptions; the camera matching uses stored evidence and deterministic filters.

**Common cars:** choose **White Dzires**. Five separate plausible candidates remain separate. Select two, compare, and add them to a case. A review reason is required before accepting a case connection. This does not confirm identity or stolen status.

**Covered cars:** choose **Covered vehicles**. Hidden paint/model details remain unknown. The blue covering is a visible attribute, not proof of the underlying body color.

**Quiet alerts:** open Alerts and use **Vehicle alert controls → Mute for 15 minutes**. Select the **Muted** filter to retrieve it; unmute it afterward. Administrator “Stop alerts for everyone” also dismisses current alerts. Evidence continues accumulating.

**Abnormal features:** open **Investigations → Vehicle description** and click **White car · Sticker on rear glass**: only `DL8CAF2041` (Ganesh sticker) and `DL4CAB6672` ("Baby on board" sticker) remain, and the **Logged features** column shows why. Open the **Camera feasibility guide** to explain why stickers and large damage work on traffic cameras while a 1 cm windshield chip needs a close-up. Open `DL8CAF2041`: its sticker, cracked tail light, and suggested windshield chip are listed with the camera where each was seen. Click **Log on selected sighting**, add "Taped-up left headlight", broken part, headlight, 22 cm, then search the feature description "taped" to show it is immediately searchable. Unplated sightings, such as the white Dzire with a cab operator decal, remain findable by feature alone. A shared feature narrows the search; it does not establish identity.

**Independent registration:** open Registration lookup and click **DL10CZ7788**. This synthetic registry entry has never been seen by a camera. Search `DL99ZZ9999` to demonstrate the honest unavailable state.

If asked about accuracy, say: “The demo target is recognized correctly. Our broader exploratory result is 7/31 exact plates, or 22.6%, so 90% is a research target, not a demonstrated result.” No live police database or live registration integration is connected.
