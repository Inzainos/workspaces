"""El tiempo de vida de una firma, en horas y para los nueve bots.

Pedido del operador el 2026-09-27: *«que todo eso tiene que estar en el
entrenamiento […] si una firma es idéntica a una que vimos en el pasado podremos
intuir que tiene cierto tiempo de vida»*.

Estaba implementado a medias. Medido ese día:

  * **182 de 19.578 firmas** tenían `lag_promedio_h`, y las 182 eran de `padre`
    --- había un filtro fijo `if f["bot_name"] == "padre"`.
  * La rejilla `[336, 240, 168, 120, 72, 24]` tiene huecos de 48 a 96 h, así que
    medía en DÍAS. De 37 valores distintos, los seis puntos de la rejilla
    concentraban las firmas y el resto eran promedios de dos o tres puntos.
  * Y como el barrido va de lejos a cerca y para en el primer emparejamiento,
    **redondea hacia abajo**: una firma que empieza a emparejar a las 100 h se
    registraba como 72.
"""
import pytest

from sentinel_omega.infrastructure.pipeline import entrenamiento as tr


class _ConnFalsa:
    """Registra qué offsets se sondearon, para poder contar el coste."""
    def __init__(self):
        self.sondeos = []


@pytest.fixture
def espia(monkeypatch):
    """Sustituye la extracción de ventana y la similitud por un umbral exacto.

    `umbral_h` es la verdad: la firma empareja en todo offset <= umbral_h.
    """
    estado = {"umbral_h": 0.0, "sondeos": []}

    def _ventana(conn, ts, id_nodo):
        from datetime import datetime
        estado["sondeos"].append(ts)
        return {"ts": ts}

    def _similitud(a, b):
        from datetime import datetime
        t = datetime.strptime(a["ts"], "%Y-%m-%d %H:%M")
        t0 = datetime(2026, 1, 15, 0, 0)
        offset_h = (t0 - t).total_seconds() / 3600
        return 0.95 if offset_h <= estado["umbral_h"] else 0.10

    # OJO con el espacio de nombres: `entrenamiento` importa `similitud` a nivel
    # de MÓDULO (línea 33), así que parchear
    # `signature_engine.similitud` no toca el nombre ya enlazado aquí --- se
    # ejecutaría la similitud real sobre un diccionario de prueba, devolvería ~0
    # y todo daría None. Hay que parchear `tr.similitud`.
    monkeypatch.setattr(tr, "extraer_features_ventana", _ventana)
    monkeypatch.setattr(tr, "similitud", _similitud)
    return estado


def _detecta(espia, umbral_h):
    from datetime import datetime
    espia["umbral_h"] = umbral_h
    espia["sondeos"].clear()
    return tr._lag_detectado(_ConnFalsa(), {"x": 1.0},
                             datetime(2026, 1, 15, 0, 0), 31)


def test_encuentra_el_inicio_con_resolucion_de_una_hora(espia):
    """100 h de anticipación real. La rejilla sola habría dicho 72."""
    assert _detecta(espia, 100) == pytest.approx(100, abs=tr.LAG_RESOLUCION_H)


def test_la_rejilla_sola_habria_redondeado_a_la_baja(espia):
    """La regresión que justifica el cambio: el punto grueso bajo 100 h es 72."""
    detectado = _detecta(espia, 100)
    punto_grueso = max(o for o in tr.LAG_OFFSETS_H if o <= 100)
    assert punto_grueso == 72
    assert detectado > punto_grueso, (
        f"sigue midiendo en la rejilla: {detectado} en vez de ~100")


@pytest.mark.parametrize("verdad", [25, 47, 73, 119, 167, 200, 239, 300])
def test_varios_inicios_reales(espia, verdad):
    assert _detecta(espia, verdad) == pytest.approx(verdad, abs=tr.LAG_RESOLUCION_H)


def test_si_empareja_en_el_punto_mas_lejano_no_extrapola(espia):
    """336 h es el borde de la ventana de la firma. Más allá no se inventa."""
    assert _detecta(espia, 400) == 336.0


def test_si_nunca_empareja_devuelve_none(espia):
    """Sin evidencia no se fabrica un lag."""
    assert _detecta(espia, 0) is None


def test_el_coste_no_explota(espia):
    """~13 sondeos, no los 336 de un barrido horario."""
    _detecta(espia, 100)
    n = len(espia["sondeos"])
    assert n <= 16, f"{n} sondeos; la bisección no está acotando"
    assert n >= len([o for o in tr.LAG_OFFSETS_H if o > 100]) + 1


def test_ya_no_se_mide_solo_al_padre():
    """El filtro fijo que dejaba a ocho bots sin anticipación."""
    # Se mira el AST, no el texto. El docstring explica el filtro que se quitó,
    # así que buscar «padre» en la fuente se caza a sí mismo --- exactamente el
    # error que ya se cometió dos veces hoy (`"limit" not in fuente` en
    # test_conteo_sismico_vivo.py, y un primer intento de esta misma prueba).
    import ast
    import inspect
    import textwrap

    arbol = ast.parse(textwrap.dedent(
        inspect.getsource(tr.calcular_lags_anticipacion)))
    fn = arbol.body[0]
    cuerpo = fn.body[1:] if isinstance(
        getattr(fn.body[0], "value", None), ast.Constant) else fn.body
    codigo = "\n".join(ast.unparse(n) for n in cuerpo)
    assert "padre" not in codigo, (
        f"volvió el filtro por bot en el CÓDIGO (no en la prosa): "
        f"{[l for l in codigo.splitlines() if 'padre' in l]}")
    assert "consolidadas" in codigo


def test_el_tope_de_muestra_es_por_bot_y_clase():
    """Con el tope por clase, padre (73 % de las firmas) se lo comía entero y
    quitar el filtro no habría cambiado nada."""
    import inspect
    fuente = inspect.getsource(tr.calcular_lags_anticipacion)
    assert "(bot, clase)" in fuente, "el cupo no está desagregado por bot"
    assert "evaluados_por_clase" not in fuente, "quedó el tope viejo por clase"


# ─── El lag tiene que LLEGAR al aviso, y en horas ───────────────────────────

def _bloque_matches() -> str:
    """El trozo del launcher que anota la ventana típica en cada match.

    Antes esto cortaba una ventana FIJA de caracteres (`i-600 : i+2000`) y era
    una trampa: el 2026-10-08 se añadió al mismo bloque la rama de «medida y
    sin anticipación» (~1.100 caracteres) y la consulta del promedio de clase
    salió del recorte. El test se puso rojo sin que el comportamiento hubiera
    cambiado --- la firma seguía ganándole a la clase.

    Ahora se ancla a la FUNCIÓN que contiene el bloque, así que crece con ella.

    Y el ancla es la COLUMNA, no la ortografía del SELECT: el mismo día el SQL
    pasó a leer también `lag_calma_h`/`lag_calma_n` y se partió en varias
    líneas, así que buscar la consulta literal volvió a poner rojos cuatro
    tests sin que nada se hubiera roto. Un test no puede depender de dónde
    caen los saltos de línea de una cadena.
    """
    import inspect
    from sentinel_omega import launcher
    fuente = inspect.getsource(launcher._auditar_ciclo)
    assert "lag_promedio_h" in fuente, (
        "el bloque de la ventana típica ya no vive en `_auditar_ciclo`: "
        "actualiza este ancla")
    return fuente


def test_el_lag_de_la_firma_gana_al_promedio_de_su_clase():
    """Lo que pidió el operador: «si una firma es idéntica a una que vimos en el
    pasado podremos intuir que tiene cierto tiempo de vida». El promedio de la
    clase es el respaldo, no la respuesta."""
    b = _bloque_matches()
    i_firma = b.index("FROM TBL_FIRMAS")
    i_clase = b.index("tbl_lag_anticipacion")
    assert i_firma < i_clase, "el promedio de clase se consulta antes que la firma"
    assert "else:" in b[i_firma:i_clase], "no es un respaldo, se consultan las dos"


def test_la_ventana_se_reporta_en_horas():
    """La rejilla vieja era de 48–96 h, así que dividir por 24 no perdía nada.
    Con resolución de 1 h sí: 202,7 h impresas como «8 días» tiran la precisión.
    """
    b = _bloque_matches()
    assert 'ventana_tipica_h' in b, "no se expone la ventana en horas"
    assert 'ventana_tipica_dias' in b, (
        "se quitó el campo en días, y lo leen muro_lags, generar_reporte y el "
        "reporte ejecutivo --- campo añadido, ninguno quitado")


def test_el_texto_del_aviso_dice_horas_antes_que_dias():
    b = _bloque_matches()
    texto = b[b.index("ESTA firma"): b.index("ESTA firma") + 220]
    assert " h " in texto or " h\\n" in texto or "h antes" in texto, texto


def test_una_firma_MEDIDA_SIN_anticipacion_no_hereda_la_ventana_de_su_clase():
    """El tercer caso, que existe desde el 2026-10-08.

    Con `lag_medido_at` se puede saber que una firma SÍ se midió y que su
    patrón no se reconoce antes de su propio evento. Caer entonces al promedio
    de la clase sería imprimir «ventana típica ~211 h» sobre una firma de la
    que acabamos de medir que no da tiempo de aviso: una afirmación que
    contradice nuestra propia medición.

    Son 4 de las 982 exigibles en producción. Pocas, y aun así es el patrón que
    este proyecto persigue: un respaldo genérico tapando una medición concreta.
    """
    b = _bloque_matches()
    assert "lag_medido_at IS NOT NULL" in b, (
        "el aviso no distingue «medida sin anticipación» de «sin medir», así "
        "que vuelve a caer al promedio de la clase")
    i_marca = b.index("lag_medido_at IS NOT NULL")
    i_clase = b.index("tbl_lag_anticipacion")
    assert i_marca < i_clase, (
        "la comprobación tiene que ir ANTES de consultar el promedio de clase")
    assert "SIN anticipación" in b
