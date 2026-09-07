import { Component, useEffect, useMemo, useRef, type ReactNode } from "react";
import { Canvas, useFrame, useThree } from "@react-three/fiber";
import { Html, Line, OrbitControls } from "@react-three/drei";
import * as THREE from "three";
import type {
  Comparison,
  Coordinates,
  ElevationGrid,
  AccessibilityEvent,
  Location,
  Network,
} from "./types";

type Point = [number, number, number];
type Props = {
  network: Network;
  locations: Location[];
  result: Comparison | null;
  origin: string;
  destination: string;
  closedIds: string[];
  mode: "3d" | "flat";
  reset: number;
  showRisk: boolean;
  selected: string;
  terrain: ElevationGrid | null;
  events: AccessibilityEvent[];
};

function FallbackMap({ network, result, origin, destination, events }: Props) {
  let west = Infinity,
    east = -Infinity,
    south = Infinity,
    north = -Infinity;
  for (const feature of network.features) {
    for (const [lon, lat] of feature.geometry.coordinates) {
      west = Math.min(west, lon);
      east = Math.max(east, lon);
      south = Math.min(south, lat);
      north = Math.max(north, lat);
    }
  }
  const project = ([lon, lat]: Coordinates) => {
    const x = 5 + ((lon - west) / Math.max(east - west, 0.0001)) * 90;
    const y = 95 - ((lat - south) / Math.max(north - south, 0.0001)) * 90;
    return `${x},${y}`;
  };
  const roads = network.features.slice(0, 1800);
  const routeLines = result?.routes.filter((r) => r.status === "available") ?? [];
  const locationFor = (id: string) => {
    const feature = network.features.find((f) => f.properties.u === id || f.properties.v === id);
    return feature?.geometry.coordinates[0];
  };
  return (
    <div className="map-fallback fallback-map">
      <svg viewBox="0 0 100 100" role="img" aria-label="OSM route map fallback">
        <rect width="100" height="100" fill="#102229" />
        {roads.map((feature) => (
          <polyline
            key={feature.properties.id}
            points={feature.geometry.coordinates.map(project).join(" ")}
            className={feature.properties.risk >= 0.45 ? "fallback-road risk" : "fallback-road"}
          />
        ))}
        {routeLines.map((route) => (
          <polyline
            key={route.id}
            points={route.geometry.coordinates.map(project).join(" ")}
            className={`fallback-route ${route.id}`}
          />
        ))}
        {[{ id: origin, label: "A" }, { id: destination, label: "B" }].map((item) => {
          const point = locationFor(item.id);
          if (!point) return null;
          const [x, y] = project(point).split(",").map(Number);
          return <g key={item.id}><circle cx={x} cy={y} r="2.2" className="fallback-marker" /><text x={x + 3} y={y - 3} className="fallback-label">{item.label}</text></g>;
        })}
        {events.map((event) => {
          const [x, y] = project([event.lon, event.lat]).split(",").map(Number);
          return <g key={event.id}><circle cx={x} cy={y} r="2.6" className={`incident-marker ${event.accessibility_status}`} /><text x={x + 3} y={y + 3} className="incident-label">!</text></g>;
        })}
      </svg>
      <div className="fallback-caption"><strong>OSM road network</strong><span>WebGL fallback · route geometry and risk layer remain live</span></div>
    </div>
  );
}

function height(x: number, z: number): number {
  const hill = (cx: number, cz: number, spread: number, peak: number) =>
    peak * Math.exp(-((x - cx) ** 2 + (z - cz) ** 2) / spread);
  return (
    1.5 +
    hill(-43, -32, 700, 13) +
    hill(46, -27, 570, 18) +
    hill(52, 34, 420, 8) +
    Math.sin(x * 0.085) * Math.cos(z * 0.07) * 1.5
  );
}

function Ground({ heightAt }: { heightAt: (x: number, z: number) => number }) {
  const geometry = useMemo(() => {
    const geo = new THREE.PlaneGeometry(180, 132, 100, 76);
    geo.rotateX(-Math.PI / 2);
    const vertices = geo.attributes.position;
    const colors = [];
    const low = new THREE.Color("#173735");
    const high = new THREE.Color("#3c5750");
    for (let i = 0; i < vertices.count; i++) {
      const h = heightAt(vertices.getX(i), vertices.getZ(i));
      vertices.setY(i, h);
      const color = low.clone().lerp(high, Math.min(1, h / 22));
      colors.push(color.r, color.g, color.b);
    }
    geo.setAttribute("color", new THREE.Float32BufferAttribute(colors, 3));
    geo.computeVertexNormals();
    return geo;
  }, [heightAt]);
  useEffect(() => () => geometry.dispose(), [geometry]);
  return (
    <group>
      <mesh geometry={geometry}>
        <meshStandardMaterial vertexColors roughness={1} metalness={0} />
      </mesh>
      <mesh geometry={geometry} position={[0, 0.045, 0]}>
        <meshBasicMaterial
          color="#74998b"
          wireframe
          transparent
          opacity={0.055}
        />
      </mesh>
      <gridHelper
        args={[200, 25, "#284044", "#192f34"]}
        position={[0, -0.6, 0]}
      />
    </group>
  );
}

function CameraRig({ mode, reset }: Pick<Props, "mode" | "reset">) {
  const { camera } = useThree();
  useEffect(() => {
    camera.position.set(
      0,
      mode === "flat" ? 155 : 101,
      mode === "flat" ? 0.01 : 95,
    );
    camera.lookAt(0, 0, 0);
    camera.updateProjectionMatrix();
  }, [camera, mode, reset]);
  return (
    <OrbitControls
      key={`${mode}-${reset}`}
      makeDefault
      target={[0, 0, 0]}
      minDistance={30}
      maxDistance={220}
      maxPolarAngle={Math.PI / 2.25}
      enableRotate={mode === "3d"}
      enableDamping
      dampingFactor={0.08}
    />
  );
}

function SceneMotion() {
  const beacon = useRef<THREE.Group>(null);
  useFrame(({ clock }) => {
    if (!beacon.current) return;
    if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) return;
    const t = clock.getElapsedTime();
    beacon.current.rotation.y = t * 0.08;
    beacon.current.position.y = Math.sin(t * 0.7) * 0.18;
  });
  return (
    <group ref={beacon} position={[-62, 2.2, -45]}>
      <mesh rotation={[-Math.PI / 2, 0, 0]}>
        <ringGeometry args={[1.4, 1.55, 32]} />
        <meshBasicMaterial color="#8af4cb" transparent opacity={0.34} />
      </mesh>
      <mesh position={[0, 0.45, 0]}>
        <icosahedronGeometry args={[0.22, 1]} />
        <meshBasicMaterial color="#8af4cb" />
      </mesh>
    </group>
  );
}

function MapScene(props: Props) {
  const {
    network,
    locations,
    result,
    origin,
    destination,
    closedIds,
    mode,
    reset,
    showRisk,
    selected,
    terrain,
  } = props;
  const { project, heightAt } = useMemo(() => {
    const coords = network.features.flatMap((f) => f.geometry.coordinates);
    let west = Infinity,
      east = -Infinity,
      south = Infinity,
      north = -Infinity;
    for (const [lon, lat] of coords) {
      west = Math.min(west, lon);
      east = Math.max(east, lon);
      south = Math.min(south, lat);
      north = Math.max(north, lat);
    }
    const cos = Math.cos((((south + north) / 2) * Math.PI) / 180);
    const scale = Math.min(
      120 / ((east - west) * cos || 1),
      78 / (north - south || 1),
    );
    const heightAt = (x: number, z: number) => {
      if (!terrain) return height(x, z);
      const lon = x / (cos * scale) + (west + east) / 2;
      const lat = -z / scale + (south + north) / 2;
      const fy = Math.max(
        0,
        Math.min(
          terrain.rows - 1,
          ((terrain.north - lat) / (terrain.north - terrain.south)) *
            (terrain.rows - 1),
        ),
      );
      const fx = Math.max(
        0,
        Math.min(
          terrain.cols - 1,
          ((lon - terrain.west) / (terrain.east - terrain.west)) *
            (terrain.cols - 1),
        ),
      );
      const y = Math.floor(fy),
        x0 = Math.floor(fx),
        y1 = Math.min(y + 1, terrain.rows - 1),
        x1 = Math.min(x0 + 1, terrain.cols - 1);
      const a = terrain.values[y][x0] ?? 0,
        b = terrain.values[y][x1] ?? a;
      const c = terrain.values[y1][x0] ?? a,
        d = terrain.values[y1][x1] ?? a;
      const elevation =
        (a * (1 - (fx - x0)) + b * (fx - x0)) * (1 - (fy - y)) +
        (c * (1 - (fx - x0)) + d * (fx - x0)) * (fy - y);
      return ((elevation * scale) / 111320) * terrain.vertical_exaggeration;
    };
    const project = ([lon, lat]: Coordinates, lift = 0.6): Point => {
      const x = (lon - (west + east) / 2) * cos * scale;
      const z = -(lat - (south + north) / 2) * scale;
      return [x, heightAt(x, z) + lift, z];
    };
    return { project, heightAt };
  }, [network, terrain]);
  const densify = (coordinates: Coordinates[], lift = 0.65): Point[] => {
    const points: Point[] = [];
    for (let i = 0; i < coordinates.length - 1; i++) {
      const a = coordinates[i],
        b = coordinates[i + 1];
      for (let j = 0; j < 6; j++) {
        const t = j / 6;
        points.push(
          project([a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t], lift),
        );
      }
    }
    points.push(project(coordinates[coordinates.length - 1], lift));
    return points;
  };
  const roadGeometry = useMemo(() => {
    const positions: number[] = [],
      colors: number[] = [];
    for (const feature of network.features) {
      const risk = feature.properties.risk;
      const closed =
        feature.properties.closed || closedIds.includes(feature.properties.id);
      const color = new THREE.Color(
        closed ? "#fa8177" : showRisk && risk >= 0.45 ? "#e7a65f" : "#557a77",
      );
      const points = densify(feature.geometry.coordinates);
      for (let i = 0; i < points.length - 1; i++) {
        positions.push(...points[i], ...points[i + 1]);
        colors.push(color.r, color.g, color.b, color.r, color.g, color.b);
      }
    }
    const geometry = new THREE.BufferGeometry();
    geometry.setAttribute(
      "position",
      new THREE.Float32BufferAttribute(positions, 3),
    );
    geometry.setAttribute("color", new THREE.Float32BufferAttribute(colors, 3));
    return geometry;
    // Projection changes only with the network; densification is deterministic.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [network, project, showRisk, closedIds]);
  useEffect(() => () => roadGeometry.dispose(), [roadGeometry]);
  const hazards = network.features.filter(
    (f) => f.properties.risk >= 0.45 && f.properties.u < f.properties.v,
  );
  return (
    <>
      <color attach="background" args={["#102229"]} />
      <fog attach="fog" args={["#102229", 160, 330]} />
      <ambientLight intensity={1.5} />
      <directionalLight
        position={[-40, 90, 20]}
        intensity={2}
        color="#ddf9eb"
      />
      <Ground heightAt={heightAt} />
      <SceneMotion />
      <lineSegments geometry={roadGeometry}>
        <lineBasicMaterial vertexColors transparent opacity={0.85} />
      </lineSegments>
      {result?.routes.map(
        (route) =>
          route.status === "available" &&
          route.edge_ids.length > 0 && (
            <Line
              key={route.id}
              points={densify(
                route.geometry.coordinates,
                route.id === "risk_aware" ? 1.3 : 1.05,
              )}
              color={route.id === "risk_aware" ? "#8af4cb" : "#b7bcc7"}
              lineWidth={selected === route.id ? 4 : 2.4}
              transparent
              opacity={selected === route.id ? 1 : 0.58}
              dashed={route.id === "fastest"}
              dashSize={1}
              gapSize={0.6}
            />
          ),
      )}
      {showRisk &&
        hazards.slice(0, 18).map((f) => {
          const point =
            f.geometry.coordinates[
              Math.floor(f.geometry.coordinates.length / 2)
            ];
          return (
            <group key={f.properties.id} position={project(point, 1.2)}>
              <mesh rotation={[-Math.PI / 2, 0, 0]}>
                <ringGeometry args={[1.1, 1.6, 32]} />
                <meshBasicMaterial
                  color="#ffb56d"
                  transparent
                  opacity={0.9}
                  side={THREE.DoubleSide}
                />
              </mesh>
              <mesh position={[0, 1.2, 0]}>
                <octahedronGeometry args={[0.65]} />
                <meshBasicMaterial color="#ffb56d" />
              </mesh>
            </group>
          );
        })}
      {locations.map((location) => {
        const endpoint = location.id === origin || location.id === destination;
        return (
          <group
            key={location.id}
            position={project([location.lon, location.lat], 1)}
          >
            <mesh>
              <sphereGeometry args={[endpoint ? 0.85 : 0.35, 12, 12]} />
              <meshBasicMaterial color={endpoint ? "#c8ffe9" : "#769c93"} />
            </mesh>
            {endpoint && (
              <>
                <mesh rotation={[-Math.PI / 2, 0, 0]}>
                  <ringGeometry args={[1.3, 1.55, 32]} />
                  <meshBasicMaterial color="#8af4cb" side={THREE.DoubleSide} />
                </mesh>
                <Html
                  position={[0, 3, 0]}
                  center
                  zIndexRange={[15, 0]}
                  style={{ pointerEvents: "none" }}
                >
                  <div className="map-pin">
                    <b>{location.id === origin ? "A" : "B"}</b>
                    <span>{location.label}</span>
                  </div>
                </Html>
              </>
            )}
          </group>
        );
      })}
      <CameraRig mode={mode} reset={reset} />
    </>
  );
}

class MapBoundary extends Component<
  Props & { children: ReactNode },
  { failed: boolean }
> {
  state = { failed: false };
  static getDerivedStateFromError() {
    return { failed: true };
  }
  render() {
    return this.state.failed ? (
      <FallbackMap {...this.props} />
    ) : (
      this.props.children
    );
  }
}

export default function TerrainMap(props: Props) {
  return (
    <MapBoundary {...props}>
      <Canvas
        camera={{ position: [0, 101, 95], fov: 48, near: 0.1, far: 500 }}
        dpr={[1, 1.7]}
        frameloop="always"
        performance={{ min: 0.55, max: 1, debounce: 120 }}
        gl={{ antialias: true, alpha: false }}
        fallback={
          <FallbackMap {...props} />
        }
      >
        <MapScene {...props} />
      </Canvas>
    </MapBoundary>
  );
}
