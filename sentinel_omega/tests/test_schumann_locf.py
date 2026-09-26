"""Una señal congelada no es una señal.

Auditado el 2026-09-26: `tbl_schumann_vivo` tenía 38 filas con **un único
valor** (8,26 Hz / 21,46 %). La fuente real (Tomsk) devolvía 404 desde el día
24, y el respaldo LOCF --- arrastrar la última lectura buena --- lo hacía **sin
límite de edad** y además **volvía a guardar** el valor arrastrado como si fuera
la medición de esa hora. Así se perpetuaba solo.

Schumann entra en el Fantasma, el termómetro principal, donde ese valor fijo
aportaba un desplazamiento constante: dejó de informar y nadie se enteró porque
el número seguía apareciendo.
"""
import inspect

from sentinel_omega import launcher


def test_el_arrastre_tiene_limite_de_edad():
    assert launcher.SCHUMANN_LOCF_HORAS > 0
    assert launcher.SCHUMANN_LOCF_HORAS <= 24, (
        "arrastrar mas de un dia una senal horaria es inventar")


def test_la_consulta_del_arrastre_filtra_por_fecha():
    fuente = inspect.getsource(launcher)
    i = fuente.index("FROM tbl_schumann_vivo")
    bloque = fuente[i - 400:i + 400]
    assert "timestamp_blk >= ?" in bloque, (
        "el LOCF tomaba la ultima fila sin mirar cuando era")
    assert "SCHUMANN_LOCF_HORAS" in bloque


def test_lo_arrastrado_no_se_vuelve_a_guardar():
    """La regresión exacta: re-guardarlo lo convertía en una medición nueva cada
    hora y hacía eterno el valor congelado."""
    fuente = inspect.getsource(launcher)
    assert "venia_de_locf" in fuente
    i = fuente.index("venia_de_locf = True")
    j = fuente.index("if venia_de_locf:", i)
    assert j > i, "la marca tiene que consultarse DESPUES de ponerla"


def test_sin_lectura_reciente_el_valor_es_desconocido():
    fuente = inspect.getsource(launcher)
    assert "Schumann DESCONOCIDO" in fuente
    # Y no se rellena con la frecuencia de libro (7,83 Hz), que es el cero
    # sintético clásico de esta señal.
    i = fuente.index("Schumann DESCONOCIDO")
    assert "7.83" not in fuente[i - 300:i + 300]


def test_el_placeholder_de_libro_sigue_reconociendose():
    from sentinel_omega.infrastructure.api.schumann import is_baseline_placeholder
    assert is_baseline_placeholder(7.83, 0.0) is True
    assert is_baseline_placeholder(8.26, 21.46) is False
    assert is_baseline_placeholder(None, None) is True
