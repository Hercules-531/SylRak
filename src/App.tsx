import { useEffect, useState } from "react";
import {
  NavLink,
  Routes,
  Route,
  useLocation,
  useNavigate,
  Link,
} from "react-router-dom";
import { useQueryClient } from "@tanstack/react-query";
import {
  LayoutDashboard,
  Search,
  Camera,
  ChartNoAxesCombined,
  ShieldAlert,
  ListFilter,
  ArrowUpRight,
  ScanLine,
  Play,
  Pause,
  RotateCcw,
  ChevronRight,
  PanelLeft,
  CornerDownLeft,
  Check,
  TriangleAlert,
  Activity,
  X,
} from "lucide-react";
import {
  post,
  useGet,
  time,
  date,
  number,
  type Snapshot,
  type Observation,
  type Alert,
} from "./api";
import MapView from "./MapView";
import {RegistrationPage, AppearancePage, CasesPage, CasePage, NotificationBanners} from './extensions';
import {
  Plate,
  Modal,
  ObservationTable,
  AlertCard,
  EvidenceDetails,
  Empty,
  Loading,
  ErrorState,
  useAction,
} from "./ui";
import {
  Investigations,
  VehiclePage,
  AlertsPage,
  CamerasPage,
  TrafficPage,
  WatchlistPage,
  RecognitionPanel,
} from "./pages";
const nav = [
  { to: "/", name: "Command", icon: LayoutDashboard },
  { to: "/investigations", name: "Investigations", icon: Search },
  { to: "/alerts", name: "Alerts", icon: ShieldAlert },
  { to: "/cameras", name: "Cameras", icon: Camera },
  { to: "/traffic", name: "Traffic analytics", icon: ChartNoAxesCombined },
  { to: "/watchlist", name: "Watchlist", icon: ListFilter },
  { to: "/registrations", name: "Registration lookup", icon: Search },
];
export default function App() {
  const user = useGet<any>("/auth/me");
  const [toast, setToast] = useState<{
    message: string;
    error: boolean;
  } | null>(null);
  useEffect(() => {
    let timer: ReturnType<typeof setTimeout>;
    const handler = (event: Event) => {
      setToast((event as CustomEvent).detail);
      clearTimeout(timer);
      timer = setTimeout(() => setToast(null), 6000);
    };
    window.addEventListener("sylrak:notice", handler);
    return () => {
      window.removeEventListener("sylrak:notice", handler);
      clearTimeout(timer);
    };
  }, []);
  return (
    <>
      {user.isLoading ? (
        <Loading />
      ) : user.data ? (
        <Workspace user={user.data} />
      ) : (
        <ErrorState error={user.error || new Error('Local server is unavailable.')} retry={()=>user.refetch()} />
      )}
      {toast && (
        <div className={"toast " + (toast.error ? "error" : "")} role="status">
          {toast.error ? <TriangleAlert size={18} /> : <Check size={18} />}
          <span>{toast.message}</span>
          <button
            className="icon-btn"
            onClick={() => setToast(null)}
            aria-label="Dismiss notification"
          >
            <X size={16} />
          </button>
        </div>
      )}
    </>
  );
}
function Workspace({ user }: { user: any }) {
  const client = useQueryClient(),
    navigate = useNavigate(),
    location = useLocation();
  const snap = useGet<Snapshot>("/snapshot");
  const [connected, setConnected] = useState(false),
    [query, setQuery] = useState(""),
    [recognition, setRecognition] = useState(false),
    [evidence, setEvidence] = useState<Observation | null>(null);
  const action = useAction();
  const [navigationOpen,setNavigationOpen]=useState(false);
  const [wallClock,setWallClock]=useState(()=>Date.now());
  useEffect(()=>{const timer=setInterval(()=>setWallClock(Date.now()),60000);return()=>clearInterval(timer)},[]);
  useEffect(()=>setNavigationOpen(false),[location.pathname]);
  useEffect(() => {
    let timer: ReturnType<typeof setTimeout> | undefined;
    let stopped = false;
    const stream = new EventSource("/api/v1/events");
    stream.onopen = () => setConnected(true);
    stream.onerror = () => setConnected(false);
    stream.addEventListener("session.expired", () => {
      stream.close();
      client.invalidateQueries({ queryKey: ["/auth/me"] });
    });
    stream.addEventListener("update", () => {
      if (timer || stopped) return;
      timer = setTimeout(() => {
        client.invalidateQueries({
          predicate: (q) => q.queryKey[0] != "/auth/me",
        });
        timer = undefined;
      }, 350);
    });
    return () => {
      stopped = true;
      stream.close();
      clearTimeout(timer);
    };
  }, [client]);
  const openAlert = (a: Alert) => {
    if (a.vehicle_id)
      navigate("/vehicles/" + a.vehicle_id + "?run=" + a.observation.run_id);
    else setEvidence(a.observation);
  };
  const active = nav.find((n) =>
    n.to === "/"
      ? location.pathname === "/"
      : location.pathname.startsWith(n.to),
  );
  return (
    <div className="app-shell">
      <NotificationBanners />
      <div className={'navigation-drawer'+(navigationOpen?' is-open':'')}
        onMouseEnter={()=>setNavigationOpen(true)}
        onMouseLeave={e=>{if(!e.currentTarget.contains(document.activeElement))setNavigationOpen(false)}}
        onFocusCapture={()=>setNavigationOpen(true)}
        onBlur={e=>{if(!e.currentTarget.contains(e.relatedTarget))setNavigationOpen(false)}}
        onKeyDown={e=>{if(e.key==='Escape'){e.currentTarget.querySelector<HTMLButtonElement>('.navigation-trigger')?.focus();setNavigationOpen(false)}}}>
      <button className="navigation-trigger" aria-label="Open navigation" aria-expanded={navigationOpen} aria-controls="navigation-panel" title="Hover to open navigation" onClick={()=>setNavigationOpen(true)}><PanelLeft size={16}/></button>
      <aside id="navigation-panel" className="sidebar" inert={!navigationOpen}>
        <Link to="/" className="brand">
          <span className="brand-symbol">
            <i />
            <i />
            <i />
          </span>
          <span>
            sylrak<small>VEHICLE INTELLIGENCE</small>
          </span>
        </Link>
        <div className="workspace-tag">
          <span className="flag-bars">
            <i />
            <i />
            <i />
          </span>
          <div>
            Delhi workspace<small>Central & East districts</small>
          </div>
        </div>
        <div className="nav-label">OPERATIONS</div>
        <nav aria-label="Main navigation">
          {nav.map(({ to, name, icon: Icon }, i) => (
            <NavLink
              key={to}
              to={to}
              end={to === "/"}
              className={({ isActive }) =>
                "nav-item " + (isActive ? "active" : "")
              }
            >
              <Icon size={18} />
              <span>{name}</span>
              {i === 2 && !!snap.data?.summary.active_alerts && (
                <b>{snap.data.summary.active_alerts}</b>
              )}
            </NavLink>
          ))}
        </nav>
        <div className="sidebar-bottom">
          <div id="notification-sound-control"/>
          <div className="system-status">
            <span className={"dot " + (connected ? "online" : "offline")} />
            {connected ? "Local backend connected" : "Reconnecting…"}
          </div>
          <span className="sidebar-version">
            SYLRAK / SIH26127<span>v0.2 · Local prototype</span>
          </span>
        </div>
      </aside>
      </div>
      <section className="main-shell" onPointerDown={()=>setNavigationOpen(false)}>
        <header className="topbar">
          <div className="breadcrumb">
            Workspace
            <ChevronRight size={13} />
            <strong>
              {location.pathname.startsWith("/vehicles")
                ? "Vehicle history"
                : active?.name || (location.pathname.startsWith('/cases')?'Investigation cases':'Appearance search')}
            </strong>
          </div>
          <form
            className="global-search"
            onSubmit={(e) => {
              e.preventDefault();
              navigate("/investigations?q=" + encodeURIComponent(query));
            }}
          >
            <Search size={15} />
            <input
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Find a registration…"
              aria-label="Search vehicle registration"
            />
            <kbd aria-label="Press Enter"><CornerDownLeft size={14}/></kbd>
          </form>
          <div className="header-date">
            {date(wallClock/1000)}
            <span>TODAY · IST</span>
          </div>
          <div className="user-chip"><span>SR</span><div>Local workspace<small>No sign-in required</small></div></div>
        </header>
        <div className="demo-strip">
          <span>
            <i className="dot amber" />
            DEMONSTRATION
          </span>
          <p>
            Simulated Delhi cameras and watchlists. Sample recognition runs
            locally.
          </p>
          <span className="network-local">OFFLINE READY</span>
        </div>
        {snap.isError ? (
          <ErrorState error={snap.error} retry={() => snap.refetch()} />
        ) : !snap.data ? (
          <Loading />
        ) : (
          <>
            <div className="workspace-toolbar">
              <div>
                
                <h1>
                  {location.pathname === "/"
                    ? "City command"
                    : location.pathname.startsWith("/vehicles")
                      ? "Vehicle investigation"
                      : active?.name || (location.pathname.startsWith('/cases')?'Investigation cases':'Appearance search')}
                </h1>
              </div>
              <div className="demo-controls">
                <div className="scenario-clock">
                  <span className="mono">
                    {time(snap.data.run.clock, true)}
                  </span>
                  <small>
                    {date(snap.data.run.clock)} · IST ·{" "}
                    {snap.data.run.status === "running"
                      ? "PLAYING"
                      : snap.data.run.status.toUpperCase()}
                  </small>
                </div>
                {user.role === "admin" && (
                  <>
                    <button
                      className="icon-btn replay-btn"
                      aria-label={
                        snap.data.run.status === "running"
                          ? "Pause replay"
                          : "Start replay"
                      }
                      title={
                        snap.data.run.status === "running"
                          ? "Pause replay"
                          : "Start replay"
                      }
                      onClick={() =>
                        action(() =>
                          post("/demo", {
                            action:
                              snap.data!.run.status === "running"
                                ? "pause"
                                : "start",
                          }),
                        )
                      }
                    >
                      {snap.data.run.status === "running" ? (
                        <Pause size={17} />
                      ) : (
                        <Play size={17} />
                      )}
                    </button>
                    <select
                      className="speed-select"
                      value={snap.data.run.speed}
                      aria-label="Replay speed"
                      onChange={(e) =>
                        action(() =>
                          post("/demo", {
                            action: "speed",
                            speed: Number(e.target.value),
                          }),
                        )
                      }
                    >
                      {[1, 6, 12, 60].map((v) => (
                        <option key={v} value={v}>
                          {v}×
                        </option>
                      ))}
                    </select>
                    <button
                      className="icon-btn"
                      aria-label="New demo run"
                      title="Start a new run; previous history is preserved"
                      onClick={() =>
                        action(
                          () => post("/demo", { action: "reset" }),
                          "New run ready. Previous history is preserved.",
                        )
                      }
                    >
                      <RotateCcw size={16} />
                    </button>
                  </>
                )}
                <button
                  className="primary"
                  onClick={() => setRecognition(true)}
                >
                  <ScanLine size={17} />
                  Recognize vehicle
                </button>
              </div>
            </div>
            <Routes>
              <Route path="/registrations" element={<RegistrationPage/>}/>
              <Route path="/appearance" element={<AppearancePage cameras={snap.data.cameras} onEvidence={setEvidence}/>}/>
              <Route path="/cases" element={<CasesPage/>}/>
              <Route path="/cases/:id" element={<CasePage cameras={snap.data.cameras} onEvidence={setEvidence}/>}/>
              <Route
                path="/"
                element={
                  <Command
                    snapshot={snap.data}
                    onEvidence={setEvidence}
                    onAlert={openAlert}
                    onRecognize={() => setRecognition(true)}
                  />
                }
              />
              <Route
                path="/investigations"
                element={
                  <Investigations
                    cameras={snap.data.cameras}
                    onEvidence={setEvidence}
                  />
                }
              />
              <Route
                path="/vehicles/:id"
                element={
                  <VehiclePage
                    cameras={snap.data.cameras}
                    onEvidence={setEvidence}
                  />
                }
              />
              <Route
                path="/alerts"
                element={
                  <AlertsPage onEvidence={setEvidence} onAlert={openAlert} />
                }
              />
              <Route
                path="/cameras"
                element={
                  <CamerasPage
                    cameras={snap.data.cameras}
                    user={user}
                    onEvidence={setEvidence}
                    onRecognize={() => setRecognition(true)}
                  />
                }
              />
              <Route
                path="/traffic"
                element={<TrafficPage clock={snap.data.run.clock} />}
              />
              <Route
                path="/watchlist"
                element={<WatchlistPage user={user} />}
              />
              <Route
                path="*"
                element={
                  <Empty title="View not found">
                    <Link to="/">Return to Command</Link>
                  </Empty>
                }
              />
            </Routes>
          </>
        )}
        <footer className="workspace-footer">
          <span>
            <ShieldAlert size={12} /> Human verification required before
            operational action
          </span>
          <span>All timestamps in IST · Camera coverage is simulated</span>
        </footer>
      </section>
      <Modal
        open={recognition}
        onClose={() => setRecognition(false)}
        title="Recognize a vehicle"
        wide
      >
        <RecognitionPanel
          cameras={snap.data?.cameras || []}
          onEvidence={(o) => {
            setRecognition(false);
            setEvidence(o);
          }}
          onClose={() => setRecognition(false)}
        />
      </Modal>
      <Modal
        open={!!evidence}
        onClose={() => setEvidence(null)}
        title="Observation evidence"
        wide
      >
        {evidence && (
          <EvidenceDetails
            observation={evidence}
            onReviewed={() => setEvidence(null)}
          />
        )}
      </Modal>
    </div>
  );
}
function Command({
  snapshot,
  onEvidence,
  onAlert,
  onRecognize,
}: {
  snapshot: Snapshot;
  onEvidence: (o: Observation) => void;
  onAlert: (a: Alert) => void;
  onRecognize: () => void;
}) {
  const [selectedCamera, setSelectedCamera] = useState<string>();
  const c = snapshot.cameras.find((c) => c.id === selectedCamera);
  const detail = useGet<any>("/cameras/" + selectedCamera, !!selectedCamera);
  const target = useGet<Observation>(
    "/observations/" + snapshot.run.target_observation_id,
    !!snapshot.run.target_observation_id,
  );
  const vehicle = useGet<any>(
    "/vehicles/" + target.data?.vehicle_id,
    !!target.data?.vehicle_id,
  );
  const metrics = [
    {
      label: "Vehicle passages",
      value: number(snapshot.summary.passages),
      detail: "Current scenario",
      icon: Activity,
    },
    {
      label: "Cameras online",
      value:
        snapshot.cameras.filter((c) => c.status === "online").length +
        " / " +
        snapshot.cameras.length,
      detail:
        snapshot.cameras.filter((c) => c.status === "degraded").length +
        " degraded · " +
        snapshot.cameras.filter((c) => c.status === "offline").length +
        " offline",
      icon: Camera,
    },
    {
      label: "Active alerts",
      value: snapshot.summary.active_alerts,
      detail: "Watchlist & route reviews",
      icon: ShieldAlert,
    },
    {
      label: "Identified registrations",
      value: number(snapshot.summary.identified),
      detail: "Accepted plate identities",
      icon: ScanLine,
    },
  ];
  return (
    <div className="command-content">
      <div className="metrics-strip">
        {metrics.map((m, i) => (
          <div className="metric" key={m.label}>
            <div className="metric-heading">
              {m.label}
              <m.icon size={16} />
            </div>
            <div className={"metric-number " + (i === 2 ? "red-text" : "")}>
              {m.value}
            </div>
            <div className="metric-detail">
              {i === 2 && <i className="dot red" />}
              {m.detail}
            </div>
          </div>
        ))}
      </div>
      <div className="command-grid">
        <section className="panel map-panel">
          <div className="panel-heading">
            <h2>
              Camera network<span className="panel-counter">12</span>
            </h2>
            <div className="panel-right">
              <span className="dot online" />
              Local replay
            </div>
          </div>
          <MapView
            cameras={snapshot.cameras}
            selectedCamera={selectedCamera}
            onCamera={setSelectedCamera}
            observations={vehicle.data?.observations || []}
          />
          {c && (
            <div className="camera-summary">
              <div>
                <span className="mono camera-code">{c.id}</span>
                <strong>{c.name}</strong>
                <span>
                  {c.direction} · {c.status}
                </span>
              </div>
              <button
                className="text-button"
                onClick={() => setSelectedCamera(undefined)}
              >
                Clear selection
                <X size={14} />
              </button>
            </div>
          )}
        </section>
        <aside className="panel alert-panel">
          <div className="panel-heading">
            <h2>
              Priority alerts
              <span className="panel-counter red-counter">
                {snapshot.summary.active_alerts}
              </span>
            </h2>
            <Link
              to="/alerts"
              className="icon-btn"
              aria-label="View all alerts"
            >
              <ArrowUpRight size={17} />
            </Link>
          </div>
          <div className="alerts-scroll">
            {snapshot.alerts.length ? (
              snapshot.alerts.map((a) => (
                <AlertCard key={a.id} alert={a} onOpen={() => onAlert(a)} />
              ))
            ) : (
              <Empty title="No active alerts">
                New watchlist matches appear here.
              </Empty>
            )}
          </div>
          <div className="target-prompt">
            <div className="eyebrow">TARGET VEHICLE DEMO</div>
            {snapshot.run.target_observation_id ? (
              <>
                <Plate value={snapshot.run.target_plate} small />
                <p>
                  Recognition complete. Start replay to follow the next three
                  camera sightings.
                </p>
              </>
            ) : (
              <>
                <p>
                  Recognize a real Indian plate, then follow its journey across
                  four cameras.
                </p>
                <button className="text-button" onClick={onRecognize}>
                  Process target sample
                  <ArrowUpRight size={15} />
                </button>
              </>
            )}
          </div>
        </aside>
      </div>
      <section className="panel recent-panel">
        <div className="panel-heading">
          <h2>
            {c ? "Sightings at " + c.name : "Recent sightings"}
            <span className="panel-counter">
              {c
                ? detail.data?.observations.length || 0
                : snapshot.recent.length}
            </span>
          </h2>
          <Link
            className="text-button"
            to={"/investigations" + (c ? "?camera=" + c.id : "")}
          >
            Search history
            <ArrowUpRight size={15} />
          </Link>
        </div>
        <ObservationTable
          items={c ? detail.data?.observations || [] : snapshot.recent}
          onEvidence={onEvidence}
          compact
        />
      </section>
    </div>
  );
}
