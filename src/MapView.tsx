import { useEffect, useRef, useState } from "react";
import * as maplibregl from "maplibre-gl";
import { Map as LibreMap, GeoJSONSource } from "maplibre-gl";
import mapWorkerUrl from "maplibre-gl/dist/maplibre-gl-worker.mjs?worker&url";
import { Protocol } from "pmtiles";
import { layers, namedFlavor } from "@protomaps/basemaps";
import "maplibre-gl/dist/maplibre-gl.css";
import { LocateFixed, MapPin, TriangleAlert } from "lucide-react";
import {time, type Camera, type Observation} from "./api";
let installed = false;
function install() {
  if (!installed) {
    maplibregl.setWorkerUrl(mapWorkerUrl);
    const protocol = new Protocol();
    maplibregl.addProtocol("pmtiles", protocol.tile);
    installed = true;
  }
}
function style(oled = false): any {
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
    // Background matches earth so zoomed-out views fade past the offline extract instead of showing a hard edge.
    ...(oled ? {background:'#090c10',earth:'#090c10',water:'#071722',park_a:'#0c1714',park_b:'#101c17',buildings:'#11171d',minor_a:'#252e37',minor_b:'#252e37',major:'#424e5b',highway:'#576573'} : {}),
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
    layers: layers("protomaps", flavor, { lang: "en" }).filter((layer:any)=>!oled||!layer.id.startsWith('poi')),
  };
}
export default function MapView({
  cameras,
  observations = [],
  selectedCamera,
  onCamera,
  heat = false,
  compact = false,
  connectionColor = '#b6d4ff',
  pageScroll = false,
  cinematic = false,
  focusObservationId,
}: {
  cameras: Camera[];
  observations?: Observation[];
  selectedCamera?: string;
  onCamera?: (id: string) => void;
  heat?: boolean;
  compact?: boolean;
  connectionColor?: string;
  pageScroll?: boolean;
  cinematic?: boolean;
  focusObservationId?: string;
}) {
  const element = useRef<HTMLDivElement>(null),
    map = useRef<LibreMap | null>(null),
    markers = useRef<maplibregl.Marker[]>([]),
    lastBounds = useRef(''),
    callback = useRef(onCamera);
  callback.current = onCamera;
  const [ready, setReady] = useState(false),
    [error, setError] = useState(false);
  useEffect(() => {
    install();
    if (!element.current) return;
    const m = new LibreMap({
      container: element.current,
      style: style(pageScroll),
      scrollZoom: !pageScroll,
      cooperativeGestures: pageScroll,
      center: [77.2505, 28.6285],
      zoom: 12.65,
      pitch: cinematic && !matchMedia('(prefers-reduced-motion: reduce)').matches ? 42 : 0,
      bearing: cinematic && !matchMedia('(prefers-reduced-motion: reduce)').matches ? -12 : 0,
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
    // Expose the finished map for browser verification without making requests
    // or keeping an animation loop alive while the scene is offscreen.
    (element.current as HTMLDivElement & {sylrakMap?:LibreMap}).sylrakMap=m;
    m.on("error", (e) => {
      setError(true);
    });
    const resize = new ResizeObserver(() => m.resize());
    resize.observe(element.current);
    return () => {
      resize.disconnect();
      m.remove();
      map.current = null;
      lastBounds.current = '';
      setReady(false);
    };
  }, []);
  useEffect(()=>{
    if(!cinematic||!ready||!map.current||!element.current)return;
    const scene=element.current.closest<HTMLElement>('[data-map-scene]');if(!scene)return;
    const reduced=matchMedia('(prefers-reduced-motion: reduce)');let frame=0;
    const render=()=>{frame=0;const rect=scene.getBoundingClientRect();if(rect.bottom<0||rect.top>innerHeight)return;
      const progress=reduced.matches?1:Math.max(0,Math.min(1,-rect.top/Math.max(1,rect.height-innerHeight)));
      map.current?.jumpTo({pitch:42*(1-progress),bearing:-12*(1-progress)});
    };
    const schedule=()=>{if(!frame)frame=requestAnimationFrame(render)};
    addEventListener('scroll',schedule,{passive:true});addEventListener('resize',schedule);reduced.addEventListener('change',schedule);render();
    return()=>{cancelAnimationFrame(frame);removeEventListener('scroll',schedule);removeEventListener('resize',schedule);reduced.removeEventListener('change',schedule)};
  },[cinematic,ready]);
  useEffect(() => {
    if (!map.current || !ready) return;
    const m = map.current;
    markers.current.forEach((x) => x.remove());
    markers.current = [];
    const accepted=observations.filter(o=>o.status==='accepted');
    for (const c of cameras) {
      const routeIndex=accepted.findIndex(o=>o.camera_id===c.id);
      const last=accepted.at(-1);
      const focused=accepted.find(o=>o.id===focusObservationId)?.camera_id===c.id;
      const el = document.createElement("button");
      el.className =
        "camera-pin " + c.status + (selectedCamera === c.id || focused ? " selected" : "") + (routeIndex>=0?' route-camera':'') + (last?.camera_id===c.id?' last-observed':'');
      el.setAttribute("aria-label", `${c.name}, ${c.id}, ${c.status}`);
      el.title = c.name;
      el.innerHTML =
        '<span class="camera-pin-symbol"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7"><rect x="3" y="6" width="12" height="12" rx="2"/><path d="m15 10 6-3v10l-6-3"/></svg></span><span class="camera-pin-label"></span>';
      el.querySelector(".camera-pin-label")!.textContent = c.id;
      if(routeIndex>=0){
        el.querySelector('.camera-pin-symbol')!.textContent=String(routeIndex+1);
        el.title=`${c.name} · Recorded sighting ${routeIndex+1}`;
        if(last?.camera_id===c.id){const label=document.createElement('span');label.className='last-observed-label';label.textContent='Last observed · '+time(last.observed_at)+' IST';el.append(label)}
      }
      el.onclick = () => callback.current?.(c.id);
      markers.current.push(
        new maplibregl.Marker({ element: el, anchor: "center" })
          .setLngLat([c.lon, c.lat])
          .addTo(m),
      );
    }
  }, [cameras, selectedCamera, ready, observations, focusObservationId]);
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
        id: "trajectory-casing",
        type: "line",
        source: "trajectory",
        layout:{'line-cap':'round','line-join':'round'},
        paint:{'line-color':'#030609','line-width':10,'line-opacity':.9},
      });
      m.addLayer({
        id: "trajectory-halo",
        type: "line",
        source: "trajectory",
        paint: {
          "line-color": "#4985dc",
          "line-width": 14,
          "line-opacity": 0.12,
        },
      });
      m.addLayer({
        id: "trajectory-line",
        type: "line",
        source: "trajectory",
        layout:{'line-cap':'round','line-join':'round'},
        paint: {
          "line-color": "#7aacfa",
          "line-width": 4.5,
        },
      });
    }
    m.setPaintProperty('trajectory-line','line-color',connectionColor);
    m.setPaintProperty('trajectory-halo','line-color',connectionColor);
    const signature = accepted.map(o=>`${o.camera.lon},${o.camera.lat}`).join(';');
    if (accepted.length > 1 && signature !== lastBounds.current) {
      lastBounds.current = signature;
      const bounds = new maplibregl.LngLatBounds();
      accepted.forEach((o) => bounds.extend([o.camera.lon, o.camera.lat]));
      m.fitBounds(bounds, {
        padding: cinematic ? {top:150,bottom:130,left:innerWidth<600?46:110,right:innerWidth<600?46:150} : compact ? 60 : 80,
        maxZoom: 14,
        duration: matchMedia('(prefers-reduced-motion: reduce)').matches ? 0 : 250,
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
    <div className={"map-wrapper " + (compact ? "compact" : "") + (pageScroll ? " map-page-scroll" : "") + (ready ? " map-ready" : "") + (cinematic ? " cinematic-map" : "")}>
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
        onClick={(event) =>
          map.current?.flyTo({
            center: [77.2505, 28.6285],
            zoom: 12.65,
            duration: event.detail===0 || matchMedia('(prefers-reduced-motion: reduce)').matches ? 0 : 250,
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
            Estimated connection · not a verified route
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
