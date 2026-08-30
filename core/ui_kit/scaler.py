"""Módulo centralizado de escalado responsive y configuración de diseño UI.

Todos los tamaños base de fuentes, paddings y dimensiones de la interfaz
están centralizados en la clase UIConfig al inicio de este archivo.
Cualquier cambio realizado en los parámetros numéricos de UIConfig se reflejará
automáticamente en toda la aplicación.
"""

from tkinter import ttk


class UIConfig:
    """Configuración centralizada de tamaños base para el diseño a 1280x800.

    Modificar los valores numéricos de esta clase cambia automáticamente los
    tamaños de fuentes, celdas y márgenes en todas las pantallas del proyecto.
    """

    # --- Familias de Fuente ---
    FONT_PRIMARY = "Segoe UI"     # Fuente principal de interfaz (etiquetas, botones, tí­tulos, entradas)
    FONT_CONSOLE = "Consolas"     # Fuente monoespaciada para las consolas de texto y logs de medición

    # --- Tamaños Base de Fuente (en Puntos) ---
    SIZE_TITLE_MAIN = 14          # Tí­tulo principal de bienvenida ("Automatizador de medidas")
    SIZE_SUBTITLE = 8.5           # Subtí­tulo principal de bienvenida ("Seleccione el modo de uso")
    SIZE_CARD_TITLE = 8         # Tí­tulo en cabecera de tarjetas de modo (ðŸ“Š Medidas estáticas, etc.)
    SIZE_SECTION_HEADER = 7       # Tí­tulos de secciones dentro de los cuadros LabelFrame
    SIZE_LABEL = 4               # Texto de etiquetas estándar, casillas Checkbutton y botones Radiobutton
    SIZE_ENTRY = 4               # Texto editable dentro de las celdas de entrada (Entry, Combobox, listas)
    SIZE_COMBOBOX_LIST = 4       # Texto de las opciones desplegables del menú (listbox de Combobox)
    SIZE_BUTTON = 4               # Texto dentro de los botones de acción (â–¶ INICIAR, Buscar..., etc.)
    SIZE_CONSOLE = 4              # Texto impreso dentro de la consola / resultados de medición
    SIZE_INFO_ITALIC = 4          # Textos informativos secundarios o en cursiva explicativa

    # --- Dimensiones de Widgets (en Pí­xeles) --- (Solo funciona scrollbar_width)
    ENTRY_HEIGHT = 22             # Altura total de las celdas de texto editables (Entry)
    ENTRY_MIN_WIDTH = 30          # Ancho mí­nimo de las celdas de texto editables en pí­xeles
    COMBOBOX_HEIGHT = 22          # Altura total de los desplegables/selectores (Combobox)
    COMBOBOX_MIN_WIDTH = 80       # Ancho mí­nimo de los desplegables/selectores en pí­xeles
    BUTTON_HEIGHT = 24            # Altura total de los botones de acción
    BUTTON_MIN_WIDTH = 60         # Ancho mí­nimo de los botones de acción en pí­xeles
    SCROLLBAR_WIDTH = 16          # Ancho de las barras de desplazamiento (scrollbar vertical/horizontal)
    CONSOLE_HEIGHT = 13           # Filas base de la consola de salida

    # --- Márgenes Internos y Paddings Base (en Pí­xeles) ---
    PADDING_MAIN_CONTAINER = 30   # Padding alrededor del contenedor principal de la pantalla de bienvenida
    PADDING_CARD = 15             # Padding interno de cada tarjeta de selección de modo
    PADDING_SECTION = 8          # Padding interno de las secciones de configuración (LabelFrame)
    PADDING_ENTRY_HORIZONTAL = 2  # Margen interno izquierdo/derecho dentro de las celdas (ancho de celda)
    PADDING_ENTRY_VERTICAL = 1    # Margen interno superior/inferior dentro de las celdas (altura de celda)
    PADDING_BUTTON_HORIZONTAL = 5 # Margen interno horizontal de los botones
    PADDING_BUTTON_VERTICAL = 2   # Margen interno vertical de los botones
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
    WRAPLENGTH_CARD = 350         # Ancho máximo en pí­xeles antes de hacer salto de lí­nea en tarjetas
    TREEVIEW_ROW_HEIGHT = 14      # Altura de cada fila en las tablas Treeview o desplegables
    THEME_COMBOBOX_WIDTH = 18     # Anchura en caracteres del selector de temas


class Scaler:
    """Gestor central de escalado responsive de la interfaz de usuario."""

    BASE_W = 1280    # Ancho de pantalla de referencia en el que se diseñó la interfaz
    BASE_H = 800     # Alto de pantalla de referencia en el que se diseñó la interfaz
    MIN_SCALE = 0.70 # Lí­mite inferior de escala para evitar que la UI quede absurdamente diminuta
    MAX_SCALE = 2.50 # Lí­mite superior de escala para evitar que la UI quede absurdamente gigante en 4K

    def __init__(self):
        self.ui_scale = 1.0

    def update(self, width: int, height: int) -> float:
        """Recalcula la escala UI basada en el ancho y alto actuales de la ventana."""
        if width <= 0 or height <= 0:
            return self.ui_scale

        scale_w = width / self.BASE_W
        scale_h = height / self.BASE_H
        raw_scale = min(scale_w, scale_h)

        # Aplicar lí­mites razonables para evitar elementos absurdamente pequeños o grandes
        self.ui_scale = max(self.MIN_SCALE, min(self.MAX_SCALE, raw_scale))
        return self.ui_scale

    def scale(self, value: float | int) -> int:
        """Escala un valor numérico de diseño según la escala UI actual."""
        return int(round(value * self.ui_scale))

    def font(self, family: str, size: float | int, weight: str = "") -> tuple:
        """Retorna una tupla de fuente de Tkinter con tamaño en puntos escalado.

        El uso de tamaños en puntos positivos escalados proporcionalmente por ui_scale
        garantiza que tanto las celdas (TEntry/TCombobox) como las etiquetas (TLabel)
        utilicen la misma fórmula de renderizado de Tkinter, manteniendo la relación de
        aspecto y proporción de texto 100% uniforme en cualquier monitor o DPI.
        """
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

            # Dimensiones escaladas de widgets
            entry_h = self.scale(UIConfig.ENTRY_HEIGHT)
            combobox_h = self.scale(UIConfig.COMBOBOX_HEIGHT)
            button_h = self.scale(UIConfig.BUTTON_HEIGHT)
            scrollbar_w = self.scale(UIConfig.SCROLLBAR_WIDTH)

            style.configure("TButton", padding=btn_padding, font=font_button)
            style.configure("TLabelframe.Label", font=self.font(UIConfig.FONT_PRIMARY, UIConfig.SIZE_SECTION_HEADER, "bold"))
            style.configure("TLabel", font=font_label)

            # Celdas de entrada: fuente, padding y altura controladas desde UIConfig
            style.configure("TEntry", padding=entry_padding, font=font_entry)
            style.map("TEntry", fieldbackground=[("readonly", "#f0f0f0")])

            # Desplegables (Combobox): fuente, padding y altura controladas desde UIConfig
            style.configure("TCombobox", padding=entry_padding, font=font_entry)

            # Barras de scroll: ancho controlado desde UIConfig
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
                    # Altura de Entry y Combobox ví­a option database
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

            # Aplicar configuración cromática completa del tema activo
            try:
                from core.ui_kit.theme import theme_mgr
                theme_mgr.apply_ttk_theme(style, root_app)
            except Exception:
                pass
        except Exception:
            pass


# Instancia global singleton del gestor de escalado
scaler = Scaler()


def ui(value: float | int) -> int:
    """Función global rápida para escalar valores de diseño en pí­xeles."""
    return scaler.scale(value)


def ui_font(family: str, size: float | int, weight: str = "") -> tuple:
    """Función global rápida para generar tuplas de fuentes escaladas."""
    return scaler.font(family, size, weight)


# Helpers temáticos centralizados usando UIConfig
def ui_font_title_main() -> tuple:
    """Retorna la fuente escalada para el tí­tulo principal."""
    return scaler.font(UIConfig.FONT_PRIMARY, UIConfig.SIZE_TITLE_MAIN, "bold")


def ui_font_subtitle() -> tuple:
    """Retorna la fuente escalada para el subtí­tulo principal."""
    return scaler.font(UIConfig.FONT_PRIMARY, UIConfig.SIZE_SUBTITLE)


def ui_font_card_title() -> tuple:
    """Retorna la fuente escalada para tí­tulos de tarjetas."""
    return scaler.font(UIConfig.FONT_PRIMARY, UIConfig.SIZE_CARD_TITLE, "bold")


def ui_font_section_header() -> tuple:
    """Retorna la fuente escalada para tí­tulos de sección (LabelFrame/Header)."""
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

