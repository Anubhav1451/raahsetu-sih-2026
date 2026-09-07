# Continuous Northeast basemap

The dashboard opens in 3D terrain mode. The optional Explore NE view uses Leaflet with viewport-requested OpenStreetMap tiles. All Northeast fits when that view opens; users can pan/zoom and follow the selected real journey. Risk-A* stays server-side. Synthetic routes are excluded from the real basemap. Existing state search selects journey endpoints; cross-state routing is not introduced by this map change.

Attribution is visible above the map footer. Browser HTTP caching is used; no tile prefetch or offline download is implemented. The OSM tile URL can be configured with VITE_OSM_TILE_URL. Community tiles are best-effort, not a guaranteed production service. See https://operations.osmfoundation.org/policies/tiles/.

Browser automation blocks community tile requests and exercises real journey overlays and overview controls; it does not validate provider availability. Production build is checked separately.
