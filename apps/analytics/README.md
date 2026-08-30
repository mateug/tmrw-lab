# Apps / Analytics

Módulo de visualización y análisis de curvas I-V guardadas en Excel.

## Funcionalidades
- **Escaneo automático:** Busca recursivamente archivos Excel (`.xlsx`) en una carpeta seleccionada.
- **Normalización de unidades:** Convierte corrientes (A, mA, µA, nA) y voltajes (V, mV) a unidades homogéneas seleccionadas por el usuario.
- **Visualización interactiva:**
  - **Pestaña I-V:** Curvas comparativas de todas las medidas seleccionadas con tooltips de inspección al pasar el cursor.
  - **Pestaña Isc:** Evolución temporal de la corriente de cortocircuito (`Isc vs Tiempo`).
- **Exportación:**
  - Archivo Excel combinado (`iv_combinado.xlsx`) con pestaña de datos concatenados y resumen con parámetros fotovoltaicos calculados.
  - Exportación de figuras en formatos PNG/PDF.

## Estructura interna
- `engine.py`: Motor de lectura, análisis y combinación de DataFrames (sin dependencias de interfaz gráfica).
- `ui/panel.py`: Panel de interfaz gráfica en Tkinter integrado con el sistema de temas de `core.ui_kit`.
