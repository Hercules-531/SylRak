import { chromium } from "playwright";
import { readFile, mkdir, writeFile } from "node:fs/promises";
import assert from "node:assert/strict";
const base =
  process.argv[2] || process.env.SYLRAK_URL || "http://127.0.0.1:5173";
const env = Object.fromEntries(
  (await readFile(".env", "utf8"))
    .split(/\r?\n/)
    .filter((x) => x.includes("="))
    .map((x) => [x.slice(0, x.indexOf("=")), x.slice(x.indexOf("=") + 1)]),
);
await mkdir("artifacts/qa", { recursive: true });
const browser = await chromium.launch({ channel: "chrome", headless: true });
const context = await browser.newContext({
  viewport: { width: 1440, height: 900 },
  deviceScaleFactor: 1,
});
const errors = [],
  external = [],
  checks = [];
await context.route("**/*", (route) => {
  const u = new URL(route.request().url());
  if (
    ["http:", "https:"].includes(u.protocol) &&
    !["localhost", "127.0.0.1"].includes(u.hostname)
  ) {
    external.push(u.href);
    return route.abort();
  }
  return route.continue();
});
const page = await context.newPage();
page.on("pageerror", (e) => errors.push(e.message));
page.on("response", (response) => {
  if (response.status() >= 400)
    errors.push(`${response.status()} ${response.url()}`);
});
page.on("console", (msg) => {
  if (msg.type() === "error") errors.push(msg.text());
});
async function request(path, body) {
  const response = await context.request.post(base + "/api/v1" + path, {
    data: body,
  });
  assert.ok(response.ok(), path + ": " + (await response.text()));
  return response.json();
}
async function get(path) {
  const response = await context.request.get(base + "/api/v1" + path);
  assert.ok(response.ok(), await response.text());
  return response.json();
}
try {
  await request("/auth/login", {
    username: "admin",
    password: env.SYLRAK_ADMIN_PASSWORD,
  });
  await request("/demo", { action: "reset" });
  await page.goto(base);
  await page
    .getByRole("heading", { name: "City command", exact: true })
    .waitFor();
  await page.locator(".camera-pin").first().waitFor();
  await page.waitForTimeout(3500);
  await page.screenshot({
    path: "artifacts/qa/command-1440.png",
    fullPage: true,
  });
  checks.push(
    "Command and local Delhi map loaded with external network blocked",
  );
  await page
    .getByRole("button", { name: "Recognize vehicle", exact: true })
    .click();
  await page
    .getByRole("button", { name: "Run recognition", exact: true })
    .click();
  await page
    .getByRole("heading", { name: "Recognition complete", exact: true })
    .waitFor({ timeout: 90000 });
  await page.screenshot({
    path: "artifacts/qa/recognition.png",
    fullPage: true,
  });
  assert.ok(
    await page
      .locator(".recognition-result-row")
      .filter({ hasText: "KL22L9038" })
      .count(),
  );
  const before = await get("/snapshot");
  assert.ok(before.run.target_observation_id, "Actual target was not accepted");
  const target = await get("/observations/" + before.run.target_observation_id);
  assert.equal(target.raw_plate, "KL22L9038");
  assert.equal(target.source_kind, "real_inference");
  assert.ok(
    target.details.vehicle_box &&
      target.details.plate_box &&
      target.evidence.plate_url,
  );
  await page.getByRole("button", { name: "Close", exact: true }).click();
  await page.getByRole("button", { name: "Start replay", exact: true }).click();
  await page.waitForTimeout(1200);
  await page.getByRole("button", { name: "Pause replay", exact: true }).click();
  await page.getByRole("combobox", { name: "Replay speed" }).selectOption("60");
  await page.getByRole("button", { name: "Start replay", exact: true }).click();
  let snapshot;
  for (let i = 0; i < 50; i++) {
    snapshot = await get("/snapshot");
    if (snapshot.run.status === "completed") break;
    await page.waitForTimeout(1000);
  }
  assert.equal(snapshot.run.status, "completed");
  const vehicle = await get(
    "/vehicles/" + target.vehicle_id + "?run_id=" + target.run_id,
  );
  assert.deepEqual(
    vehicle.observations
      .filter((o) => o.status === "accepted")
      .map((o) => o.camera_id),
    ["C01", "C02", "C03", "C04"],
  );
  assert.equal(
    vehicle.alerts.filter((a) => a.match_method === "exact").length,
    1,
  );
  assert.equal(
    vehicle.alerts.find((a) => a.match_method === "exact").observation
      .camera_id,
    "C04",
  );
  assert.ok(vehicle.observations.some((o) => o.status === "possible"));
  checks.push(
    "Real OCR, one exact alert, pause/resume, four chronological cameras, separate possible match",
  );
  await page.goto(
    base + "/vehicles/" + target.vehicle_id + "?run=" + target.run_id,
  );
  await page
    .getByRole("heading", { name: "Historical trajectory", exact: true })
    .waitFor();
  await page.waitForTimeout(1800);
  await page
    .locator(".timeline-row")
    .filter({ hasText: "ITO junction" })
    .first()
    .click();
  await page.screenshot({
    path: "artifacts/qa/vehicle-history-1440.png",
    fullPage: true,
  });
  for (const width of [1366, 1000]) {
    await page.setViewportSize({ width, height: width === 1366 ? 768 : 900 });
    await page.waitForTimeout(500);
    assert.equal(
      await page.evaluate(
        () => document.documentElement.scrollWidth > innerWidth,
      ),
      false,
      "Page overflow at " + width,
    );
    await page.screenshot({
      path: `artifacts/qa/vehicle-history-${width}.png`,
      fullPage: true,
    });
  }
  await page.setViewportSize({ width: 1440, height: 900 });
  await page.goto(base + "/investigations?q=kl%2022-l9038");
  await page
    .getByRole("heading", { name: "Matching observations", exact: false })
    .waitFor();
  await page.locator("tbody tr").first().waitFor();
  assert.ok((await page.locator("tbody tr").count()) >= 4);
  checks.push(
    "Normalized history search and date/camera filter controls rendered",
  );
  await page.screenshot({ path: "artifacts/qa/search.png", fullPage: true });
  await page.getByRole("tab", { name: "Vehicle description" }).click();
  await page
    .getByRole("button", { name: /White · Car · Mid-size · Honda City/ })
    .click();
  const described = page.locator("tbody tr").filter({ hasText: "DL8CAF2041" });
  await described.first().waitFor();
  assert.ok((await described.count()) >= 4);
  await page.screenshot({
    path: "artifacts/qa/description-search.png",
    fullPage: true,
  });
  await described.first().getByRole("link").first().click();
  await page.getByText("Honda City", { exact: true }).first().waitFor();
  await page.getByText(/mid-size · sedan/i).waitFor();
  assert.ok((await page.locator(".timeline-row").count()) >= 4);
  await page.locator(".camera-pin").first().waitFor();
  await page.waitForTimeout(700);
  checks.push(
    "Description search finds seeded make, color, type and size and opens its full path",
  );
  await page.screenshot({
    path: "artifacts/qa/description-history.png",
    fullPage: true,
  });
  for (const route of ["alerts", "cameras", "traffic", "watchlist"]) {
    await page.goto(base + "/" + route);
    await page.locator(".page-content").waitFor();
    await page.waitForTimeout(1100);
    assert.equal(
      await page.evaluate(
        () => document.documentElement.scrollWidth > innerWidth,
      ),
      false,
    );
    await page.screenshot({
      path: `artifacts/qa/${route}.png`,
      fullPage: true,
    });
  }
  checks.push(
    "Alerts, camera health, traffic aggregates and watchlist views render",
  );
  await request("/demo", { action: "reset" });
  const history = await get(
    "/vehicles/" + target.vehicle_id + "?run_id=" + target.run_id,
  );
  assert.equal(history.sightings, 4);
  assert.ok(history.runs.some((r) => !r.active));
  const search = await get("/observations?plate=KL22L9038");
  assert.ok(search.total >= 4);
  checks.push(
    "Replay reset archives and preserves vehicle history and evidence",
  );
  await page.goto(
    base + "/vehicles/" + target.vehicle_id + "?run=" + target.run_id,
  );
  await page.locator(".timeline-row").first().waitFor();
  await page.waitForTimeout(1000);
  await page.screenshot({
    path: "artifacts/qa/archived-history.png",
    fullPage: true,
  });
  const badErrors = errors.filter((x) => !x.includes("401 (Unauthorized)"));
  assert.equal(badErrors.length, 0, badErrors.join("\n"));
  assert.equal(external.length, 0, "Unexpected external asset requests");
  await writeFile(
    "artifacts/qa/browser-results.json",
    JSON.stringify(
      {
        checks,
        errors: badErrors,
        external_requests: external,
        archived_target: target.vehicle_id,
        archived_run: target.run_id,
      },
      null,
      2,
    ),
  );
  console.log(
    JSON.stringify({ checks, errors: badErrors, external_requests: external }),
  );
} catch (e) {
  await page.screenshot({ path: "artifacts/qa/failure.png", fullPage: true });
  await writeFile(
    "artifacts/qa/browser-errors.json",
    JSON.stringify({ error: String(e), errors, external }, null, 2),
  );
  throw e;
} finally {
  await browser.close();
}
