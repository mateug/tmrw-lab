"""Menú de bienvenida de TMRW Lab.

Lee APP_REGISTRY de apps/__init__.py y construye las tarjetas de modo
dinámicamente — los modos no están hardcodeados aquí.

Para añadir un modo nuevo: crear su carpeta en apps/, definir su MANIFEST,
añadir una línea en apps/__init__.py. Sin tocar este archivo.
"""
from __future__ import annotations

import ctypes
import sys
import tkinter as tk
from tkinter import ttk, messagebox

from core.ui_kit.theme import theme_mgr, apply_mode_accent
from core.ui_kit.scaler import scaler, ui, ui_font, ui_font_title_main, ui_font_subtitle, UIConfig
from core.ui_kit.assets import load_logo


def _enable_high_dpi() -> None:
    if sys.platform != "win32":
        return
    try:
        user32 = ctypes.windll.user32
        shcore = ctypes.windll.shcore
        set_context = getattr(user32, "SetProcessDpiAwarenessContext", None)
        if set_context is not None and set_context(ctypes.c_void_p(-4)):
            return
        set_awareness = getattr(shcore, "SetProcessDpiAwareness", None)
        if set_awareness is not None and set_awareness(2) == 0:
            return
        set_legacy = getattr(user32, "SetProcessDPIAware", None)
        if set_legacy is not None:
            set_legacy()
    except Exception:
        pass


# Colores por índice de tarjeta (hasta 8 modos)
# Colores por índice de tarjeta (hasta 4 modos, correspondientes a las apps)
_CARD_STYLES = [
    {"border": "#0284c7", "hover": "#dbeafe", "title_fg": "#0a2240", "num_fg": "#0284c7"}, # 0: Studio (Azul)
    {"border": "#059669", "hover": "#d1fae5", "title_fg": "#065f46", "num_fg": "#059669"}, # 1: Lite (Verde)
    {"border": "#7c3aed", "hover": "#ede9fe", "title_fg": "#4c1d95", "num_fg": "#7c3aed"}, # 2: Analytics (Morado)
    {"border": "#d97706", "hover": "#fef3c7", "title_fg": "#78350f", "num_fg": "#d97706"}, # 3: Stress (Naranja)
]


class WelcomeFrame(ttk.Frame):
    """Pantalla de bienvenida con tarjetas de modo generadas desde APP_REGISTRY."""

    def __init__(self, parent, callback_seleccionar_modo, app_registry=None, **kwargs):
        super().__init__(parent, **kwargs)
        self._callback = callback_seleccionar_modo
        self._app_registry = app_registry or []
        self._build()

    def _build(self):
        t = theme_mgr.get_current_theme()
        self.configure(style="Window.TFrame")

        main = ttk.Frame(self, style="Window.TFrame")
        main.pack(expand=True, fill="both", padx=ui(20), pady=ui(20))

        # Barra superior: logo + selector de tema
        top = ttk.Frame(main, style="Header.TFrame")
        top.pack(fill="x", pady=(0, ui(10)))

        self._logo = load_logo("logo_y_texto.png", (117, 90))  # (150, 115)
        if self._logo:
            tk.Label(
                top, image=self._logo,
                bg=t["bg_window"], borderwidth=0, highlightthickness=0
            ).pack(side="left")

        f_theme = ttk.Frame(top)
        f_theme.pack(side="right")
        ttk.Label(
            f_theme, text="Tema:",
            font=ui_font("Segoe UI", UIConfig.SIZE_LABEL, "bold"),
            style="HeaderMuted.TLabel",
        ).pack(side="left", padx=(0, ui(4)))

        theme_list = theme_mgr.get_theme_list()
        theme_names = [n for _, n in theme_list]
        theme_ids = [tid for tid, _ in theme_list]
        curr_idx = 0
        curr_id = theme_mgr.get_current_theme_id()
        if curr_id in theme_ids:
            curr_idx = theme_ids.index(curr_id)

        cb_theme = ttk.Combobox(f_theme, values=theme_names, state="readonly", width=22)
        cb_theme.current(curr_idx)
        cb_theme.pack(side="left")

        def _on_theme(event=None):
            idx = cb_theme.current()
            if 0 <= idx < len(theme_ids):
                root = self.winfo_toplevel()
                if hasattr(root, "cambiar_tema"):
                    root.cambiar_tema(theme_ids[idx])

        cb_theme.bind("<<ComboboxSelected>>", _on_theme)

        # Título
        ttk.Label(
            main, text="TMRW LAB",
            font=ui_font_title_main(), style="Window.TLabel", anchor="center"
        ).pack(fill="x", pady=(0, ui(2)))

        # Logo TMRW Lab encima del título
        self._logo_tmrw = load_logo("tmrw_lab.ico", (ui(125), ui(125)))
        if self._logo_tmrw:
            tk.Label(
                main, image=self._logo_tmrw,
                bg=t["bg_window"], borderwidth=0, highlightthickness=0
            ).pack(pady=(ui(10), ui(4)))

        ttk.Label(
            main, text="Automatización de medidas de laboratorio",
            font=ui_font_subtitle(), style="Window.TLabel", anchor="center"
        ).pack(fill="x", pady=(0, ui(12)))
        ttk.Separator(main, orient="horizontal").pack(fill="x", pady=(0, ui(15)))

        # Tarjetas de modo
        cards = ttk.Frame(main, style="Window.TFrame")
        cards.pack(expand=True, fill="both", padx=ui(10), pady=ui(10))
        n = max(1, len(self._app_registry))
        for col in range(n):
            cards.columnconfigure(col, weight=1, uniform="card")
        cards.rowconfigure(0, weight=1)

        for i, manifest in enumerate(self._app_registry):
            style = _CARD_STYLES[i % len(_CARD_STYLES)]
            self._crear_tarjeta(cards, manifest, i, style)

    def _crear_tarjeta(self, parent, manifest, col_idx, style):
        t = theme_mgr.get_current_theme()
        bg = t.get("bg_card_default", "#e2e8f0")

        # Cargar icono .ico del modo
        icono_archivo = manifest.get("icono_archivo", "")
        icono_img = None
        if icono_archivo:
            icono_img = load_logo(f"{icono_archivo}.ico", (ui(100), ui(100)))

        frame = tk.Frame(
            parent,
            bg=bg,
            relief="flat",
            bd=0,
            highlightthickness=2,
            highlightbackground=style["border"],
            cursor="hand2",
        )
        frame.grid(row=0, column=col_idx, padx=ui(8), pady=ui(8), sticky="nsew")

        # Número de modo
        tk.Label(
            frame,
            text=f"Modo {col_idx + 1}",
            bg=bg,
            fg=style["num_fg"],
            font=ui_font("Segoe UI", 6.5, "bold"),
            cursor="hand2",
        ).pack(pady=(ui(16), ui(4)))

        # Título
        tk.Label(
            frame,
            text=manifest["nombre"],
            bg=bg,
            fg=style["title_fg"],
            font=ui_font("Segoe UI", 9.5, "bold"),
            wraplength=ui(220),
            justify="center",
            cursor="hand2",
        ).pack(pady=(0, ui(6)))

        # Icono del modo (entre nombre y descripción)
        if icono_img:
            lbl_ico = tk.Label(
                frame,
                image=icono_img,
                bg=bg,
                borderwidth=0,
                highlightthickness=0,
                cursor="hand2",
            )
            lbl_ico.image = icono_img  # mantener referencia
            lbl_ico.pack(pady=(0, ui(8)))

        # Descripción
        tk.Label(
            frame,
            text=manifest.get("descripcion", ""),
            bg=bg,
            fg=t.get("fg_muted", "#475569"),
            font=ui_font("Segoe UI", 5.8),
            wraplength=ui(220),
            justify="center",
            cursor="hand2",
        ).pack(padx=ui(14), pady=(0, ui(16)), fill="both", expand=True)

        # Hover & click
        modo_id = manifest["id"]

        def _hover_on(e, f=frame, s=style):
            f.configure(bg=s["hover"])
            for child in f.winfo_children():
                try:
                    child.configure(bg=s["hover"])
                except Exception:
                    pass

        def _hover_off(e, f=frame, bg_=bg):
            f.configure(bg=bg_)
            for child in f.winfo_children():
                try:
                    child.configure(bg=bg_)
                except Exception:
                    pass

        def _click(e=None, mid=modo_id):
            self._callback(mid)

        for widget in [frame] + list(frame.winfo_children()):
            widget.bind("<Enter>", _hover_on)
            widget.bind("<Leave>", _hover_off)
            widget.bind("<Button-1>", _click)

        frame.bind("<Enter>", _hover_on)
        frame.bind("<Leave>", _hover_off)
        frame.bind("<Button-1>", _click)


class App(tk.Tk):
    """Ventana raíz de TMRW Lab."""

    _RESIZE_THRESHOLD = 0.025

    def __init__(self, app_registry=None):
        _enable_high_dpi()
        super().__init__()
        self.title("TMRW Lab")
        self._app_registry = app_registry or []
        self._last_scale = scaler.ui_scale

        self._configure_scaling()
        screen_w = self.winfo_screenwidth()
        screen_h = self.winfo_screenheight()
        target_w, target_h = self._set_geometry(screen_w, screen_h)
        scaler.update(target_w, target_h)

        self._style = ttk.Style(self)
        try:
            self._style.theme_use("clam")
        except Exception:
            pass
        scaler.apply_style_scaling(self._style, self)
        t = theme_mgr.get_current_theme()
        self.configure(background=t["bg_window"])

        self._container = ttk.Frame(self)
        self._container.pack(fill="both", expand=True)

        self._welcome_frame = None
        self._mode_frame = None
        self._modo_actual = None

        self.mostrar_bienvenida()
        self.bind("<Configure>", self._on_resize, add="+")

    def _configure_scaling(self):
        try:
            dpi = float(self.winfo_fpixels("1i"))
            if dpi > 0:
                self.tk.call("tk", "scaling", dpi / 72.0)
        except Exception:
            pass

    def _set_geometry(self, sw, sh) -> tuple[int, int]:
        tw = max(960, int(sw * 0.75))
        th = max(680, int(sh * 0.82))
        tw, th = min(tw, sw), min(th, sh)
        self.minsize(min(sw, max(960, int(sw * 0.5))), min(sh, max(680, int(sh * 0.5))))
        x, y = max(0, (sw - tw) // 2), max(0, (sh - th) // 2)
        self.geometry(f"{tw}x{th}+{x}+{y}")
        return tw, th

    def _on_resize(self, event: tk.Event):
        if event.widget is not self or event.width <= 0 or event.height <= 0:
            return
        new_scale = scaler.update(event.width, event.height)
        if abs(new_scale - self._last_scale) < self._RESIZE_THRESHOLD:
            return
        self._last_scale = new_scale
        scaler.apply_style_scaling(self._style, self)

    def cambiar_tema(self, nuevo_tema_id: str):
        theme_mgr.set_theme(nuevo_tema_id)
        scaler.apply_style_scaling(self._style, self)
        t = theme_mgr.get_current_theme()
        self.configure(background=t["bg_window"])
        if self._modo_actual is None:
            self.mostrar_bienvenida()
        else:
            self.cargar_modo(self._modo_actual)

    def mostrar_bienvenida(self):
        self._modo_actual = None
        # Restablecemos el tema base por si venimos de un modo con acento
        theme_mgr.apply_ttk_theme(self._style, self)
        if self._mode_frame:
            self._mode_frame.destroy()
            self._mode_frame = None
        if self._welcome_frame:
            self._welcome_frame.destroy()
        self._welcome_frame = WelcomeFrame(
            self._container,
            callback_seleccionar_modo=self.cargar_modo,
            app_registry=self._app_registry,
        )
        self._welcome_frame.pack(fill="both", expand=True)

    def cargar_modo(self, modo_id: str):
        manifest = next((m for m in self._app_registry if m["id"] == modo_id), None)
        if manifest is None:
            messagebox.showerror("Error", f"Modo '{modo_id}' no encontrado en APP_REGISTRY.")
            return

        self._modo_actual = modo_id
        if self._welcome_frame:
            self._welcome_frame.destroy()
            self._welcome_frame = None
        if self._mode_frame:
            self._mode_frame.destroy()

        self._mode_frame = manifest["crear_frame"](
            self._container,
            callback_volver=self.mostrar_bienvenida,
        )
        self._mode_frame.pack(fill="both", expand=True)
        
        # Aplicamos el color de acento del modo activo
        apply_mode_accent(self._style, modo_id, self)


def launch(app_registry=None):
    if app_registry is None:
        try:
            import importlib
            apps_mod = importlib.import_module("apps")
            app_registry = getattr(apps_mod, "APP_REGISTRY", [])
        except Exception:
            app_registry = []
    App(app_registry=app_registry).mainloop()
