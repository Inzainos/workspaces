"""Un modelo que devuelve una constante no es un modelo: es una alarma fija.

Qué pasó (2026-10-07, persiguiendo 159 falsos positivos)
--------------------------------------------------------
Los ocho ONNX reentrenados en `53f51e7` (5-oct 17:06) salieron devolviendo
prácticamente un número fijo. Desviación típica de la confianza sobre 27 ciclos
vivos de cada bot:

    beta2 0,0026 · loki 0,0100 · omega 0,0149 · beta1 0,0153
    delta 0,0183 · jupiter 0,0199        contra        alfa1 0,1663

`loki` devolvía 0,736 ± 1,4 % en todos los ciclos. Eso no responde al dato:
devuelve el promedio del objetivo.

Lo que costó, medido:

    cinco bots (padre, omega, loki, delta, alfa2) alarmaron el 100 % de los ciclos
    ganancia de Molchan a 2 h: 0,81x   --- PEOR QUE EL AZAR
    159 falsos positivos contra 55 aciertos
    seis de los nueve pesos en el suelo de 0,300, y con peso <0,6 el consenso
    degrada todo a WATCH

Y la correlación que cierra el caso: **cuanto menos alarma un bot, mejor su
peso**. `beta2` (36 % de alarma) tenía 0,926; los que alarmaban al 100 %,
0,30-0,47. `alfa1`, el único modelo que VARÍA, es también el único de los
alarmantes que no llegaba al 100 %.

El canario ya había cantado
---------------------------
La suite llevaba ROJA desde el 5-oct con el diagnóstico escrito, y nadie miró:

    «el fantasma VOLVIÓ: con el Kp ausente sale WATCH 0.599»
        test_fantasma_alfa1_kp_cero
    «loki: el modelo volvió a alarmar con kp_mean bajo (WATCH 0.7399)
     --- la fuga de procedencia regresó»
        test_claves_omega_loki

Esta prueba existe para que la próxima vez el rojo diga *constante*, que es la
causa, y no solo *alarmó*, que es el síntoma.
"""
import pytest

from sentinel_omega.config.onnx_config import onnx_config

# Por debajo de esto, la confianza no lleva información: es ruido alrededor de
# un valor fijo. Medido --- los apagados están en 0,0026-0,0183 y alfa1, que sí
# discrimina, en 0,1663. El corte en 0,02 cae limpio en ese hueco.
DESVIACION_MINIMA = 0.02

# Lo que se midió el 2026-10-07, para que el umbral de arriba no sea numerología.
DESVIACIONES_MEDIDAS = {
    "beta2": 0.0026, "loki": 0.0100, "omega": 0.0149, "beta1": 0.0153,
    "delta": 0.0183, "jupiter": 0.0199, "alfa1": 0.1663,
}

CONSTANTES_APAGADOS = {"beta1", "beta2", "delta", "loki", "omega"}


@pytest.mark.parametrize("bot", sorted(CONSTANTES_APAGADOS))
def test_los_modelos_constantes_siguen_apagados(bot):
    assert getattr(onnx_config, bot).enabled is False, (
        f"{bot} se encendió. Antes de hacerlo hay que REENTRENAR y comprobar "
        f"que la desviación típica de su confianza sube de {DESVIACION_MINIMA}: "
        f"el 2026-10-07 era {DESVIACIONES_MEDIDAS[bot]}, o sea un número fijo. "
        "Encenderlo constante es volver a alarmar sin información.")


def test_alfa1_sigue_encendido_porque_SI_varia():
    """Es el único con discriminación real (0,1663). Apagarlo por error dejaría
    al sistema sin ningún modelo que responda al dato."""
    assert onnx_config.alfa1.enabled is True, (
        "se apagó alfa1, el único modelo cuya confianza varía de verdad "
        f"({DESVIACIONES_MEDIDAS['alfa1']} contra <0,02 de los demás)")


def test_jupiter_sigue_encendido_porque_FRENA_su_regla():
    """Contraintuitivo y medido: el modelo de jupiter dice NEUTRAL 22/22 y su
    REGLA dice watch en el 22 % de los ciclos. Apagarlo SUBIRÍA su alarma del
    0 % al 22 %. No todo modelo apagado mejora el sistema."""
    assert onnx_config.jupiter.enabled is True, (
        "se apagó jupiter: su modelo estaba frenando los watches de su regla, "
        "así que apagarlo sube su alarma del 0 % al 22 %")


# `jupiter` mide 0,0199 --- por debajo del corte --- y sigue ENCENDIDO a
# propósito: su modelo dice NEUTRAL 22/22 y está frenando los watches de su
# propia regla, así que apagarlo SUBIRÍA su alarma del 0 % al 22 %. Es la única
# excepción y va con su medición al lado, para que no se pueda añadir otra sin
# una.
EXCEPCIONES_MEDIDAS = {
    "jupiter": "su NEUTRAL frena los watches de su propia regla (0 % contra 22 %)",
}


def test_el_corte_y_lo_apagado_se_derivan_de_la_misma_medicion():
    """Lo que esta prueba comprobaba antes era **nada** (hallado 2026-10-07).

    Decía:

        constantes = [v for b, v in DESVIACIONES_MEDIDAS.items() if b not in ...]
        assert max(constantes) < DESVIACION_MINIMA < DESVIACIONES_MEDIDAS["alfa1"]

    O sea: afirmaba relaciones entre literales del PROPIO archivo. No puede
    fallar salvo que alguien edite los literales, y no toca el sistema por
    ningún lado. Parecía una calibración contra datos --- regla dura 8 --- y era
    documentación disfrazada de prueba.

    Ahora el corte es load-bearing: de la medición se DERIVA qué tiene que estar
    apagado, y eso se compara contra `onnx_config`, que es el sistema. Así
    `DESVIACIONES_MEDIDAS` deja de ser decorativo --- tocar un número cambia el
    conjunto derivado y la prueba cae, que es lo correcto: esos números son
    historia medida, y cambiarlos es reescribirla.
    """
    derivados = {b for b, v in DESVIACIONES_MEDIDAS.items()
                 if v < DESVIACION_MINIMA and b not in EXCEPCIONES_MEDIDAS}
    assert derivados == CONSTANTES_APAGADOS, (
        f"la medición ya no deriva en la lista de apagados: de "
        f"DESVIACIONES_MEDIDAS sale {sorted(derivados)} y CONSTANTES_APAGADOS "
        f"dice {sorted(CONSTANTES_APAGADOS)}. Si cambió una medición, cambia la "
        "lista; si cambió la lista, trae la medición que lo respalde")
    for bot in derivados:
        assert getattr(onnx_config, bot).enabled is False, (
            f"{bot} mide {DESVIACIONES_MEDIDAS[bot]} (por debajo de "
            f"{DESVIACION_MINIMA}) y está ENCENDIDO en onnx_config")
    # Y que el hueco siga existiendo: si un día un «constante» sube por encima
    # del corte, lo que hay que hacer es reentrenar y volver a medir, no mover
    # el corte para que siga cuadrando.
    assert max(DESVIACIONES_MEDIDAS[b] for b in derivados) < DESVIACION_MINIMA




def test_queda_al_menos_un_modelo_vivo():
    """El sistema no puede quedarse sin ninguna rama ML sin que alguien lo
    decida: si todos se apagan, que falle aquí y se vea."""
    from sentinel_omega.core.features_onnx import BOT_DIMS

    vivos = [b for b in BOT_DIMS if getattr(onnx_config, b).enabled]
    assert vivos, "se apagaron TODOS los modelos ONNX"
    assert "alfa1" in vivos, vivos
