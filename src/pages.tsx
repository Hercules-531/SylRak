import ReviewScore,{ReviewWarning} from './ReviewScore';
import { useEffect, useState, type FormEvent } from "react";
import {NotificationControls} from './extensions';
import {
  Link,
  useNavigate,
  useParams,
  useSearchParams,
} from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import {
  Search,
  ArrowUpRight,
  ChevronLeft,
  ChevronRight,
  Clock,
  MapPin,
  Camera as CameraIcon,
  ScanLine,
  Upload,
  Check,
  Plus,
  Pencil,
  ShieldAlert,
  Activity,
  Route as RouteIcon,
  ArrowRight,
  History,
  TriangleAlert,
  ImageOff,
  CarFront,
} from "lucide-react";
import {
  api,
  post,
  patch,
  useGet,
  time,
  date,
  pct,
  number,
  type Camera,
  type Observation,
  type Alert,
} from "./api";
import {
  Badge,
  StateBadge,
  SourceBadge,
  Plate,
  Empty,
  Loading,
  ErrorState,
  Modal,
  ObservationTable,
  Frame,
  EvidenceDetails,
  useAction,
  notice,
} from "./ui";
import MapView from "./MapView";
const stamp = (s: string) =>
  s ? new Date(s + ":00+05:30").getTime() / 1000 : undefined;
function QueryState({ query }: { query: any }) {
  return query.isError ? (
    <ErrorState error={query.error} retry={() => query.refetch()} />
  ) : (
    <Loading />
  );
}

export function Investigations({
  cameras,
  onEvidence,
}: {
  cameras: Camera[];
  onEvidence: (o: Observation) => void;
}) {
  const [params, setParams] = useSearchParams();
  const [mode, setMode] = useState<"plate" | "description">(
    params.get("mode") === "description" ? "description" : "plate",
  );
  const [form, setForm] = useState<Record<string, string>>({
    plate: params.get("q") || "",
    camera: params.get("camera") || "",
    vehicle_type: "",
    color: "",
    size_class: "",
    make_model: "",
    body_style: "",
    status: "",
    watchlist_status: "",
    alert_status: "",
    from: "",
    to: "",
    run_id: "current",
  });
  const [offset, setOffset] = useState(0);
  const [applied, setApplied] = useState(form);
  useEffect(() => {
    const value = {
      ...form,
      plate: params.get("q") || "",
      camera: params.get("camera") || "",
    };
    setForm(value);
    setApplied(value);
    setOffset(0);
  }, [params.get("q"), params.get("camera")]);
  const queryParams = new URLSearchParams();
  Object.entries(applied).forEach(([k, v]) => {
    if (v && k !== "from" && k !== "to") queryParams.set(k, v);
  });
  if (applied.from) queryParams.set("from_time", String(stamp(applied.from)));
  if (applied.to) queryParams.set("to_time", String(stamp(applied.to)));
  queryParams.set("offset", String(offset));
  queryParams.set("limit", "25");
  queryParams.set("include_review", "true");
  const result = useGet<any>("/observations?" + queryParams);
  const set = (k: string, v: string) => setForm((f) => ({ ...f, [k]: v }));
  const submit = (e: FormEvent) => {
    e.preventDefault();
    setApplied(form);
    setOffset(0);
  };
  const clear = () => {
    const empty = Object.fromEntries(Object.keys(form).map((k) => [k, ""]));
    empty.run_id = "current";
    setForm(empty);
    setApplied(empty);
    setOffset(0);
    setParams({});
  };
  const chooseMode = (next: "plate" | "description") => {
    clear();
    setMode(next);
  };
  return (
    <div className="page-content">
      <div className="section-intro">
        <div>
          <h2>Find a vehicle. Reconstruct its history.</h2>
          <p>
            Search by registration or descriptive attributes, then open its
            latest or archived path.
          </p>
        </div>
        <Badge>
          <History size={13} />
          Historical records
        </Badge>
      </div>
      <div
        className="search-mode-tabs"
        role="tablist"
        aria-label="Vehicle search method"
      >
        <button
          type="button"
          role="tab"
          aria-selected={mode === "plate"}
          className={mode === "plate" ? "active" : ""}
          onClick={() => chooseMode("plate")}
        >
          <Search size={16} />
          Number plate
        </button>
        <button
          type="button"
          role="tab"
          aria-selected={mode === "description"}
          className={mode === "description" ? "active" : ""}
          onClick={() => chooseMode("description")}
        >
          <CarFront size={16} />
          Vehicle description
        </button>
      </div>
      <div className="investigation-links"><Link to="/appearance" className="secondary">Distinctive appearance & missing plates <ArrowUpRight size={15}/></Link><Link to="/cases" className="text-button">Case workspace</Link></div>
      <form className="search-panel panel" onSubmit={submit}>
        {mode === "plate" ? (
          <div className="search-primary">
            <label className="plate-search">
              <Search size={19} />
              <input
                value={form.plate}
                onChange={(e) => set("plate", e.target.value)}
                placeholder="Enter a plate, e.g. KL22L9038 or DL"
                aria-label="Plate search"
              />
              <kbd>REGISTRATION</kbd>
            </label>
            <button className="primary" type="submit">
              <Search size={16} />
              Show travel history
            </button>
          </div>
        ) : (
          <>
            <div className="description-search">
              <label>
                Vehicle type
                <select
                  aria-label="Vehicle type"
                  value={form.vehicle_type}
                  onChange={(e) => set("vehicle_type", e.target.value)}
                >
                  <option value="">Any type</option>
                  {["car", "motorcycle", "bus", "truck"].map((v) => (
                    <option key={v}>{v}</option>
                  ))}
                </select>
              </label>
              <label>
                Color
                <select
                  aria-label="Vehicle color"
                  value={form.color}
                  onChange={(e) => set("color", e.target.value)}
                >
                  <option value="">Any color</option>
                  {["white", "silver", "black", "blue", "red"].map((v) => (
                    <option key={v}>{v}</option>
                  ))}
                </select>
              </label>
              <label>
                Size
                <select
                  aria-label="Vehicle size"
                  value={form.size_class}
                  onChange={(e) => set("size_class", e.target.value)}
                >
                  <option value="">Any size</option>
                  {["compact", "mid-size", "large", "two-wheeler"].map((v) => (
                    <option key={v}>{v}</option>
                  ))}
                </select>
              </label>
              <label>
                Make / model
                <input
                  aria-label="Make or model"
                  value={form.make_model}
                  onChange={(e) => set("make_model", e.target.value)}
                  placeholder="e.g. Honda City"
                />
              </label>
              <button className="primary" type="submit">
                <Search size={16} />
                Find vehicles
              </button>
            </div>
            <div className="demo-query">
              <span>DEMO QUERY</span>
              <button
                type="button"
                onClick={() => {
                  const value = {
                    ...form,
                    plate: "",
                    vehicle_type: "car",
                    color: "white",
                    size_class: "mid-size",
                    make_model: "Honda City",
                    run_id: "current",
                  };
                  setForm(value);
                  setApplied(value);
                  setOffset(0);
                }}
              >
                White · Car · Mid-size · Honda City
                <ArrowUpRight size={14} />
              </button>
              <small>
                Attributes are labeled synthetic metadata for this prototype.
              </small>
            </div>
          </>
        )}
        <details className="advanced-filters">
          <summary>More filters</summary>
          <div className="filter-grid">
            <label>
              Camera
              <select
                value={form.camera}
                onChange={(e) => set("camera", e.target.value)}
              >
                <option value="">All cameras</option>
                {cameras.map((c) => (
                  <option key={c.id} value={c.id}>
                    {c.id} · {c.name}
                  </option>
                ))}
              </select>
            </label>
            <label>
              From · IST
              <input
                type="datetime-local"
                value={form.from}
                onChange={(e) => set("from", e.target.value)}
              />
            </label>
            <label>
              Until · IST
              <input
                type="datetime-local"
                value={form.to}
                onChange={(e) => set("to", e.target.value)}
              />
            </label>
            <label>
              Body style
              <select
                value={form.body_style}
                onChange={(e) => set("body_style", e.target.value)}
              >
                <option value="">Any body style</option>
                {[
                  "sedan",
                  "hatchback",
                  "SUV",
                  "motorcycle",
                  "city bus",
                  "goods carrier",
                ].map((v) => (
                  <option key={v}>{v}</option>
                ))}
              </select>
            </label>
            <label>
              Association
              <select
                value={form.status}
                onChange={(e) => set("status", e.target.value)}
              >
                <option value="">All associations</option>
                <option value="accepted">Accepted</option>
                <option value="possible">Needs review</option>
                <option value="conflict">Conflicting evidence</option>
                <option value="unresolved">Unresolved</option>
              </select>
            </label>
            <label>
              Watchlist
              <select
                value={form.watchlist_status}
                onChange={(e) => set("watchlist_status", e.target.value)}
              >
                <option value="">Any status</option>
                {[
                  "any",
                  "stolen",
                  "wanted",
                  "flagged",
                  "blacklisted",
                  "suspended",
                ].map((v) => (
                  <option key={v}>{v}</option>
                ))}
              </select>
            </label>
            <label>
              Alert state
              <select
                value={form.alert_status}
                onChange={(e) => set("alert_status", e.target.value)}
              >
                <option value="">Any state</option>
                {["open", "acknowledged", "dismissed"].map((v) => (
                  <option key={v}>{v}</option>
                ))}
              </select>
            </label>
            <label>
              Record scope
              <select
                value={form.run_id}
                onChange={(e) => set("run_id", e.target.value)}
              >
                <option value="">All stored runs</option>
                <option value="current">Current run</option>
              </select>
            </label>
          </div>
        </details>
        <button
          type="button"
          className="text-button reset-filters"
          onClick={clear}
        >
          Clear search
        </button>
      </form>
      <section className="panel">
        <div className="panel-heading">
          <h2>
            Matching observations{" "}
            <span className="panel-counter">{number(result.data?.total)}</span>
          </h2>
          <span className="muted">
            Select a registration to open its complete journey
          </span>
        </div>
        {result.data ? (
          <><ReviewWarning/><ObservationTable items={result.data.items} onEvidence={onEvidence} showReview /></>
        ) : (
          <QueryState query={result} />
        )}
        <div className="pagination">
          <span>
            {result.data?.total
              ? `${offset + 1}–${Math.min(offset + 25, result.data.total)} of ${number(result.data.total)}`
              : "0 observations"}
          </span>
          <div>
            <button
              className="secondary"
              disabled={!offset}
              onClick={() => setOffset(Math.max(0, offset - 25))}
            >
              <ChevronLeft size={15} />
              Previous
            </button>
            <button
              className="secondary"
              disabled={!result.data || offset + 25 >= result.data.total}
              onClick={() => setOffset(offset + 25)}
            >
              Next
              <ChevronRight size={15} />
            </button>
          </div>
        </div>
      </section>
    </div>
  );
}

export function VehiclePage({
  cameras,
  onEvidence,
}: {
  cameras: Camera[];
  onEvidence: (o: Observation) => void;
}) {
  const { id } = useParams();
  const [params, setParams] = useSearchParams();
  const run = params.get("run") || "current";
  const [selected, setSelected] = useState<string>(),
    [from, setFrom] = useState(""),
    [to, setTo] = useState("");
  const suffix = new URLSearchParams({ run_id: run });
  if (from) suffix.set("from_time", String(stamp(from)));
  if (to) suffix.set("to_time", String(stamp(to)));
  const q = useGet<any>(`/vehicles/${id}?${suffix}`);
  const data = q.data;
  const obs: Observation[] = data?.observations || [];
  const accepted = obs.filter((o) => o.status === "accepted");
  const current =
    obs.find((o) => o.id === selected) ||
    [...accepted].reverse().find((o) => o.evidence) ||
    accepted.at(-1) ||
    obs.at(-1);
  const latest = accepted.at(-1);
  const alert: Alert | undefined = data?.alerts.find(
    (a: Alert) => a.status !== "dismissed",
  );
  useEffect(() => setSelected(undefined), [id, run]);
  if (!data) return <QueryState query={q} />;
  return (
    <div className="page-content vehicle-page">
      <div className="vehicle-heading">
        <div>
          <Link to="/investigations" className="back-link">
            <ChevronLeft size={14} />
            Vehicle search
          </Link>
          <div className="vehicle-title">
            <Plate value={data.plate} />
            {alert ? (
              <Badge tone={alert.match_method === "exact" ? "red" : "amber"}>
                {alert.match_method === "possible"
                  ? "Possible watchlist match"
                  : alert.category.toUpperCase() + " · DEMO"}
              </Badge>
            ) : (
              <Badge tone="green">No active alert</Badge>
            )}
          </div>
        </div>
        <NotificationControls subject={'plate:'+data.plate}/>
        <label className="run-select">
          Recorded journey
          <select
            value={run === "current" ? data.selected_run_id : run}
            onChange={(e) => setParams({ run: e.target.value })}
          >
            {data.runs.map((r: any, i: number) => (
              <option value={r.id} key={r.id}>
                {r.active ? "Current run" : "Archived run"} ·{" "}
                {date(r.created_at)} {time(r.created_at, true)}
              </option>
            ))}
          </select>
        </label>
      </div>
      <div className="vehicle-review"><ReviewWarning/><ReviewScore value={data.theft_review}/></div>
      <div className="vehicle-stats">
        <div>
          <span>First recorded</span>
          <strong className="mono">
            {time(accepted[0]?.observed_at, true)}
          </strong>
          <small>{date(accepted[0]?.observed_at)}</small>
        </div>
        <div>
          <span>Last recorded</span>
          <strong className="mono">{time(latest?.observed_at, true)}</strong>
          <small>{latest?.camera.name || "No accepted sighting"}</small>
        </div>
        <div>
          <span>Accepted sightings</span>
          <strong>{accepted.length.toString().padStart(2, "0")}</strong>
          <small>
            {new Set(accepted.map((o) => o.camera_id)).size} cameras encountered
          </small>
        </div>
        <div>
          <span>Possible associations</span>
          <strong className={obs.length > accepted.length ? "amber-text" : ""}>
            {obs.length - accepted.length}
          </strong>
          <small>Excluded from accepted path</small>
        </div>
      </div>
      <div className="attribute-strip">
        <div><span>Vehicle type</span><strong>{data.attributes?.vehicle_type || "unknown"}</strong></div>
        <div><span>Color</span><strong>{data.attributes?.color || "unknown"}</strong></div>
        <div><span>Make / model</span><strong>{data.attributes?.make_model || "unknown"}</strong></div>
        <div><span>Size / body</span><strong>{data.attributes?.size_class || "unknown"} · {data.attributes?.body_style || "unknown"}</strong></div>
        <small>Model and size are seeded demonstration metadata unless the evidence says otherwise.</small>
      </div>
      {alert && (
        <div
          className={
            "case-alert " +
            (alert.match_method === "possible" ? "amber-case" : "")
          }
        >
          <ShieldAlert size={19} />
          <div>
            <strong>
              {alert.match_method === "exact"
                ? "Watchlist match"
                : "Possible match requiring review"}
            </strong>
            <p>{alert.reason}</p>
          </div>
          <Link to="/alerts" className="text-button">
            Open alert queue
            <ArrowUpRight size={15} />
          </Link>
        </div>
      )}
      <div className="history-controls">
        <span>
          <History size={16} />
          Recorded movement history
        </span>
        <label>
          From · IST
          <input
            type="datetime-local"
            value={from}
            onChange={(e) => setFrom(e.target.value)}
          />
        </label>
        <label>
          Until · IST
          <input
            type="datetime-local"
            value={to}
            onChange={(e) => setTo(e.target.value)}
          />
        </label>
        <button
          className="text-button"
          onClick={() => {
            setFrom("");
            setTo("");
          }}
        >
          All times
        </button>
      </div>
      <div className="vehicle-grid">
        <aside className="panel vehicle-evidence">
          <div className="panel-heading">
            <h2>Selected observation</h2>
            {current && <SourceBadge source={current.source_kind} />}
          </div>
          {current ? (
            <>
              <Frame observation={current} />
              <div className="selected-observation-body">
                <div className="selected-camera">
                  <span className="camera-code mono">{current.camera_id}</span>
                  <strong>{current.camera.name}</strong>
                </div>
                <div className="selected-time mono">
                  {time(current.observed_at, true)} IST
                </div>
                {current.evidence?.plate_url && (
                  <img
                    className="plate-crop"
                    src={current.evidence.plate_url}
                    alt="Captured plate crop"
                  />
                )}
                <dl className="facts">
                  <dt>Plate OCR</dt>
                  <dd className="mono">{current.raw_plate || "Unreadable"}</dd>
                  <dt>OCR score</dt>
                  <dd>{pct(current.ocr_confidence)}</dd>
                  <dt>Type / color</dt>
                  <dd>
                    {current.vehicle_type} / {current.color}
                  </dd>
                  <dt>Make / model</dt>
                  <dd>{current.details?.make_model || "unknown"}</dd>
                  <dt>Size / body</dt>
                  <dd>{current.details?.size_class || "unknown"} / {current.details?.body_style || "unknown"}</dd>
                  <dt>Direction</dt>
                  <dd>{current.camera.direction}</dd>
                  <dt>Association</dt>
                  <dd>
                    <StateBadge status={current.status} />
                  </dd>
                </dl>
                <button
                  className="secondary full-width"
                  onClick={() => onEvidence(current)}
                >
                  Inspect full evidence
                  <ArrowUpRight size={16} />
                </button>
                <p className="small-note">
                  Locations are camera sightings in the scenario. Replayed
                  observations reuse the source photograph.
                </p>
              </div>
            </>
          ) : (
            <Empty title="No sightings in this range" />
          )}
        </aside>
        <section className="panel history-panel">
          <div className="panel-heading">
            <h2>Historical trajectory</h2>
            <span className="muted">
              {accepted.length} accepted observations
            </span>
          </div>
          <MapView
            cameras={cameras}
            observations={accepted}
            selectedCamera={current?.camera_id}
            onCamera={(cam) => {
              const o = [...obs].reverse().find((o) => o.camera_id === cam);
              if (o) setSelected(o.id);
            }}
            compact
          />
          <div className="trajectory-caption">
            <RouteIcon size={16} />
            <span>
              Dashed lines connect recorded cameras. The route between sightings
              is estimated.
            </span>
          </div>
          <div className="timeline-heading">
            <h3>Observation timeline</h3>
            <span>CHRONOLOGICAL · IST</span>
          </div>
          <div className="timeline">
            {obs.map((o, i) => (
              <button
                key={o.id}
                className={
                  "timeline-row " +
                  (current?.id === o.id ? "selected" : "") +
                  " " +
                  o.status
                }
                onClick={() => setSelected(o.id)}
              >
                <span className="timeline-index">
                  {String(i + 1).padStart(2, "0")}
                </span>
                <div className="timeline-point">
                  <i />
                </div>
                <div className="timeline-place">
                  <strong>{o.camera.name}</strong>
                  <span>
                    {o.camera_id} · {o.camera.direction}{" "}
                    <SourceBadge source={o.source_kind} />
                  </span>
                </div>
                <div className="timeline-meta">
                  <strong className="mono">{time(o.observed_at, true)}</strong>
                  <span>
                    {pct(o.ocr_confidence)} OCR{" "}
                    {o.status !== "accepted" ? "· Review" : ""}
                  </span>
                </div>
                <ChevronRight size={15} />
              </button>
            ))}
            {!obs.length && (
              <Empty title="No recorded movement in this range" />
            )}
          </div>
        </section>
      </div>
    </div>
  );
}

export function AlertsPage({
  onEvidence,
  onAlert,
}: {
  onEvidence: (o: Observation) => void;
  onAlert: (a: Alert) => void;
}) {
  const [filter, setFilter] = useState("");
  const q = useGet<Alert[]>("/alerts" + (filter ? "?status=" + filter : ""));
  const action = useAction();
  return (
    <div className="page-content">
      <div className="section-intro">
        <div>
          <h2>Alerts and verification</h2>
          <p>Review the record and plate evidence before taking action.</p>
        </div>
        <select
          aria-label="Alert state filter"
          value={filter}
          onChange={(e) => setFilter(e.target.value)}
        >
          <option value="">Active alerts</option>
          {["open", "acknowledged", "dismissed", "muted"].map((s) => (
            <option key={s}>{s}</option>
          ))}
        </select>
      </div>
      {!q.data ? (
        <QueryState query={q} />
      ) : !q.data.length ? (
        <Empty title="No alerts in this selection" />
      ) : (
        <div className="alert-list">
          {q.data.map((a) => (
            <article
              className={"panel alert-detail-card " + a.priority}
              key={a.id}
            >
              <div className="alert-detail-top">
                <Badge tone={a.priority === "critical" ? "red" : "amber"}>
                  {a.priority.toUpperCase()}
                </Badge>
                <span className="eyebrow">
                  {a.match_method === "exact"
                    ? a.category + " · DEMO"
                    : a.match_method === "possible"
                      ? "POSSIBLE WATCHLIST MATCH"
                      : a.match_method === 'appearance' ? 'APPEARANCE LEAD · REVIEW REQUIRED' : "ROUTE REVIEW"}
                </span>
                <span className="alert-status">{a.notification?.muted ? 'Muted · ' : ''}{a.status} · {a.sighting_count || 1} sightings</span>
                <span className="mono muted">
                  {time(a.updated_at, true)} IST
                </span>
              </div>
              <div className="alert-detail-content">
                <div className="alert-evidence-thumb">
                  {a.observation.evidence?.vehicle_url ? (
                    <img
                      src={a.observation.evidence.vehicle_url}
                      alt="Vehicle evidence"
                    />
                  ) : (
                    <ImageOff size={25} />
                  )}
                </div>
                <div className="alert-description">
                  <Plate
                    value={a.watchlist?.plate || a.observation.plate}
                    small
                  />
                  <p>{a.reason}</p>
                  <div className="alert-evidence-line">
                    <CameraIcon size={14} />
                    {a.observation.camera_id} · {a.observation.camera.name}
                    <span>OCR {pct(a.observation.ocr_confidence)}</span>
                    <SourceBadge source={a.observation.source_kind} />
                  </div>
                </div>
                <div className="alert-actions">
                  <button className="primary" onClick={() => onAlert(a)}>
                    Open investigation
                    <ArrowUpRight size={15} />
                  </button>
                  <button
                    className="secondary"
                    onClick={() => onEvidence(a.observation)}
                  >
                    Inspect plate evidence
                  </button>
                </div>
              </div>
              <NotificationControls subject={a.subject || ('observation:'+a.observation.id)}/>
              <div className="alert-detail-footer">
                <span>
                  Observed{" "}
                  <span className="mono">{a.observation.raw_plate || "—"}</span>{" "}
                  ·{" "}
                  {a.match_method === "exact"
                    ? "Exact normalized plate match"
                    : "Human verification required"}
                </span>
                <div>
                  <button
                    className="text-button"
                    disabled={a.status === "acknowledged"}
                    onClick={() =>
                      action(
                        () =>
                          patch("/alerts/" + a.id, { status: "acknowledged" }),
                        "Alert acknowledged",
                      )
                    }
                  >
                    <Check size={15} />
                    Acknowledge
                  </button>
                  <button
                    className="text-button muted"
                    onClick={() =>
                      action(
                        () =>
                          patch("/alerts/" + a.id, {
                            status:
                              a.status === "dismissed" ? "open" : "dismissed",
                          }),
                        "Alert updated",
                      )
                    }
                  >
                    {a.status === "dismissed" ? "Reopen" : "Dismiss"}
                  </button>
                </div>
              </div>
            </article>
          ))}
        </div>
      )}
    </div>
  );
}

export function CamerasPage({
  cameras,
  user,
  onEvidence,
  onRecognize,
}: {
  cameras: Camera[];
  user: any;
  onEvidence: (o: Observation) => void;
  onRecognize: () => void;
}) {
  const [selected, setSelected] = useState("C01");
  const q = useGet<any>("/cameras/" + selected);
  const action = useAction();
  return (
    <div className="page-content">
      <div className="section-intro">
        <div>
          <h2>Camera network</h2>
          <p>
            12 simulated locations on Delhi roads. Health controls affect this
            demonstration only.
          </p>
        </div>
        <Badge>
          {cameras.filter((c) => c.status !== "offline").length} reporting nodes
        </Badge>
      </div>
      <div className="camera-page-grid">
        <section className="panel camera-list">
          {cameras.map((c) => (
            <button
              key={c.id}
              className={
                "camera-list-row " + (selected === c.id ? "selected" : "")
              }
              onClick={() => setSelected(c.id)}
            >
              <CameraIcon size={17} />
              <div>
                <strong>{c.name}</strong>
                <small className="mono">
                  {c.id} · {c.direction}
                </small>
              </div>
              <i className={"dot " + c.status} />
            </button>
          ))}
        </section>
        <section className="panel">
          <MapView
            cameras={cameras}
            selectedCamera={selected}
            onCamera={setSelected}
            compact
          />
          {q.data && (
            <div className="camera-info">
              <div>
                <h2>{q.data.name}</h2>
                <p>{q.data.road}</p>
                <span className="mono muted">
                  {q.data.lat.toFixed(4)}, {q.data.lon.toFixed(4)}
                </span>
              </div>
              <div>
                <StateBadge status={q.data.status} />
                <p>Last heartbeat {time(q.data.heartbeat, true)} IST</p>
                {user.role === "admin" && (
                  <select
                    aria-label="Camera health simulation"
                    value={q.data.status}
                    onChange={(e) =>
                      action(
                        () =>
                          patch("/cameras/" + selected, {
                            status: e.target.value,
                          }),
                        "Simulated camera health updated",
                      )
                    }
                  >
                    {["online", "degraded", "offline"].map((v) => (
                      <option key={v}>{v}</option>
                    ))}
                  </select>
                )}
              </div>
              <button className="primary" onClick={onRecognize}>
                <ScanLine size={16} />
                Process an image
              </button>
            </div>
          )}
        </section>
      </div>
      <section className="panel">
        <div className="panel-heading">
          <h2>Recent observations · {selected}</h2>
          <Link
            className="text-button"
            to={"/investigations?camera=" + selected}
          >
            Search camera history
            <ArrowUpRight size={15} />
          </Link>
        </div>
        {q.data ? (
          <ObservationTable
            items={q.data.observations}
            onEvidence={onEvidence}
          />
        ) : (
          <QueryState query={q} />
        )}
      </section>
    </div>
  );
}

export function TrafficPage({ clock }: { clock: number }) {
  const [window, setWindow] = useState(120);
  const end = Math.floor(clock / 30) * 30;
  const q = useGet<any>(
    `/traffic?from_time=${end - window * 60}&to_time=${end}`,
  );
  const [selected, setSelected] = useState<string>();
  const data = q.data;
  if (!data) return <QueryState query={q} />;
  const names = Object.fromEntries(
    data.camera_flow.map((c: Camera) => [c.id, c.name]),
  );
  const max = Math.max(1, ...data.buckets.map((b: any) => b.count));
  return (
    <div className="page-content">
      <div className="section-intro">
        <div>
          <h2>Observed traffic movement</h2>
          <p>
            Aggregates from stored observations. Camera coverage and sample
            counts qualify every estimate.
          </p>
        </div>
        <select
          aria-label="Traffic time window"
          value={window}
          onChange={(e) => setWindow(Number(e.target.value))}
        >
          <option value={30}>Last 30 scenario minutes</option>
          <option value={60}>Last 60 scenario minutes</option>
          <option value={120}>Last 2 scenario hours</option>
        </select>
      </div>
      <div className="analytics-metrics">
        <div>
          <span>Observed passages</span>
          <strong>{number(data.passages)}</strong>
        </div>
        <div>
          <span>Identified registrations</span>
          <strong>{number(data.identified_vehicles)}</strong>
        </div>
        <div>
          <span>Unreadable plates</span>
          <strong>{data.unreadable}</strong>
        </div>
        <div>
          <span>Camera coverage</span>
          <strong>
            {data.coverage.online} / {data.coverage.total}
          </strong>
        </div>
      </div>
      <div className="traffic-map-grid">
        <section className="panel">
          <div className="panel-heading">
            <h2>Observation intensity</h2>
            <span className="heat-legend">
              Lower <i /> Higher
            </span>
          </div>
          <MapView
            cameras={data.camera_flow}
            selectedCamera={selected}
            onCamera={setSelected}
            heat
            compact
          />
          <div className="chart-note">
            {selected
              ? `${names[selected]}: ${data.camera_flow.find((c: Camera) => c.id === selected)?.passages} observed passages. `
              : ""}
            Intensity at monitored points; not physical road density.
          </div>
        </section>
        <section className="panel od-panel">
          <div className="panel-heading">
            <h2>Observed O–D pairs</h2>
          </div>
          <div className="od-list">
            {data.od.length ? (
              data.od.slice(0, 7).map((p: any) => (
                <div className="od-row" key={p.from + p.to}>
                  <div>
                    <span>{names[p.from]}</span>
                    <ArrowRight size={13} />
                    <span>{names[p.to]}</span>
                  </div>
                  <b>
                    {p.count}
                    <small>journeys</small>
                  </b>
                </div>
              ))
            ) : (
              <Empty title="Not enough linked sightings" />
            )}
          </div>
          <div className="chart-note">
            First and last observed cameras. A gap over 30 minutes starts a new
            journey.
          </div>
        </section>
      </div>
      <section className="panel">
        <div className="panel-heading">
          <h2>Flow over time</h2>
          <span className="muted">Passages per 5 minutes · IST</span>
        </div>
        <div
          className="bar-chart"
          aria-label="Five-minute vehicle flow histogram"
        >
          {data.buckets.map((b: any, i: number) => (
            <div
              className="bar-column"
              key={b.time}
              title={`${time(b.time)} · ${b.count} passages`}
            >
              <div className="bar-track">
                <i
                  style={{ height: Math.max(1, (b.count / max) * 100) + "%" }}
                />
                <span>{b.count}</span>
              </div>
              <small>
                {i % Math.max(1, Math.floor(data.buckets.length / 8)) === 0
                  ? time(b.time)
                  : ""}
              </small>
            </div>
          ))}
        </div>
      </section>
      <section className="panel">
        <div className="panel-heading">
          <h2>Corridor travel estimates</h2>
          <span className="muted">Configured distance ÷ elapsed time</span>
        </div>
        <div className="table-scroll">
          <table className="data-table">
            <thead>
              <tr>
                <th>Observed corridor</th>
                <th>Journeys</th>
                <th>Median travel</th>
                <th>Estimated speed</th>
                <th>Indicator</th>
              </tr>
            </thead>
            <tbody>
              {data.corridors.map((c: any) => (
                <tr key={c.from + c.to}>
                  <td>
                    {names[c.from]} <span className="muted">→</span>{" "}
                    {names[c.to]}
                  </td>
                  <td>{c.samples}</td>
                  <td>
                    {c.median_seconds
                      ? Math.round(c.median_seconds / 60) + " min"
                      : "Insufficient data"}
                  </td>
                  <td>{c.estimated_kmh ? c.estimated_kmh + " km/h" : "—"}</td>
                  <td>
                    <Badge tone={c.congestion ? "amber" : "neutral"}>
                      {c.congestion
                        ? "Possible congestion"
                        : c.samples < 3
                          ? "Low sample count"
                          : "Within baseline"}
                    </Badge>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <div className="chart-note">
          Possible congestion: median travel time exceeds 1.5× the configured
          baseline, with at least 3 journeys. Speed is an estimate, not a
          speeding measurement. Offline cameras represent unknown coverage.
        </div>
      </section>
    </div>
  );
}

const initialWatch = {
  plate: "",
  category: "stolen",
  priority: "critical",
  reason: "",
  reference: "",
  active: true,
  valid_from: null as number | null,
  valid_until: null as number | null,
};
export function WatchlistPage({ user }: { user: any }) {
  const q = useGet<any[]>("/watchlist");
  const [editing, setEditing] = useState<any>(null);
  const [form, setForm] = useState({ ...initialWatch });
  const [busy, setBusy] = useState(false);
  const action = useAction();
  const open = (entry?: any) => {
    setEditing(entry || { id: null });
    setForm(entry ? { ...entry } : { ...initialWatch });
  };
  const save = async (e: FormEvent) => {
    e.preventDefault();
    setBusy(true);
    const result = await action(
      () =>
        api("/watchlist" + (editing.id ? "/" + editing.id : ""), {
          method: editing.id ? "PUT" : "POST",
          body: JSON.stringify(form),
        }),
      "Watchlist record saved",
    );
    setBusy(false);
    if (result) setEditing(null);
  };
  return (
    <div className="page-content">
      <div className="section-intro">
        <div>
          <h2>Demonstration watchlist</h2>
          <p>
            Training records only. These entries do not claim any vehicle has
            real-world stolen or wanted status.
          </p>
        </div>
        {user.role === "admin" && (
          <button className="primary" onClick={() => open()}>
            <Plus size={17} />
            Add registration
          </button>
        )}
      </div>
      <section className="panel">
        {q.data ? (
          <div className="table-scroll">
            <table className="data-table">
              <thead>
                <tr>
                  <th>Registration</th>
                  <th>Category</th>
                  <th>Reference</th>
                  <th>Reason</th>
                  <th>Status</th>
                  <th />
                </tr>
              </thead>
              <tbody>
                {q.data.map((w) => (
                  <tr key={w.id}>
                    <td>
                      <Plate value={w.plate} small />
                    </td>
                    <td>
                      <Badge tone={w.category === "stolen" ? "red" : "amber"}>
                        {w.category}
                      </Badge>
                    </td>
                    <td className="mono">{w.reference}</td>
                    <td className="wrap-cell">{w.reason}</td>
                    <td>
                      <Badge tone={w.active ? "green" : "neutral"}>
                        {w.active ? "Active" : "Inactive"}
                      </Badge>
                    </td>
                    <td>
                      {user.role === "admin" && (
                        <button
                          className="icon-btn"
                          title="Edit watchlist entry"
                          aria-label={"Edit " + w.plate}
                          onClick={() => open(w)}
                        >
                          <Pencil size={16} />
                        </button>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <QueryState query={q} />
        )}
      </section>
      <div className="info-box">
        <ShieldAlert size={19} />
        <div>
          <strong>Confidence-aware matching</strong>
          <p>
            Exact accepted registrations create watchlist alerts. Uncertain
            reads are presented for human verification. Acknowledgement and
            investigation access are recorded in the local audit log.
          </p>
        </div>
      </div>
      <Modal
        open={!!editing}
        onClose={() => setEditing(null)}
        title={
          editing?.id ? "Edit demonstration record" : "Add demonstration record"
        }
      >
        <form className="watch-form" onSubmit={save}>
          <label>
            Registration
            <input
              value={form.plate}
              onChange={(e) =>
                setForm({ ...form, plate: e.target.value.toUpperCase() })
              }
              placeholder="DL01AB1234"
              required
              minLength={4}
              maxLength={20}
            />
          </label>
          <div className="form-columns">
            <label>
              Category
              <select
                value={form.category}
                onChange={(e) => setForm({ ...form, category: e.target.value })}
              >
                {[
                  "stolen",
                  "wanted",
                  "flagged",
                  "blacklisted",
                  "suspended",
                ].map((v) => (
                  <option key={v}>{v}</option>
                ))}
              </select>
            </label>
            <label>
              Priority
              <select
                value={form.priority}
                onChange={(e) => setForm({ ...form, priority: e.target.value })}
              >
                {["critical", "high", "medium"].map((v) => (
                  <option key={v}>{v}</option>
                ))}
              </select>
            </label>
          </div>
          <label>
            Record reference
            <input
              value={form.reference}
              onChange={(e) => setForm({ ...form, reference: e.target.value })}
              required
              minLength={3}
              placeholder="DEMO-ST-004"
            />
          </label>
          <label>
            Reason
            <textarea
              value={form.reason}
              onChange={(e) => setForm({ ...form, reason: e.target.value })}
              required
              minLength={3}
              placeholder="Explain why the demonstration record is flagged"
            />
          </label>
          <div className="form-columns">
            <label>
              Valid from · IST
              <input
                type="datetime-local"
                onChange={(e) =>
                  setForm({
                    ...form,
                    valid_from: stamp(e.target.value) || null,
                  })
                }
              />
            </label>
            <label>
              Valid until · IST
              <input
                type="datetime-local"
                onChange={(e) =>
                  setForm({
                    ...form,
                    valid_until: stamp(e.target.value) || null,
                  })
                }
              />
            </label>
          </div>
          <label className="checkbox-label">
            <input
              type="checkbox"
              checked={form.active}
              onChange={(e) => setForm({ ...form, active: e.target.checked })}
            />
            Active record
          </label>
          <div className="button-row">
            <button
              className="secondary"
              type="button"
              onClick={() => setEditing(null)}
            >
              Cancel
            </button>
            <button className="primary" disabled={busy} type="submit">
              Save record
            </button>
          </div>
        </form>
      </Modal>
    </div>
  );
}

export function RecognitionPanel({
  cameras,
  onEvidence,
  onClose,
}: {
  cameras: Camera[];
  onEvidence: (o: Observation) => void;
  onClose: () => void;
}) {
  const samples = useGet<any>("/samples");
  const [sample, setSample] = useState(""),
    [camera, setCamera] = useState("C01"),
    [file, setFile] = useState<File | null>(null),
    [preview, setPreview] = useState(""),
    [jobId, setJobId] = useState<string | null>(null),
    [busy, setBusy] = useState(false);
  const action = useAction();
  useEffect(() => {
    if (samples.data && !sample)
      setSample(
        samples.data.target_sample_id || samples.data.items[0]?.id || "",
      );
  }, [samples.data]);
  useEffect(() => {
    if (!file) {
      setPreview("");
      return;
    }
    const url = URL.createObjectURL(file);
    setPreview(url);
    return () => URL.revokeObjectURL(url);
  }, [file]);
  const job = useQuery<any>({
    queryKey: ["/inference/jobs/" + jobId],
    queryFn: () => api("/inference/jobs/" + jobId),
    enabled: !!jobId,
    refetchInterval: (q) =>
      q.state.data && ["completed", "failed"].includes(q.state.data.status)
        ? false
        : 800,
  });
  const submit = async () => {
    setBusy(true);
    const form = new FormData();
    form.set("camera_id", camera);
    if (file) form.set("file", file);
    else form.set("sample_id", sample);
    const response = await action(() =>
      api("/inference/jobs", { method: "POST", body: form }),
    );
    if (response) setJobId(response.id);
    setBusy(false);
  };
  const pending = busy || ["queued", "running"].includes(job.data?.status);
  const selectedSample = samples.data?.items.find((s: any) => s.id === sample);
  return (
    <div className="recognition-panel">
      <div className="recognition-layout">
        <div className="sample-preview">
          {file || sample ? (
            <img
              src={preview || `/api/v1/samples/${sample}/image`}
              alt="Input image for vehicle recognition"
            />
          ) : (
            <ImageOff size={28} />
          )}
          <span>ORIGINAL SAMPLE</span>
        </div>
        <div className="recognition-form">
          <div className="eyebrow">LOCAL VISION PIPELINE</div>
          <h3>Read a plate from an image</h3>
          <p>
            Vehicle detection → plate localization → OCR. Recognition uses the
            image pixels.
          </p>
          <label>
            Bundled sample
            <select
              value={sample}
              disabled={pending}
              onChange={(e) => {
                setSample(e.target.value);
                setFile(null);
                setJobId(null);
              }}
            >
              {samples.data?.items.map((s: any) => (
                <option key={s.id} value={s.id}>
                  {s.id === samples.data.target_sample_id
                    ? "Target vehicle · "
                    : ""}
                  {s.id}
                </option>
              ))}
            </select>
          </label>
          <label>
            Simulated camera assignment
            <select
              value={camera}
              disabled={pending}
              onChange={(e) => setCamera(e.target.value)}
            >
              {cameras.map((c) => (
                <option key={c.id} value={c.id}>
                  {c.id} · {c.name}
                </option>
              ))}
            </select>
          </label>
          <label className="upload-control">
            <Upload size={17} />
            <span>{file ? file.name : "Or select your own JPEG / PNG"}</span>
            <input
              type="file"
              accept="image/jpeg,image/png"
              disabled={pending}
              onChange={(e) => {
                const f = e.target.files?.[0];
                if (f && f.size > 10 * 1024 * 1024) {
                  notice("Select an image smaller than 10 MB.", true);
                  return;
                }
                setFile(f || null);
                setJobId(null);
              }}
            />
          </label>
          <small className="muted">
            Maximum 10 MB. Locations and times remain simulated.
          </small>
          <button
            className="primary full-width"
            disabled={pending || (!sample && !file)}
            onClick={submit}
          >
            {pending ? <span className="spinner" /> : <ScanLine size={17} />}{" "}
            {pending ? "Running recognition…" : "Run recognition"}
          </button>
        </div>
      </div>
      {jobId && (
        <div
          className={
            "recognition-result " +
            (job.data?.status === "failed" ? "failed" : "")
          }
        >
          <div className="panel-heading">
            <h3>
              {job.data?.status === "completed"
                ? "Recognition complete"
                : job.data?.status === "failed"
                  ? "Recognition failed"
                  : "Processing image locally"}
            </h3>
            {job.data?.result && (
              <span className="mono">
                {job.data.result.duration_seconds}s ·{" "}
                {job.data.result.detections} observations
              </span>
            )}
          </div>
          {job.data?.error ? (
            <p className="form-error">{job.data.error}</p>
          ) : job.data?.result ? (
            <div className="result-observations">
              {job.data.result.observation_ids.map((id: string) => (
                <RecognitionResult
                  key={id}
                  id={id}
                  onEvidence={onEvidence}
                  onClose={onClose}
                />
              ))}
            </div>
          ) : (
            <p className="muted">
              The model worker is processing the image. Results appear here when
              complete.
            </p>
          )}
        </div>
      )}
      <div className="provenance">
        {file ? (
          "User supplied image."
        ) : (
          <>
            Sample source:{" "}
            <a
              href={
                selectedSample?.source_url ||
                "https://www.kaggle.com/datasets/tkm22092/indian-number-plate-images"
              }
              target="_blank"
              rel="noreferrer"
            >
              Indian Number Plate Images
            </a>{" "}
            · Publisher-declared CC0.
          </>
        )}{" "}
        Scores are model outputs and may be wrong; inspect the crop.
      </div>
    </div>
  );
}
function RecognitionResult({
  id,
  onEvidence,
  onClose,
}: {
  id: string;
  onEvidence: (o: Observation) => void;
  onClose: () => void;
}) {
  const q = useGet<Observation>("/observations/" + id);
  const navigate = useNavigate();
  if (!q.data) return null;
  const o = q.data;
  return (
    <div className="recognition-result-row">
      {o.evidence?.plate_url ? (
        <img src={o.evidence.plate_url} alt="Recognized plate crop" />
      ) : (
        <ImageOff size={20} />
      )}
      <div>
        <Plate value={o.plate} small />
        <small>
          {pct(o.ocr_confidence)} OCR · {o.vehicle_type}
        </small>
      </div>
      <StateBadge status={o.status} />
      <button className="secondary" onClick={() => onEvidence(o)}>
        Evidence
      </button>
      {o.vehicle_id && (
        <button
          className="primary"
          onClick={() => {
            onClose();
            navigate("/vehicles/" + o.vehicle_id + "?run=" + o.run_id);
          }}
        >
          Open history
          <ArrowUpRight size={15} />
        </button>
      )}
    </div>
  );
}
