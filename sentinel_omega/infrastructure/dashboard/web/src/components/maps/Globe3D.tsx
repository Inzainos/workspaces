import { useEffect, useRef, useState } from "react";

type Pt = { lat: number; lon: number; tipo?: string; mag?: number; highlight?: boolean };
type LngLat = [number, number];
type V3 = { x: number; y: number; z: number };

const TIPO: Record<string, string> = { real: "#5e6ad2", ghost: "#8a8f98", geobattery: "#ffc107" };
const CONTINENTS: LngLat[][] = [
  [[-168, 72], [-145, 70], [-128, 61], [-124, 48], [-118, 33], [-110, 27], [-98, 20], [-84, 22], [-76, 30], [-69, 45], [-82, 58], [-102, 70], [-130, 73]],
  [[-81, 12], [-74, 5], [-70, -10], [-66, -20], [-60, -32], [-54, -44], [-48, -53], [-40, -50], [-36, -33], [-43, -15], [-52, 0], [-66, 8]],
  [[-10, 72], [20, 72], [50, 65], [85, 60], [118, 54], [136, 48], [150, 38], [136, 30], [110, 22], [88, 18], [75, 8], [60, 8], [44, 16], [32, 31], [17, 35], [3, 45], [-8, 56]],
  [[-17, 37], [6, 35], [24, 30], [33, 19], [40, 7], [44, -12], [38, -28], [28, -35], [15, -35], [3, -23], [-5, -6], [-10, 10]],
  [[112, -11], [122, -18], [134, -24], [146, -30], [153, -37], [146, -44], [130, -42], [118, -33], [112, -22]],
  [[-54, 82], [-38, 78], [-30, 72], [-42, 65], [-56, 68], [-62, 75]],
];

function rotateAndProject(lat: number, lon: number, rotLon: number, rotLat: number, w: number, h: number, R: number): V3 {
  const lon2 = ((lon + rotLon + 540) % 360) - 180;
  const lat2 = Math.max(-85, Math.min(85, lat + rotLat));
  const phi = (lat2 * Math.PI) / 180;
  const lam = (lon2 * Math.PI) / 180;
  const x = R * Math.cos(phi) * Math.sin(lam);
  const y = -R * Math.sin(phi);
  const z = Math.cos(phi) * Math.cos(lam);
  return { x: w / 2 + x, y: h / 2 + y, z };
}

export function Globe3D({ nodes, quakes }: { nodes: Pt[]; quakes?: Pt[] }) {
  const ref = useRef<HTMLCanvasElement>(null);
  const [noCv, setNoCv] = useState(false);
  const rot = useRef({ lon: 20, lat: 10 });

  useEffect(() => {
    const c = ref.current;
    if (!c) {
      setNoCv(true);
      return;
    }
    const ctx = c.getContext("2d");
    if (!ctx) {
      setNoCv(true);
      return;
    }

    const w = c.width;
    const h = c.height;
    const R = Math.min(w, h) * 0.42;

    const drawPolyline = (pts: V3[], stroke: string, width = 1, alpha = 1) => {
      let started = false;
      ctx.save();
      ctx.strokeStyle = stroke;
      ctx.globalAlpha = alpha;
      ctx.lineWidth = width;
      ctx.beginPath();
      for (const p of pts) {
        if (p.z < 0) {
          started = false;
          continue;
        }
        if (!started) {
          ctx.moveTo(p.x, p.y);
          started = true;
        } else {
          ctx.lineTo(p.x, p.y);
        }
      }
      ctx.stroke();
      ctx.restore();
    };

    const draw = () => {
      ctx.fillStyle = "#08090a";
      ctx.fillRect(0, 0, w, h);

      // Disco del planeta
      ctx.beginPath();
      ctx.arc(w / 2, h / 2, R, 0, Math.PI * 2);
      ctx.fillStyle = "#0b0c0d";
      ctx.fill();
      ctx.strokeStyle = "rgba(94,106,210,0.45)";
      ctx.lineWidth = 1.2;
      ctx.stroke();

      // Graticula (lat/lon) para dar referencia de mapamundi
      for (const lat of [-60, -30, 0, 30, 60]) {
        const pts: V3[] = [];
        for (let lon = -180; lon <= 180; lon += 8) {
          pts.push(rotateAndProject(lat, lon, rot.current.lon, rot.current.lat, w, h, R));
        }
        drawPolyline(pts, "rgba(148,163,184,0.22)", 0.8);
      }
      for (const lon of [-150, -120, -90, -60, -30, 0, 30, 60, 90, 120, 150]) {
        const pts: V3[] = [];
        for (let lat = -80; lat <= 80; lat += 6) {
          pts.push(rotateAndProject(lat, lon, rot.current.lon, rot.current.lat, w, h, R));
        }
        drawPolyline(pts, "rgba(148,163,184,0.18)", 0.7);
      }

      // Continentes simplificados
      for (const poly of CONTINENTS) {
        const pts = poly.map(([lon, lat]) => rotateAndProject(lat, lon, rot.current.lon, rot.current.lat, w, h, R));
        const visible = pts.filter((p) => p.z >= 0);
        if (visible.length < 3) continue;
        ctx.beginPath();
        ctx.moveTo(visible[0].x, visible[0].y);
        for (let i = 1; i < visible.length; i += 1) ctx.lineTo(visible[i].x, visible[i].y);
        ctx.closePath();
        ctx.fillStyle = "rgba(94,106,210,0.16)";
        ctx.fill();
        ctx.strokeStyle = "rgba(148,163,184,0.26)";
        ctx.lineWidth = 0.8;
        ctx.stroke();
      }

      for (const p of nodes) {
        const q = rotateAndProject(p.lat, p.lon, rot.current.lon, rot.current.lat, w, h, R);
        if (q.z < 0) continue;
        ctx.fillStyle = p.highlight ? "#ffffff" : TIPO[p.tipo || "real"] || "#5e6ad2";
        ctx.beginPath();
        ctx.arc(q.x, q.y, p.highlight ? 3.2 : 1.7, 0, Math.PI * 2);
        ctx.fill();
      }

      for (const p of quakes || []) {
        const q = rotateAndProject(p.lat, p.lon, rot.current.lon, rot.current.lat, w, h, R);
        if (q.z < 0) continue;
        ctx.strokeStyle = "#ff1744";
        ctx.lineWidth = 1;
        ctx.beginPath();
        ctx.arc(q.x, q.y, 2 + Math.max(0, (p.mag || 4.5) - 4), 0, Math.PI * 2);
        ctx.stroke();
      }
    };

    draw();

    let dragging = false;
    let last = { x: 0, y: 0 };
    const onDown = (e: PointerEvent) => {
      dragging = true;
      last = { x: e.clientX, y: e.clientY };
    };
    const onMove = (e: PointerEvent) => {
      if (!dragging) return;
      rot.current.lon += (e.clientX - last.x) * 0.4;
      rot.current.lat = Math.max(-60, Math.min(60, rot.current.lat + (e.clientY - last.y) * 0.2));
      last = { x: e.clientX, y: e.clientY };
      draw();
    };
    const onUp = () => {
      dragging = false;
    };

    c.addEventListener("pointerdown", onDown);
    window.addEventListener("pointermove", onMove);
    window.addEventListener("pointerup", onUp);
    return () => {
      c.removeEventListener("pointerdown", onDown);
      window.removeEventListener("pointermove", onMove);
      window.removeEventListener("pointerup", onUp);
    };
  }, [nodes, quakes]);

  if (noCv) {
    return <div className="rounded-lg border border-dashed border-border p-6 text-sm text-muted">Canvas no disponible. Use el mapa 2D.</div>;
  }

  return (
    <div className="space-y-2">
      <canvas ref={ref} width={720} height={380} className="w-full rounded-lg border border-border bg-[#08090a]" />
      <p className="text-xs text-muted">Globo 3D canvas con graticula + continentes (aproximados). Arrastra para rotar.</p>
    </div>
  );
}
