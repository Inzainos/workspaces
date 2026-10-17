"""Lo que sale hacia Telegram tiene que ser parseable por Telegram.

El 2026-10-08 quince digestos seguidos (13:49 → 18:25) no llegaron al teléfono.
El log del Concilio, que es quien despacha la cola, lo decía entero:

    Can't parse entities: unsupported start tag "50)" at byte offset 1499
    Cola: aviso «Direct Alert» descartado tras 5 intentos

El entrenador escribe «NO se reentrena: 38 muestras reales (<50) y sin prior»
en `models_meta.json` y el digesto lo interpolaba en HTML sin escapar. Había un
test que metía EXACTAMENTE ese texto (`test_aviso_habilidad_modelos`) y pasaba,
porque comprobaba que el motivo apareciera --- nunca que el resultado se
pudiera parsear. Esa es la prueba que faltaba.
"""
import json
import re
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from sentinel_omega.infrastructure.api.telegram import (  # noqa: E402
    sanear_html_telegram,
)
from sentinel_omega.infrastructure.messaging import consenso_vigilante as cv  # noqa: E402
from sentinel_omega.infrastructure.messaging.alert_service import AlertTemplates  # noqa: E402

# Las mismas etiquetas que admite el Bot API en modo HTML. `br` NO está.
TAGS_OK = (
    "b", "strong", "i", "em", "u", "ins", "s", "strike", "del",
    "a", "code", "pre", "span", "tg-spoiler", "tg-emoji", "blockquote",
)
_TAG = re.compile(r"</?(?:" + "|".join(TAGS_OK) + r")(?:\s[^<>]*)?>", re.IGNORECASE)
_ENTIDAD = re.compile(r"&(?:[a-zA-Z][a-zA-Z0-9]{1,31}|#\d{1,7}|#[xX][0-9a-fA-F]{1,6});")


def exigir_parseable(texto: str) -> None:
    """Falla si Telegram rechazaría el mensaje.

    Es la regla del parser: cualquier `<` que no abra una etiqueta permitida es
    «unsupported start tag», y cualquier `&` que no abra una entidad válida es
    un «unsupported entity». Se quitan las etiquetas y las entiades buenas; lo
    que quede con `<` o `&` es lo que mataría el aviso.
    """
    resto = _ENTIDAD.sub("", _TAG.sub("", texto))
    assert "<" not in resto, f"Telegram rechazaría esto: {resto[resto.find('<') - 40:][:90]!r}"
    assert "&" not in resto, f"entidad inválida: {resto[resto.find('&') - 40:][:90]!r}"


# --- el saneador de la puerta de salida ----------------------------------


def test_el_texto_que_mato_quince_digestos():
    malo = "NO se reentrena: 38 muestras reales (<50) y sin prior"
    sano = sanear_html_telegram(f"❔ ALFA2 — <b>sin habilidad medible</b>: {malo}")

    exigir_parseable(sano)
    assert "&lt;50)" in sano, "el `<50)` tiene que quedar escapado"
    assert "<b>sin habilidad medible</b>" in sano, "el formato bueno se conserva"


def test_lo_que_ya_estaba_sano_sale_identico():
    bueno = (
        "🤖 <b>Modelos ONNX</b>\n<i>nota</i>\n"
        "<code>auc 0.800</code> <a href=\"https://x.test/a?b=1&amp;c=2\">link</a>"
    )
    assert sanear_html_telegram(bueno) == bueno


def test_br_se_vuelve_salto_de_linea_porque_telegram_no_la_admite():
    sano = sanear_html_telegram("<b>A</b><br>B<br/>C")

    exigir_parseable(sano)
    assert sano == "<b>A</b>\nB\nC"


def test_la_ampersand_suelta_se_escapa_y_la_entidad_se_respeta():
    sano = sanear_html_telegram("Bz &lt; 0 &amp;&amp; viento & protones &#8212; fin")

    exigir_parseable(sano)
    assert "&amp; protones" in sano
    assert "&lt; 0" in sano and "&amp;&amp;" in sano and "&#8212;" in sano


@pytest.mark.parametrize("veneno", [
    "(<50)",
    "a < b > c",
    "<script>alert(1)</script>",
    "<div>bloque</div>",
    "100% & subiendo",
    "<b>sin cerrar",
    "",
])
def test_cualquier_texto_libre_sale_parseable(veneno):
    exigir_parseable(sanear_html_telegram(f"<b>x</b> {veneno} <i>y</i>"))


def test_el_recorte_no_puede_partir_una_etiqueta(tmp_path, monkeypatch):
    """Recortar DESPUÉS de sanear partiría `<b` y rompería el parseo.

    `send_alert` recorta primero y sanea al final justamente por esto.
    """
    from sentinel_omega.infrastructure.api import telegram as tg

    enviados = []
    monkeypatch.setattr(tg, "ALERT_QUEUE_AVAILABLE", True)
    monkeypatch.setattr(tg, "queue_alert",
                        lambda t, m, p, pm: enviados.append(m), raising=False)

    # Dos condiciones, y hacen falta las dos: el mensaje tiene que PASAR de
    # 4.000 para que se recorte, y el corte de 3990 tiene que caer dentro de
    # una etiqueta de apertura. Con un relleno más corto no se recorta nada y
    # la prueba no prueba nada (comprobado: sin esto, invertir el orden pasaba).
    mensaje = "x" * 3988 + "<b>" + "y" * 20 + "</b>"
    assert len(mensaje) > 4000, "si no pasa de 4.000 no se recorta y no se prueba nada"
    assert mensaje[:3990].endswith("<b"), "el corte debe quedar DENTRO de la etiqueta"
    assert tg.send_alert(mensaje, parse_mode="HTML") is True

    exigir_parseable(enviados[0])
    assert len(enviados[0]) < 4096


# --- los constructores de verdad -----------------------------------------


def test_el_digesto_de_modelos_con_el_metadato_real(tmp_path, monkeypatch):
    """`get_model_status` con el metadato que tenía producción hoy."""
    monkeypatch.setattr(cv, "MODELS_DIR", tmp_path)
    for bot, nombre in cv.NOMBRES_ONNX.items():
        (tmp_path / nombre).write_bytes(b"onnx")
    (tmp_path / "models_meta.json").write_text(json.dumps({
        "retrained_at": "2026-10-08T19:30:19Z",
        "bots": {
            "alfa2": {"n": 0, "reentrenado": False,
                      "source": "NO se reentrena: 38 muestras reales (<50) y sin prior"},
            "jupiter": {"n": 53, "habilidad": {
                "auc": None, "aprueba": False,
                "motivo": "solo 53 muestras; <60 el AUC es ruido"}},
            "beta1": {"n": 7000, "habilidad": {
                "auc": 0.800, "aprueba": False, "ganancia_sobre_nulo": -0.099,
                "motivo": "la tasa base del nodo (0,899) ya supera el AUC"}},
        },
    }))

    txt = cv.get_model_status("/no/existe.db")

    exigir_parseable(txt)
    # y sin perder la razón de cada uno (lo que fija el test de hoy)
    assert "38 muestras" in txt
    assert "el AUC es ruido" in txt


def test_las_alertas_inmediatas_con_texto_sucio():
    """Las plantillas que pagan al teléfono, con `<` en los campos de la DB."""
    casos = [
        AlertTemplates.cimatica_consistente(
            7, "bz<0 & viento>600", 3, event_class="SISMO_M4<test>", ambito="nodo<1>"),
        AlertTemplates.cimatica_nuevo(
            9, "clave <rara> & suelta", ambito="general<x>", event_class="A&B"),
        AlertTemplates.firma_nueva("beta1<x>", "SISMO_M5 & M6", firma_id=4),
    ]
    for m in casos:
        exigir_parseable(m.html)
        assert "<br>" not in m.html, "Telegram no admite <br>"

    # `plain` es «sin marcado»: las entidades vuelven a ser caracteres
    assert "bz<0 & viento>600" in casos[0].plain


def test_el_recorte_que_partia_un_tag_se_cierra_solo():
    """El caso medido del 2026-10-17: 36 avisos reenviados SIN FORMATO.

    El recorte a 3990 podía caer entre un `<i>` y su `</i>` (digestos con
    93 avisos): Telegram rechazaba el mensaje ENTERO («can't find end tag
    corresponding to start tag "i"») y el reenvío sin formato mostraba los
    `<b></b>` crudos en el chat. El saneo ahora GARANTIZA lo parseable:
    cierra lo abierto, al final y en orden.
    """
    truncado = "<b>REPORTE</b>\n<i>2026-10-17 06:00"  # el recorte comió el </i>
    out = sanear_html_telegram(truncado)
    exigir_parseable(out)
    # emparejado: cada apertura tiene su cierre
    assert out.count("<i>") == out.count("</i>")
    assert out.count("<b>") == out.count("</b>")


def test_el_cierre_huerfano_se_tira_no_el_mensaje():
    """Un `</b>` sin apertura venía de recortes que dejaban la cola suelta."""
    out = sanear_html_telegram("texto </b> suelto")
    exigir_parseable(out)
    assert "</b>" not in out
    assert "texto" in out and "suelto" in out


def test_el_cierre_que_salta_nidacion_cierra_los_intermedios():
    """Telegram exige anidado correcto: `<b><i>x</b>` no parsea. El saneo
    cierra el `<i>` antes del `</b>` — reordenar, no inventar."""
    out = sanear_html_telegram("<b><i>marcado</b>")
    exigir_parseable(out)
    assert out == "<b><i>marcado</i></b>"
