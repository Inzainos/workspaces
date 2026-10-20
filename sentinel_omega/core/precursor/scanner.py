"""
Precursor Scanner — Runs all detection functions against live pipeline data.

On each geodynamic cycle, the scanner evaluates atmospheric readings,
Kp series, seismic catalogs, SO2/air quality, NOAA space weather,
NHC hurricane data, and financial signals to detect active precursors
across all 15 categories.

Each detected precursor is returned as a PrecursorDetection with its
type, source station/region, confidence, and raw values.
"""

import logging
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

import numpy as np

from sentinel_omega.core.precursor.precursor_types import (
    PrecursorType,
    PRECURSOR_DISPLAY_NAMES,
    PRECURSOR_PROFILES,
    detect_blue_jet,
    detect_niebla_tule,
    detect_silent_trigger,
    detect_seismic_cluster,
    detect_volcanic_precursor,
    detect_sprite_rojo,
    detect_hurricane_proximity,
    detect_tsunami_potential,
    compute_precipitacion_potencial,
    detect_precipitacion_potencial,
)

logger = logging.getLogger(__name__)

# Precipitation scanner confidence thresholds
_PREC_HUMIDITY_HIGH = 80.0
_PREC_CLOUDS_HIGH = 70.0
_PREC_PI_VERY_HIGH = 45.0
_PREC_CONF_BASE = 0.50
_PREC_CONF_HUMIDITY_BOOST = 0.15
_PREC_CONF_CLOUDS_BOOST = 0.10
_PREC_CONF_PI_BOOST = 0.10


@dataclass
class PrecursorDetection:
    tipo: PrecursorType
    display_name: str
    station: str
    lat: Optional[float]
    lon: Optional[float]
    confidence: float
    values: Dict[str, Any] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)


class PrecursorScanner:

    def __init__(self):
        self.last_detections: List[PrecursorDetection] = []

    def scan(
        self,
        alfa1_data: Dict[str, Any],
        beta1_data: Dict[str, Any],
        delta_data: Dict[str, Any],
        hurricane_data: Optional[Dict[str, Any]] = None,
        financial_data: Optional[Dict[str, Any]] = None,
        risk: Optional[Any] = None,
    ) -> List[PrecursorDetection]:
        detections: List[PrecursorDetection] = []

        atmospheric = delta_data.get("atmospheric_readings", [])
        air_quality = delta_data.get("air_quality", {})
        kp_series = beta1_data.get("kp_series")
        seismic_mags = beta1_data.get("seismic_magnitudes")
        schumann_hz = beta1_data.get("schumann_frequency")
        # Sin default 0.0: desde el retiro del Hz (2026-10-09) la actividad
        # es lo único medido, y un 0.0 inventado es la regla 7 en la puerta
        # de una detección. Si no hay, que sea None y las ramas lo nombren.
        schumann_pct = beta1_data.get("schumann_activity")

        omni_df = alfa1_data.get("omni_dataframe")
        bz = 0.0
        viento = 0.0
        bz_min = None
        bz_min_2h = None
        viento_max = None
        if omni_df is not None:
            if "bz_gsm" in omni_df.columns:
                _sbz = np.asarray(omni_df["bz_gsm"], dtype=float)
                _sbz = _sbz[np.isfinite(_sbz)]
                if _sbz.size:
                    bz = float(_sbz.mean())
                    bz_min = float(_sbz.min())
                    # Corte de 2 h (2026-10-13, orden del operador): la
                    # PERTURBACIÓN juzga el AHORA, no el día arrastrado.
                    # Con la ventana de 24 h, UNA hora de grieta compraba
                    # 24 de bandera (medido el mismo día: 1 hora real de
                    # disturbio → 93 % de los ciclos con detección). Con
                    # cortes de 2 h: 4,64 %/h en 30 años, rachas medianas
                    # de 3 h — fluctúa con el disturbio real.
                    bz_min_2h = float(_sbz[-120:].min())
            if "plasma_speed" in omni_df.columns:
                _sv = np.asarray(omni_df["plasma_speed"], dtype=float)
                _sv = _sv[np.isfinite(_sv)]
                if _sv.size:
                    viento = float(_sv.mean())
                    viento_max = float(_sv.max())

        kp_mean = 0.0
        kp_max = None
        kp_max_2h = None
        if kp_series is not None and len(kp_series) > 0:
            _skp = np.asarray(kp_series, dtype=float)
            _skp = _skp[np.isfinite(_skp)]
            if _skp.size:
                kp_mean = float(_skp.mean())
                kp_max = float(_skp.max())
                kp_max_2h = float(_skp[-120:].max())

        detections.extend(self._scan_blue_jets(atmospheric))
        detections.extend(self._scan_sprites_rojos(atmospheric))
        detections.extend(self._scan_niebla_tule(atmospheric))
        detections.extend(self._scan_silent_trigger(kp_series))
        detections.extend(
            self._scan_seismic_cluster(seismic_mags, beta1_data.get("m4_count_24h"))
        )
        detections.extend(self._scan_fantasma(risk))
        detections.extend(self._scan_volcanic(air_quality, seismic_mags, atmospheric))
        detections.extend(self._scan_schumann(schumann_hz, schumann_pct))
        detections.extend(self._scan_tormenta_solar(bz_min, kp_max, viento_max))
        detections.extend(self._scan_perturbacion_geomagnetica(bz_min_2h, kp_max_2h))
        detections.extend(self._scan_tsunami(seismic_mags, delta_data, beta1_data))
        detections.extend(self._scan_hurricanes(hurricane_data or {}))
        detections.extend(self._scan_financial_correlation(financial_data or {}))
        detections.extend(self._scan_precipitacion(atmospheric, schumann_hz))

        self.last_detections = detections
        if detections:
            logger.warning(
                f"PRECURSOR SCAN: {len(detections)} active — "
                f"{[d.tipo.value for d in detections]}"
            )
        else:
            logger.info("Precursor scan: no active precursors")

        return detections

    def _scan_blue_jets(
        self, atmospheric: List[Dict[str, Any]]
    ) -> List[PrecursorDetection]:
        results = []
        for reading in atmospheric:
            # Sin dato → sin detección (regla 7/8): un campo ausente ya no
            # simula tormenta despejada (weather_id 800) ni 20 °C.
            temp_c = reading.get("temp_c")
            weather_id = reading.get("weather_id")
            pressure = reading.get("pressure_hpa")
            if temp_c is None or weather_id is None:
                continue

            if detect_blue_jet(temp_c, weather_id, pressure):
                confidence = 0.7
                if pressure is not None and pressure < 1008:
                    confidence += 0.1
                if temp_c > 30:
                    confidence += 0.1

                results.append(PrecursorDetection(
                    tipo=PrecursorType.BLUE_JET,
                    display_name=PRECURSOR_DISPLAY_NAMES[PrecursorType.BLUE_JET],
                    station=reading.get("station", "unknown"),
                    lat=reading.get("lat"),
                    lon=reading.get("lon"),
                    confidence=min(confidence, 0.95),
                    values={
                        "temp_c": temp_c,
                        "weather_id": weather_id,
                        "pressure_hpa": pressure,
                    },
                ))
        return results

    def _scan_niebla_tule(
        self, atmospheric: List[Dict[str, Any]]
    ) -> List[PrecursorDetection]:
        results = []
        for reading in atmospheric:
            humidity = reading.get("humidity_pct")
            visibility = reading.get("visibility_m")
            # Sin humitud/visibilidad medidas → sin evaluación de niebla.
            if humidity is None or visibility is None:
                continue

            if detect_niebla_tule(humidity, visibility):
                confidence = 0.6
                if visibility < 500:
                    confidence += 0.15
                if humidity > 95:
                    confidence += 0.1

                results.append(PrecursorDetection(
                    tipo=PrecursorType.NIEBLA_TULE,
                    display_name=PRECURSOR_DISPLAY_NAMES[PrecursorType.NIEBLA_TULE],
                    station=reading.get("station", "unknown"),
                    lat=reading.get("lat"),
                    lon=reading.get("lon"),
                    confidence=min(confidence, 0.95),
                    values={
                        "humidity_pct": humidity,
                        "visibility_m": visibility,
                    },
                ))
        return results

    def _scan_silent_trigger(
        self, kp_series: Optional[Any]
    ) -> List[PrecursorDetection]:
        if kp_series is None or len(kp_series) < 12:
            return []

        kp_list = list(kp_series[-24:]) if len(kp_series) > 24 else list(kp_series)
        if not detect_silent_trigger(kp_list):
            return []

        kp_mean = sum(kp_list) / len(kp_list)
        confidence = 0.65
        if len(kp_list) >= 24:
            confidence += 0.15
        if kp_mean < 1.0:
            confidence += 0.1

        return [PrecursorDetection(
            tipo=PrecursorType.SILENT_TRIGGER,
            display_name=PRECURSOR_DISPLAY_NAMES[PrecursorType.SILENT_TRIGGER],
            station="global",
            lat=None,
            lon=None,
            confidence=min(confidence, 0.95),
            values={
                "kp_median": float(np.median(kp_list)),
                "kp_max": float(max(kp_list)),
                "kp_mean": kp_mean,
                "calm_duration_h": len(kp_list) * 3,
            },
        )]

    def _scan_fantasma(self, risk: Optional[Any]) -> List[PrecursorDetection]:
        """Emite el Índice Fantasma (TITAN V32) como precursor de la muralla
        geofísica.

        FANTASMA figuraba en WALL_MEMBERS[WALL_GEOFISICO] desde siempre, pero
        ningún scanner lo emitía: el índice central del sistema nunca llegaba
        al Muro. Umbral HIGH (>=15) según los niveles documentados
        (LOW<5, MODERATE 5-15, HIGH 15-30, CRITICAL>=30); sobre 3.380 ciclos
        reales MODERATE es el estado normal (77%) y HIGH aparece en el 22.8%,
        así que discrimina. Se elige HIGH y no CRITICAL por la pérdida
        asimétrica (miss = 10x).
        """
        if risk is None:
            return []
        valor = getattr(risk, "fantasma", None)
        if valor is None:
            return []
        try:
            valor = float(valor)
        except (TypeError, ValueError):
            return []
        if valor < 15.0:
            return []
        nivel = str(getattr(risk, "risk_level", "") or "")
        return [PrecursorDetection(
            tipo=PrecursorType.FANTASMA,
            display_name=PRECURSOR_DISPLAY_NAMES[PrecursorType.FANTASMA],
            station="global",
            lat=None,
            lon=None,
            confidence=0.85 if valor >= 30.0 else 0.7,
            values={"fantasma": round(valor, 2), "nivel_riesgo": nivel},
        )]

    def _scan_seismic_cluster(
        self, seismic_mags: Optional[Any], m4_count_24h: Optional[int] = None
    ) -> List[PrecursorDetection]:
        if seismic_mags is None:
            return []

        # detect_seismic_cluster espera un conteo de 24 h. Antes se le pasaba
        # el de la ventana completa del fetch (30 días), así que comparaba
        # ~800 eventos contra un umbral pensado para un día: siempre disparaba.
        if m4_count_24h is not None:
            m4_count = int(m4_count_24h)
        else:
            m4_count = int(np.sum(seismic_mags >= 4.0))
        if not detect_seismic_cluster(m4_count):
            return []

        confidence = 0.7
        if m4_count >= 20:
            confidence += 0.15
        max_mag = float(np.max(seismic_mags))
        if max_mag >= 5.5:
            confidence += 0.1

        return [PrecursorDetection(
            tipo=PrecursorType.SEISMIC_CLUSTER,
            display_name=PRECURSOR_DISPLAY_NAMES[PrecursorType.SEISMIC_CLUSTER],
            station="regional",
            lat=None,
            lon=None,
            confidence=min(confidence, 0.95),
            values={
                "event_count": m4_count,
                "max_magnitude": max_mag,
                "total_events": len(seismic_mags),
            },
        )]

    def _scan_volcanic(
        self,
        air_quality: Dict[str, Any],
        seismic_mags: Optional[Any],
        atmospheric: List[Dict[str, Any]],
    ) -> List[PrecursorDetection]:
        so2 = air_quality.get("so2", 0.0)
        seismic_count = 0
        if seismic_mags is not None:
            seismic_count = int(np.sum(seismic_mags >= 3.0))

        if not detect_volcanic_precursor(so2, seismic_count):
            return []

        confidence = 0.6
        if so2 > 200:
            confidence += 0.15
        if seismic_count >= 10:
            confidence += 0.1

        lat, lon = None, None
        station = "regional"
        if atmospheric:
            station = atmospheric[0].get("station", "regional")
            lat = atmospheric[0].get("lat")
            lon = atmospheric[0].get("lon")

        return [PrecursorDetection(
            tipo=PrecursorType.VOLCANICO,
            display_name=PRECURSOR_DISPLAY_NAMES[PrecursorType.VOLCANICO],
            station=station,
            lat=lat,
            lon=lon,
            confidence=min(confidence, 0.95),
            values={
                "so2_mass": so2,
                "seismic_count": seismic_count,
            },
        )]

    def _scan_schumann(
        self, schumann_hz: Optional[float], schumann_pct: Optional[float]
    ) -> List[PrecursorDetection]:
        # RUTA SILENCIADA POR DISEÑO desde el retiro del Hz (2026-10-09):
        # el fetcher ya no fabrica `7,83 + actividad×0,02`, así que
        # `schumann_hz` llega None SIEMPRE y esta detección no dispara.
        # Se mantiene la rama completa para el día que exista una fuente de
        # FRECUENCIA calibrada en vivo (Eskdalemuir es la candidata); mientras
        # tanto, inventar un umbral sobre la ACTIVIDAD sin su distribución
        # medida sería numerología (regla 8).
        if schumann_hz is None:
            return []

        deviation = abs(schumann_hz - 7.83)
        if deviation < 0.5 and (schumann_pct is None or schumann_pct < 150):
            return []

        confidence = 0.5
        if deviation >= 1.0:
            confidence += 0.2
        if schumann_pct is not None and schumann_pct >= 200:
            confidence += 0.15

        return [PrecursorDetection(
            tipo=PrecursorType.SCHUMANN,
            display_name=PRECURSOR_DISPLAY_NAMES[PrecursorType.SCHUMANN],
            station="global",
            lat=None,
            lon=None,
            confidence=min(confidence, 0.95),
            values={
                "schumann_hz": schumann_hz,
                "deviation_hz": deviation,
                "schumann_activity_pct": schumann_pct,
            },
        )]

    def _scan_tormenta_solar(
        self, bz_min: Optional[float], kp_max: Optional[float],
        viento_max: Optional[float],
    ) -> List[PrecursorDetection]:
        """Tormenta geomagnética: GRIETA (Bz sur profundo) + Kp de tormenta.

        Recalibrado el 2026-10-12 contra 287.178 h de historia (regla 8):
        la compuerta vieja leía las MEDIAS de ventana (bz ≤ −10 Y kp ≥ 5)
        y sólo se cruzaba en las tormentas del siglo — 187 h en 30 años,
        **0 en 1.770 h vivas**, incluida la del 10-oct (Kp 7, Bz_min −28,9,
        2 h de pico que la media de 24 h diluyó a ~−3). TORMENTA_SOLAR no
        disparó NI UNA VEZ en toda la historia de TBL_DETECCIONES.

        La nueva lee EXTREMOS: bz_min(24 h) ≤ −10 ∧ kp_max(6 h) ≥ 5.
        Coincidencia por hora en el histórico: 1.305 h (0,45 %) — dispara
        en tormentas reales y casi nunca en calma. Sin dato (None), no
        dispara: ausencia no es cero (regla 7).
        """
        if bz_min is None or kp_max is None:
            return []
        if bz_min > -10.0 or kp_max < 5.0:
            return []

        confidence = 0.7
        if bz_min < -20.0:
            confidence += 0.15
        if viento_max is not None and viento_max > 600:
            confidence += 0.1

        return [PrecursorDetection(
            tipo=PrecursorType.TORMENTA_SOLAR,
            display_name=PRECURSOR_DISPLAY_NAMES[PrecursorType.TORMENTA_SOLAR],
            station="global",
            lat=None,
            lon=None,
            confidence=min(confidence, 0.95),
            values={
                "bz_min_nT": bz_min,
                "kp_max": kp_max,
                "viento_max_kms": viento_max,
            },
        )]

    def _scan_perturbacion_geomagnetica(
        self, bz_min_2h: Optional[float], kp_max_2h: Optional[float],
    ) -> List[PrecursorDetection]:
        """Perturbación moderada AHORA: cortes de 2 h (2026-10-13, operador).

        La versión de ventana de 24 h convertía UNA hora de grieta en 24 de
        bandera: medido ese día, 1 hora real de disturbio (Bz mín −8,7) dejó
        la detección en el 93 % de los ciclos y el muro en breach sostenido.
        Con cortes de 2 h, contra 30 años de la tabla horaria:
        **4,64 %/h** de tasa, rachas medianas de 3 h (p90: 7 h, máx 33 h) —
        fluctúa con el disturbio real: ese mismo día habría estado activa
        5 h en 3 episodios (01-03, 11-13, 15-16).

        La TORMENTA conserva su ventana de 24 h a propósito: una tormenta
        ES un estado de días; una perturbación es un estado de horas.
        Si el corte de 2 h cumple la compuerta de tormenta, esto calla.
        Sin dato (None) no dispara: ausencia no es cero (regla 7).
        """
        if bz_min_2h is None or kp_max_2h is None:
            return []
        if bz_min_2h > -5.0 or kp_max_2h < 3.0:
            return []
        if bz_min_2h <= -10.0 and kp_max_2h >= 5.0:
            return []

        confidence = 0.55
        if abs(bz_min_2h) > 7:
            confidence += 0.1
        if kp_max_2h >= 4:
            confidence += 0.1

        return [PrecursorDetection(
            tipo=PrecursorType.PERTURBACION_GEOMAGNETICA,
            display_name=PRECURSOR_DISPLAY_NAMES[PrecursorType.PERTURBACION_GEOMAGNETICA],
            station="global",
            lat=None,
            lon=None,
            confidence=min(confidence, 0.95),
            values={
                "bz_min_2h_nT": bz_min_2h,
                "kp_max_2h": kp_max_2h,
            },
        )]

    def _scan_sprites_rojos(
        self, atmospheric: List[Dict[str, Any]]
    ) -> List[PrecursorDetection]:
        results = []
        for reading in atmospheric:
            weather_id = reading.get("weather_id")
            temp_c = reading.get("temp_c")
            pressure = reading.get("pressure_hpa")
            clouds = reading.get("clouds_pct")
            # Sin dato → sin evaluación de sprite (regla 7/8): antes
            # weather_id 800/20 °C simulaban cielo despejado medido.
            if None in (weather_id, temp_c, pressure, clouds):
                continue

            if detect_sprite_rojo(weather_id, temp_c, pressure, clouds):
                confidence = 0.65
                if pressure < 1000:
                    confidence += 0.15
                if temp_c > 32:
                    confidence += 0.1

                results.append(PrecursorDetection(
                    tipo=PrecursorType.SPRITE_ROJO,
                    display_name=PRECURSOR_DISPLAY_NAMES[PrecursorType.SPRITE_ROJO],
                    station=reading.get("station", "unknown"),
                    lat=reading.get("lat"),
                    lon=reading.get("lon"),
                    confidence=min(confidence, 0.95),
                    values={
                        "weather_id": weather_id,
                        "temp_c": temp_c,
                        "pressure_hpa": pressure,
                        "clouds_pct": clouds,
                    },
                ))
        return results

    def _scan_hurricanes(
        self, hurricane_data: Dict[str, Any]
    ) -> List[PrecursorDetection]:
        cyclones = hurricane_data.get("active_cyclones", [])
        results = []
        for cyc in cyclones:
            category = cyc.get("category", 0)
            distance = cyc.get("distance_deg", 999)

            if not detect_hurricane_proximity(category, distance):
                continue

            confidence = 0.6
            if category >= 3:
                confidence += 0.2
            elif category >= 2:
                confidence += 0.1
            if distance < 5:
                confidence += 0.1

            results.append(PrecursorDetection(
                tipo=PrecursorType.HURACAN,
                display_name=PRECURSOR_DISPLAY_NAMES[PrecursorType.HURACAN],
                station=cyc.get("name", "unknown"),
                lat=cyc.get("lat"),
                lon=cyc.get("lon"),
                confidence=min(confidence, 0.95),
                values={
                    "category": category,
                    "max_wind_kt": cyc.get("max_wind_kt", 0),
                    "pressure_mb": cyc.get("pressure_mb", 1013),
                    "distance_deg": distance,
                },
            ))
        return results

    def _scan_tsunami(
        self,
        seismic_mags: Optional[Any],
        delta_data: Dict[str, Any],
        beta1_data: Optional[Dict[str, Any]] = None,
    ) -> List[PrecursorDetection]:
        if seismic_mags is None or len(seismic_mags) == 0:
            return []

        max_mag = float(np.max(seismic_mags))
        # La profundidad es la del sismo de mayor magnitud, escrita junto a
        # las magnitudes (beta1). delta solo conserva pruebas que ya la
        # pasaban ahí. Si falta, falta: no se usa 30 ni 0.
        if isinstance(beta1_data, dict) and "max_quake_depth_km" in beta1_data:
            raw_depth = beta1_data.get("max_quake_depth_km")
        elif isinstance(delta_data, dict) and "max_quake_depth_km" in delta_data:
            raw_depth = delta_data.get("max_quake_depth_km")
        else:
            raw_depth = None
        if raw_depth is None:
            return []
        try:
            depth_km = float(raw_depth)
        except (TypeError, ValueError):
            return []
        if not np.isfinite(depth_km):
            return []

        if not detect_tsunami_potential(max_mag, depth_km):
            return []

        confidence = 0.7
        if max_mag >= 8.0:
            confidence += 0.15
        if depth_km < 30:
            confidence += 0.1

        return [PrecursorDetection(
            tipo=PrecursorType.TSUNAMI,
            display_name=PRECURSOR_DISPLAY_NAMES[PrecursorType.TSUNAMI],
            station="regional",
            lat=None,
            lon=None,
            confidence=min(confidence, 0.95),
            values={
                "magnitude": max_mag,
                "depth_km": depth_km,
            },
        )]

    def _scan_financial_correlation(
        self, financial_data: Dict[str, Any]
    ) -> List[PrecursorDetection]:
        fear_greed = financial_data.get("fear_greed", 50)
        vix = financial_data.get("vix", 20.0)
        btc_change = financial_data.get("btc_change_pct", 0.0)
        market_signal = financial_data.get("market_signal", "neutral")

        extreme_fear = fear_greed < 20
        vix_spike = vix > 30
        btc_crash = btc_change < -10.0
        bearish = market_signal in ("bearish", "alert")

        active_signals = sum([extreme_fear, vix_spike, btc_crash, bearish])
        if active_signals < 2:
            return []

        confidence = 0.5 + (active_signals * 0.1)

        return [PrecursorDetection(
            tipo=PrecursorType.CORRELACION_FINANCIERA,
            display_name=PRECURSOR_DISPLAY_NAMES[PrecursorType.CORRELACION_FINANCIERA],
            station="global",
            lat=None,
            lon=None,
            confidence=min(confidence, 0.95),
            values={
                "fear_greed": fear_greed,
                "vix": vix,
                "btc_change_pct": btc_change,
                "market_signal": market_signal,
                "active_financial_signals": active_signals,
            },
        )]

    def _scan_precipitacion(
        self,
        atmospheric: List[Dict[str, Any]],
        schumann_hz: Optional[float],
    ) -> List[PrecursorDetection]:
        """
        Detect anomalous precipitation potential via the Schumann-modular formula:

            Π_i(t) = μ_i(t) · ( Φ_i(t)  mod  Φ_S(t) )

        where μ_i is local humidity, Φ_i is the regional atmospheric energy
        flux proxy, and Φ_S is the Schumann modal reference scale.
        A high Π_i means large residual energy (not absorbed by the global
        resonator) is available to couple with moisture and reorganise as
        precipitation.

        RUTA SILENCIADA POR DISEÑO desde el retiro del Hz (2026-10-09): esta
        fórmula usaba la «frecuencia» fabricada como escala modal, o sea
        que medía una recta sobre un conteo de píxeles. Con hz=None SIEMPRE
        retorna vacío; se mantiene por si una frecuencia calibrada vuelve.
        """
        if schumann_hz is None or schumann_hz <= 0:
            return []

        results = []
        for reading in atmospheric:
            humidity = reading.get("humidity_pct", 50.0)
            temp_c = reading.get("temp_c", 20.0)
            clouds = reading.get("clouds_pct", 0.0)

            if not detect_precipitacion_potencial(humidity, temp_c, clouds, schumann_hz):
                continue

            pi_i = compute_precipitacion_potencial(humidity, temp_c, clouds, schumann_hz)

            confidence = _PREC_CONF_BASE
            if humidity >= _PREC_HUMIDITY_HIGH:
                confidence += _PREC_CONF_HUMIDITY_BOOST
            if clouds >= _PREC_CLOUDS_HIGH:
                confidence += _PREC_CONF_CLOUDS_BOOST
            if pi_i >= _PREC_PI_VERY_HIGH:
                confidence += _PREC_CONF_PI_BOOST

            results.append(PrecursorDetection(
                tipo=PrecursorType.PRECIPITACION,
                display_name=PRECURSOR_DISPLAY_NAMES[PrecursorType.PRECIPITACION],
                station=reading.get("station", "unknown"),
                lat=reading.get("lat"),
                lon=reading.get("lon"),
                confidence=min(confidence, 0.95),
                values={
                    "humidity_pct": humidity,
                    "temp_c": temp_c,
                    "clouds_pct": clouds,
                    "schumann_hz": schumann_hz,
                    "pi_i": round(pi_i, 3),
                },
            ))
        return results
