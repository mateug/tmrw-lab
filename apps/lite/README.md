# Apps / Lite

Modo simplificado de ejecución de secuencias de medida definidas en Excel.

## Funcionalidades
- **Carga de Receta Excel:** Selección de archivo `.xlsx` con combinaciones de ejes.
- **Detección y clasificación automática de columnas:**
  - **Eje Estructura:** Columnas tipo `Estructura`, `Device`, `Dispositivo`.
  - **Eje Motor:** Columnas de posición tipo `Motor`, `Posición`, `Pasos`, `Steps`.
  - **Eje Iluminación:** Canales LED individuales (`390`, `450`, `660`, `950`, `Cool White`, `Warm White`) o potencia.
- **Resumen y vista previa interactiva:**
  - Muestra el número total de combinaciones detectadas.
  - Informa de los ejes reconocidos.
  - Tabla de previsualización antes de iniciar la medida (el botón de inicio se activa solo tras una lectura válida).
- **Ejecución desatendida:** Orquesta la secuencia completa con el Keithley 2450.

## Estructura interna
- `config.py`: Esquema de configuración de Lite.
- `ui/panel.py`: Panel de interfaz gráfica con análisis de Excel, resumen previo y ejecutor multihilo.
