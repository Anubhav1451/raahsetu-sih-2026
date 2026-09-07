import { useEffect, useRef, useState } from 'react';
import L from 'leaflet';
import 'leaflet/dist/leaflet.css';
import type { Comparison, AccessibilityEvent } from './types';

const northeast: L.LatLngBoundsExpression = [[21.9, 87.9], [29.6, 97.5]];
export default function NortheastMap({ result, selected, events, reset, synthetic }: {
  result: Comparison | null; selected: string; events: AccessibilityEvent[]; reset: number; synthetic: boolean;
}) {
  const container = useRef<HTMLDivElement>(null);
  const map = useRef<L.Map | null>(null);
  const [tileError, setTileError] = useState(false);
  const [followRoute, setFollowRoute] = useState(false);
  useEffect(() => {
    if (!container.current) return;
    const reduced = matchMedia('(prefers-reduced-motion: reduce)').matches;
    const instance = L.map(container.current, {zoomControl: false, zoomAnimation: !reduced, fadeAnimation: !reduced}).fitBounds(northeast);
    map.current = instance;
    L.control.zoom({position: 'bottomleft'}).addTo(instance);
    L.tileLayer(import.meta.env.VITE_OSM_TILE_URL || 'https://tile.openstreetmap.org/{z}/{x}/{y}.png', {
      maxZoom: 19, keepBuffer: 0, attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap contributors</a>',
    }).on('tileerror', () => setTileError(true)).addTo(instance);
    const observer = new ResizeObserver(() => instance.invalidateSize());
    observer.observe(container.current);
    return () => { observer.disconnect(); instance.remove(); map.current = null; };
  }, []);
  useEffect(() => { map.current?.fitBounds(northeast, {animate: false}); setFollowRoute(false); }, [reset]);
  useEffect(() => {
    const instance = map.current;
    if (!instance) return;
    const group = L.featureGroup().addTo(instance);
    if (!synthetic) {
      result?.routes.filter(route => route.status === 'available').forEach(route => {
        const points = route.geometry.coordinates.map(([lon, lat]) => L.latLng(lat, lon));
        L.polyline(points, {color: route.id === 'risk_aware' ? '#176747' : '#765cb5', weight: selected === route.id ? 6 : 3, dashArray: route.id === 'fastest' ? '8 7' : undefined}).addTo(group);
        if (selected === route.id && points.length) {
          for (const [point, label] of [[points[0], 'A · Origin'], [points[points.length - 1], 'B · Destination']] as const) {
            L.circleMarker(point, {radius: 7, color: '#13291c', fillColor: '#b4edce', fillOpacity: 1}).bindTooltip(label, {permanent: true}).addTo(group);
          }
        }
      });
      events.forEach(event => {
        const label = document.createElement('span');
        label.textContent = `Reported accessibility: ${event.accessibility_status}`;
        L.circleMarker([event.lat, event.lon], {radius: 8, color: '#b84926'}).bindPopup(label).addTo(group);
      });
    }
    if (followRoute && group.getBounds().isValid()) instance.fitBounds(group.getBounds(), {padding: [55, 100], maxZoom: 14, animate: false});
    return () => { group.remove(); };
  }, [result, selected, events, synthetic, followRoute]);
  return <div className="ne-map-shell">
    <div ref={container} className="ne-basemap" aria-label="OpenStreetMap Northeast explorer" />
    <div className="ne-map-actions">
      <button className="button secondary" onClick={() => {setFollowRoute(false); map.current?.fitBounds(northeast, {animate: false});}}>All Northeast</button>
      <button className="button secondary" disabled={synthetic || !result?.routes.some(route => route.status === 'available')} onClick={() => setFollowRoute(true)}>Follow selected journey</button>
    </div>
    <p className="ne-map-note" role="status">{tileError ? 'Some map tiles unavailable. Check your connection.' : synthetic ? 'Explore Northeast. Select a real OSM network to show journey routes.' : 'Map coverage is continuous. Routing uses the selected state network.'}</p>
  </div>;
}
