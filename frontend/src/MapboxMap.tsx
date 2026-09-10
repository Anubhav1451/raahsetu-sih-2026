import { useEffect, useMemo, useRef, useState } from "react";
import mapboxgl, { type GeoJSONSource, type LngLatBoundsLike, type Map as MapboxInstance } from "mapbox-gl";
import "mapbox-gl/dist/mapbox-gl.css";
import type { AccessibilityEvent, Comparison, Location, Network } from "./types";

type Props = {
  network: Network;
  locations: Location[];
  result: Comparison | null;
  origin: string;
  destination: string;
  selected: string;
  showRisk: boolean;
  events: AccessibilityEvent[];
  reset: number;
};

export default function MapboxMap({ network, locations, result, origin, destination, selected, showRisk, events, reset }: Props) {
  const host = useRef<HTMLDivElement>(null);
  const mapRef = useRef<MapboxInstance | null>(null);
  const markers = useRef<mapboxgl.Marker[]>([]);
  const [message, setMessage] = useState("Loading live map…");
  const token = import.meta.env.VITE_MAPBOX_TOKEN?.trim();
  const reducedMotion = useMemo(() => window.matchMedia("(prefers-reduced-motion: reduce)").matches, []);
  const routeData = useMemo<GeoJSON.FeatureCollection>(() => {
    const features: GeoJSON.Feature[] = (result?.routes ?? [])
      .flatMap((route) => route.status === "available" ? [{
        type: "Feature" as const,
        geometry: route.geometry,
        properties: { id: route.id, selected: route.id === selected },
      }] : [])
      .sort((a, b) => Number(a.properties?.selected) - Number(b.properties?.selected));
    return { type: "FeatureCollection", features };
  }, [result, selected]);
  const routeDataRef = useRef(routeData);
  routeDataRef.current = routeData;

  const bounds = useMemo(() => {
    const value = new mapboxgl.LngLatBounds();
    network.features.forEach((feature) => feature.geometry.coordinates.forEach(([lon, lat]) => value.extend([lon, lat])));
    return value;
  }, [network]);

  useEffect(() => {
    if (!host.current || !token) return;
    // React StrictMode mounts effects twice in development. Mapbox expects an
    // empty container whenever a new map instance is created.
    host.current.replaceChildren();
    mapboxgl.accessToken = token;
    const map = new mapboxgl.Map({
      container: host.current,
      style: "mapbox://styles/mapbox/dark-v11",
      center: [network.metadata.focus.lon, network.metadata.focus.lat],
      zoom: 10,
      pitch: 54,
      bearing: -18,
      antialias: true,
      attributionControl: true,
      cooperativeGestures: true,
    });
    mapRef.current = map;
    map.addControl(new mapboxgl.NavigationControl({ visualizePitch: true }), "bottom-right");
    map.addControl(new mapboxgl.ScaleControl({ unit: "metric" }), "bottom-left");
    map.on("load", () => {
      map.addSource("raahsetu-dem", {
        type: "raster-dem",
        url: "mapbox://mapbox.mapbox-terrain-dem-v1",
        tileSize: 512,
        maxzoom: 14,
      });
      map.setTerrain({ source: "raahsetu-dem", exaggeration: 1.35 });
      map.addSource("roads", { type: "geojson", data: network as unknown as GeoJSON.FeatureCollection });
      map.addLayer({
        id: "roads-base",
        type: "line",
        source: "roads",
        paint: { "line-color": "#8BA8A1", "line-opacity": 0.32, "line-width": ["interpolate", ["linear"], ["zoom"], 7, 0.5, 14, 2.2] },
      });
      map.addLayer({
        id: "roads-risk",
        type: "line",
        source: "roads",
        filter: [">=", ["get", "risk"], 0.45],
        paint: { "line-color": "#EF4444", "line-opacity": showRisk ? 0.72 : 0, "line-width": 3 },
      });
      map.addSource("routes", { type: "geojson", data: routeDataRef.current });
      map.addLayer({ id: "route-glow", type: "line", source: "routes", paint: { "line-color": ["match", ["get", "id"], "risk_aware", "#10B981", "#F97316"], "line-opacity": 0.25, "line-blur": 7, "line-width": 13 } });
      map.addLayer({ id: "routes-main", type: "line", source: "routes", paint: { "line-color": ["match", ["get", "id"], "risk_aware", "#5EE7B2", "#F97316"], "line-opacity": ["case", ["==", ["get", "selected"], true], 1, 0.48], "line-width": ["case", ["==", ["get", "selected"], true], 6, 3] }, layout: { "line-cap": "round", "line-join": "round" } });
      map.fitBounds(bounds as LngLatBoundsLike, { padding: 54, pitch: 54, duration: reducedMotion ? 0 : 1100 });
      setMessage("");
    });
    map.on("error", (event) => setMessage(event.error?.message || "Map tiles could not be loaded."));
    const mapHost = host.current;
    return () => {
      markers.current.forEach((marker) => marker.remove());
      markers.current = [];
      map.remove();
      mapHost?.replaceChildren();
      mapRef.current = null;
    };
  }, [network, token, bounds, reducedMotion]);

  useEffect(() => {
    const map = mapRef.current;
    if (!map?.isStyleLoaded()) return;
    (map.getSource("routes") as GeoJSONSource | undefined)?.setData(routeData);
    const chosen = result?.routes.find((route) => route.id === selected && route.status === "available");
    if (!chosen || chosen.status !== "available" || chosen.geometry.coordinates.length < 2) return;
    const routeBounds = new mapboxgl.LngLatBounds();
    chosen.geometry.coordinates.forEach(([lon, lat]) => routeBounds.extend([lon, lat]));
    map.fitBounds(routeBounds as LngLatBoundsLike, {
      padding: { top: 82, right: 64, bottom: 82, left: 64 },
      pitch: 48,
      maxZoom: 14,
      duration: reducedMotion ? 0 : 900,
    });
  }, [result, selected, routeData, reducedMotion]);

  useEffect(() => {
    const map = mapRef.current;
    if (map?.getLayer("roads-risk")) map.setPaintProperty("roads-risk", "line-opacity", showRisk ? 0.72 : 0);
  }, [showRisk]);

  useEffect(() => {
    const map = mapRef.current;
    if (!map?.isStyleLoaded()) return;
    markers.current.forEach((marker) => marker.remove());
    markers.current = [];
    const endpointData = [locations.find((item) => item.id === origin), locations.find((item) => item.id === destination)].filter(Boolean) as Location[];
    endpointData.forEach((item, index) => {
      const element = document.createElement("div");
      element.className = `mapbox-endpoint ${index ? "destination" : "origin"}`;
      element.textContent = index ? "B" : "A";
      markers.current.push(new mapboxgl.Marker({ element, anchor: "center" }).setLngLat([item.lon, item.lat]).setPopup(new mapboxgl.Popup({ offset: 18 }).setText(item.label)).addTo(map));
    });
    events.slice(0, 80).forEach((event) => {
      const element = document.createElement("button");
      element.className = `mapbox-hazard ${event.accessibility_status}`;
      element.type = "button";
      element.setAttribute("aria-label", `${event.kind}: ${event.accessibility_status}`);
      element.textContent = "!";
      markers.current.push(new mapboxgl.Marker({ element, anchor: "center" }).setLngLat([event.lon, event.lat]).setPopup(new mapboxgl.Popup({ offset: 16 }).setHTML(`<strong>${event.kind.replaceAll("_", " ")}</strong><br>${event.accessibility_status} · severity ${event.severity}`)).addTo(map));
    });
  }, [locations, origin, destination, events, network]);

  useEffect(() => {
    mapRef.current?.fitBounds(bounds as LngLatBoundsLike, { padding: 54, pitch: 54, duration: reducedMotion ? 0 : 850 });
  }, [reset, bounds, reducedMotion]);

  if (!token) return <div className="mapbox-status"><strong>Mapbox token missing</strong><span>Add VITE_MAPBOX_TOKEN to frontend/.env and restart the frontend.</span></div>;
  return <div className="mapbox-shell"><div ref={host} className="mapbox-surface" />{message && <div className="mapbox-status"><span>{message}</span></div>}<div className="mapbox-live-badge"><i /> LIVE OSM BASEMAP</div></div>;
}
