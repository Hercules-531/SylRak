import { useEffect, useRef, useState } from "react";
import * as maplibregl from "maplibre-gl";
import { Map as LibreMap, GeoJSONSource } from "maplibre-gl";
import mapWorkerUrl from "maplibre-gl/dist/maplibre-gl-worker.mjs?worker&url";
import { Protocol } from "pmtiles";
import { layers, namedFlavor } from "@protomaps/basemaps";
import "maplibre-gl/dist/maplibre-gl.css";
import { LocateFixed, MapPin, TriangleAlert } from "lucide-react";
import type { Camera, Observation } from "./api";
let installed = false;
function install() {
  if (!installed) {
    maplibregl.setWorkerUrl(mapWorkerUrl);
    const protocol = new Protocol();
    maplibregl.addProtocol("pmtiles", protocol.tile);
    installed = true;
  }
}
function style(): any {
  const flavor = {
    ...namedFlavor("dark"),
    background: "#111820",
    earth: "#151c24",
    water: "#0c2636",
    park_a: "#182a29",
    park_b: "#1b2d2b",
    buildings: "#1c252f",
    minor_a: "#303d4a",
    minor_b: "#303d4a",
    major: "#435362",
    highway: "#526171",
    roads_label_minor: "#81919f",
    roads_label_major: "#9cabb8",
    subplace_label: "#a2aeb9",
    city_label: "#c1cad2",
  };
  return {
    version: 8,
    glyphs: location.origin + "/map-assets/fonts/{fontstack}/{range}.pbf",
    sprite: location.origin + "/map-assets/dark",
    sources: {
      protomaps: {
        type: "vector",
        url: "pmtiles://" + location.origin + "/map-assets/delhi.pmtiles",
        attribution: "© OpenStreetMap contributors · Protomaps",
      },
    },
    layers: layers("protomaps", flavor, { lang: "en" }),
  };
}
export default function MapView({
  cameras,
  observations = [],
  selectedCamera,
  onCamera,
  heat = false,
  compact = false,
  connectionColor = '#7aacfa',
}: {
  cameras: Camera[];
  observations?: Observation[];
  selectedCamera?: string;
  onCamera?: (id: string) => void;
  heat?: boolean;
  compact?: boolean;
  connectionColor?: string;
}) {
  const element = useRef<HTMLDivElement>(null),
    map = useRef<LibreMap | null>(null),
    markers = useRef<maplibregl.Marker[]>([]),
    callback = useRef(onCamera);
  callback.current = onCamera;
  const [ready, setReady] = useState(false),
    [error, setError] = useState(false);
  useEffect(() => {
    install();
    if (!element.current) return;
    const m = new LibreMap({
      container: element.current,
      style: style(),
      center: [77.2505, 28.6285],
      zoom: 12.65,
      minZoom: 10.5,
      maxZoom: 16,
      maxBounds: [
        [77.17, 28.56],
        [77.34, 28.69],
      ],
      attributionControl: { compact: true },
    });
    map.current = m;
    m.addControl(
      new maplibregl.NavigationControl({ showCompass: false }),
      "bottom-right",
    );
    m.on("load", () => {
      setReady(true);
      setError(false);
    });
    m.on("error", (e) => {
      setError(true);
    });
    const resize = new ResizeObserver(() => m.resize());
    resize.observe(element.current);
    return () => {
      resize.disconnect();
      m.remove();
      map.current = null;
      setReady(false);
    };
  }, []);
  useEffect(() => {
    if (!map.current || !ready) return;
    const m = map.current;
    markers.current.forEach((x) => x.remove());
    markers.current = [];
    for (const c of cameras) {
      const el = document.createElement("button");
      el.className =
        "camera-pin " + c.status + (selectedCamera === c.id ? " selected" : "");
      el.setAttribute("aria-label", `${c.name}, ${c.id}, ${c.status}`);
      el.title = c.name;
      el.innerHTML =
        '<span class="camera-pin-symbol"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7"><rect x="3" y="6" width="12" height="12" rx="2"/><path d="m15 10 6-3v10l-6-3"/></svg></span><span class="camera-pin-label"></span>';
      el.querySelector(".camera-pin-label")!.textContent = c.id;
      el.onclick = () => callback.current?.(c.id);
      markers.current.push(
        new maplibregl.Marker({ element: el, anchor: "center" })
          .setLngLat([c.lon, c.lat])
          .addTo(m),
      );
    }
  }, [cameras, selectedCamera, ready]);
  useEffect(() => {
    if (!ready || !map.current) return;
    const m = map.current;
    const accepted = observations.filter((o) => o.status === "accepted");
    const data: any = {
      type: "FeatureCollection",
      features:
        accepted.length > 1
          ? [
              {
                type: "Feature",
                geometry: {
                  type: "LineString",
                  coordinates: accepted.map((o) => [
                    o.camera.lon,
                    o.camera.lat,
                  ]),
                },
                properties: {},
              },
            ]
          : [],
    };
    if (m.getSource("trajectory"))
      (m.getSource("trajectory") as GeoJSONSource).setData(data);
    else {
      m.addSource("trajectory", { type: "geojson", data });
      m.addLayer({
        id: "trajectory-halo",
        type: "line",
        source: "trajectory",
        paint: {
          "line-color": "#4985dc",
          "line-width": 8,
          "line-opacity": 0.14,
        },
      });
      m.addLayer({
        id: "trajectory-line",
        type: "line",
        source: "trajectory",
        paint: {
          "line-color": "#7aacfa",
          "line-width": 2.5,
          "line-dasharray": [2, 2],
        },
      });
    }
    m.setPaintProperty('trajectory-line','line-color',connectionColor);
    m.setPaintProperty('trajectory-halo','line-color',connectionColor);
    if (accepted.length > 1) {
      const bounds = new maplibregl.LngLatBounds();
      accepted.forEach((o) => bounds.extend([o.camera.lon, o.camera.lat]));
      m.fitBounds(bounds, {
        padding: compact ? 60 : 95,
        maxZoom: 14,
        duration: 500,
      });
    }
  }, [observations, ready, compact, connectionColor]);
  useEffect(() => {
    if (!ready || !map.current) return;
    const m = map.current;
    const data: any = {
      type: "FeatureCollection",
      features: cameras.map((c) => ({
        type: "Feature",
        geometry: { type: "Point", coordinates: [c.lon, c.lat] },
        properties: { count: c.passages || 0 },
      })),
    };
    if (m.getSource("flow"))
      (m.getSource("flow") as GeoJSONSource).setData(data);
    else {
      m.addSource("flow", { type: "geojson", data });
      m.addLayer(
        {
          id: "flow-heat",
          type: "heatmap",
          source: "flow",
          paint: {
            "heatmap-weight": [
              "interpolate",
              ["linear"],
              ["get", "count"],
              0,
              0,
              150,
              1,
            ],
            "heatmap-intensity": 1.7,
            "heatmap-radius": 65,
            "heatmap-opacity": 0.7,
            "heatmap-color": [
              "interpolate",
              ["linear"],
              ["heatmap-density"],
              0,
              "rgba(0,0,0,0)",
              0.2,
              "#16445d",
              0.5,
              "#247c94",
              0.7,
              "#cbac5a",
              1,
              "#ed8059",
            ],
          },
        },
        "trajectory-halo",
      );
    }
    m.setLayoutProperty("flow-heat", "visibility", heat ? "visible" : "none");
  }, [heat, cameras, ready]);
  return (
    <div className={"map-wrapper " + (compact ? "compact" : "")}>
      <div ref={element} className="city-map" />
      <div className="map-label">
        <MapPin size={14} />
        <span>
          NEW DELHI <span className="map-label-muted">/ CENTRAL & EAST</span>
        </span>
      </div>
      <button
        className="map-center icon-btn"
        title="Reset map view"
        aria-label="Reset map view"
        onClick={() =>
          map.current?.flyTo({
            center: [77.2505, 28.6285],
            zoom: 12.65,
            duration: 400,
          })
        }
      >
        <LocateFixed size={17} />
      </button>
      <div className="map-key">
        <span>
          <i className="dot online" />
          Online camera
        </span>
        <span>
          <i className="dot offline" />
          Offline
        </span>
        {observations.length > 1 && (
          <span>
            <i className="line-key" />
            Estimated connection
          </span>
        )}
        <span className="map-source">Simulated camera network</span>
      </div>
      {error && (
        <div className="map-error">
          <TriangleAlert size={20} />
          Local map unavailable. Run setup to restore map assets.
        </div>
      )}
    </div>
  );
}
