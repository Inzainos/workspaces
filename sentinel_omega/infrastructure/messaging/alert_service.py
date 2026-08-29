"""
Sentinel Omega — AlertService unificado
Centraliza reportes, alertas y mensajes de Telegram/Correo/Log.
Antes: formatos dispersos en telegram.py, correo.py, muro_*.py, risk_calculator.py
Ahora: unico punto con templates versionables y despacho multi-canal.
"""
from __future__ import annotations
import logging, os
from dataclasses import dataclass
from datetime import datetime, timezone, timedelta
from enum import Enum
from typing import Optional, Dict, List
from pathlib import Path
logger = logging.getLogger(__name__)
class Severity(str, Enum):
    ROJO = "rojo"
    AMARILLO = "amarillo"
    VERDE = "verde"
    AZUL = "azul"
SEVERITY_EMOJI = {Severity.ROJO: "🔴", Severity.AMARILLO: "🟠", Severity.VERDE: "🟢", Severity.AZUL: "🔵"}
@dataclass
class FormattedMessage:
    html: str
    markdown: str
    plain: str
    subject: str
    severity: Severity
    alert_type: str
def _now_utc_str() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
def _window_str(hours: int) -> str:
    return (datetime.now(timezone.utc) + timedelta(hours=hours)).strftime("%d/%m %H:%M UTC")
class AlertTemplates:
    @staticmethod
    def centinela_critico(risk: float, bz: float, wind: float, schumann: Optional[float] = None, severity: Severity = Severity.ROJO) -> FormattedMessage:
        subj = f"[SENTINEL] ALERTA CRITICA — Fantasma {risk:.2f}"
        extra = f"\n🌐 Schumann: {schumann:.2f} Hz" if schumann else ""
        html = f"🔴 <b>ALERTA CRITICA</b>\n\n⚠️ Fantasma: <b>{risk:.2f}</b>\n🧲 Bz: {bz:.1f} nT\n💨 Viento: {wind:.0f} km/s{extra}\n<i>{_now_utc_str()}</i>"
        md = f"**ALERTA CRITICA**\n\nFantasma: **{risk:.2f}**\nBz: {bz:.1f} nT | Viento: {wind:.0f} km/s{extra}"
        plain = html.replace("<b>","").replace("</b>","").replace("<i>","").replace("</i>","")
        return FormattedMessage(html=html, markdown=md, plain=plain, subject=subj, severity=severity, alert_type="CRITICO")
    @staticmethod
    def centinela_grieta(bz: float) -> FormattedMessage:
        subj = f"[SENTINEL] GRIETA — Bz {bz:.1f} nT"
        html = f"🛡️ <b>FALLO DE ESCUDO (GRIETA)</b>\n\nBz colapsado: <b>{bz:.1f} nT</b>\nPosible entrada de energía solar.\n<i>{_now_utc_str()}</i>"
        md = f"**FALLO DE ESCUDO (GRIETA)**\n\nBz colapsado: **{bz:.1f} nT**"
        plain = html.replace("<b>","").replace("</b>","")
        return FormattedMessage(html=html, markdown=md, plain=plain, subject=subj, severity=Severity.ROJO, alert_type="GRIETA")
    @staticmethod
    def centinela_tormenta(wind: float) -> FormattedMessage:
        subj = f"[SENTINEL] TORMENTA SOLAR — Viento {wind:.0f} km/s"
        html = f"🌪️ <b>TORMENTA SOLAR</b>\n\nViento: <b>{wind:.0f} km/s</b>\nPresión sobre magnetosfera.\n<i>{_now_utc_str()}</i>"
        md = f"**TORMENTA SOLAR**\n\nViento: **{wind:.0f} km/s**"
        plain = html.replace("<b>","").replace("</b>","")
        return FormattedMessage(html=html, markdown=md, plain=plain, subject=subj, severity=Severity.AMARILLO, alert_type="TORMENTA")
    @staticmethod
    def centinela_advertencia(risk: float, bz: float, wind: float) -> FormattedMessage:
        subj = f"[SENTINEL] Actividad elevada — Fantasma {risk:.2f}"
        html = f"🟠 <b>ACTIVIDAD ELEVADA</b>\n\nFantasma: {risk:.2f}\nBz: {bz:.1f} | Viento: {wind:.0f}\n<i>{_now_utc_str()}</i>"
        md = f"**ACTIVIDAD ELEVADA**\n\nFantasma: {risk:.2f}"
        plain = html.replace("<b>","").replace("</b>","")
        return FormattedMessage(html=html, markdown=md, plain=plain, subject=subj, severity=Severity.AMARILLO, alert_type="ADVERTENCIA")
    @staticmethod
    def precursor(precursor_type: str, display_name: str, value: float, details: str, lat: Optional[float]=None, lon: Optional[float]=None, lugar: Optional[str]=None, lag_horas: Optional[float]=None) -> FormattedMessage:
        subj = f"[SENTINEL] PRECURSOR {display_name} — {value:.0%}"
        loc = ""
        if lugar: loc += f"\n<b>Zona:</b> {lugar}"
        if lat is not None and lon is not None: loc += f"\n<b>Coords:</b> {lat:.2f}, {lon:.2f}"
        if lag_horas and lag_horas>0: ventanas = f"\n<b>Ventana:</b> ~{int(lag_horas)}h → {_window_str(int(lag_horas))}\n"
        else: ventanas = f"\n<b>Ventanas:</b> 72h→{_window_str(72)} | 48h→{_window_str(48)} | 24h→{_window_str(24)}\n"
        html = f"<b>SENTINEL OMEGA — PRECURSOR</b>\n\n<b>Tipo:</b> {display_name}\n<b>Conf:</b> <code>{value:.0%}</code>{loc}{ventanas}\n{details}\n\n<i>{_now_utc_str()}</i>"
        md = f"**SENTINEL OMEGA — PRECURSOR {display_name}**\nConf: **{value:.0%}**{loc}\n{details}"
        plain = html.replace("<b>","").replace("</b>","").replace("<code>","").replace("</code>","")
        sev = Severity.ROJO if value>=0.75 else Severity.AMARILLO if value>=0.55 else Severity.VERDE
        return FormattedMessage(html=html, markdown=md, plain=plain, subject=subj, severity=sev, alert_type=f"PRECURSOR_{precursor_type.upper()}")
    @staticmethod
    def consenso(layer: str, signal_type: str, confidence: float, agents_n: int, dual_ask: Optional[Dict]=None, omega_voto: Optional[Dict]=None) -> FormattedMessage:
        sev = Severity.ROJO if signal_type.lower()=="alert" else Severity.AMARILLO if signal_type.lower()=="watch" else Severity.VERDE
        subj = f"[SENTINEL] {layer.upper()} CONSENSO — {signal_type} {confidence:.0%}"
        lines = [f"<b>SENTINEL OMEGA — {layer.upper()} CONSENSUS</b>\n", f"Final: <code>{signal_type}</code> ({confidence:.0%})", f"Agents: <code>{agents_n}</code>"]
        if omega_voto: lines.append(f"Ω Omega: <code>{omega_voto.get('signal')}</code> ({float(omega_voto.get('confidence') or 0):.0%})")
        if dual_ask: lines.append(f"\n🔁 <b>Dual-ask</b>: {dual_ask.get('texto','')}")
        lines.append(f"\n<i>{_now_utc_str()}</i>")
        html = "\n".join(lines)
        md = html.replace("<b>","**").replace("</b>","**").replace("<code>","`").replace("</code>","`")
        plain = html.replace("<b>","").replace("</b>","").replace("<code>","").replace("</code>","")
        return FormattedMessage(html=html, markdown=md, plain=plain, subject=subj, severity=sev, alert_type=f"CONSENSUS_{signal_type.upper()}")
    @staticmethod
    def cimatica_consistente(patron_id: int, clave: str, frecuencia: int, event_class=None, ambito: str = "general", id_nodo=None) -> FormattedMessage:
        subj = f"[SENTINEL] CIMATICA CONSISTENTE - patron {patron_id} x{frecuencia}"
        nodo = f" nodo {id_nodo}" if id_nodo else ""
        ec = f" asoc. {event_class}" if event_class else " (sin clase aun)"
        desc = "Patron repetido 3+ veces - deja de ser coincidencia y se vuelve firma. Revisar entrenamiento del Padre."
        html = (
            f"<b>CIMATICA CONSISTENTE</b><br>"
            f"<b>Patron:</b> <code>{patron_id}</code>{nodo} ({ambito})<br>"
            f"<b>Frecuencia:</b> <code>{frecuencia} veces</code>{ec}<br>"
            f"<b>Clave:</b> <code>{clave[:64]}</code><br>"
            f"<b>Que significa:</b> {desc}<br>"
            f"<i>{_now_utc_str()}</i>"
        )
        md = f"**CIMATICA CONSISTENTE** Patron {patron_id}{nodo} x{frecuencia}{ec}"
        plain = html.replace("<b>", "").replace("</b>", "")
        return FormattedMessage(html=html, markdown=md, plain=plain, subject=subj, severity=Severity.AMARILLO, alert_type="CIMATICA")

    @staticmethod
    def reporte_resumen(fantasma: float, muro: str, precursores: list, consenso: str = "") -> FormattedMessage:
        n = len(precursores)
        tabla = ""
        if precursores:
            tabla = "<b>Precursores</b><br>"
            for r in precursores[:5]:
                tabla += f"- {r.get('tipo', r.get('display_name', ''))} {r.get('conf', '')} {r.get('zona', '')}<br>"
        html = (
            f"<b>SENTINEL OMEGA - RESUMEN</b><br>"
            f"<b>Fantasma:</b> <code>{fantasma:.1f}</code>  <b>Muro:</b> <code>{muro}</code>  <b>Precursores:</b> <code>{n}</code><br>"
            f"{tabla}"
            f"<b>Consenso:</b> {consenso or ''}<br>"
            f"<i>{_now_utc_str()}</i> - ver estado/REPORTE.md"
        )
        return FormattedMessage(html=html, markdown=html, plain=html, subject=f"[SENTINEL] RESUMEN Fantasma {fantasma:.1f}", severity=Severity.AZUL, alert_type="RESUMEN")

    @staticmethod
    def sistema_online() -> FormattedMessage:
        return FormattedMessage(html="🔵 <b>SISTEMA ONLINE</b>\nSentinel Omega vigilando telemetría y precursores.", markdown="**SISTEMA ONLINE**", plain="SISTEMA ONLINE", subject="[SENTINEL] Sistema ONLINE", severity=Severity.AZUL, alert_type="ONLINE")
    @staticmethod
    def sistema_dead(minutes: float) -> FormattedMessage:
        return FormattedMessage(html=f"💀 <b>FALLO DE CICLO PRINCIPAL</b>\n\nSin datos recientes (~{int(minutes)} min).\nRevisar launcher / orchestrator.", markdown=f"**FALLO DE CICLO** — {int(minutes)} min", plain=f"FALLO {int(minutes)} min", subject="[SENTINEL] FALLO DE CICLO", severity=Severity.ROJO, alert_type="SYSTEM_DEAD")
    @staticmethod
    def heartbeat(status_line: str) -> FormattedMessage:
        return FormattedMessage(html=f"💓 <b>REPORTE DE ESTADO</b>\n{status_line}\n<i>{_now_utc_str()}</i>", markdown=f"**REPORTE DE ESTADO**\n{status_line}", plain=status_line, subject="[SENTINEL] Heartbeat", severity=Severity.AZUL, alert_type="HEARTBEAT")
class AlertService:
    def __init__(self, dry_run: Optional[bool] = None):
        if dry_run is None: dry_run = os.environ.get("SENTINEL_DRY_RUN","").lower() in ("1","true","yes")
        self.dry_run = dry_run
    def dispatch(self, msg: FormattedMessage, channels: Optional[List[str]]=None, conn=None, cooldown: Optional[int]=None) -> Dict[str, bool]:
        if channels is None: channels = ["telegram","correo","log"]
        results: Dict[str,bool] = {}
        if "log" in channels:
            logger.info(f"ALERT [{msg.severity.value}/{msg.alert_type}] {msg.subject}")
            results["log"] = True
        if "telegram" in channels:
            if self.dry_run:
                logger.info(f"[DRY_RUN] Telegram {msg.alert_type}: {msg.html[:120]}")
                results["telegram"] = True
            else:
                try:
                    from sentinel_omega.infrastructure.api.telegram import send_alert_gated
                    cd = cooldown if cooldown is not None else 1800
                    results["telegram"] = send_alert_gated(msg.html, msg.alert_type, cooldown=cd)
                except Exception as e:
                    logger.error(f"Telegram dispatch failed: {e}")
                    results["telegram"] = False
        if "correo" in channels and conn is not None:
            try:
                from sentinel_omega.infrastructure.api.correo import encolar_correo
                encolar_correo(conn, asunto=msg.subject, cuerpo=msg.plain + "\n\n" + msg.html, tipo="ALERTA")
                results["correo"] = True
            except Exception as e:
                logger.error(f"Correo dispatch failed: {e}")
                results["correo"] = False
        return results
    def centinela_threat(self, risk: float, bz: float, wind: float, schumann: Optional[float]=None) -> Optional[FormattedMessage]:
        th_warn = float(os.environ.get("TG_TH_RISK_WARN","0.60"))
        th_crit = float(os.environ.get("TG_TH_RISK_CRIT","0.75"))
        th_bz = float(os.environ.get("TG_TH_BZ_CRACK","-5.0"))
        th_wind = float(os.environ.get("TG_TH_WIND_STORM","600"))
        r = risk/10.0 if risk>1.5 else risk
        if r >= th_crit: return AlertTemplates.centinela_critico(r, bz, wind, schumann)
        if bz <= th_bz: return AlertTemplates.centinela_grieta(bz)
        if wind >= th_wind: return AlertTemplates.centinela_tormenta(wind)
        if r >= th_warn: return AlertTemplates.centinela_advertencia(r, bz, wind)
        return None
