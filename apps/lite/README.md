# Apps / Lite

Modo simplificado de ejecución de secuencias de medida definidas en Excel.

## Formato Excel

La primera fila contiene los encabezados y cada fila posterior es una combinación de motores y LEDs. Los encabezados canónicos de motores son:

- `motor_lineal_step`, `motor_lineal_stop`
- `motor_inclinacion_step`, `motor_inclinacion_stop`
- `motor_rotacion_step`, `motor_rotacion_stop`

Los LEDs se escriben con etiquetas humanas, por ejemplo `390 nm`, `650 nm`, `Warm white` o `Cool white`. Se aceptan intensidades en tanto por uno (`0` a `1`) o en porcentaje (`0` a `100`), según la opción seleccionada en la interfaz.

La columna única `Estructura` contiene IDs separados por comas, por ejemplo `1,2,3,6,7`. Cada ID produce una medida independiente para esa fila. El ID `0`, las celdas vacías y las intensidades cero no activan ese eje. Los IDs válidos son del `1` al `7`.

Si no existe la columna `Estructura`, la receta representa una única medida sin estructura física. Lite muestra una configuración Keithley genérica denominada `Medida única` y no conecta el Arduino del relé.

Una pareja de motor con ambos valores vacíos o cero desactiva ese motor. Una pareja parcialmente informada es inválida. No se crea un producto cartesiano: solo se expanden las estructuras de cada fila y se conserva el orden del Excel.

Los tiempos de motor, iluminación, conmutación y enfriamiento aparecen en la receta únicamente cuando el eje correspondiente está activo en alguna fila.

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
