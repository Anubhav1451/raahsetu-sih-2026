import type { City } from "./routeData";

export function roadEndpoints(origin: City, destination: City) {
  return {
    dataset_id: "osm-ner-roads",
    origin: { lon: origin.lon, lat: origin.lat },
    destination: { lon: destination.lon, lat: destination.lat },
  };
}
