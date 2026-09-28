"""
Layer Runner — orchestrates fetch → ingest → analyze → consensus.
Agents: Alfa-1, Alfa-2, Beta-1, Beta-2, Delta, Jupiter, Omega, Loki, Padre.

Hierarchical validation:
  1. All agents fetch and analyze independently
  2. #2 agents report to #1 agents for validation
  3. Padre cross-validates across families (+ Omega dual-ask)
  4. Everything correlates against Schumann (Beta-1)
  5. Loki provides Bayesian probability collapse (Act 3)
"""

import logging
import math
from pathlib import Path
from typing import Dict, List, Optional

import pandas as pd

from sentinel_omega.core.shared.agent_base import (
    AgentSignal, ConsensusResult, SignalType, valor_medido,
)
from sentinel_omega.core.precursor.risk_calculator import (
    PrecursorRisk,
    compute_fantasma,
    format_risk_report,
)
from sentinel_omega.core.precursor.assertivity import AssertivityTracker
from sentinel_omega.core.precursor.scanner import PrecursorScanner, PrecursorDetection
from sentinel_omega.core.precursor.muro_cinco_eventos import MuroCincoEventos, MuroResult

from sentinel_omega.layers.geodynamic.alfa1.agent import Alfa1Agent
from sentinel_omega.layers.geodynamic.alfa2.agent import Alfa2Agent
from sentinel_omega.layers.geodynamic.beta1.agent import Beta1Agent
from sentinel_omega.layers.geodynamic.beta2.agent import Beta2Agent
from sentinel_omega.layers.geodynamic.delta.agent import DeltaAgent
from sentinel_omega.layers.geodynamic.padre.agent import GeodynamicPadre
from sentinel_omega.layers.geodynamic.jupiter.agent import JupiterAgent
from sentinel_omega.layers.geodynamic.omega.agent import OmegaAgent
from sentinel_omega.layers.geodynamic.loki.agent import LokiAgent

from sentinel_omega.infrastructure.pipeline.data_pipeline import GeodynamicPipeline

logger = logging.getLogger(__name__)


# ─── Modelos callados por FUGA de presencia ──────────────────────────────────
#
# Medido el 2026-09-27 (diagnóstico omega_diag): desde las 13:59 CST alfa1,
# loki y omega dijeron WATCH en 44 de 44 ciclos, con la regla en neutral. La
# causa no es el vector sino lo que el modelo aprendió de `kp_mean`:
#
#   * en las FIRMAS (etiquetas de evento) `kp_mean` vale 0 en el 100 % ---
#     nunca se midió ahí, así que el 0 es «ausente»;
#   * en el feedback del Juez, cuando SÍ viene (> 0,2), está etiquetado
#     NEUTRAL en el 100 % (594/594 filas de omega).
#
# El bosque aprendió «kp_mean ≈ 0 ⇒ firma de evento ⇒ WATCH»: la PRESENCIA del
# dato funciona como etiqueta. Y el ciclo vivo calcula `kp_mean` como la media
# del Kp entero de 1 minuto, que en calma baja de 0,31 --- a las 13:59 cruzó
# ese umbral y los tres bots saltaron a la vez. Con `kp_mean` en cualquier
# valor de 0,33 a 2,0 el mismo modelo da NO_SIGNAL/NEUTRAL.
#
# Mientras no se reentrene con máscara de presencia, el modelo de estos bots
# NO habla: manda la regla, y el registro dice por qué calló.
RASGOS_CON_FUGA: Dict[str, List[str]] = {
    # VACÍO desde el 2026-09-27 23:25, y el mecanismo se conserva a propósito.
    #
    # Era el tapón de Agente-C mientras la fuga de etiqueta por procedencia
    # estaba viva: alfa1, loki y omega leían `kp_mean`=0 como «firma de evento»
    # (P(alarma|kp=0) = 96,7-100 %), así que al modelo ni se le preguntaba. Su
    # condición de retirada --- «hasta que P(alarma|rasgo=0) colapse» --- se
    # cumplió con el rebuild y el reentreno, y está medida:
    #
    #     bot     con kp≈0                          con kp real 336 h
    #     alfa1   NO_SIGNAL 0,2932 (era WATCH 0,68)   NO_SIGNAL 0,2755
    #     omega   NEUTRAL   0,4034 (era WATCH 0,61)   NEUTRAL   0,6623
    #     loki    NEUTRAL   0,3555 (era WATCH 0,82)   NEUTRAL   0,3577
    #
    # Se deja la tabla, no el nombre muerto: si aparece otra fuga, aquí se
    # apunta con su medición y el modelo se calla sin tocar más código.
}

# Rasgos cuyo CERO no puede ser una medición. Si uno falta --- ausente, no
# finito, o cero --- al modelo no se le pregunta y manda la regla.
#
# Es la «bandera de rasgo presente» que llevaba días propuesta, puesta en la
# puerta de la inferencia en vez de dentro del vector. Razón: `vector_para` pone
# 0,0 en lo que falta, y para un modelo 0,0 es un valor medido (regla dura 7).
#
# `beta2` con la marea, medido el 2026-09-27 tras el reentreno:
#
#     con marea real (lo que da el ciclo)   NO_SIGNAL 0,3500
#     sin marea                            WATCH     0,7126   <-- fantasma
#
# Y no es fuga de procedencia: tras el rebuild la marea está en el 100 % de las
# DOS mitades, así que el modelo nunca vio un cero y extrapola cualquier cosa.
# Es una región de entrada **nunca medida**, que es un defecto distinto y se
# tapa distinto. `marea_total` sirve de canario: las ocho se calculan juntas por
# efemérides, así que si falta una faltan todas --- y solo pueden faltar si
# `ephem` no está instalado. Cero es imposible por física: la Luna siempre tira.
RASGOS_REQUERIDOS: Dict[str, List[str]] = {
    "beta2": ["marea_total"],
}


def _rasgo_requerido_ausente(bot: str, rasgos) -> Optional[str]:
    """El primer rasgo requerido que falta, o None si están todos."""
    for clave in RASGOS_REQUERIDOS.get(bot, ()):
        v = rasgos.get(clave) if hasattr(rasgos, "get") else None
        if v is None:
            return clave
        try:
            f = float(v)
        except (TypeError, ValueError):
            return clave
        if not math.isfinite(f) or f == 0.0:
            return clave
    return None


ETIQUETA_FUGA: Dict[str, str] = {"beta2": "marea"}


def _es_finito_o_no_numerico(v) -> bool:
    """Descarta NaN/inf numéricos; lo no numérico pasa tal cual."""
    if isinstance(v, bool) or not isinstance(v, (int, float)):
        return True
    return math.isfinite(float(v))


class GeodynamicLayerRunner:

    def __init__(self, enable_satellite: bool = True, repo=None):
        self.pipeline = GeodynamicPipeline()
        # Repo para persistir el catálogo sísmico vivo en la operativa que lee
        # el Juez. Lazy: si no se inyecta, se crea contra la DB canónica.
        self._repo = repo
        self.alfa1 = Alfa1Agent()
        self.alfa2 = Alfa2Agent() if enable_satellite else None
        self.beta1 = Beta1Agent()
        self.beta2 = Beta2Agent()
        self.delta = DeltaAgent()
        self.jupiter = JupiterAgent()
        self.omega = OmegaAgent()
        self.loki = LokiAgent()  # Act 3 - Unified Field
        self.padre = GeodynamicPadre()
        self._enable_satellite = enable_satellite
        self.assertivity = AssertivityTracker(radius_degrees=5.0, window_days=30)
        self.scanner = PrecursorScanner()
        self.muro = MuroCincoEventos(min_walls_for_breach=3)
        self.last_risk: Optional[PrecursorRisk] = None
        self.last_detections: List[PrecursorDetection] = []
        self.last_muro: Optional[MuroResult] = None

    def _get_repo(self):
        """Repo lazy contra la DB canónica (per-thread connection)."""
        if self._repo is None:
            from sentinel_omega.infrastructure.database.repository import (
                SentinelRepository,
            )
            self._repo = SentinelRepository()
        return self._repo

    def _bind_locf(self) -> None:
        """Enlaza el repo al pipeline para que el LOCF persista en la DB.

        El patch (data_pipeline_locf_patch) instala bind_repository, pero
        nadie lo llamaba: el pipeline se construye sin `repository`, así que
        `self._repo` quedaba None y _locf_set nunca escribía en
        tbl_locf_cache (el fallo se tragaba en su try/except). Idempotente.
        """
        if getattr(self, "_locf_bound", False):
            return
        bind = getattr(self.pipeline, "bind_repository", None)
        if bind is None:
            return  # patch LOCF no activo
        try:
            bind(self._get_repo())
            self._locf_bound = True
            logger.info("LOCF enlazado al repositorio — persistencia activa")
        except Exception as exc:  # noqa: BLE001 — fail-soft
            logger.warning("No se pudo enlazar LOCF al repo: %s", exc)

    def _persist_sismos(self, beta1_data: Dict) -> None:
        """Persiste el catálogo sísmico vivo en TBL_HISTORICO_SISMICO (Juez).

        Fail-soft: nunca bloquea el ciclo. INSERT OR IGNORE dedup por event_id.
        """
        eventos = beta1_data.get("seismic_events") if isinstance(beta1_data, dict) else None
        if not eventos:
            return
        try:
            n = self._get_repo().bulk_insert_sismos(eventos)
            logger.info(
                "Sismos → operativa (Juez): +%d nuevos de %d vivos", n, len(eventos)
            )
        except Exception as exc:  # noqa: BLE001 — fail-soft por diseño
            logger.warning("Persistencia sísmica falló (no bloqueante): %s", exc)

    def _persist_jupiter(self, jupiter_data: Dict) -> None:
        """Persiste rayos X GOES e interés de búsqueda para Júpiter.

        Hasta ahora `fetch_jupiter_data()` bajaba `xray_df` y `trends_df` cada
        ciclo, se los pasaba al agente y los tiraba: no había escritor ni
        tabla. Por eso Júpiter no tenía histórico que entrenar --- el mismo
        patrón del catálogo sísmico, no un problema de nombres de features.

        Dos tablas propias, INSERT OR IGNORE por marca temporal. Fail-soft:
        que falle el guardado no debe tumbar el ciclo.
        """
        if not isinstance(jupiter_data, dict):
            return
        try:
            repo = self._get_repo()
            repo._execute(
                "CREATE TABLE IF NOT EXISTS tbl_xray_vivo ("
                " timestamp_blk TEXT PRIMARY KEY,"
                " flux_max REAL, flux_avg REAL, banda TEXT)"
            )
            repo._execute(
                "CREATE TABLE IF NOT EXISTS tbl_trends_vivo ("
                " fecha TEXT PRIMARY KEY, solar_interest REAL)"
            )

            xray = jupiter_data.get("xray_df")
            if xray is not None and len(xray) and "time_tag" in xray.columns:
                x = xray.copy()
                x["blk"] = x["time_tag"].dt.strftime("%Y-%m-%d %H:00")
                agg = x.groupby("blk")["flux"].agg(["max", "mean"]).reset_index()
                banda = str(x["energy"].iloc[0]) if "energy" in x.columns else ""
                repo._executemany(
                    "INSERT OR IGNORE INTO tbl_xray_vivo "
                    "(timestamp_blk, flux_max, flux_avg, banda) VALUES (?,?,?,?)",
                    [(r["blk"], float(r["max"]), float(r["mean"]), banda)
                     for _, r in agg.iterrows()
                     if pd.notna(r["max"]) and pd.notna(r["mean"])],
                )

            trends = jupiter_data.get("trends_df")
            if (trends is not None and len(trends)
                    and {"date", "solar_interest"}.issubset(trends.columns)):
                repo._executemany(
                    "INSERT OR IGNORE INTO tbl_trends_vivo "
                    "(fecha, solar_interest) VALUES (?,?)",
                    [(pd.Timestamp(r["date"]).strftime("%Y-%m-%d"),
                      float(r["solar_interest"]))
                     for _, r in trends.iterrows()
                     if pd.notna(r["solar_interest"])],
                )
        except Exception as e:  # noqa: BLE001
            logger.warning("No se pudo persistir la telemetría de Júpiter: %s", e)

    def _persist_clima(self, alfa1_data: Dict) -> None:
        """Persiste la telemetría horaria en tbl_clima_espacial_raw.

        Antes solo la llenaban el backcast y un gapfill manual, así que la
        tabla llevaba parada desde 2026-09-11 aunque el ciclo bajara estos
        datos de NOAA cada vuelta. De ella comen el entrenamiento (features
        bz/viento/kp/protones) y el fallback de delta_enriched.

        INSERT OR IGNORE por timestamp_blk. Fail-soft.
        """
        filas = alfa1_data.get("clima_horas") if isinstance(alfa1_data, dict) else None
        if not filas:
            return
        try:
            repo = self._get_repo()
            antes = repo._execute(
                "SELECT COUNT(*) FROM tbl_clima_espacial_raw"
            ).fetchone()[0]
            repo._executemany(
                "INSERT OR IGNORE INTO tbl_clima_espacial_raw "
                "(timestamp_blk, bz_promedio, bz_derivada, bz_min, bz_max, "
                " viento_solar_avg, viento_solar_max, kp_max, kp_promedio, "
                " proton_flux_10mev) VALUES (?,?,?,?,?,?,?,?,?,?)",
                filas,
            )
            despues = repo._execute(
                "SELECT COUNT(*) FROM tbl_clima_espacial_raw"
            ).fetchone()[0]
            if despues > antes:
                logger.info(
                    "Clima espacial → DB: +%d horas nuevas de %d",
                    despues - antes, len(filas),
                )
        except Exception as exc:  # noqa: BLE001 — fail-soft por diseño
            logger.warning("Persistencia de clima falló (no bloqueante): %s", exc)

    def _compute_precursor_risk(
        self,
        alfa1_data: Dict,
        beta1_data: Dict,
        beta2_data: Dict,
    ) -> PrecursorRisk:
        """Compute TITAN V32 fantasma from raw pipeline data."""
        import numpy as np

        bz = None  # sin magnetómetro (columna ausente o toda NaN): NULL, no 0
        viento = None  # sin plasma (columna ausente o toda NaN): NULL, no 0
        omni_df = alfa1_data.get("omni_dataframe")
        if omni_df is not None:
            if "bz_gsm" in omni_df.columns:
                serie_bz = np.asarray(omni_df["bz_gsm"], dtype=float)
                serie_bz = serie_bz[np.isfinite(serie_bz)]
                bz = float(serie_bz.mean()) if serie_bz.size else None
            if "plasma_speed" in omni_df.columns:
                serie_v = np.asarray(omni_df["plasma_speed"], dtype=float)
                serie_v = serie_v[np.isfinite(serie_v)]
                viento = float(serie_v.mean()) if serie_v.size else None

        # Sin lectura viva de Schumann (la API falló o dio el placeholder):
        # None → NULL en PREC y «sin dato» en el reporte, no un 0 sintético.
        # Beta-1 y el vector ONNX siguen con su propio 0 = «no lo sé».
        _sch_act = beta1_data.get("schumann_activity")
        try:
            _sch_act = float(_sch_act) if _sch_act is not None else None
        except (TypeError, ValueError):
            _sch_act = None
        sch_wpc = _sch_act / 100.0 if _sch_act is not None and np.isfinite(_sch_act) else None

        kp_series = beta1_data.get("kp_series")
        kp = float(np.nanmean(kp_series)) if kp_series is not None and len(kp_series) > 0 else 0.0

        lod_series = beta1_data.get("lod_ms")
        lod_ms = float(np.nanmean(lod_series)) if lod_series is not None and len(lod_series) > 0 else None
        if lod_ms is not None and not np.isfinite(lod_ms):
            lod_ms = None  # sin dato del IERS: NULL, no un 0 sintético

        pressure_hpa = 1013.0
        pg = beta2_data.get("pressure_gradient")
        if pg:
            pressure_hpa = pg.get("mean_pressure", 1013.0)

        risk = compute_fantasma(
            bz=bz, viento=viento, sch_wpc=sch_wpc,
            pressure_hpa=pressure_hpa, kp=kp, lod_ms=lod_ms,
        )
        self.last_risk = risk
        logger.info(f"Precursor risk: fantasma={risk.fantasma:.2f} level={risk.risk_level}")
        return risk

    def _fetch_hurricane_data(self) -> Dict:
        try:
            from sentinel_omega.infrastructure.api.noaa_hazards import (
                fetch_active_hurricanes,
                compute_hurricane_proximity,
            )
            cyclones = fetch_active_hurricanes()
            if not cyclones:
                return {}
            nearby = compute_hurricane_proximity(cyclones, 19.0, -99.0, max_distance_deg=15.0)
            return {
                "active_cyclones": [
                    {
                        "name": c.name, "category": c.category,
                        "lat": c.lat, "lon": c.lon,
                        "max_wind_kt": c.max_wind_kt,
                        "pressure_mb": c.pressure_mb,
                        "distance_deg": n["distance_deg"],
                    }
                    for c, n in zip(cyclones, nearby)
                ] if nearby else [],
            }
        except Exception as e:
            logger.warning(f"Hurricane data fetch failed (non-blocking): {e}")
            return {}

    def _aplicar_modelos(self, signals) -> None:
        """Pasa los rasgos del ciclo por el modelo de cada bot.

        El veredicto del modelo se ANOTA siempre en la señal (`onnx_*`), para
        que el Juez pueda comparar después quién acertaba, y sustituye a la
        rama de reglas solo cuando el modelo dice algo --- si devuelve None
        (sin modelo, vector vacío o «nada que reportar»), manda la regla.

        El techo de cada bot se respeta: delta nunca vota ALERT, porque el
        estrés financiero es contexto, no evidencia sísmica.
        """
        from sentinel_omega.core.onnx_mixin import senal_desde_rasgos
        from sentinel_omega.core.shared.agent_base import SignalType

        try:
            rasgos = self._rasgos_del_ciclo()
        except Exception as e:  # noqa: BLE001 — el ciclo sigue con las reglas
            logger.warning("No se pudieron armar los rasgos del ciclo: %s", e)
            return
        if not rasgos:
            return

        SIN_ALERTA = {"delta"}     # su techo es WATCH, por diseño
        for sig in signals:
            bot = str(getattr(sig, "agent_name", "") or "").lower()
            if not bot:
                continue
            fuga = RASGOS_CON_FUGA.get(bot)
            falta = _rasgo_requerido_ausente(bot, rasgos)
            if fuga or falta:
                # Modelo callado (ver RASGOS_CON_FUGA): ni se le pregunta. La
                # regla conserva señal, confianza y texto; no hay empate que
                # resolver, así que tampoco se escribe `gano`.
                datos = getattr(sig, "data", None)
                if isinstance(datos, dict):
                    datos["onnx"] = False
                    datos["onnx_callado"] = (
                        "fuga:" + ETIQUETA_FUGA.get(bot, fuga[0]) if fuga
                        else "falta:" + falta)
                logger.debug("%s: modelo callado (fuga=%s, falta=%s)", bot, fuga, falta)
                continue
            try:
                salida = senal_desde_rasgos(
                    bot, rasgos, permitir_alerta=bot not in SIN_ALERTA)
            except Exception as e:  # noqa: BLE001
                logger.debug("%s: modelo no utilizable (%s)", bot, e)
                continue
            datos = getattr(sig, "data", None)
            if not isinstance(datos, dict):
                continue
            if salida is None:
                datos["onnx"] = False
                continue
            tipo, conf, nombre = salida
            regla_senal = sig.signal_type.value
            regla_conf = float(sig.confidence or 0.0)
            regla_texto = sig.reasoning or "(la regla no dejó texto)"
            datos.update({
                "onnx": True,
                "onnx_senal": nombre,
                "onnx_conf": round(float(conf), 4),
                "regla_senal": regla_senal,
                "regla_conf": round(regla_conf, 4),
            })
            # ── Quién gana el empate: EL DE MÁS CONFIANZA ──────────────────
            #
            # Hasta el 2026-09-27 el modelo ganaba SIEMPRE que hablara: estas dos
            # asignaciones eran incondicionales y la comparación de arriba solo
            # decidía si se escribía una línea de log. Así que un modelo con 0,35
            # apagaba una alarma de regla con 0,60.
            #
            # Se vio en cuanto el registro dejó de mentir --- sobre cinco horas de
            # operación real, con los campos `onnx_*` recién persistidos:
            #
            #     beta1   modelo=WATCH    regla=neutral    22 veces
            #     beta2   modelo=NEUTRAL  regla=watch       8 veces
            #
            # Las 8 de beta2 son alarmas de la regla que el modelo apagó. Decisión
            # del operador, consultada: **gana el de más confianza**, simétrico ---
            # ni se privilegia alarmar ni callar, y las dos ramas se tratan como
            # iguales. Si el modelo trae menos confianza que la regla, manda la
            # regla y su texto queda intacto.
            #
            # `>=` y no `>`: en un empate exacto manda el modelo, que es lo que
            # aprendió de 19.578 firmas frente a un umbral escrito a mano.
            gana_el_modelo = float(conf) >= regla_conf
            if not gana_el_modelo:
                logger.info(
                    "%s: manda la REGLA %s (%.2f) sobre el modelo %s (%.2f)",
                    bot, regla_senal, regla_conf, nombre, conf,
                )
                datos["gano"] = "regla"
                continue
            if tipo != sig.signal_type:
                logger.info(
                    "%s: modelo %s (%.2f) sobre regla %s (%.2f)",
                    bot, nombre, conf, regla_senal, regla_conf,
                )
            datos["gano"] = "modelo"
            sig.signal_type = tipo
            sig.confidence = float(conf)
            # El `reasoning` también, o el registro miente. Hasta el 2026-09-27
            # aquí se sustituían la señal y la confianza y se dejaba el texto de
            # la REGLA, así que el Juez guardaba filas como
            #
            #     beta1  watch 0.735  "Normal spectral distribution"
            #
            # --- el texto describe lo que concluyó la regla y el veredicto es
            # del modelo. Quien audita esa fila lee una contradicción y no sabe
            # cuál mandó. Es primo de la regla dura 10 de AGENTS.md: una
            # sustitución silenciosa esconde lo que de verdad pasó.
            #
            # Se conservan LOS DOS. El texto de la regla no se tira: es la
            # segunda opinión, y cuando el modelo se equivoque va a ser lo
            # primero que haya que leer.
            sig.reasoning = (
                f"modelo ONNX: {nombre} ({conf:.0%}) "
                f"[regla: {regla_senal} ({regla_conf:.0%}) — {regla_texto}]"
            )

    def _rasgos_del_ciclo(self) -> Dict[str, float]:
        """Los rasgos con los nombres canónicos, desde la misma función que
        alimenta al Juez: si el modelo se entrena con esos nombres, tiene que
        inferir con esos nombres."""
        from sentinel_omega.launcher import _build_live_features
        # La conexión es para los rasgos que viven en tablas (rayos X,
        # tendencias). Se abre en SOLO LECTURA: el ciclo no escribe desde aquí.
        conn = None
        try:
            import sqlite3
            from sentinel_omega.config.sentinel_config import load_config
            cfg = load_config()
            ruta = (Path(__file__).resolve().parents[2]
                    / cfg.databases.geodynamic_db)
            conn = sqlite3.connect(f"file:{ruta}?mode=ro", uri=True, timeout=5)
        except Exception as e:  # noqa: BLE001 — sin conexión, esos rasgos faltan
            logger.debug("rasgos de tabla no disponibles: %s", e)
        try:
            rasgos = _build_live_features(self, conn) or {}
        finally:
            if conn is not None:
                conn.close()
        # Un NaN no es un rasgo medido. `_build_live_features` deja pasar los
        # acoplamientos de delta como NaN (`delta_cross_coupling`,
        # `delta_schumann_coupling`: 44/44 ciclos el 2026-09-27); aquí se
        # quitan para que ningún consumidor del runner los lea como dato.
        return {k: v for k, v in rasgos.items() if _es_finito_o_no_numerico(v)}

    def _datos_omega(self, alfa1_data: Optional[Dict],
                     beta1_data: Optional[Dict]) -> Dict:
        """Lo que ve omega: la telemetría cruda de alfa1 MÁS los rasgos
        canónicos del ciclo (`bz_mean`, `kp_max`, `viento_avg`, `fase_lunar`,
        `es_sicigia`, `schumann_*`…), los mismos que usa `_aplicar_modelos` y
        que guarda el Juez.

        Hasta el 2026-09-27 omega recibía solo `alfa1_data` --- un DataFrame y
        ningún escalar --- y escribía «Bz=sin dato; Kp=sin dato» con el ciclo
        trayendo Bz −0,93 y Kp 1. Tampoco se piden ya `schumann_mean` ni
        `schumann_std` a beta1: beta1 nunca los produce (esos dos vienen, si
        hay lectura, en los rasgos del ciclo).
        """
        omega_data = dict(alfa1_data or {})
        try:
            omega_data.update(self._rasgos_del_ciclo())
        except Exception as e:  # noqa: BLE001 — omega sigue con lo crudo
            logger.debug("omega sin rasgos del ciclo: %s", e)
        omega_data["schumann_hz"] = valor_medido(
            beta1_data or {}, "schumann_frequency", "schumann_hz")
        return omega_data

    @staticmethod
    def _datos_loki(alfa1_data: Optional[Dict], beta1_data: Optional[Dict],
                    delta_data: Optional[Dict]) -> Dict:
        """Entradas de Loki con los nombres que Loki lee, y None donde no hay
        lectura.

        Antes: Bz 0.0 si faltaba, viento 400, Schumann 7,83 (de una clave
        `schumann_mean` que beta1 nunca produce, así que era SIEMPRE 7,83), VIX
        20 y LOD 0.0. Valores inventados que la regla trataba como medidos.
        """
        import numpy as np

        def _ultimo_real(df, col):
            if df is None or col not in getattr(df, "columns", []):
                return None
            serie = pd.to_numeric(df[col], errors="coerce").to_numpy(dtype=float)
            serie = serie[np.isfinite(serie)]
            return float(serie[-1]) if serie.size else None

        omni = (alfa1_data or {}).get("omni_dataframe")
        lod_ms = None
        serie_lod = (beta1_data or {}).get("lod_ms")
        if serie_lod is not None and len(serie_lod) > 0:
            v = np.asarray(serie_lod, dtype=float)
            v = v[np.isfinite(v)]
            lod_ms = float(v[-1]) if v.size else None
        return {
            "bz_gsm": _ultimo_real(omni, "bz_gsm"),
            "solar_wind": _ultimo_real(omni, "plasma_speed"),
            # La potencia de Schumann (% de actividad), solo si hubo lectura.
            "schumann_activity": valor_medido(beta1_data or {}, "schumann_activity"),
            "vix": valor_medido(delta_data or {}, "vix"),
            "lod_ms": lod_ms,
        }

    def run(self, financial_data: Optional[Dict] = None) -> ConsensusResult:
        logger.info("=== Sentinel Omega Cycle ===")

        self._bind_locf()

        alfa1_data = self.pipeline.fetch_alfa1_data()
        beta1_data = self.pipeline.fetch_beta1_data()
        beta2_data = self.pipeline.fetch_beta2_data()
        delta_data = self.pipeline.fetch_delta_data()

        # El fetch de Beta-1 ya trajo el catálogo USGS: registrarlo en la
        # operativa que lee el Juez (antes se descartaba → Juez ciego).
        self._persist_sismos(beta1_data)
        # Ídem con la telemetría de Alfa-1 → tbl_clima_espacial_raw.
        self._persist_clima(alfa1_data)

        risk = self._compute_precursor_risk(alfa1_data, beta1_data, beta2_data)

        hurricane_data = self._fetch_hurricane_data()
        detections = self.scanner.scan(
            alfa1_data, beta1_data, beta2_data,
            hurricane_data=hurricane_data,
            financial_data=delta_data,
            risk=risk,
        )
        self.last_detections = detections

        muro_result = self.muro.evaluate(detections)
        self.last_muro = muro_result

        self.alfa1.ingest(alfa1_data)
        self.beta1.ingest(beta1_data)
        self.beta2.ingest(beta2_data)
        self.delta.ingest(delta_data)

        signals: List[AgentSignal] = [
            self.alfa1.analyze(),
            self.beta1.analyze(),
            self.beta2.analyze(),
            self.delta.analyze(),
        ]

        if self._enable_satellite and self.alfa2:
            try:
                alfa2_data = self.pipeline.fetch_alfa2_data()
                self.alfa2.ingest(alfa2_data)
                signals.append(self.alfa2.analyze())
                self._last_alfa2_data = alfa2_data
            except Exception as e:
                logger.warning(f"Satellite layer failed (non-blocking): {e}")
                self._last_alfa2_data = None
        else:
            self._last_alfa2_data = None

        try:
            jupiter_data = self.pipeline.fetch_jupiter_data()
            self.jupiter.ingest(jupiter_data)
            signals.append(self.jupiter.analyze())
            self._persist_jupiter(jupiter_data)
        except Exception as e:
            logger.warning(f"Júpiter layer failed (non-blocking): {e}")

        # Omega: telemetría espacial + pregunta a Beta-1
        try:
            beta1_sig = next(
                (s for s in signals if getattr(s, "agent_name", "") == "beta1"),
                None,
            )
            omega_data = self._datos_omega(alfa1_data, beta1_data)
            self.omega.ingest(omega_data)
            self.omega.set_beta_context(beta1_sig)
            signals.append(self.omega.analyze())
        except Exception as e:
            logger.warning(f"Omega layer failed (non-blocking): {e}")

        # Loki (Act 3): Unified Field - Fractal-Bayesian collapse
        try:
            # Sin valores por defecto: lo que falta llega como None y Loki
            # emite NO_SIGNAL si le faltan sus entradas clave.
            loki_data = self._datos_loki(alfa1_data, beta1_data, delta_data)
            self.loki.ingest(loki_data)
            signals.append(self.loki.analyze())
            logger.info(f"Loki signal: {signals[-1].signal_type.value} (conf={signals[-1].confidence:.2f})")
        except Exception as e:
            logger.warning(f"Loki layer failed (non-blocking): {e}")

        # ── Cada experto opina con SU modelo ──────────────────────────
        # Hasta el 2026-09-26 solo alfa1 y omega inferían con ONNX: se
        # entrenaban OCHO modelos y seis no se usaban. Y eso deformaba la
        # disciplina --- lo vio el operador: el que no alarma no puede ser
        # castigado por alarmar, así que el Juez hundía al que participa
        # (alfa1: 669 alarmas, peso 0.300) y dejaba en el techo a los que
        # callan (loki, delta, alfa2: 0 alarmas, 0 castigos, peso 1.000, y los
        # 37 eventos del periodo perdidos).
        #
        # La arquitectura es de expertos: cada bot en su dominio, con su modelo
        # y su memoria, y el Padre buscando patrones entre patrones. Un experto
        # que no opina no aporta, y tampoco se puede corregir.
        self._aplicar_modelos(signals)

        consensus = self.padre.evaluate_consensus(signals)
        consensus.precursor_risk = risk
        consensus.precursor_detections = detections
        # Exponer señales por bot para registrar_prediccion en launcher
        consensus.agent_signals = signals

        logger.info(
            f"Consensus: {consensus.final_signal.value} "
            f"(reached={consensus.consensus_reached}, conf={consensus.confidence:.2f}, "
            f"fantasma={risk.fantasma:.2f}, precursors={len(detections)}, "
            f"muro={muro_result.walls_active}/{muro_result.total_walls})"
        )
        return consensus