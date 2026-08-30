"""Módulo de gestión de temas y paletas corporativas/científicas para la interfaz.

Define la arquitectura cromática rica y diferenciada por sección para:
1. TMRW Silicon (Corporativo)
2. Nordic Graphite & Navy
3. TMRW Lab (Multicolor por modo — azul/verde/morado/naranja)
"""

import tkinter as tk
from tkinter import ttk


# ---------------------------------------------------------------------------
# Paletas de acento por modo para el tema TMRW Lab
# ---------------------------------------------------------------------------
MODE_ACCENT_PALETTES = {
    "studio": {
        "dark": "#0a2240",
        "mid": "#0284c7",
        "light": "#dbeafe",
        "bg_tint": "#e4ecf4",
        "console_accent": "#38bdf8",
        "tab_fg": "#0a2240",
        "btn_quick": "#1e3a5f",
        "btn_quick_hover": "#284d7a",
        "btn_tool": "#475569",
        "btn_tool_hover": "#64748b",
    },
    "lite": {
        "dark": "#065f46",
        "mid": "#059669",
        "light": "#d1fae5",
        "bg_tint": "#e2f5ee",
        "console_accent": "#34d399",
        "tab_fg": "#065f46",
        "btn_quick": "#047857",
        "btn_quick_hover": "#059669",
        "btn_tool": "#4b7a62",
        "btn_tool_hover": "#5f9e7e",
    },
    "analytics": {
        "dark": "#4c1d95",
        "mid": "#7c3aed",
        "light": "#ede9fe",
        "bg_tint": "#ede9f8",
        "console_accent": "#a78bfa",
        "tab_fg": "#4c1d95",
        "btn_quick": "#6d28d9",
        "btn_quick_hover": "#7c3aed",
        "btn_tool": "#6b5b8a",
        "btn_tool_hover": "#8b7aa8",
    },
    "stress": {
        "dark": "#78350f",
        "mid": "#d97706",
        "light": "#fef3c7",
        "bg_tint": "#f8ecd5",
        "console_accent": "#fbbf24",
        "tab_fg": "#78350f",
        "btn_quick": "#b45309",
        "btn_quick_hover": "#d97706",
        "btn_tool": "#7a5c2e",
        "btn_tool_hover": "#9a7840",
    },
    "_default": {
        "dark": "#0a2240",
        "mid": "#0284c7",
        "light": "#dbeafe",
        "bg_tint": "#e4ecf4",
        "console_accent": "#38bdf8",
        "tab_fg": "#0a2240",
        "btn_quick": "#1e3a5f",
        "btn_quick_hover": "#284d7a",
        "btn_tool": "#475569",
        "btn_tool_hover": "#64748b",
    },
}


THEMES = {
    "tmrw_silicon": {
        "id": "tmrw_silicon",
        "name": "TMRW Silicon (Corporativo)",
        "bg_window": "#cbd5e1",
        "bg_card_default": "#e2e8f0",
        "border_card": "#94a3b8",
        "fg_text": "#0f172a",
        "fg_muted": "#475569",
        "bg_input": "#f8fafc",
        "fg_input": "#0f172a",
        "border_focus": "#0284c7",
        # [1] Sección Keithley
        "keithley": {
            "bg": "#e2e8f0",
            "border": "#94a3b8",
            "header_fg": "#0a2240",
            "accent_bar": "#0a2240",
        },
        # [2] Sección Parámetros Especí­ficos (Motor / Irradiancia / Repetitividad)
        "params": {
            "bg": "#e2e8f0",
            "border": "#94a3b8",
            "header_fg": "#0a2240",
            "accent_bar": "#0284c7",
        },
        # [3] Sección Control y Botonera
        "control": {
            "bg": "#e2e8f0",
            "border": "#94a3b8",
            "header_fg": "#0a2240",
            "accent_bar": "#0284c7",
        },
        # Botones
        "buttons": {
            "primary_bg": "#0a2240",
            "primary_fg": "#ffffff",
            "primary_hover": "#12335c",
            "quick_bg": "#1e3a5f",
            "quick_fg": "#ffffff",
            "quick_hover": "#284d7a",
            "danger_bg": "#991b1b",
            "danger_fg": "#ffffff",
            "danger_hover": "#b91c1c",
            "tool_bg": "#475569",
            "tool_fg": "#ffffff",
            "tool_hover": "#64748b",
        },
        # [4] Sección Resultados y Consola
        "results": {
            "bg": "#e2e8f0",
            "border": "#94a3b8",
            "header_fg": "#0a2240",
            "accent_bar": "#0a2240",
            "bg_console": "#08182b",
            "fg_console": "#e2e8f0",
            "fg_accent": "#38bdf8",
            "fg_success": "#4ade80",
            "fg_warn": "#fbbf24",
            "badge_ready_bg": "#0a2240",
            "badge_ready_fg": "#38bdf8",
            "badge_running_bg": "#14532d",
            "badge_running_fg": "#86efac",
            "badge_abort_bg": "#7f1d1d",
            "badge_abort_fg": "#fca5a5",
        },
        # Pestañas Submodos
        "tabs": {
            "active_bg": "#e2e8f0",
            "active_fg": "#0a2240",
            "inactive_bg": "#cbd5e1",
            "inactive_fg": "#475569",
            "accent_line": "#0284c7",
        },
        # Tarjetas de Bienvenida
        "welcome": {
            "header_fg": "#0a2240",
            "card1": {"bg": "#e2e8f0", "border": "#0a2240", "hover": "#d5e0eb", "title_fg": "#0a2240"},
            "card2": {"bg": "#e2e8f0", "border": "#2563eb", "hover": "#dbeafe", "title_fg": "#1e40af"},
            "card3": {"bg": "#e2e8f0", "border": "#0284c7", "hover": "#e0f2fe", "title_fg": "#0369a1"},
        },
    },
    "nordic_graphite": {
        "id": "nordic_graphite",
        "name": "Nordic Graphite & Navy",
        "bg_window": "#d8dcde",
        "bg_card_default": "#eaedef",
        "border_card": "#7f8c96",
        "fg_text": "#111827",
        "fg_muted": "#4b5563",
        "bg_input": "#f9fafb",
        "fg_input": "#111827",
        "border_focus": "#1d4ed8",
        "keithley": {
            "bg": "#eaedef",
            "border": "#7f8c96",
            "header_fg": "#1a2d42",
            "accent_bar": "#1d4ed8",
        },
        "params": {
            "bg": "#eaedef",
            "border": "#7f8c96",
            "header_fg": "#1a2d42",
            "accent_bar": "#1d4ed8",
        },
        "control": {
            "bg": "#eaedef",
            "border": "#7f8c96",
            "header_fg": "#1a2d42",
            "accent_bar": "#1d4ed8",
        },
        "buttons": {
            "primary_bg": "#1d4ed8",
            "primary_fg": "#ffffff",
            "primary_hover": "#2563eb",
            "quick_bg": "#374151",
            "quick_fg": "#ffffff",
            "quick_hover": "#4b5563",
            "danger_bg": "#a12323",
            "danger_fg": "#ffffff",
            "danger_hover": "#be123c",
            "tool_bg": "#4b5563",
            "tool_fg": "#ffffff",
            "tool_hover": "#6b7280",
        },
        "results": {
            "bg": "#eaedef",
            "border": "#7f8c96",
            "header_fg": "#1a2d42",
            "accent_bar": "#1d4ed8",
            "bg_console": "#1f2937",
            "fg_console": "#f3f4f6",
            "fg_accent": "#60a5fa",
            "fg_success": "#4ade80",
            "fg_warn": "#fbbf24",
            "badge_ready_bg": "#111827",
            "badge_ready_fg": "#60a5fa",
            "badge_running_bg": "#14532d",
            "badge_running_fg": "#86efac",
            "badge_abort_bg": "#7f1d1d",
            "badge_abort_fg": "#fca5a5",
        },
        "tabs": {
            "active_bg": "#eaedef",
            "active_fg": "#1a2d42",
            "inactive_bg": "#d8dcde",
            "inactive_fg": "#4b5563",
            "accent_line": "#1d4ed8",
        },
        "welcome": {
            "header_fg": "#1a2d42",
            "card1": {"bg": "#eaedef", "border": "#1d4ed8", "hover": "#dbeafe", "title_fg": "#1a2d42"},
            "card2": {"bg": "#eaedef", "border": "#4b5563", "hover": "#e5e7eb", "title_fg": "#374151"},
            "card3": {"bg": "#eaedef", "border": "#d97706", "hover": "#fef3c7", "title_fg": "#92400e"},
        },
    },
    # ── TMRW Lab: tema multicolor por modo ─────────────────────────────────
    "tmrw_lab": {
        "id": "tmrw_lab",
        "name": "TMRW Lab (Multicolor por modo)",
        "bg_window": "#cfd8e3",
        "bg_card_default": "#dce5ef",
        "border_card": "#8fa3bb",
        "fg_text": "#0f172a",
        "fg_muted": "#475569",
        "bg_input": "#f8fafc",
        "fg_input": "#0f172a",
        "border_focus": "#0284c7",
        "keithley": {
            "bg": "#dce5ef",
            "border": "#8fa3bb",
            "header_fg": "#0a2240",
            "accent_bar": "#0a2240",
        },
        "params": {
            "bg": "#dce5ef",
            "border": "#8fa3bb",
            "header_fg": "#0a2240",
            "accent_bar": "#0284c7",
        },
        "control": {
            "bg": "#dce5ef",
            "border": "#8fa3bb",
            "header_fg": "#0a2240",
            "accent_bar": "#0284c7",
        },
        "buttons": {
            "primary_bg": "#0a2240",
            "primary_fg": "#ffffff",
            "primary_hover": "#12335c",
            "quick_bg": "#1e3a5f",
            "quick_fg": "#ffffff",
            "quick_hover": "#284d7a",
            "danger_bg": "#991b1b",
            "danger_fg": "#ffffff",
            "danger_hover": "#b91c1c",
            "tool_bg": "#475569",
            "tool_fg": "#ffffff",
            "tool_hover": "#64748b",
        },
        "results": {
            "bg": "#dce5ef",
            "border": "#8fa3bb",
            "header_fg": "#0a2240",
            "accent_bar": "#0a2240",
            "bg_console": "#08182b",
            "fg_console": "#e2e8f0",
            "fg_accent": "#38bdf8",
            "fg_success": "#4ade80",
            "fg_warn": "#fbbf24",
            "badge_ready_bg": "#0a2240",
            "badge_ready_fg": "#38bdf8",
            "badge_running_bg": "#14532d",
            "badge_running_fg": "#86efac",
            "badge_abort_bg": "#7f1d1d",
            "badge_abort_fg": "#fca5a5",
        },
        "tabs": {
            "active_bg": "#dce5ef",
            "active_fg": "#0a2240",
            "inactive_bg": "#c8d4e0",
            "inactive_fg": "#475569",
            "accent_line": "#0284c7",
        },
        "welcome": {
            "header_fg": "#0a2240",
        },
    },
}


def apply_mode_accent(style: ttk.Style, mode_id: str, root=None) -> None:
    """Aplica el acento cromático del modo activo sobre el tema TMRW Lab.

    Solo actúa cuando el tema activo es 'tmrw_lab'. En otros temas es no-op.
    Tiñe los estilos TTK de frames de sección, botones y pestañas con la
    paleta del modo: azul (studio), verde (lite), morado (analytics), naranja (stress).
    """
    if ThemeManager.get_current_theme_id() != "tmrw_lab":
        return

    pal = MODE_ACCENT_PALETTES.get(mode_id, MODE_ACCENT_PALETTES["_default"])
    t = THEMES["tmrw_lab"]
    bg_tint = pal["bg_tint"]

    # ── Frames y LabelFrames de sección con tinte del modo ───────────────
    for sec in ("Keithley", "Params", "Control"):
        style.configure(f"{sec}.TFrame", background=bg_tint)
        style.configure(f"{sec}.TLabelframe", background=bg_tint, bordercolor=t["bg_window"])
        style.configure(f"{sec}.TLabelframe.Label", background=bg_tint, foreground=pal["dark"])
        style.configure(f"{sec}.TLabel", background=bg_tint, foreground=t["fg_text"])
        style.configure(f"{sec}.TCheckbutton", background=bg_tint, foreground=t["fg_text"])
        style.configure(f"{sec}.TRadiobutton", background=bg_tint, foreground=t["fg_text"])

    # ── Botón Primario ────────────────────────────────────────────────────
    style.configure("Primary.TButton", background=pal["dark"], foreground="#ffffff",
                    bordercolor=pal["dark"], relief="flat")
    style.map("Primary.TButton",
              background=[("active", pal["mid"]), ("disabled", t["border_card"])],
              foreground=[("disabled", t["fg_muted"])])

    # ── Botón Quick ───────────────────────────────────────────────────────
    style.configure("Quick.TButton", background=pal["btn_quick"], foreground="#ffffff",
                    bordercolor=pal["btn_quick"], relief="flat")
    style.map("Quick.TButton",
              background=[("active", pal["btn_quick_hover"]), ("disabled", t["border_card"])],
              foreground=[("disabled", t["fg_muted"])])

    # ── Botón Tool ────────────────────────────────────────────────────────
    style.configure("Tool.TButton", background=pal["btn_tool"], foreground="#ffffff",
                    bordercolor=pal["btn_tool"], relief="flat")
    style.map("Tool.TButton",
              background=[("active", pal["btn_tool_hover"]), ("disabled", t["border_card"])],
              foreground=[("disabled", t["fg_muted"])])

    # ── Pestañas: activa tintada con el color del modo ────────────────────
    style.map("TNotebook.Tab",
              background=[("selected", pal["light"]), ("active", pal["light"])],
              foreground=[("selected", pal["tab_fg"]), ("active", pal["tab_fg"])],
              expand=[("selected", [1, 2, 1, 0])])

    if root is not None:
        try:
            root.configure(background=t["bg_window"])
        except Exception:
            pass


class ThemeManager:
    """Gestor centralizado de temas de la aplicación."""

    _current_theme_id = "tmrw_silicon"
    _listeners = []

    @classmethod
    def get_current_theme_id(cls) -> str:
        return cls._current_theme_id

    @classmethod
    def get_current_theme(cls) -> dict:
        return THEMES.get(cls._current_theme_id, THEMES["tmrw_silicon"])

    @classmethod
    def get_theme_list(cls) -> list[tuple[str, str]]:
        """Retorna lista de tuplas (id, nombre_visible)."""
        return [(t_id, t_data["name"]) for t_id, t_data in THEMES.items()]

    @classmethod
    def set_theme(cls, theme_id: str):
        if theme_id in THEMES:
            cls._current_theme_id = theme_id
            cls._notify_listeners()

    @classmethod
    def add_listener(cls, callback):
        if callback not in cls._listeners:
            cls._listeners.append(callback)

    @classmethod
    def remove_listener(cls, callback):
        if callback in cls._listeners:
            cls._listeners.remove(callback)

    @classmethod
    def _notify_listeners(cls):
        for cb in list(cls._listeners):
            try:
                cb(cls.get_current_theme())
            except Exception:
                pass

    @classmethod
    def apply_ttk_theme(cls, style: ttk.Style, root=None):
        """Aplica la configuración cromática completa del tema actual a ttk.Style."""
        t = cls.get_current_theme()

        # Fondos globales y base
        style.configure("TFrame", background=t["bg_window"])
        style.configure("Window.TFrame", background=t["bg_window"])

        # Tarjetas genéricas
        style.configure("Card.TFrame", background=t["bg_card_default"])

        # ------------------------------------------------------------------
        # Frames internos por sección
        # ------------------------------------------------------------------
        style.configure(
            "Keithley.TFrame",
            background=t["keithley"]["bg"],
        )
        style.configure(
            "Params.TFrame",
            background=t["params"]["bg"],
        )
        style.configure(
            "Control.TFrame",
            background=t["control"]["bg"],
        )
        style.configure(
            "Results.TFrame",
            background=t["results"]["bg"],
        )
        style.configure("Header.TFrame", background=t["bg_window"])

        # LabelFrame base
        style.configure(
            "TLabelframe",
            background=t["bg_card_default"],
            bordercolor=t["border_card"],
            relief="solid",
        )
        style.configure(
            "TLabelframe.Label",
            background=t["bg_card_default"],
            foreground=t["fg_text"],
        )

        # [1] LabelFrame Keithley
        style.configure(
            "Keithley.TLabelframe",
            background=t["keithley"]["bg"],
            bordercolor=t["bg_window"],
            relief="solid",
        )
        style.configure(
            "Keithley.TLabelframe.Label",
            background=t["keithley"]["bg"],
            foreground=t["keithley"]["header_fg"],
        )

        # [2] LabelFrame Parámetros Especí­ficos
        style.configure(
            "Params.TLabelframe",
            background=t["params"]["bg"],
            bordercolor=t["bg_window"],
            relief="solid",
        )
        style.configure(
            "Params.TLabelframe.Label",
            background=t["params"]["bg"],
            foreground=t["params"]["header_fg"],
        )

        # [3] LabelFrame Control
        style.configure(
            "Control.TLabelframe",
            background=t["control"]["bg"],
            bordercolor=t["bg_window"],
            relief="solid",
        )
        style.configure(
            "Control.TLabelframe.Label",
            background=t["control"]["bg"],
            foreground=t["control"]["header_fg"],
        )

        # [4] LabelFrame Resultados
        style.configure(
            "Results.TLabelframe",
            background=t["results"]["bg"],
            bordercolor=t["bg_window"],
            relief="solid",
        )
        style.configure(
            "Results.TLabelframe.Label",
            background=t["results"]["bg"],
            foreground=t["results"]["header_fg"],
        )

        # Etiquetas (TLabel)
        style.configure("TLabel", background=t["bg_card_default"], foreground=t["fg_text"])
        style.configure("Window.TLabel", background=t["bg_window"], foreground=t["fg_text"])
        style.configure("Header.TLabel", background=t["bg_window"], foreground=t["fg_text"])
        style.configure("HeaderMuted.TLabel", background=t["bg_window"], foreground=t["fg_muted"])
        style.configure("Muted.TLabel", background=t["bg_card_default"], foreground=t["fg_muted"])
        style.configure("Params.TLabel", background=t["params"]["bg"], foreground=t["fg_text"])

        # ------------------------------------------------------------------
        # Etiquetas por sección
        # ------------------------------------------------------------------
        style.configure(
            "Keithley.TLabel",
            background=t["keithley"]["bg"],
            foreground=t["fg_text"],
        )
        style.configure(
            "Control.TLabel",
            background=t["control"]["bg"],
            foreground=t["fg_text"],
        )
        style.configure(
            "Results.TLabel",
            background=t["results"]["bg"],
            foreground=t["fg_text"],
        )

        # Celdas Entry y Combobox
        style.configure("TEntry", fieldbackground=t["bg_input"], foreground=t["fg_input"])
        style.configure("TCombobox", fieldbackground=t["bg_input"], foreground=t["fg_input"])

        # Checkbutton & Radiobutton
        style.configure("TCheckbutton", background=t["bg_card_default"], foreground=t["fg_text"])
        style.configure("Params.TCheckbutton", background=t["params"]["bg"], foreground=t["fg_text"])
        style.configure("TRadiobutton", background=t["bg_card_default"], foreground=t["fg_text"])
        style.configure("Params.TRadiobutton", background=t["params"]["bg"], foreground=t["fg_text"])

        # ------------------------------------------------------------------
        # Checkbutton & Radiobutton por sección
        # ------------------------------------------------------------------
        style.configure(
            "Keithley.TCheckbutton",
            background=t["keithley"]["bg"],
            foreground=t["fg_text"],
        )
        style.configure(
            "Control.TCheckbutton",
            background=t["control"]["bg"],
            foreground=t["fg_text"],
        )
        style.configure(
            "Results.TCheckbutton",
            background=t["results"]["bg"],
            foreground=t["fg_text"],
        )

        style.configure(
            "Keithley.TRadiobutton",
            background=t["keithley"]["bg"],
            foreground=t["fg_text"],
        )
        style.configure(
            "Control.TRadiobutton",
            background=t["control"]["bg"],
            foreground=t["fg_text"],
        )
        style.configure(
            "Results.TRadiobutton",
            background=t["results"]["bg"],
            foreground=t["fg_text"],
        )

        # Botonerí­a Jerárquica
        b = t["buttons"]

        # Botón Primario (Iniciar Medida)
        style.configure(
            "Primary.TButton",
            background=b["primary_bg"],
            foreground=b["primary_fg"],
            bordercolor=b["primary_bg"],
            relief="flat",
        )
        style.map(
            "Primary.TButton",
                  background=[("active", b["primary_hover"]), ("disabled", t["border_card"])],
            foreground=[("disabled", t["fg_muted"])],
        )

        # Botón Quick (Medida Rápida)
        style.configure(
            "Quick.TButton",
            background=b["quick_bg"],
            foreground=b["quick_fg"],
            bordercolor=b["quick_bg"],
            relief="flat",
        )
        style.map(
            "Quick.TButton",
                  background=[("active", b["quick_hover"]), ("disabled", t["border_card"])],
            foreground=[("disabled", t["fg_muted"])],
        )

        # Botón Danger (Detener / Abortar)
        style.configure(
            "Danger.TButton",
            background=b["danger_bg"],
            foreground=b["danger_fg"],
            bordercolor=b["danger_bg"],
            relief="flat",
        )
        style.map(
            "Danger.TButton",
                  background=[("active", b["danger_hover"]), ("disabled", t["border_card"])],
            foreground=[("disabled", t["fg_muted"])],
        )

        # Botón Tool (Herramientas / Secundario)
        style.configure(
            "Tool.TButton",
            background=b["tool_bg"],
            foreground=b["tool_fg"],
            bordercolor=b["tool_bg"],
            relief="flat",
        )
        style.map(
            "Tool.TButton",
                  background=[("active", b["tool_hover"]), ("disabled", t["border_card"])],
            foreground=[("disabled", t["fg_muted"])],
        )

        # Pestañas de Notebook (Submodos)
        tab_c = t["tabs"]
        style.configure("TNotebook", background=t["bg_window"], tabmargins=[2, 5, 2, 0])
        style.configure(
            "TNotebook.Tab",
            background=tab_c["inactive_bg"],
            foreground=tab_c["inactive_fg"],
            padding=[10, 4],
            relief="flat",
        )
        style.map(
            "TNotebook.Tab",
                  background=[("selected", tab_c["active_bg"]), ("active", tab_c["active_bg"])],
                  foreground=[("selected", tab_c["active_fg"]), ("active", tab_c["active_fg"])],
            expand=[("selected", [1, 2, 1, 0])],
        )

        if root is not None:
            try:
                root.configure(background=t["bg_window"])
            except Exception:
                pass


# Instancia global de acceso rápido
theme_mgr = ThemeManager
