import tkinter as tk
from tkinter import ttk, messagebox, filedialog

from core.ui_kit.scaler import ui, ui_font, ui_font_section_header, UIConfig, scaler
from core.ui_kit.theme import theme_mgr
from core.ui_kit.assets import load_logo


class ScrollableFrame(ttk.Frame):
    """Contenedor desplegable vertical que ajusta dinámicamente su ancho al del Canvas."""

    _instances = []
    _mousewheel_bound_roots = set()

    def __init__(self, parent, *args, **kwargs):
        super().__init__(parent, *args, **kwargs)

        t = theme_mgr.get_current_theme()
        self.canvas = tk.Canvas(
            self,
            borderwidth=0,
            highlightthickness=0,
            background=t["bg_window"],
        )
        self.scrollbar = ttk.Scrollbar(
            self,
            orient="vertical",
            command=self.canvas.yview,
        )
        self.scroll_content = ttk.Frame(self.canvas)

        self.scroll_content.bind(
            "<Configure>",
            lambda e: self.canvas.configure(
                scrollregion=self.canvas.bbox("all")
            ),
        )

        self.window_id = self.canvas.create_window(
            (0, 0),
            window=self.scroll_content,
            anchor="nw",
        )

        self.canvas.configure(yscrollcommand=self.scrollbar.set)

        self.canvas.pack(side="left", fill="both", expand=True)
        self.scrollbar.pack(side="right", fill="y")

        # Ajusta automáticamente el ancho del contenido interno
        # al cambiar el tamaño de la ventana.
        self.canvas.bind("<Configure>", self._on_canvas_configure)

        # Registra esta instancia para poder determinar qué
        # ScrollableFrame está bajo el cursor del ratón.
        ScrollableFrame._instances.append(self)

        # El binding se realiza una sola vez por ventana principal.
        root = self.winfo_toplevel()

        if root not in ScrollableFrame._mousewheel_bound_roots:
            root.bind_all(
                "<MouseWheel>",
                ScrollableFrame._handle_mousewheel,
                add="+",
            )
            ScrollableFrame._mousewheel_bound_roots.add(root)

    def _on_canvas_configure(self, event):
        """Ajusta el ancho del contenido interno al ancho del Canvas."""
        self.canvas.itemconfig(self.window_id, width=event.width)

    @classmethod
    def _handle_mousewheel(cls, event):
        """Desplaza el ScrollableFrame que contiene el widget bajo el cursor."""
        widget = event.widget

        for scrollable_frame in reversed(cls._instances):
            if cls._widget_is_inside(widget, scrollable_frame):
                scrollable_frame.canvas.yview_scroll(
                    -int(event.delta / 120),
                    "units",
                )
                return "break"

        return None

    @staticmethod
    def _widget_is_inside(widget, scrollable_frame):
        """Comprueba si un widget pertenece a un ScrollableFrame."""
        current = widget

        while current is not None:
            if current is scrollable_frame.scroll_content:
                return True

            if current is scrollable_frame.canvas:
                return True

            if current is scrollable_frame:
                return True

            current = getattr(current, "master", None)

        return False

    def destroy(self):
        """Elimina la instancia de la lista de ScrollableFrames."""
        if self in ScrollableFrame._instances:
            ScrollableFrame._instances.remove(self)

        super().destroy()


def crear_barra_superior(master, titulo_modo, callback_volver):
    """Crea una barra de navegación superior con botón 'â† Volver al menú principal', tí­tulo y selector de tema."""
    t = theme_mgr.get_current_theme()
    header_frame = ttk.Frame(master, style="Header.TFrame")
    header_frame.pack(fill="x", padx=ui(12), pady=(ui(8), ui(4)))

    btn_volver = ttk.Button(
        header_frame,
        text="â† Volver al menú principal",
        command=callback_volver,
        style="Tool.TButton",
    )
    btn_volver.pack(side="left")

    logo_simbolo = load_logo("logo.jpg", (32, 32))
    if logo_simbolo is not None:
        lbl_logo = tk.Label(
            header_frame,
            image=logo_simbolo,
            bg=t["bg_window"],
            borderwidth=0,
            highlightthickness=0,
        )
        lbl_logo.image = logo_simbolo
        lbl_logo.pack(side="left", padx=(ui(12), ui(4)))

    lbl_titulo = ttk.Label(
        header_frame,
        text=titulo_modo,
        font=ui_font_section_header(),
        style="Header.TLabel",
    )
    lbl_titulo.pack(side="left", padx=ui(15))

    # Selector de tema en la esquina derecha
    f_theme = ttk.Frame(header_frame, style="Header.TFrame")
    f_theme.pack(side="right")

    ttk.Label(f_theme, text="Tema:", font=ui_font("Segoe UI", UIConfig.SIZE_LABEL, "bold"), style="HeaderMuted.TLabel").pack(side="left", padx=(0, ui(4)))

    theme_list = theme_mgr.get_theme_list()
    theme_names = [name for _, name in theme_list]
    theme_ids = [t_id for t_id, _ in theme_list]

    current_idx = 0
    curr_id = theme_mgr.get_current_theme_id()
    if curr_id in theme_ids:
        current_idx = theme_ids.index(curr_id)

    cb_theme = ttk.Combobox(
        f_theme,
        values=theme_names,
        state="readonly",
        width=max(18, scaler.scale(UIConfig.COMBOBOX_MIN_WIDTH) // 5),
    )
    cb_theme.current(current_idx)
    cb_theme.pack(side="left")

    def _on_theme_select(event=None):
        sel_idx = cb_theme.current()
        if 0 <= sel_idx < len(theme_ids):
            nuevo_id = theme_ids[sel_idx]
            app_root = master.winfo_toplevel()
            if hasattr(app_root, "cambiar_tema"):
                app_root.cambiar_tema(nuevo_id)

    cb_theme.bind("<<ComboboxSelected>>", _on_theme_select)

    ttk.Separator(master, orient="horizontal").pack(fill="x", padx=ui(12), pady=ui(4))
    return header_frame


def crear_seccion_frame(master, texto_titulo, tipo_seccion="default"):
    """Crea un LabelFrame enriquecido con estilo diferenciado según el tipo de sección.

    Tipos admitidos:
    - 'keithley' -> Estilo hardware [1]
    - 'params'   -> Estilo parámetros de módulo [2]
    - 'control'  -> Estilo panel de acción [3]
    - 'results'  -> Estilo resultados [4]
    - 'default'  -> Estilo estándar
    """
    estilo_map = {
        "keithley": "Keithley.TLabelframe",
        "params": "Params.TLabelframe",
        "control": "Control.TLabelframe",
        "results": "Results.TLabelframe",
        "default": "TLabelframe",
    }
    style_name = estilo_map.get(tipo_seccion, "TLabelframe")
    lf = ttk.LabelFrame(
        master,
        text=f" {texto_titulo} ",
        padding=ui(UIConfig.PADDING_SECTION),
        style=style_name,
    )
    lf.pack(fill="x", expand=True, padx=ui(12), pady=ui(5))
    return lf


def crear_campo_directorio(parent, variable_path, row, label_text="Carpeta de salida:"):
    """Crea una fila con etiqueta, entrada de texto y botón de examinar carpeta."""
    ttk.Label(parent, text=label_text).grid(row=row, column=0, sticky="w", pady=ui(2))
    entry = ttk.Entry(parent, textvariable=variable_path)
    entry.grid(row=row, column=1, sticky="ew", padx=ui(6), pady=ui(2))

    def _examinar():
        dir_sel = filedialog.askdirectory(initialdir=variable_path.get())
        if dir_sel:
            variable_path.set(dir_sel)

    btn = ttk.Button(parent, text="Buscar...", command=_examinar, style="Tool.TButton")
    btn.grid(row=row, column=2, sticky="e", pady=ui(2))
    parent.columnconfigure(1, weight=1)
    return entry, btn


def crear_panel_keithley_basico(parent, vars_dict):
    """Crea el panel de configuración común de parámetros Keithley (VISA, Barrido, Imax, Superficie, Irradiancia)."""
    lf = crear_seccion_frame(parent, "[1] Configuración del Instrumento Keithley 2450", tipo_seccion="keithley")

    # Fila 1: Carpeta de salida
    crear_campo_directorio(lf, vars_dict["carpeta_salida"], row=1)

    # Fila 2: Carpeta de la ejecución
    ttk.Label(lf, text="Nombre de carpeta:").grid(row=2, column=0, sticky="w", pady=ui(2))
    ttk.Entry(lf, textvariable=vars_dict["nombre_carpeta_medida"]).grid(
        row=2, column=1, columnspan=3, sticky="ew", padx=ui(6), pady=ui(2)
    )

    # Fila 3: Nombre de medida y modo de barrido
    ttk.Label(lf, text="Nombre de medida:").grid(row=3, column=0, sticky="w", pady=ui(2))
    ttk.Entry(lf, textvariable=vars_dict["nombre_medida"]).grid(row=3, column=1, sticky="ew", padx=ui(6), pady=ui(2))

    ttk.Label(lf, text="Modo de barrido:").grid(row=3, column=2, sticky="w", pady=ui(2), padx=(ui(10), ui(2)))
    cb_modo = ttk.Combobox(
        lf,
        textvariable=vars_dict["modo_medida"],
        values=["completa", "directa", "inversa"],
        state="readonly",
        width=max(8, scaler.scale(UIConfig.COMBOBOX_MIN_WIDTH) // 7),
    )
    cb_modo.grid(row=3, column=3, sticky="w", pady=ui(2))

    # Fila 4: Parámetros del barrido directo/completo
    f_barrido = ttk.Frame(lf, style="Keithley.TFrame")
    f_barrido.grid(row=4, column=0, columnspan=4, sticky="ew", pady=ui(5))

    ttk.Label(f_barrido, text="V ini (mV):").pack(side="left")
    ttk.Entry(f_barrido, textvariable=vars_dict["v_ini_dir"], width=8).pack(side="left", padx=(ui(2), ui(10)))

    ttk.Label(f_barrido, text="V fin (mV):").pack(side="left")
    ttk.Entry(f_barrido, textvariable=vars_dict["v_fin_dir"], width=8).pack(side="left", padx=(ui(2), ui(10)))

    ttk.Label(f_barrido, text="Paso (mV):").pack(side="left")
    ttk.Entry(f_barrido, textvariable=vars_dict["paso_dir"], width=8).pack(side="left", padx=(ui(2), ui(10)))

    ttk.Label(f_barrido, text="I_max (ÂµA):").pack(side="left")
    ttk.Entry(f_barrido, textvariable=vars_dict["i_max_uA"], width=10).pack(side="left", padx=(ui(2), ui(10)))

    # Fila 5: Parámetros del barrido inverso
    f_inv = ttk.Frame(lf, style="Keithley.TFrame")
    f_inv.grid(row=5, column=0, columnspan=4, sticky="ew", pady=ui(2))

    ttk.Label(f_inv, text="[Inversa] V fin (V):").pack(side="left")
    ttk.Entry(f_inv, textvariable=vars_dict["v_fin_inv"], width=8).pack(side="left", padx=(ui(2), ui(10)))

    ttk.Label(f_inv, text="[Inversa] Paso (mV):").pack(side="left")
    ttk.Entry(f_inv, textvariable=vars_dict["paso_inv"], width=8).pack(side="left", padx=(ui(2), ui(10)))

    # Fila 6: Muestra y opciones fí­sicas
    f_muestra = ttk.Frame(lf, style="Keithley.TFrame")
    f_muestra.grid(row=6, column=0, columnspan=4, sticky="ew", pady=ui(5))

    ttk.Label(f_muestra, text="Superficie (ÂµmÂ²):").pack(side="left")
    ttk.Entry(f_muestra, textvariable=vars_dict["superficie_um2"], width=12).pack(side="left", padx=(ui(2), ui(12)))

    ttk.Label(f_muestra, text="Irradiancia (mW/cmÂ²):").pack(side="left")
    ttk.Entry(f_muestra, textvariable=vars_dict["irradiancia_mW_cm2"], width=10).pack(side="left", padx=(ui(2), ui(12)))

    ttk.Checkbutton(f_muestra, text="Invertir eje Y", variable=vars_dict["invertir_eje_y"]).pack(side="left", padx=ui(6))
    ttk.Checkbutton(f_muestra, text="Readback tensión real", variable=vars_dict["medir_tension_real"]).pack(side="left", padx=ui(6))

    lf.columnconfigure(1, weight=1)
    return lf


def mostrar_error(titulo, mensaje):
    messagebox.showerror(titulo, mensaje)


def mostrar_info(titulo, mensaje):
    messagebox.showinfo(titulo, mensaje)

# ---------------------------------------------------------------------------
# Aliases para compatibilidad con devices-degradation
# ---------------------------------------------------------------------------

section = crear_seccion_frame
directory_field = crear_campo_directorio
header = crear_barra_superior
