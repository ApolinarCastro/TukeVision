"""Enterprise Localization module for TukeVision Command Center.

Default locale: es-CL (Spanish - Chile).
Provides typed translations, formatting helpers, and fallback to English if needed.
"""

from typing import Dict, Any


DEFAULT_LOCALE = "es-CL"

TRANSLATIONS: Dict[str, Dict[str, str]] = {
    "es-CL": {
        # Brand & Header
        "app_title": "TUKEVISION",
        "app_subtitle": "Centro de Mando · Inteligencia Retail & Prevención de Pérdidas",
        "store_label": "Tienda:",
        "zone_label": "Zona:",
        "all_zones": "Todas",
        "live_status_live": "EN VIVO",
        "live_status_idle": "INACTIVO",
        "status_operational_normal": "OPERACIONAL: NORMAL",
        "status_operational_attention": "OPERACIONAL: ATENCIÓN",
        "status_operational_degraded": "OPERACIONAL: DEGRADADO",
        "status_ai_active": "CASCADA IA: ACTIVA",
        "status_ai_degraded": "CASCADA IA: MODO SEGURO",
        "cameras_live_format": "CÁMARAS: {live} / {total} EN VIVO",
        "mode_prefix": "MODO: ",

        # Navigation Tabs
        "tab_overview": "📊 RESUMEN",
        "tab_grid": "📹 EN VIVO",
        "tab_situations": "⚠️ SITUACIONES",
        "tab_investigations": "🔍 INVESTIGACIONES",
        "tab_evidence": "📁 EVIDENCIA",
        "tab_map": "🗺️ MAPA / ZONAS",
        "tab_system": "⚙️ ESTADO DEL SISTEMA",

        # Common Actions / Controls
        "btn_start": "Iniciar",
        "btn_stop": "Detener",
        "btn_settings": "Ajustes",
        "btn_review": "Revisión",
        "btn_fullscreen": "Pantalla Completa",
        "btn_back_grid": "Volver a Cuadrícula",
        "btn_zoom_in": "Zoom +",
        "btn_zoom_out": "Zoom -",
        "btn_zoom_reset": "Restablecer",
        "btn_switch_stream": "Alternar Flujo",
        "btn_dispatch_alert": "Despachar Alerta",
        "btn_export_evidence": "Exportar Evidencia",

        # HUD (Focus & Tiles)
        "hud_source": "FUENTE: ",
        "hud_display": "PRESENTACIÓN: ",
        "hud_inference": "INFERENCIA: ",
        "hud_profile_main": "PERFIL: PRINCIPAL (HD)",
        "hud_profile_sub": "PERFIL: SECUNDARIO",
        "active_tracks_format": "● {count} activos",

        # Overview / Executive Cards
        "kpi_active_cameras": "CÁMARAS ACTIVAS",
        "kpi_active_situations": "SITUACIONES ACTIVAS",
        "kpi_open_investigations": "INVESTIGACIONES",
        "kpi_stored_evidence": "EVIDENCIAS SHA-256",
        "kpi_agent_status": "ESTADO DEL AGENTE",

        # Empty / Nominal States (Zero-Fake Data)
        "no_active_situations": "SIN SITUACIONES ACTIVAS",
        "no_active_situations_sub": "Todas las zonas operando bajo parámetros nominales.",
        "attention_queue_empty": "COLA DE ATENCIÓN VACÍA",
        "attention_queue_empty_sub": "No hay eventos que requieran intervención del operador.",
        "no_open_investigations": "SIN INVESTIGACIONES PENDIENTES",
        "no_open_investigations_sub": "El monitor de agentes no registra incidentes abiertos.",
        "no_evidence_recorded": "SIN PAQUETES DE EVIDENCIA",
        "no_evidence_recorded_sub": "Los paquetes de evidencia se generan ante eventos validados.",
        "map_no_geometry": "GEOMETRÍA NO CALIBRADA",
        "map_no_geometry_sub": "Se requiere plano de tienda para renderizar vista de planta.",
        "system_nominal": "SISTEMA OPERACIONALMENTE SALUDABLE",

        # Epistemic Badges
        "epistemic_fact": "HECHO",
        "epistemic_inference": "INFERENCIA",
        "epistemic_unknown": "DESCONOCIDO",

        # Agent States
        "agent_observing": "OBSERVANDO",
        "agent_tracking": "RASTREANDO",
        "agent_investigating": "INVESTIGANDO",
        "agent_preserving": "PRESERVANDO",
        "agent_resolved": "RESUELTO",
        "agent_escalated": "ESCALADO",
        "agent_idle": "INACTIVO",
        "agent_safe_mode": "MODO SEGURO",

        # Data Status / Provenance
        "data_real": "DATO REAL",
        "data_derived": "DERIVADO",
        "data_unknown": "DESCONOCIDO",
        "data_not_available": "NO DISPONIBLE",
    },
    "en": {
        "app_title": "TUKEVISION",
        "app_subtitle": "Command Center · Retail Intelligence & Loss Prevention",
        "store_label": "Store:",
        "zone_label": "Zone:",
        "all_zones": "All",
        "live_status_live": "LIVE",
        "live_status_idle": "IDLE",
        "status_operational_normal": "OPERATIONAL: NORMAL",
        "status_operational_attention": "OPERATIONAL: ATTENTION",
        "status_operational_degraded": "OPERATIONAL: DEGRADED",
        "status_ai_active": "AI CASCADE: ACTIVE",
        "status_ai_degraded": "AI CASCADE: SAFE MODE",
        "cameras_live_format": "CAMERAS: {live} / {total} LIVE",
        "mode_prefix": "MODE: ",

        "tab_overview": "📊 OVERVIEW",
        "tab_grid": "📹 LIVE GRID",
        "tab_situations": "⚠️ SITUATIONS",
        "tab_investigations": "🔍 INVESTIGACIONES",
        "tab_evidence": "📁 EVIDENCE",
        "tab_map": "🗺️ MAP / ZONES",
        "tab_system": "⚙️ SYSTEM HEALTH",

        "btn_start": "Start",
        "btn_stop": "Stop",
        "btn_settings": "Settings",
        "btn_review": "Review",
        "btn_fullscreen": "Fullscreen",
        "btn_back_grid": "Back to Grid",
        "btn_zoom_in": "Zoom +",
        "btn_zoom_out": "Zoom -",
        "btn_zoom_reset": "Reset",
        "btn_switch_stream": "Switch Stream",
        "btn_dispatch_alert": "Dispatch Alert",
        "btn_export_evidence": "Export Evidence",

        "hud_source": "SOURCE: ",
        "hud_display": "DISPLAY: ",
        "hud_inference": "INFERENCE: ",
        "hud_profile_main": "PROFILE: MAIN (HD)",
        "hud_profile_sub": "PROFILE: SUBSTREAM",
        "active_tracks_format": "● {count} active",

        "kpi_active_cameras": "ACTIVE CAMERAS",
        "kpi_active_situations": "ACTIVE SITUATIONS",
        "kpi_open_investigations": "INVESTIGATIONS",
        "kpi_stored_evidence": "SHA-256 EVIDENCE",
        "kpi_agent_status": "AGENT STATUS",

        "no_active_situations": "NO ACTIVE SITUATIONS",
        "no_active_situations_sub": "All zones operating within nominal parameters.",
        "attention_queue_empty": "ATTENTION QUEUE EMPTY",
        "attention_queue_empty_sub": "No events requiring operator intervention.",
        "no_open_investigations": "NO OPEN INVESTIGATIONS",
        "no_open_investigations_sub": "Agent monitor reports no active incidents.",
        "no_evidence_recorded": "NO EVIDENCE BUNDLES",
        "no_evidence_recorded_sub": "Evidence bundles are generated on validated situations.",
        "map_no_geometry": "GEOMETRY NOT CALIBRATED",
        "map_no_geometry_sub": "Store plan required to render top-down layout.",
        "system_nominal": "SYSTEM HEALTH NOMINAL",

        "epistemic_fact": "FACT",
        "epistemic_inference": "INFERENCE",
        "epistemic_unknown": "UNKNOWN",

        "agent_observing": "OBSERVING",
        "agent_tracking": "TRACKING",
        "agent_investigating": "INVESTIGATING",
        "agent_preserving": "PRESERVING",
        "agent_resolved": "RESOLVED",
        "agent_escalated": "ESCALATED",
        "agent_idle": "IDLE",
        "agent_safe_mode": "SAFE MODE",

        "data_real": "REAL DATA",
        "data_derived": "DERIVED",
        "data_unknown": "UNKNOWN",
        "data_not_available": "NOT AVAILABLE",
    }
}


class I18n:
    """Localization manager for TukeVision."""

    _current_locale: str = DEFAULT_LOCALE

    @classmethod
    def set_locale(cls, locale: str) -> None:
        if locale in TRANSLATIONS:
            cls._current_locale = locale
        else:
            cls._current_locale = DEFAULT_LOCALE

    @classmethod
    def get_locale(cls) -> str:
        return cls._current_locale

    @classmethod
    def t(cls, key: str, **kwargs: Any) -> str:
        """Translate a key into the active locale, substituting any formatting kwargs."""
        table = TRANSLATIONS.get(cls._current_locale, TRANSLATIONS[DEFAULT_LOCALE])
        text = table.get(key, TRANSLATIONS["en"].get(key, key))
        if kwargs:
            try:
                return text.format(**kwargs)
            except Exception:
                return text
        return text


# Global convenient alias
_ = I18n.t
