"""Módulo centralizado de escalado responsive y configuración de diseño UI.

Todos los tamaños base de fuentes, paddings y dimensiones de la interfaz
están centralizados en la clase UIConfig al inicio de este archivo.
Cualquier cambio realizado en los parámetros numéricos de UIConfig se reflejará
automáticamente en toda la aplicación.
"""
from __future__ import annotations
from tkinter import ttk


class UIConfig:
    """Configuración centralizada de tamaños base para el diseño a 1280x800."""

    # --- Familias de Fuente ---
    FONT_PRIMARY = "Segoe UI"     # Fuente principal de interfaz
    FONT_CONSOLE = "Consolas"     # Fuente monoespaciada para consolas y logs

    # --- Tamaños Base de Fuente (en Puntos) ---
    SIZE_TITLE_MAIN = 14          # Título principal de bienvenida
    SIZE_SUBTITLE = 8.5           # Subtítulo principal de bienvenida
    SIZE_CARD_TITLE = 9.5         # Título en cabecera de tarjetas de modo
    SIZE_SECTION_HEADER = 7.0     # Títulos de secciones dentro de los cuadros LabelFrame
    SIZE_LABEL = 4.5              # Texto de etiquetas estándar, casillas y botones de radio
    SIZE_ENTRY = 4.5              # Texto editable dentro de las celdas de entrada (Entry, Combobox)
    SIZE_COMBOBOX_LIST = 4.5      # Texto de las opciones desplegables del menú (listbox de Combobox)
    SIZE_BUTTON = 4.5             # Texto dentro de los botones de acción
    SIZE_CONSOLE = 4.5            # Texto impreso dentro de la consola / resultados
    SIZE_INFO_ITALIC = 4.5        # Textos informativos secundarios o en cursiva explicativa

    # --- Dimensiones de Widgets (en Píxeles) ---
    ENTRY_HEIGHT = 22             # Altura total de las celdas de texto editables (Entry)
    ENTRY_MIN_WIDTH = 30          # Ancho mínimo de las celdas de texto editables
    COMBOBOX_HEIGHT = 22          # Altura total de los desplegables (Combobox)
    COMBOBOX_MIN_WIDTH = 80       # Ancho mínimo de los desplegables
    BUTTON_HEIGHT = 24            # Altura total de los botones de acción
    BUTTON_MIN_WIDTH = 60         # Ancho mínimo de los botones de acción
    SCROLLBAR_WIDTH = 16          # Ancho de las barras de desplazamiento
    CONSOLE_HEIGHT = 13           # Filas base de la consola de salida

    # --- Márgenes Internos y Paddings Base (en Píxeles) ---
    PADDING_MAIN_CONTAINER = 30   # Padding alrededor del contenedor principal de bienvenida
    PADDING_CARD = 15             # Padding interno de cada tarjeta de modo
    PADDING_SECTION = 8           # Padding interno de las secciones de configuración (LabelFrame)
    PADDING_ENTRY_HORIZONTAL = 2  # Margen interno horizontal en celdas
    PADDING_ENTRY_VERTICAL = 1    # Margen interno vertical en celdas
    PADDING_BUTTON_HORIZONTAL = 5 # Margen interno horizontal de botones
    PADDING_BUTTON_VERTICAL = 2   # Margen interno vertical de botones
    PADDING_SECTION_OUTER_HORIZONTAL = 12
    PADDING_SECTION_OUTER_VERTICAL = 5
    PADDING_HEADER_HORIZONTAL = 12
    PADDING_HEADER_TOP = 8
    PADDING_HEADER_BOTTOM = 4
    PADDING_HEADER_TITLE = 6
    PADDING_FIELD_HORIZONTAL = 6
    PADDING_GRID_HORIZONTAL = 4
    PADDING_GRID_VERTICAL = 2
    PADDING_CONTROL_VERTICAL = 8
    PADDING_NOTE_BOTTOM = 8
    PADDING_TAB = 10
    PADDING_TAB_CONTAINER_VERTICAL = 6
    WRAPLENGTH_SECTION = 900
    WRAPLENGTH_CARD = 350         # Ancho máximo en píxeles antes de salto de línea en tarjetas
    TREEVIEW_ROW_HEIGHT = 14      # Altura de cada fila en las tablas Treeview
    THEME_COMBOBOX_WIDTH = 18     # Anchura en caracteres del selector de temas


class Scaler:
    """Gestor central de escalado responsive de la interfaz de usuario."""

    BASE_W = 1280    # Ancho de pantalla de referencia
    BASE_H = 800     # Alto de pantalla de referencia
    MIN_SCALE = 0.70 # Límite inferior de escala
    MAX_SCALE = 2.50 # Límite superior de escala

    def __init__(self):
        self.ui_scale = 1.0

    def update(self, width: int, height: int) -> float:
        """Recalcula la escala UI basada en el ancho y alto actuales de la ventana."""
        if width <= 0 or height <= 0:
            return self.ui_scale

        scale_w = width / self.BASE_W
        scale_h = height / self.BASE_H
        raw_scale = min(scale_w, scale_h)

        self.ui_scale = max(self.MIN_SCALE, min(self.MAX_SCALE, raw_scale))
        return self.ui_scale

    def scale(self, value: float | int) -> int:
        """Escala un valor numérico de diseño según la escala UI actual."""
        return int(round(value * self.ui_scale))

    def font(self, family: str, size: float | int, weight: str = "") -> tuple:
        """Retorna una tupla de fuente de Tkinter con tamaño en puntos escalado."""
        scaled_pt = max(6, int(round(size * self.ui_scale)))
        if weight:
            return (family, scaled_pt, weight)
        return (family, scaled_pt)

    def apply_style_scaling(self, style: ttk.Style, root_app=None):
        """Aplica configuraciones escaladas a los estilos predeterminados de ttk."""
        try:
            btn_padding = (
                self.scale(UIConfig.PADDING_BUTTON_HORIZONTAL),
                self.scale(UIConfig.PADDING_BUTTON_VERTICAL),
            )
            entry_padding = (
                self.scale(UIConfig.PADDING_ENTRY_HORIZONTAL),
                self.scale(UIConfig.PADDING_ENTRY_VERTICAL),
            )

            font_entry = self.font(UIConfig.FONT_PRIMARY, UIConfig.SIZE_ENTRY)
            font_label = self.font(UIConfig.FONT_PRIMARY, UIConfig.SIZE_LABEL)
            font_label_bold = self.font(UIConfig.FONT_PRIMARY, UIConfig.SIZE_LABEL, "bold")
            font_button = self.font(UIConfig.FONT_PRIMARY, UIConfig.SIZE_BUTTON, "bold")

            entry_h = self.scale(UIConfig.ENTRY_HEIGHT)
            combobox_h = self.scale(UIConfig.COMBOBOX_HEIGHT)
            button_h = self.scale(UIConfig.BUTTON_HEIGHT)
            scrollbar_w = self.scale(UIConfig.SCROLLBAR_WIDTH)

            style.configure("TButton", padding=btn_padding, font=font_button)
            style.configure("TLabelframe.Label", font=self.font(UIConfig.FONT_PRIMARY, UIConfig.SIZE_SECTION_HEADER, "bold"))
            style.configure("TLabel", font=font_label)
            style.configure("Header.TLabel", font=self.font(UIConfig.FONT_PRIMARY, UIConfig.SIZE_SECTION_HEADER, "bold"))

            style.configure("TEntry", padding=entry_padding, font=font_entry)
            style.map("TEntry", fieldbackground=[("readonly", "#f0f0f0")])

            style.configure("TCombobox", padding=entry_padding, font=font_entry)

            style.configure("Vertical.TScrollbar", arrowsize=scrollbar_w, width=scrollbar_w)
            style.configure("Horizontal.TScrollbar", arrowsize=scrollbar_w, width=scrollbar_w)

            if root_app is not None:
                try:
                    root_app.option_add("*Entry.font", font_entry)
                    root_app.option_add("*TEntry.font", font_entry)
                    root_app.option_add("*Entry*font", font_entry)
                    root_app.option_add("*Combobox.font", font_entry)
                    root_app.option_add("*TCombobox.font", font_entry)
                    root_app.option_add("*Combobox*font", font_entry)
                    root_app.option_add("*Entry.height", entry_h)
                    root_app.option_add("*TCombobox.height", combobox_h)

                    font_combo_list = self.font(UIConfig.FONT_PRIMARY, UIConfig.SIZE_COMBOBOX_LIST)
                    root_app.option_add("*TCombobox*Listbox.font", font_combo_list)
                    root_app.option_add("*Listbox.font", font_combo_list)
                except Exception:
                    pass

            style.configure("TCheckbutton", font=font_label)
            style.configure("TRadiobutton", font=font_label)
            style.configure(
                "TNotebook.Tab",
                padding=(self.scale(12), self.scale(6)),
                font=font_label_bold,
            )
            style.configure(
                "Treeview",
                rowheight=self.scale(UIConfig.TREEVIEW_ROW_HEIGHT),
                font=font_label,
            )
            style.configure("Treeview.Heading", font=font_label_bold)

            try:
                from core.ui_kit.theme import theme_mgr
                theme_mgr.apply_ttk_theme(style, root_app)
            except Exception:
                pass
        except Exception:
            pass


scaler = Scaler()


def ui(value: float | int) -> int:
    """Función global rápida para escalar valores de diseño en píxeles."""
    return scaler.scale(value)


def ui_font(family: str, size: float | int, weight: str = "") -> tuple:
    """Función global rápida para generar tuplas de fuentes escaladas."""
    return scaler.font(family, size, weight)


def ui_font_title_main() -> tuple:
    """Retorna la fuente escalada para el título principal."""
    return scaler.font(UIConfig.FONT_PRIMARY, UIConfig.SIZE_TITLE_MAIN, "bold")


def ui_font_subtitle() -> tuple:
    """Retorna la fuente escalada para el subtítulo principal."""
    return scaler.font(UIConfig.FONT_PRIMARY, UIConfig.SIZE_SUBTITLE)


def ui_font_card_title() -> tuple:
    """Retorna la fuente escalada para títulos de tarjetas."""
    return scaler.font(UIConfig.FONT_PRIMARY, UIConfig.SIZE_CARD_TITLE, "bold")


def ui_font_section_header() -> tuple:
    """Retorna la fuente escalada para títulos de sección (LabelFrame/Header)."""
    return scaler.font(UIConfig.FONT_PRIMARY, UIConfig.SIZE_SECTION_HEADER, "bold")


def ui_font_label(bold: bool = False) -> tuple:
    """Retorna la fuente escalada para etiquetas estándar."""
    weight = "bold" if bold else ""
    return scaler.font(UIConfig.FONT_PRIMARY, UIConfig.SIZE_LABEL, weight)


def ui_font_entry() -> tuple:
    """Retorna la fuente escalada para celdas de entrada (Entry/Combobox)."""
    return scaler.font(UIConfig.FONT_PRIMARY, UIConfig.SIZE_ENTRY)


def ui_font_button() -> tuple:
    """Retorna la fuente escalada para botones."""
    return scaler.font(UIConfig.FONT_PRIMARY, UIConfig.SIZE_BUTTON, "bold")


def ui_font_console() -> tuple:
    """Retorna la fuente escalada para consolas de texto."""
    return scaler.font(UIConfig.FONT_CONSOLE, UIConfig.SIZE_CONSOLE)


def ui_font_info() -> tuple:
    """Retorna la fuente escalada para notas explicativas en cursiva."""
    return scaler.font(UIConfig.FONT_PRIMARY, UIConfig.SIZE_INFO_ITALIC, "italic")
