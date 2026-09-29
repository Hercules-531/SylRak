import ReviewScore from './ReviewScore';
import { useState, type ReactNode } from "react";
import * as Dialog from "@radix-ui/react-dialog";
import {
  X,
  ArrowUpRight,
  Camera as CameraIcon,
  ImageOff,
  CarFront,
  Check,
  TriangleAlert,
} from "lucide-react";
import { Link } from "react-router-dom";
import { useQueryClient } from "@tanstack/react-query";
import {
  api,
  patch,
  pct,
  time,
  date,
  type Observation,
  type Alert,
} from "./api";
export function notice(message: string, error = false) {
  window.dispatchEvent(
    new CustomEvent("sylrak:notice", { detail: { message, error } }),
  );
}
export function useAction() {
  const client = useQueryClient();
  return async <T,>(work: () => Promise<T>, message?: string) => {
    try {
      const result = await work();
      await client.invalidateQueries();
      if (message) notice(message);
      return result;
    } catch (e) {
      notice((e as Error).message, true);
      return undefined;
    }
  };
}
export function Badge({
  children,
  tone = "neutral",
}: {
  children: ReactNode;
  tone?: string;
}) {
  return <span className={"badge " + tone}>{children}</span>;
}
export function StateBadge({ status }: { status: string }) {
  return (
    <Badge
      tone={
        status === "accepted" || status === "online"
          ? "green"
          : status === "conflict"
            ? "red"
            : status === "possible" || status === "degraded"
              ? "amber"
              : "neutral"
      }
    >
      {status === "accepted"
        ? "Exact plate"
        : status === "possible"
          ? "Needs review"
          : status}
    </Badge>
  );
}
export function SourceBadge({ source }: { source: string }) {
  return (
    <span className={"source-label " + source}>
      {source === "real_inference"
        ? "Sample inference"
        : source === "replay"
          ? "Camera replay"
          : "Simulated"}
    </span>
  );
}
export function Plate({
  value,
  small = false,
}: {
  value: string | null;
  small?: boolean;
}) {
  return (
    <span className={"plate " + (small ? "small" : "")}>
      {value || "UNREADABLE"}
    </span>
  );
}
export function Empty({
  title,
  children,
}: {
  title: string;
  children?: ReactNode;
}) {
  return (
    <div className="empty-state">
      <CameraIcon size={28} />
      <h3>{title}</h3>
      <p>{children}</p>
    </div>
  );
}
export function Loading() {
  return (
    <div className="loading">
      <span className="spinner" />
      Loading local records…
    </div>
  );
}
export function ErrorState({
  error,
  retry,
}: {
  error: Error;
  retry?: () => void;
}) {
  return (
    <div className="error-state">
      <TriangleAlert size={22} />
      <h3>Unable to load this view</h3>
      <p>{error.message}</p>
      {retry && <button onClick={retry}>Try again</button>}
    </div>
  );
}
export function Modal({
  open,
  onClose,
  title,
  children,
  wide = false,
}: {
  open: boolean;
  onClose: () => void;
  title: string;
  children: ReactNode;
  wide?: boolean;
}) {
  return (
    <Dialog.Root open={open} onOpenChange={(v) => !v && onClose()}>
      <Dialog.Portal>
        <Dialog.Overlay className="dialog-overlay" />
        <Dialog.Content
          className={"dialog " + (wide ? "wide" : "")}
          aria-describedby={undefined}
        >
          <header className="dialog-header">
            <Dialog.Title>{title}</Dialog.Title>
            <Dialog.Close asChild>
              <button className="icon-btn" aria-label="Close">
                <X size={20} />
              </button>
            </Dialog.Close>
          </header>
          {children}
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  );
}
export function Frame({
  observation,
  large = false,
}: {
  observation: Observation;
  large?: boolean;
}) {
  const [showBoxes, setShowBoxes] = useState(true);
  const e = observation.evidence;
  if (!e)
    return (
      <div className={"no-frame " + (large ? "large" : "")}>
        <ImageOff size={26} />
        <span>No photograph for this simulated observation</span>
      </div>
    );
  const boxes = [
    {
      box: observation.details.vehicle_box,
      color: "#61a0ff",
      label: observation.vehicle_type,
    },
    { box: observation.details.plate_box, color: "#6fdeac", label: "PLATE" },
  ];
  return (
    <div className={"evidence-frame " + (large ? "large" : "")}>
      <img
        src={e.original_url}
        alt={
          "Source photograph for " + (observation.plate || "unreadable vehicle")
        }
        onError={(e) => {
          e.currentTarget.alt = "Evidence file unavailable";
        }}
      />
      {showBoxes && (
        <svg
          className="frame-boxes"
          viewBox={`0 0 ${e.width} ${e.height}`}
          preserveAspectRatio="xMidYMid meet"
        >
          {boxes
            .filter((x) => x.box)
            .map((x, i) => (
              <g key={i}>
                <rect
                  x={x.box[0]}
                  y={x.box[1]}
                  width={x.box[2] - x.box[0]}
                  height={x.box[3] - x.box[1]}
                  fill="none"
                  stroke={x.color}
                  strokeWidth={Math.max(e.width / 550, 3)}
                />
              </g>
            ))}
        </svg>
      )}
      <span className="frame-corner">
        <SourceBadge source={observation.source_kind} />
      </span>
      <button
        className="frame-box-toggle"
        onClick={() => setShowBoxes(!showBoxes)}
      >
        {showBoxes ? "Hide" : "Show"} boxes
      </button>
    </div>
  );
}
export function EvidenceDetails({
  observation,
  onReviewed,
}: {
  observation: Observation;
  onReviewed?: () => void;
}) {
  const action = useAction();
  const [reason, setReason] = useState("");
  const [busy, setBusy] = useState(false);
  const review = async (status: string) => {
    setBusy(true);
    const result = await action(
      () =>
        patch("/associations/" + observation.association.id, {
          status,
          reason,
        }),
      "Association review saved",
    );
    setBusy(false);
    if (result) onReviewed?.();
  };
  return (
    <>
      <div className="evidence-layout">
        <Frame observation={observation} large />
        <div className="evidence-facts">
          <div className="eyebrow">RECOGNITION EVIDENCE</div>
          <Plate value={observation.plate} />
          {observation.evidence?.plate_url && (
            <img
              className="plate-crop"
              src={observation.evidence.plate_url}
              alt="Detected number plate crop"
            />
          )}
          <dl className="facts">
            <dt>Raw OCR</dt>
            <dd className="mono">
              {observation.raw_plate || "No readable text"}
            </dd>
            <dt>OCR score</dt>
            <dd>{pct(observation.ocr_confidence)}</dd>
            <dt>Plate detection</dt>
            <dd>{pct(observation.plate_confidence)}</dd>
            <dt>Vehicle detection</dt>
            <dd>{pct(observation.vehicle_confidence)}</dd>
            <dt>Camera</dt>
            <dd>
              {observation.camera_id} · {observation.camera.name}
            </dd>
            <dt>Scenario time</dt>
            <dd>
              {date(observation.observed_at)} ·{" "}
              {time(observation.observed_at, true)} IST
            </dd>
            <dt>Vehicle</dt>
            <dd>
              {observation.vehicle_type} · {observation.color}
            </dd>
            <dt>Association</dt>
            <dd>
              <StateBadge status={observation.status} />
            </dd>
          </dl>
        </div>
      </div>
      <div className="explanation">
        {!!observation.details?.ocr_alternatives?.length&&<details><summary>Alternative OCR readings</summary>{observation.details.ocr_alternatives.map((a:any,i:number)=><p key={i}>{a.model}: <span className="mono">{a.raw_plate||'Unreadable'}</span> · {pct(a.confidence)} model score. Same image; not independent evidence.</p>)}</details>}
        <div className="eyebrow">WHY THIS ASSOCIATION</div>
        <p>
          {observation.association?.reason || "No plate identity was assigned."}
        </p>
        {observation.association?.score != null && (
          <small>
            Rule similarity: {pct(observation.association.score)} · heuristic,
            not a calibrated probability
          </small>
        )}
      </div>
      {["possible", "conflict"].includes(observation.status) &&
        observation.association && (
          <div className="review-box">
            <label>
              Review note
              <input
                value={reason}
                onChange={(e) => setReason(e.target.value)}
                placeholder="Describe what you verified in the evidence"
              />
            </label>
            <div className="button-row">
              <button
                disabled={reason.trim().length < 3 || busy}
                onClick={() => review("accepted")}
              >
                <Check size={16} />
                Accept association
              </button>
              <button
                className="secondary"
                disabled={reason.trim().length < 3 || busy}
                onClick={() => review("rejected")}
              >
                Reject association
              </button>
            </div>
          </div>
        )}
      <div className="provenance">
        <SourceBadge source={observation.source_kind} />
        <span>
          {observation.source_kind === "replay"
            ? "Simulated sighting. The photograph and OCR result are reused from the original sample."
            : observation.source_kind === "real_inference"
              ? "Real recognition on a sample image. Camera location and event time are simulated."
              : "Synthetic event and confidence values. No real camera capture is claimed."}
        </span>
        {observation.evidence && (
          <span>
            Source:{" "}
            <a
              href={observation.evidence.source}
              target="_blank"
              rel="noreferrer"
            >
              Indian Number Plate Images
            </a>{" "}
            · {observation.evidence.license}
          </span>
        )}
      </div>
    </>
  );
}
export function ObservationTable({
  items,
  onEvidence,
  compact = false,
  showReview = false,
  showFeatures = false,
}: {
  items: Observation[];
  onEvidence: (o: Observation) => void;
  compact?: boolean;
  showReview?: boolean;
  showFeatures?: boolean;
}) {
  if (!items.length)
    return (
      <Empty title="No sightings in this selection">
        Try another plate, camera, or time range.
      </Empty>
    );
  return (
    <div className="table-scroll">
      <table className={"data-table " + (compact ? "dense" : "")}>
        <thead>
          <tr>
            <th>Registration</th>
            <th>Vehicle</th>
            <th>Camera / location</th>
            <th>Seen at · IST</th>
            <th>OCR score</th>
            {showFeatures&&<th>Logged features</th>}
            {showReview&&<th>Suspicion score</th>}
            <th>Source</th>
            <th />
          </tr>
        </thead>
        <tbody>
          {items.map((o) => (
            <tr key={o.id}>
              <td>
                {o.vehicle_id ? (
                  <Link
                    className="plate-link"
                    to={`/vehicles/${o.vehicle_id}?run=${o.run_id}`}
                  >
                    <Plate value={o.canonical_plate || o.plate} small />
                    <ArrowUpRight size={13} />
                  </Link>
                ) : (
                  <button className="text-button" onClick={() => onEvidence(o)}>
                    <Plate value={o.plate} small />
                  </button>
                )}
              </td>
              <td>
                <span className="vehicle-type">
                  <CarFront size={15} />
                  <span>
                    {o.vehicle_type}
                    <small>
                      {[o.color, o.details?.make_model, o.details?.size_class]
                        .filter((x) => x && x !== "unknown")
                        .join(" · ")}
                    </small>
                  </span>
                  <i className={"color-dot " + o.color} title={o.color} />
                </span>
              </td>
              <td>
                <span className="mono camera-code">{o.camera_id}</span>
                <span className="table-location">{o.camera.name}</span>
              </td>
              <td className="mono">{time(o.observed_at, true)}</td>
              <td>
                <span
                  className={
                    "confidence " +
                    ((o.ocr_confidence || 0) < 0.9 ? "uncertain" : "")
                  }
                >
                  {pct(o.ocr_confidence)}
                </span>
              </td>
              {showFeatures&&<td><FeatureChips features={(o as any).features}/></td>}
              {showReview&&<td><ReviewScore value={(o as any).theft_review} compact/></td>}
              <td>
                <SourceBadge source={o.source_kind} />
              </td>
              <td>
                <button
                  className="icon-btn table-evidence"
                  aria-label={"View evidence " + o.id}
                  title="View evidence"
                  onClick={() => onEvidence(o)}
                >
                  <ArrowUpRight size={16} />
                </button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
export function AlertCard({
  alert,
  onOpen,
}: {
  alert: Alert;
  onOpen: () => void;
}) {
  return (
    <button className={"alert-card " + alert.priority} onClick={onOpen}>
      <div className="alert-card-top">
        <span className="alert-category">
          {alert.match_method === "possible"
            ? "Possible watchlist match"
            : alert.category === "route pattern"
              ? "Repeated route pattern"
              : alert.category + " vehicle"}
        </span>
        <span className="mono">{time(alert.updated_at)}</span>
      </div>
      <div className="alert-plate">
        <Plate
          value={alert.watchlist?.plate || alert.observation.plate}
          small
        />
        <ArrowUpRight size={15} />
      </div>
      <div className="alert-location">
        <CameraIcon size={12} />
        {alert.observation.camera_id} · {alert.observation.camera.name}
      </div>
      <div className="alert-meta">
        <Badge tone={alert.match_method === "exact" ? "red" : "amber"}>
          {alert.match_method === "exact" ? "Exact match" : "Review required"}
        </Badge>
        <SourceBadge source={alert.observation.source_kind} />
      </div>
    </button>
  );
}
export function FeatureChips({features}:{features?:any[]}){
 if(!features?.length)return <span className="muted">—</span>;
 return <span className="feature-chips">{features.slice(0,2).map(f=><span key={f.id} className={'feature-chip '+f.status} title={`${f.label} · ${f.category} · ${f.part}${f.status==='suggested'?' · suggested, not confirmed':''}`}>{f.label}</span>)}{features.length>2&&<span className="muted">+{features.length-2}</span>}</span>
}
