const BASE = import.meta.env.VITE_API_BASE ?? "";

async function getJson<T>(path: string): Promise<T> {
  const res = await fetch(`${BASE}${path}`);
  if (!res.ok) {
    const text = await res.text();
    throw new Error(`${res.status} ${path}: ${text}`);
  }
  return res.json() as Promise<T>;
}

async function postJson<T>(path: string, body: unknown): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(`${res.status} ${path}: ${text}`);
  }
  return res.json() as Promise<T>;
}

export type Overview = {
  ts: number;
  fantasma: {
    value: number | null;
    nivel_riesgo: string | null;
    schumann_hz: number | null;
    kp: number | null;
    bz_nT: number | null;
    viento_km_s: number | null;
  };
  muro: {
    walls_active: number | null;
    muro_breach: boolean;
    correlation_score: number | null;
    risk_label: string | null;
  };
  ciclo: Record<string, unknown> | null;
  counts: {
    nodos: number;
    sismos_m45: number;
    detecciones_latest: boolean;
  };
  risk_distribution: Record<string, number>;
  cycle_alert_rate: Record<string, unknown>;
  health?: {
    last_cycle_ts: number | null;
    stale: boolean;
    stale_seconds: number;
  };
};

export type ApiHealthEntry = {
  /** LIVE | STALE | LOCF_ACTIVE | CONGELADO | DESCONOCIDO.
   *  CONGELADO = la fuente se refresca pero repite el mismo valor (Tomsk
   *  sirviendo una imagen estática). Frescura no es validez. */
  status: string;
  age_h: number | null;
  last_data_ts?: number;
  updated_at?: string;
  /** Solo en fuentes con serie: cuántos valores distintos en la ventana. */
  valores_distintos?: number;
  muestras?: number;
  nota?: string;
};
export type ApiHealth = Record<string, ApiHealthEntry>;

export type Health = {
  status: string;
  db_path: string;
  db_exists: boolean;
  db_readable?: boolean;
  stale: boolean;
  /** Antigüedad REAL del último ciclo. No confundir con stale_seconds,
   *  que es el umbral a partir del cual se considera parado. */
  antiguedad_s?: number | null;
  antiguedad_h?: number | null;
  last_cycle_ts: number | null;
  fuente_sismos: number;
  remap_aplicado: boolean;
  lectura: string;
  tree: string;
  ciclos?: number;
  error?: string;
};

export const api = {
  health: () => getJson<Health>("/api/health"),
  healthApis: () => getJson<ApiHealth>("/api/health/apis"),
  overview: () => getJson<Overview>("/api/overview"),
  precursores: (limit = 50) =>
    getJson<Record<string, unknown>[]>(`/api/precursores?limit=${limit}`),
  muro: (limit = 50) => getJson<Record<string, unknown>[]>(`/api/muro?limit=${limit}`),
  nodos: () => getJson<Record<string, unknown>[]>("/api/nodos"),
  sismos: (min = 4.5, limit = 200) =>
    getJson<{
      min_magnitude: number;
      count: number;
      total_matching: number;
      items: Record<string, unknown>[];
    }>(`/api/sismos?min_magnitude=${min}&limit=${limit}`),
  ciclos: (limit = 50) => getJson<Record<string, unknown>[]>(`/api/ciclos?limit=${limit}`),
  detecciones: (limit = 100) =>
    getJson<Record<string, unknown>[]>(`/api/detecciones?limit=${limit}`),
  aciertos: (limit = 100) =>
    getJson<{
      pesos: Record<string, unknown>[];
      recent: Record<string, unknown>[];
      summary: Record<string, unknown>;
    }>(`/api/aciertos?limit=${limit}`),
  alertas: (limit = 50) => getJson<{
    geo_alerts: unknown[];
    muro_breaches: unknown[];
    hot_detections: unknown[];
    hot_fantasma: unknown[];
    flare_alerts: Array<{
      timestamp: string;
      flux_max: number;
      flux_avg: number;
      flare_class: string;
      source: string;
      note: string;
    }>;
  }>(`/api/alertas?limit=${limit}`),
  agente: () => getJson<Record<string, unknown>>("/api/agente"),
  ask: (question: string) =>
    postJson<{ answer: string; citations: string[] }>("/api/ask", { question }),
  cimatica: (limit = 50, ambito?: string) =>
    getJson<{
      total: number;
      limit: number;
      ambito: string | null;
      by_ambito: Record<string, unknown>[];
      items: Record<string, unknown>[];
    }>(`/api/cimatica?limit=${limit}${ambito ? `&ambito=${encodeURIComponent(ambito)}` : ""}`),
  correlaciones: () =>
    getJson<{
      padre: { present: boolean; items: Record<string, unknown>[]; patrones: string[]; event_classes: string[]; table: string };
      omega: { present: boolean; items: Record<string, unknown>[]; patrones: string[]; event_classes: string[]; table: string };
    }>("/api/correlaciones"),
  bots: () => getJson<Record<string, unknown>>("/api/bots"),
  sesgo: () => getJson<Record<string, unknown>>("/api/sesgo"),
  /** ONNX con su habilidad MEDIDA: `medido: false` no es lo mismo que negado. */
  modelos: () =>
    getJson<{
      medido_at: string | null;
      sin_medir: string[];
      nota: string;
      modelos: {
        bot: string;
        archivo: string;
        existe: boolean;
        kb: number | null;
        mtime: string | null;
        medido: boolean;
        auc: number | null;
        auc_inferior: number | null;
        auc_nulo_por_nodo: number | null;
        ganancia_sobre_nulo: number | null;
        aprueba: boolean | null;
        origen: string | null;
        motivo: string | null;
        n: number | null;
        reentrenado: boolean | null;
      }[];
    }>("/api/modelos"),
  aprendizaje: () =>
    getJson<{
      present: boolean;
      source?: string;
      caption?: string;
      series: Record<string, { dia: string; asertividad_cum: number | null; n_cum: number }[]>;
    }>("/api/aprendizaje"),
  firmas: () => getJson<Record<string, unknown>>("/api/firmas"),
  lag: () =>
    getJson<{
      factores: Record<string, unknown>[];
      anticipacion: Record<string, unknown>[];
      anticipacion_solo_especificas?: boolean;
      anticipacion_nota?: string;
      /** El nulo del lag: anticipar no es lo mismo que persistir. */
      nulo?: {
        disponible?: boolean;
        universo?: string;
        exigibles?: number;
        con_lag?: number;
        especificas?: number;
        persisten?: number;
        sin_nulo?: number;
        medidas_sin_lag?: number;
        pct_especificas?: number | null;
        con_lag_fuera_del_universo?: number;
        nota?: string;
      };
    }>("/api/lag"),
  muroLags: () =>
    getJson<{
      activo: boolean;
      clases?: string[];
      firmas_ids?: unknown[];
      detectado_en?: string;
      fecha_inicio?: string;
      fecha_fin?: string;
      dias_restantes?: [number, number];
      dias_transcurridos?: number;
      similitud_max?: number;
    }>("/api/muro_lags"),
  juez: (limit = 100, fase = "viva") =>
    getJson<{ items: Record<string, unknown>[]; counts: Record<string, unknown>[]; source: string }>(
      `/api/juez?limit=${limit}&fase=${fase}`,
    ),
  layers: () => getJson<Record<string, unknown>>("/api/layers"),
  reportes: (name?: string) =>
    getJson<{ present: boolean; files: { name: string; bytes: number; mtime: number }[]; content: string | null; name: string | null; dir: string }>(
      name ? `/api/reportes?name=${encodeURIComponent(name)}` : "/api/reportes",
    ),
  unificado: () => getJson<Record<string, unknown>>("/api/unificado"),
  /** Estado vivo unificado del launcher (reestructuración 2026-10-20) */
  estadoVivo: () => getJson<{
    ok: boolean;
    ts: number;
    edad_s: number | null;
    ciclo: {
      timestamp: number; geo_signal: string; geo_confidence: number;
      fantasma: number; nivel_riesgo: string; precursors_count: number;
      precursor_types: string | null; muro_walls_active: number; muro_breach: number;
    } | null;
    telemetria: Record<string, number | null> | null;
    goes_clase: string | null;
    termico: { zonas: number; max: number } | null;
    senales: Array<{
      sitio: string; id_nodo: number; evento: string;
      similitud: number | null; recurrencia: number | null;
      lag_inicial_h: number | null; lag_restante_h: number | null; ancla_ts: number | null;
    }>;
    muro_lags: { clases: string; fecha_inicio: string; fecha_fin: string;
                 dias_restantes: [number, number] } | null;
    auditoria: {
      aciertos: number; fallos: number; falsos_positivos: number;
      ganancia: number | null; asertividad: number | null; asertividad_muda: number | null;
    };
    cimatica_total: number | null;
    cimatica_top: Array<{ frecuencia: number; event_class: string | null; ambito: string | null }>;
    serie_fantasma: Array<{ ts: number; fantasma: number; nivel: string }>;
    sismos_recientes: Array<{ ts: number; mag: number; lugar: string }>;
  }>("/api/estado-vivo"),
  telemetry: () => getJson<{
    caption_in: string;
    caption_out: string;
    sources: Array<{
      id: string;
      label: string;
      inbound: Record<string, unknown>;
      processed: Record<string, unknown>;
    }>;
    locf_cache_n: number;
    ciclo: Record<string, unknown> | null;
    precursor: Record<string, unknown> | null;
  }>("/api/telemetry"),
  telemetryHistory: (limit = 48) => getJson<{
    history: Array<{
      ts: string;
      bz: number | null;
      viento: number | null;
      kp: number | null;
      schumann: number | null;
      schumann_act: number | null;
      fantasma: number | null;
      nivel_riesgo: string | null;
      goes_flux_max: number | null;
      goes_flux_avg: number | null;
      goes_flux_class: string | null;
      alfa2_zones_anom: number;
      alfa2_avg_coverage: number | null;
    }>;
  }>(`/api/telemetry/history?limit=${limit}`),
  /** Matrices Padre+Juez / telemetría / climática */
  heatmaps: () => getJson<Record<string, unknown>>("/api/heatmaps"),
  /** Consenso: ciclos + pesos bots */
  consenso: (limit = 50) => getJson<Record<string, unknown>>(`/api/consenso?limit=${limit}`),
  /** Figura cimática live vs biblioteca */
  cimaticaAhora: () => getJson<Record<string, unknown>>("/api/cimatica/ahora"),
  /** Estado de config Telegram (sin secretos) */
  telegramStatus: () => getJson<Record<string, unknown>>("/api/telegram/status"),
  /** Serie Schumann vivo (tbl_schumann_vivo) */
  schumannVivo: (limit = 120) =>
    getJson<{
      present: boolean;
      items: Record<string, unknown>[];
      latest: Record<string, unknown> | null;
      source: string;
      caption: string;
    }>(`/api/schumann_vivo?limit=${limit}`),
  /** Delta cross + psique financiera */
  delta: (limit = 80) =>
    getJson<{
      present: boolean;
      delta: Record<string, unknown>[];
      psique: Record<string, unknown>[];
      latest_delta: Record<string, unknown> | null;
      latest_psique: Record<string, unknown> | null;
      source: string;
      caption: string;
    }>(`/api/delta?limit=${limit}`),
  /** Muestras recientes clima espacial (Bz/Kp/viento) */
  climaEspacial: (limit = 80) =>
    getJson<{
      present: boolean;
      items: Record<string, unknown>[];
      latest: Record<string, unknown> | null;
      source: string;
      caption: string;
    }>(`/api/clima_espacial?limit=${limit}`),
};
