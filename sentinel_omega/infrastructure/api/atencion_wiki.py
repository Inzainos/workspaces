"""
Atención colectiva vía Wikipedia pageviews — sustituto libre de Google Trends.

Por qué existe (2026-10-19): `pytrends` lleva días devolviendo HTTP 400 en
cada ciclo (Google cambió el endpoint de Trends sin aviso; el patrón está
documentado en los logs del launcher). El rasgo `trends_mean` de delta leía
así la última fila real de `tbl_trends_vivo` — congelada desde entonces.

La API de X/Twitter NO es alternativa: su capa gratuita sólo permite
*publicar*; el endpoint de búsqueda/conteo —lo único que mediría atención
colectiva— exige el tier Basic de pago. Reddit exige OAuth. GDELT es viable
pero mide cobertura noticiosa, no curiosidad pública.

Los pageviews de Wikipedia son EL sustituto académico estándar de Google
Trends para medir atención pública (usados en investigación de salud,
finanzas y eventos desde ~2013): gratis, sin key, sin OAuth, y con una API
REST estable de Wikimedia.

API: /metrics/pageviews/per-article/{proyecto}/all-access/user/{artículo}/
daily/{YYYYMMDD}/{YYYYMMDD}. El rango NO puede cruzar mes — se parte por
mes. `agent=user` excluye bots: es humanos curiosos, no scrapers.

⚠ CAMBIO DE ESCALA documentado: `solar_interest` pasaba de 0–100 (escala
relativa de Google) a PAGEVIEWS CRUDOS (cientos–miles/día). El rasgo
`trends_mean` de delta cambia de magnitud el 2026-10-19:
  - ONNX: sin impacto — la compuerta deshabilitó los siete modelos.
  - Firmas: `trends_mean` entró a BOT_FEATURES[delta] el 18-oct y las
    ventanas vivas hasta hoy compartían el ÚLTIMO valor congelado (varianza
    cero), así que el emparejamiento de esa dimensión ya era degenerado.
    Documentado en BITACORA_2026-10-19; se normaliza en el próximo rebuild.

Contrato igual al de `fetch_solar_storm_trends`: DataFrame ['date',
'solar_interest', <por-artículo...>], None si no hay dato (regla 7).
"""

import logging
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional

import pandas as pd

from sentinel_omega.infrastructure.api._http import get_session

logger = logging.getLogger(__name__)

_API = (
    "https://wikimedia.org/api/rest_v1/metrics/pageviews/per-article/"
    "en.wikipedia/all-access/user/{articulo}/daily/{desde}/{hasta}"
)
_TIMEOUT = 15
# Política de Wikimedia: User-Agent descriptivo con contacto.
_HEADERS = {"User-Agent": "SentinelOmega/2.5.4 (research; contact: local-ops)"}

# Vocabulario solar espejo del de google_trends: la tormenta y sus síntomas.
ARTICULOS = ["Solar_flare", "Geomagnetic_storm", "Solar_wind"]


def _por_mes(desde: datetime, hasta: datetime) -> List[tuple[str, str]]:
    """[(desde_YYYYMMDD, hasta_YYYYMMDD)] partiendo el rango por mes.

    El endpoint per-article rechaza rangos que cruzan el límite de mes con
    400, así que el mes de arranque y el de corte van en peticiones aparte.
    """
    tramos: List[tuple[str, str]] = []
    actual = desde.replace(day=1)
    while actual <= hasta:
        fin_mes = (
            (actual.replace(day=28) + timedelta(days=4)).replace(day=1)
            - timedelta(days=1)
        )
        ini = max(desde, actual)
        fin = min(hasta, fin_mes)
        tramos.append((ini.strftime("%Y%m%d"), fin.strftime("%Y%m%d")))
        actual = fin_mes + timedelta(days=1)
    return tramos


def fetch_atencion_wiki(dias: int = 8) -> Optional[pd.DataFrame]:
    """Pageviews diarios (agent=user) del vocabulario solar en en.wikipedia.

    Devuelve DataFrame ['date', 'solar_interest', <por-artículo>] donde
    `solar_interest` es el MÁXIMO entre artículos del día — el mismo
    contrato de "la señal de atención más fuerte" que usaba Trends, para
    que el consumidor (`trends_df`) no cambie de forma.
    """
    hoy = datetime.now(timezone.utc).date()
    desde = hoy - timedelta(days=dias)
    tramos = _por_mes(
        datetime(desde.year, desde.month, desde.day),
        datetime(hoy.year, hoy.month, hoy.day),
    )
    session = get_session()
    vistas: Dict[str, Dict[str, int]] = {}   # 'YYYY-MM-DD' -> {artículo: n}
    for articulo in ARTICULOS:
        for d_str, h_str in tramos:
            url = _API.format(articulo=articulo, desde=d_str, hasta=h_str)
            try:
                resp = session.get(url, timeout=_TIMEOUT, headers=_HEADERS)
                if resp.status_code == 404:
                    # Sin datos para ese tramo (artículo nuevo / fecha futura
                    # en UTC): no es error, simplemente no hay filas.
                    continue
                resp.raise_for_status()
                for item in resp.json().get("items", []):
                    # timestamp llega 'YYYYMMDD00' — se normaliza a fecha.
                    ts = str(item.get("timestamp", ""))
                    if len(ts) < 8:
                        continue
                    dia = f"{ts[0:4]}-{ts[4:6]}-{ts[6:8]}"
                    vistas.setdefault(dia, {})[articulo] = int(item.get("views", 0))
            except Exception as e:  # noqa: BLE001 — fail-soft, como Trends
                logger.warning(
                    "Wikipedia pageviews falló para %s (%s→%s): %s",
                    articulo, d_str, h_str, e,
                )
    if not vistas:
        logger.warning("Wikipedia pageviews sin datos en la ventana")
        return None
    filas = []
    for dia, por_art in sorted(vistas.items()):
        fila: Dict[str, object] = {"date": pd.Timestamp(dia)}
        for articulo in ARTICULOS:
            fila[articulo] = por_art.get(articulo, 0)
        fila["solar_interest"] = max(
            int(por_art.get(a, 0)) for a in ARTICULOS
        )
        filas.append(fila)
    df = pd.DataFrame(filas).sort_values("date").reset_index(drop=True)
    logger.info(
        "Atención Wikipedia: %d días, %d artículos (máx %d/día)",
        len(df), len(ARTICULOS), int(df["solar_interest"].max()),
    )
    return df
