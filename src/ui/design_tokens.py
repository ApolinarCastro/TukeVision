"""Unified Design System Tokens for TukeVision Command Center.

Provides enterprise-grade visual tokens: curated dark palette, typography,
spacing, borders, and semantic status/priority helpers.
"""

from typing import Dict, Any, Tuple


class DesignTokens:
    """Canonical source of visual design tokens for TukeVision."""

    # Curated Harmonious Dark Palette (Enterprise Operations Center)
    COLORS: Dict[str, str] = {
        "bg": "#0B0F19",             # Deep navy black canvas
        "surface": "#111827",        # Card and container surface
        "surface_elevated": "#1F2937", # Elevated cards / headers
        "surface_muted": "#161E2E",  # Muted container surface
        "border": "#374151",         # Subtle structural border
        "border_light": "#4B5563",   # Interactive element border
        "text": "#F9FAFB",           # Primary high-contrast text
        "text_secondary": "#D1D5DB", # Readable secondary text
        "text_dim": "#9CA3AF",       # Muted annotations and labels
        "text_dark": "#6B7280",      # Very dim / disabled text
        "accent": "#00E5FF",         # Brand cyan / primary interactive
        "accent_hover": "#33EBFF",   # Accent hover state
        "accent_bg": "#083344",      # Accent subtle background container
        
        # Operational Semantic Status Colors
        "normal": "#10B981",         # Emerald green - Nominal / Online
        "info": "#3B82F6",           # Blue - Information / Tracking
        "attention": "#F59E0B",      # Amber - Requires attention / degraded
        "high": "#F97316",           # Orange - High priority / escalated
        "critical": "#EF4444",       # Red - Critical alert / offline
        "degraded": "#F59E0B",       # Amber - Stale / degraded
        "offline": "#6B7280",        # Gray - Offline / stopped
        "unknown": "#9CA3AF",        # Slate - Unknown state

        # Epistemic Classification Colors
        "epistemic_fact": "#10B981",      # Emerald - Verifiable observation
        "epistemic_inference": "#6366F1", # Indigo - Rule / Model deduction
        "epistemic_unknown": "#9CA3AF",   # Slate - Undetermined
    }

    # Standardized Typography
    FONT_FAMILY = "Segoe UI"
    FONT_FAMILY_MONO = "Consolas"

    FONTS = {
        "title": (FONT_FAMILY, 14, "bold"),
        "subtitle": (FONT_FAMILY, 10),
        "panel_title": (FONT_FAMILY, 11, "bold"),
        "body": (FONT_FAMILY, 9),
        "body_bold": (FONT_FAMILY, 9, "bold"),
        "small": (FONT_FAMILY, 8),
        "small_bold": (FONT_FAMILY, 8, "bold"),
        "mono": (FONT_FAMILY_MONO, 8),
        "mono_bold": (FONT_FAMILY_MONO, 8, "bold"),
        "kpi_value": (FONT_FAMILY, 18, "bold"),
        "kpi_label": (FONT_FAMILY, 8, "bold"),
    }

    # Spacing Tokens (pixels)
    SPACING = {
        "xs": 4,
        "sm": 8,
        "md": 12,
        "lg": 16,
        "xl": 24,
    }

    # Component Dimensions
    SIZES = {
        "header_height": 72,
        "nav_bar_height": 34,
        "status_dot_size": 10,
        "kpi_card_width": 160,
        "kpi_card_height": 64,
        "border_width": 1,
    }

    @classmethod
    def get_status_color(cls, status_name: str) -> str:
        """Resolve any camera or system status string to its standard color token."""
        key = str(status_name or "").upper()
        if key in ("ONLINE", "NORMAL", "OPEN", "READING", "HEALTHY", "LIVE", "VERIFIED", "SUCCESS", "ALLOW"):
            return cls.COLORS["normal"]
        if key in ("DEGRADED", "STALE", "ATTENTION", "WARNING", "MEDIUM"):
            return cls.COLORS["attention"]
        if key in ("CRITICAL", "ERROR", "HIGH", "ALERT", "FAIL", "BLOCKED", "DENY"):
            return cls.COLORS["critical"]
        if key in ("OFFLINE", "STOPPED", "CLOSED", "DISABLED"):
            return cls.COLORS["offline"]
        if key in ("INFO", "OBSERVING", "TRACKING", "INVESTIGATING"):
            return cls.COLORS["info"]
        return cls.COLORS["unknown"]

    @classmethod
    def get_epistemic_color(cls, epistemic_class: str) -> str:
        """Resolve epistemic tier (FACT, INFERENCE, UNKNOWN) to color token."""
        tier = str(epistemic_class or "").upper()
        if "FACT" in tier or "HECHO" in tier:
            return cls.COLORS["epistemic_fact"]
        if "INFERENCE" in tier or "INFERENCIA" in tier:
            return cls.COLORS["epistemic_inference"]
        return cls.COLORS["epistemic_unknown"]
