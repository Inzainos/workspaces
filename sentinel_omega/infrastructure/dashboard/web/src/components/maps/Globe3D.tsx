import { useEffect, useRef, useState } from "react";
import {
  CONTINENTES,
  colorTipo,
  colorRiesgoSat,
  colorSismo,
  alfaSismo,
  infoNodo,
  infoSismo,
  LeyendaMapa,
  type LngLat,
  type NodoMapa,
  type SismoMapa,
} from "./shared";

type V3 = { x: number; y: number; z: number };

/** Canvas no entiende `var(--…)`: lee los tokens reales una vez por montaje. */
function leerVars(): Record<string, string> {
  const cs = getComputedStyle(document.documentElement);
  const v = (n: string, fb: string) => cs.getPropertyValue(n).trim() || fb;
  return {
    bg: v("--color-base-900", "#101014"),
    disco: v("--color-base-800", "#1a1a21"),
    tierra: v("--color-base-750", "#242429"),
    costa: v("--color-base-600", "#4a4a52"),
    graticula: v("--color-base-600", "#4a4a52"),
    texto: v("--color-base-100", "#e8e8ea"),
    sinLectura: v("--color-base-500", "#77777f"),
    serie1: v("--color-serie-1", "#6a86c8"),
    serie2: v("--color-serie-2", "#4fa8a0"),
    calma: v("--color-calma", "#4fbf8f"),
    atencion: v("--color-atencion", "#d9b84f"),
    aviso: v("--color-aviso", "#e8934f"),
    critico: v("--color-critico", "#e85d4f"),
  };
}

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

/**
 * Globo 3D (canvas, proyección ortográfica).
 *
 * Hasta el 2026-09-28 el caption prometía que "el tamaño y color de cada nodo
 * reflejan su saturación" y el componente ignoraba `sat`/`medido` por completo:
 * dibujaba 9 pesos fijos por tipo. Ahora es cierto: el radio crece con la
 * saturación, el aro va en la rampa de riesgo y un nodo sin lectura se dibuja
 * hueco y neutro.
 */
export function Globe3D({
  nodes,
  quakes,
  focus,
}: {
  nodes: NodoMapa[];
  quakes?: SismoMapa[];
  /** label del nodo a resaltar (hover en el ranking de tensión) */
  focus?: string | null;
}) {
  const ref = useRef<HTMLCanvasElement>(null);
  const wrapRef = useRef<HTMLDivElement>(null);
  const [noCv, setNoCv] = useState(false);
  const [tip, setTip] = useState<{ x: number; y: number; text: string } | null>(null);
  const tipRef = useRef<{ x: number; y: number; text: string } | null>(null);
  const rot = useRef({ lon: 20, lat: 10 });
  const dragging = useRef(false);
  const idleDesde = useRef(0); // 0 = interactuando; Date.now() = libre desde…

  useEffect(() => {
    const c = ref.current;
    const wrap = wrapRef.current;
    if (!c || !wrap) {
      setNoCv(true);
      return;
    }
    const ctx = c.getContext("2d");
    if (!ctx) {
      setNoCv(true);
      return;
    }

    const vars = leerVars();
    const reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

    let w = 720;
    let h = 380;
    const ajustar = () => {
      const dpr = Math.min(2.5, window.devicePixelRatio || 1);
      const cw = wrap.clientWidth || 720;
      const ch = Math.round(cw * (380 / 720));
      c.width = Math.round(cw * dpr);
      c.height = Math.round(ch * dpr);
      c.style.height = `${ch}px`;
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
      w = cw;
      h = ch;
    };
    ajustar();
    const ro = new ResizeObserver(ajustar);
    ro.observe(wrap);

    const R = () => Math.min(w, h) * 0.42;
    const proy = (lat: number, lon: number) =>
      rotateAndProject(lat, lon, rot.current.lon, rot.current.lat, w, h, R());

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
      ctx.fillStyle = vars.bg;
      ctx.fillRect(0, 0, w, h);

      // Disco con sombreado sutil para dar volumen (no es dato)
      const g = ctx.createRadialGradient(w / 2 - R() * 0.35, h / 2 - R() * 0.35, R() * 0.2, w / 2, h / 2, R());
      g.addColorStop(0, vars.tierra);
      g.addColorStop(1, vars.disco);
      ctx.beginPath();
      ctx.arc(w / 2, h / 2, R(), 0, Math.PI * 2);
      ctx.fillStyle = g;
      ctx.fill();
      ctx.strokeStyle = vars.serie1;
      ctx.globalAlpha = 0.35;
      ctx.lineWidth = 1.2;
      ctx.stroke();
      ctx.globalAlpha = 1;

      // Graticule
      for (const lat of [-60, -30, 0, 30, 60]) {
        const pts: V3[] = [];
        for (let lon = -180; lon <= 180; lon += 8) pts.push(proy(lat, lon));
        drawPolyline(pts, vars.graticula, 0.8, lat === 0 ? 0.28 : 0.18);
      }
      for (const lon of [-150, -120, -90, -60, -30, 0, 30, 60, 90, 120, 150]) {
        const pts: V3[] = [];
        for (let lat = -80; lat <= 80; lat += 6) pts.push(proy(lat, lon));
        drawPolyline(pts, vars.graticula, 0.7, 0.14);
      }

      // Continentes
      for (const poly of CONTINENTES as LngLat[][]) {
        const pts = poly.map(([lon, lat]) => proy(lat, lon));
        const visible = pts.filter((p) => p.z >= 0);
        if (visible.length < 3) continue;
        ctx.beginPath();
        ctx.moveTo(visible[0].x, visible[0].y);
        for (let i = 1; i < visible.length; i += 1) ctx.lineTo(visible[i].x, visible[i].y);
        ctx.closePath();
        ctx.fillStyle = vars.tierra;
        ctx.globalAlpha = 0.75;
        ctx.fill();
        ctx.globalAlpha = 1;
        ctx.strokeStyle = vars.costa;
        ctx.lineWidth = 0.7;
        ctx.stroke();
      }

      // Sismos (debajo de los nodos)
      for (const q of quakes || []) {
        const p = proy(q.lat, q.lon);
        if (p.z < 0) continue;
        const mag = q.mag ?? 4.5;
        const alfa = alfaSismo(q.ts);
        ctx.strokeStyle = mag >= 6 ? vars.critico : mag >= 5 ? vars.aviso : vars.atencion;
        ctx.globalAlpha = alfa;
        ctx.lineWidth = 1.1;
        ctx.beginPath();
        ctx.arc(p.x, p.y, 2 + Math.max(0, mag - 4.5), 0, Math.PI * 2);
        ctx.stroke();
        ctx.globalAlpha = 1;
      }

      // Nodos — aquí vive la corrección: sat manda en radio y aro
      for (const n of nodes) {
        const p = proy(n.lat, n.lon);
        if (p.z < 0) continue;
        const sat = typeof n.sat === "number" ? n.sat : 0;
        const cargado = sat > 0 && n.medido !== false;
        const r = n.medido === false ? 1.5 : cargado ? 1.7 + Math.min(1, sat) * 3.2 : 1.7;

        if (n.medido === false) {
          ctx.strokeStyle = vars.sinLectura;
          ctx.lineWidth = 1;
          ctx.beginPath();
          ctx.arc(p.x, p.y, r, 0, Math.PI * 2);
          ctx.stroke();
        } else {
          if (cargado) {
            ctx.strokeStyle = colorRiesgoSatCanvas(sat, vars);
            ctx.globalAlpha = 0.85;
            ctx.lineWidth = 1.2;
            ctx.beginPath();
            ctx.arc(p.x, p.y, r + 1.6, 0, Math.PI * 2);
            ctx.stroke();
            ctx.globalAlpha = 1;
          }
          ctx.fillStyle = n.highlight ? vars.texto : colorTipoVar(vars, n.tipo);
          ctx.beginPath();
          ctx.arc(p.x, p.y, r, 0, Math.PI * 2);
          ctx.fill();
        }

        if (focus && n.label === focus) {
          ctx.strokeStyle = vars.texto;
          ctx.setLineDash([2, 2]);
          ctx.lineWidth = 1;
          ctx.beginPath();
          ctx.arc(p.x, p.y, r + 4.5, 0, Math.PI * 2);
          ctx.stroke();
          ctx.setLineDash([]);
        }
      }

      // Etiqueta de Tlaxcala
      const tlax = nodes.find((n) => n.highlight);
      if (tlax) {
        const p = proy(tlax.lat, tlax.lon);
        if (p.z >= 0) {
          ctx.fillStyle = vars.texto;
          ctx.font = "9px IBM Plex Mono, monospace";
          ctx.fillText("Tlaxcala", p.x + 6, p.y - 5);
        }
      }
    };

    // ── Interacción ────────────────────────────────────────────────────────
    let last = { x: 0, y: 0 };
    const onDown = (e: PointerEvent) => {
      dragging.current = true;
      idleDesde.current = 0;
      const rect = c.getBoundingClientRect();
      last = { x: e.clientX - rect.left, y: e.clientY - rect.top };
      c.setPointerCapture(e.pointerId);
    };
    const onMove = (e: PointerEvent) => {
      const rect = c.getBoundingClientRect();
      const mx = e.clientX - rect.left;
      const my = e.clientY - rect.top;
      if (dragging.current) {
        rot.current.lon += (mx - last.x) * 0.4;
        rot.current.lat = Math.max(-60, Math.min(60, rot.current.lat + (my - last.y) * 0.2));
        last = { x: mx, y: my };
        setTip(null);
        draw();
        return;
      }
      // Hover: hit-test contra nodos visibles (y sismos)
      let mejor: { d: number; x: number; y: number; text: string } | null = null;
      for (const n of nodes) {
        const p = proy(n.lat, n.lon);
        if (p.z < 0) continue;
        const d = Math.hypot(p.x - mx, p.y - my);
        if (d < 12 && (!mejor || d < mejor.d)) mejor = { d, x: p.x, y: p.y, text: infoNodo(n) };
      }
      for (const q of quakes || []) {
        const p = proy(q.lat, q.lon);
        if (p.z < 0) continue;
        const d = Math.hypot(p.x - mx, p.y - my);
        if (d < 12 && (!mejor || d < mejor.d)) mejor = { d, x: p.x, y: p.y, text: infoSismo(q) };
      }
      setTip(mejor ? { x: mejor.x, y: mejor.y, text: mejor.text } : null);
      idleDesde.current = mejor ? 0 : idleDesde.current || Date.now();
    };
    const onUp = (e: PointerEvent) => {
      dragging.current = false;
      idleDesde.current = Date.now();
      c.releasePointerCapture(e.pointerId);
    };
    const onLeave = () => {
      setTip(null);
      if (!dragging.current) idleDesde.current = Date.now();
    };

    c.addEventListener("pointerdown", onDown);
    c.addEventListener("pointermove", onMove);
    c.addEventListener("pointerup", onUp);
    c.addEventListener("pointerleave", onLeave);

    // ── Bucle: auto-rotación en reposo, respetando reduced-motion ──────────
    let raf = 0;
    const libre = () => idleDesde.current > 0 && Date.now() - idleDesde.current > 2500;
    if (reduceMotion) {
      draw();
    } else {
      idleDesde.current = Date.now();
      const loop = () => {
        if (!dragging.current && !tipRef.current) rot.current.lon += 0.025;
        draw();
        raf = requestAnimationFrame(loop);
      };
      raf = requestAnimationFrame(loop);
    }

    return () => {
      cancelAnimationFrame(raf);
      ro.disconnect();
      c.removeEventListener("pointerdown", onDown);
      c.removeEventListener("pointermove", onMove);
      c.removeEventListener("pointerup", onUp);
      c.removeEventListener("pointerleave", onLeave);
    };
  }, [nodes, quakes, focus]);

  tipRef.current = tip;

  if (noCv) {
    return (
      <div className="rounded-lg border border-dashed border-border p-6 text-sm text-muted">
        Canvas no disponible. Use el mapa 2D.
      </div>
    );
  }

  return (
    <div className="space-y-2">
      <div ref={wrapRef} className="relative">
        <canvas
          ref={ref}
          className="w-full touch-none rounded-lg border border-border"
          style={{ aspectRatio: "720 / 380" }}
        />
        {tip && (
          <div
            className="mono pointer-events-none absolute z-10 max-w-64 rounded border border-base-700 bg-base-850 px-2 py-1 text-meta text-base-100 shadow"
            style={{
              left: `${Math.min(tip.x + 12, (wrapRef.current?.clientWidth ?? 720) - 180)}px`,
              top: `${Math.max(4, tip.y - 34)}px`,
            }}
          >
            {tip.text}
          </div>
        )}
      </div>
      <LeyendaMapa />
      <p className="text-meta text-muted">
        Globo 3D: el radio y el aro de cada nodo crecen con su saturación acumulada (tope 1.0); un nodo sin
        lectura se dibuja hueco y neutro. Arrastra para rotar
        {typeof window !== "undefined" && !window.matchMedia("(prefers-reduced-motion: reduce)").matches
          ? "; rota solo en reposo"
          : ""}
        .
      </p>
    </div>
  );
}

/** colorRiesgoSat, resuelto a color concreto para canvas (sin `var()`). */
function colorRiesgoSatCanvas(sat: number, vars: Record<string, string>): string {
  if (sat >= 0.8) return vars.aviso;
  if (sat >= 0.6) return vars.atencion;
  return vars.calma;
}

/** colorTipo, pero resuelto a color concreto para canvas (sin `var()`). */
function colorTipoVar(vars: Record<string, string>, tipo?: string): string {
  const t = (tipo || "real").toLowerCase();
  if (t.includes("ghost") || t.includes("fantasma")) return vars.sinLectura;
  if (t.includes("geo")) return vars.serie2;
  return vars.serie1;
}
