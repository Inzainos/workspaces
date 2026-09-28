"""Dos defectos que se comían datos y mantenimiento en silencio.

Encontrados el 2026-09-28 tirando del hilo que dio el operador: «beta1 se
refresca pero repite el mismo valor: la fuente no está midiendo». Tenía razón, y
la causa estaba dos capas más abajo.

1. ESCRITURAS PERDIDAS POR EL CANDADO
-------------------------------------
Seis escrituras por ciclo fallaban con «database is locked» --- el LOCF de
alfa1, beta1, beta2 y delta, la persistencia sísmica y la del clima horario ---
y las seis son fail-soft, así que el ciclo terminaba «bien». Consecuencia
visible: `tbl_clima_espacial_raw` dejó de crecer a las 02:00, las ventanas de
336 h y 72 h del Kp se congelaron en ese borde, y beta1 devolvió exactamente
0,3665 durante doce ciclos seguidos.

La contención no era accidental: `sentinel-omega-rutinas` corría cada 15 min y
tardaba ~5, como root, así que se solapaba con el ciclo casi siempre.

El ciclo vivo usaba el defecto de SQLite (5 s) mientras los lotes ya tenían 120.
Ahora la conexión lleva `busy_timeout` de 120 s: esperar cabe en un ciclo de
~300 s; perder el dato, no.

2. EL MANTENIMIENTO DIARIO NO PODÍA CORRER NUNCA
------------------------------------------------
`sentinel-omega-mantenimiento.service` fallaba SIEMPRE con exit 1:

    ERROR Sentinel Omega is already running. Use shutdown.py first.

El guardián de instancia única se aplicaba también a los flags de tarea, y el
launcher está arriba por diseño. Se había atribuido a un timer duplicado; la
causa era ésta. Sin barrido no hay compactación, ni correlaciones, ni sesgo, ni
poda cimática.

Y quitar el guardián a secas habría sido peor: `_write_pid()` corría también en
modo tarea, así que el lote **pisaba el pid del launcher vivo** y `_clear_pid()`
lo borraba al salir, dejando ciegos a `shutdown.py` y al watchdog.

Verificado de punta a punta el 2026-09-28 con el launcher vivo:
`launcher.py --disciplina --barrido --dry-run` → exit 0, barrido completo, y el
pid siguió apuntando al proceso correcto.
"""
import inspect

import pytest


class TestEsperaDelCandado:

    def test_la_conexion_viva_espera_120_segundos(self, tmp_path):
        """El defecto de SQLite son 5 s y no alcanzan contra un escritor vivo."""
        import sqlite3

        from sentinel_omega.infrastructure.database.schema import (
            ESPERA_CANDADO_S, get_connection,
        )
        db = tmp_path / "t.db"
        sqlite3.connect(db).close()
        conn = get_connection(str(db))
        ms = conn.execute("PRAGMA busy_timeout").fetchone()[0]
        assert ms == int(ESPERA_CANDADO_S * 1000), (
            f"busy_timeout es {ms} ms; se esperaban {int(ESPERA_CANDADO_S*1000)}")
        assert ESPERA_CANDADO_S >= 60, "menos de un minuto no cubre la contención medida"

    def test_es_el_mismo_presupuesto_que_los_lotes(self):
        """Los lotes ya esperaban 120 s. Que el ciclo vivo esperara 5 era el
        desajuste, no al revés."""
        from sentinel_omega.infrastructure.database.schema import ESPERA_CANDADO_S
        from sentinel_omega.infrastructure.pipeline.entrenamiento import (
            ESPERA_CANDADO_S as LOTES,
        )
        assert ESPERA_CANDADO_S == LOTES

    def test_cabe_en_un_ciclo(self):
        """Esperar no puede costar más que el intervalo entre ciclos."""
        from sentinel_omega.infrastructure.database.schema import ESPERA_CANDADO_S
        assert ESPERA_CANDADO_S < 300, "la espera se comería el ciclo siguiente"


class TestModoTarea:
    """El lote corre su trabajo y sale; no compite con el ciclo vivo."""

    @pytest.fixture
    def fuente(self):
        from sentinel_omega import launcher
        return inspect.getsource(launcher.run)

    def test_el_guardian_no_aplica_a_los_lotes(self, fuente):
        assert "if not tarea_batch and _check_already_running():" in fuente, (
            "el guardián volvió a ser incondicional: el mantenimiento diario "
            "fallará con exit 1 mientras el launcher esté arriba, que es siempre")

    def test_el_lote_no_toca_el_pid(self, fuente):
        assert "if not tarea_batch:\n        _write_pid()" in fuente, (
            "el lote volvió a escribir el pid: pisaría el del ciclo vivo")
        cuerpo = fuente[fuente.index("if tarea_batch:\n        logger.info"):]
        salida = cuerpo[:cuerpo.index("return") + 6]
        assert "_clear_pid()" not in salida, (
            "el lote borra el pid al salir y deja ciegos a shutdown.py y al "
            "watchdog")

    def test_los_cinco_flags_cuentan_como_tarea(self, fuente):
        """Si alguno se queda fuera, ese vuelve a chocar con el guardián."""
        for flag in ("backcast", "entrenar", "disciplina", "barrido", "reporte"):
            assert f"args.{flag}" in fuente, flag

    def test_con_once_sigue_siendo_ciclo(self, fuente):
        """`--once` es bootstrap: tareas MÁS un ciclo, así que sí necesita el
        guardián y sí escribe el pid."""
        assert "and not args.once" in fuente
