"""Blanco del reporte: M>=6.0 en 24 h. El umbral del muro sigue en 3."""

from pathlib import Path

from sentinel_omega.core.precursor.baseline import es_blanco_del_reporte
from sentinel_omega.core.precursor.muro_cinco_eventos import MuroCincoEventos

ROOT = Path(__file__).resolve().parents[2]


def test_m6_dentro_de_24h_si_cuenta():
    assert es_blanco_del_reporte(6.0, 0.0) is True
    assert es_blanco_del_reporte(6.0, 24.0) is True
    assert es_blanco_del_reporte(7.4, 12.0) is True


def test_bajo_de_m6_no_cuenta():
    assert es_blanco_del_reporte(5.9, 1.0) is False


def test_fuera_de_24h_no_cuenta():
    assert es_blanco_del_reporte(6.5, 24.01) is False
    assert es_blanco_del_reporte(8.0, -0.1) is False


def test_dato_ausente_no_cuenta():
    assert es_blanco_del_reporte(None, 1.0) is False
    assert es_blanco_del_reporte(6.2, None) is False


def test_el_umbral_del_muro_sigue_en_tres():
    assert MuroCincoEventos().min_walls_for_breach == 3
    runners = (ROOT / "sentinel_omega/infrastructure/pipeline/layer_runners.py").read_text()
    assert "min_walls_for_breach=3" in runners
    periodico = (ROOT / "deploy/reporte_periodico.py").read_text()
    assert "3 o más" in periodico
    assert "BLANCO_REPORTE_MAGNITUD" in periodico
    assert "BLANCO_REPORTE_VENTANA_H" in periodico
    generar = (ROOT / "deploy/generar_reporte.py").read_text()
    assert "Muro ≥3/5" in generar
    assert "BLANCO_REPORTE_MAGNITUD" in generar
    assert "tiene un M4.5+" not in generar


def test_el_glosario_no_reetiqueta_el_conteo_historico():
    aciertos = (ROOT / "deploy/aciertos_reporte.py").read_text()
    periodico = (ROOT / "deploy/reporte_periodico.py").read_text()
    generar = (ROOT / "deploy/generar_reporte.py").read_text()
    assert "SUM(CASE WHEN resultado = 'ACIERTO' THEN 1 ELSE 0 END)" in aciertos
    assert "j.ventana_h / 24.0" in aciertos
    assert "es_blanco_del_reporte" not in aciertos
