# Plan de Implementación: Mejoras y Enriquecimiento de TMRW Lab

Este plan aborda todas las mejoras solicitadas para alcanzar la máxima fidelidad funcional y estética respecto a `iv-maker` y `devices-degradation`:

---

## 1. Sistema de Escalado y Fuentes (`core/ui_kit/scaler.py`)
- **Alinear `UIConfig` con `iv-maker`:**
  - Ajustar `FONT_PRIMARY` ("Segoe UI"), `FONT_CONSOLE` ("Consolas").
  - Calibrar tamaños base de fuentes (`SIZE_TITLE_MAIN`, `SIZE_SUBTITLE`, `SIZE_CARD_TITLE`, `SIZE_SECTION_HEADER`, `SIZE_LABEL`, `SIZE_ENTRY`, `SIZE_BUTTON`, `SIZE_CONSOLE`, `SIZE_INFO_ITALIC`).
  - Calibrar dimensiones de widgets (`ENTRY_HEIGHT`, `COMBOBOX_HEIGHT`, `BUTTON_HEIGHT`, `SCROLLBAR_WIDTH`, `CONSOLE_HEIGHT`).
  - Calibrar márgenes y paddings (`PADDING_MAIN_CONTAINER`, `PADDING_CARD`, `PADDING_SECTION`, `PADDING_BUTTON_*`, `PADDING_ENTRY_*`, `TREEVIEW_ROW_HEIGHT`).

---

## 2. Menú Principal (`core/ui_kit/menu.py`)
- **Textos de tarjetas más grandes y legibles:**
  - Incrementar tamaño del número de modo (`Modo 1`, `Modo 2`, etc.) a negrita visible.
  - Aumentar el tamaño del título de tarjeta (`ui_font_card_title()`) y descripción (`ui_font_label()`).
  - Ajustar padding interno y `wraplength` de las tarjetas para que no queden textos apretados.
  - Subtítulo actualizado a *"Automatización de medidas de laboratorio"*.

---

## 3. Modo Studio (`apps/studio/`)

### A. Reorganización del Layout
- **Eliminar el scroll innecesario de la primera columna:** Todo el panel izquierdo se estructura en contenedores limpios que caben de forma natural o utilizan scroll únicamente donde sea estrictamente necesario.
- **Secciones fijas a la izquierda (sin ser pestaña):**
  1. `[1] Guardado de Datos` (situado **encima** de Keithley): Carpeta base, subcarpeta de medida, prefijo de archivo, checkbox de guardar archivos.
  2. `[2] Keithley 2450 — Barrido I-V`: Recurso VISA, modo de medida (completa, directa, inversa), $V_{ini}/V_{fin}/paso$ directa e inversa, $I_{max}$ (µA), superficie (µm²), irradiancia ($mW/cm^2$), inversión eje Y, medición 4 hilos (Sense).
  3. `[3] Relación entre Ejes Activos`:
     - Selector con botones radiales: `Producto cartesiano (1-N)` vs `Emparejamiento directo (1-1)`.
     - **Texto explicativo y ejemplo didáctico:**
       > *• Producto cartesiano (1-N):* Se miden todas las combinaciones posibles de los ejes activos (ej. 3 posiciones de motor × 4 longitudes de onda = 12 medidas).
       > *• Emparejamiento directo (1-1):* Se empareja el paso $i$ de un eje con el paso $i$ del otro (ej. posición 1 con LED 1, posición 2 con LED 2 = 3 medidas).

### B. Notebook de Ejes Activos (Debajo de los paneles fijos)
- **Pestaña `Ejes Motor` (con sub-pestañas):**
  - Toggle de activación general del eje motor.
  - Sub-pestaña `Motor Lineal 1 (Eje X)` (preparado para agregar más motores):
    - Parámetros: Puerto COM, Baudrate, Step (pasos), Stop (pasos), Resolución (mm/paso), Espera de estabilización mecánica (s), Poner a cero al conectar, Volver a cero al finalizar.
    - **Simulador solar integrado durante el barrido motor:** Opción de luz apagada, potencia fija ($mW/cm^2$) o longitud de onda/canal fijo con tiempo de estabilización de luz ($s$).
    - **Controles de Centrado Manual:** Entrada de pasos exactos con botón *"Mover pasos"*, botones de movimiento continuo pulsado (`-Mover Continuo` / `+Mover Continuo` con eventos `ButtonPress` / `ButtonRelease`), y botón *"Fijar Cero Actual"*.
- **Pestaña `Eje Iluminación` (Simulador Solar / LEDs):**
  - Toggle de activación general del eje iluminación.
  - Parámetros de conexión: Puerto COM, Baudrate.
  - **Submodo A: Potencia Absoluta ($mW/cm^2$):** $P_{ini}$, $P_{fin}$, paso, lista personalizada, espera de estabilización ($s$), tiempo con luz encendida antes de medir ($s$), tiempo de enfriamiento/apagado entre pasos ($s$), apagar al final.
  - **Submodo B: Longitud de Onda Individual:** Selector de los 11 canales Ossila con casillas (`390`, `450`, `515`, `Cool White`, `Warm White`, `600`, `630`, `660`, `730`, `850`, `950`), $I_{ini}$ (%), $I_{fin}$ (%), paso (%), lista personalizada, espera de estabilización ($s$), espera encendido ($s$), apagar al final.
  - **Submodo C: Combinación Multicanal:** Matriz dinámica con botones *"Añadir Canal"* y *"Eliminar Canal"*, selector de canal, entrada de intensidades separadas por comas, selector de relación (`1-1` o `1-N`) entre canales sucesivos, esperas de encendido y estabilización.
  - **Submodo D: Múltiples Recetas Encadenadas:** Lista de recetas multicanal configurables.
- **Pestaña `Eje Estructura`:**
  - Toggle de activación del eje de estructura.
  - Lista de estructuras a barrer separadas por comas con conmutación física.

### C. Botonera y Consola de Studio
- Botones: `▶ INICIAR SECUENCIA`, `⚡ MEDIDA RÁPIDA` (barrido puntual de diagnóstico sin mover motor ni guardar), `⏹ ABORTAR MEDIDA`, `⚙ Liberar Keithley (Modo Manual)`.
- Consola de log con badge de estado (`[✓ LISTO]`, `[⚡ MIDIENDO]`, `[⏹ ABORTADO]`) y previsualización gráfica.

---

## 4. Modo Lite (`apps/lite/`)
- **Incorporar todos los parámetros del Submodo E de `iv-maker`:**
  - Selector de archivo Excel (`.xlsx`).
  - Selector de nombre de hoja del Excel (`hoja_excel`).
  - Selector de formato numérico: ¿Valores en tanto por uno ($0.0 - 1.0$) o porcentaje ($0 - 100\%$)?
  - Plantilla de comando SCPI/LED (`<ch{channel}:{intensity}>`).
  - Tiempo de estabilización tras encendido/cambio ($s$).
  - Tiempo con luz encendida previo a la medición ($s$).
  - Tiempo de estabilización de motor ($s$).
  - Tiempo de enfriamiento entre medidas sucesivas ($s$).
  - Checkbox para apagar LEDs al finalizar.
  - Panel de resumen previo: Número de combinaciones, ejes detectados y tabla interactiva de vista previa (Treeview).

---

## 5. Modo Stress (`apps/stress/`)
- **Corrección de símbolos y codificación UTF-8:**
  - Revisar y corregir todos los caracteres Unicode corrompidos (mojibake) en `panel.py`, `relay_degradation.py`, `scheduler.py`, `sequence.py`.
  - Asegurar que los botones muestren los iconos exactos:
    - `▶ INICIAR SECUENCIA`
    - `⚡ MEDIDA RÁPIDA`
    - `⚙ Modo manual / automático`
    - `🔌 TESTEAR RELÉS Y ESTRUCTURAS`
    - `⏹ DETENER / ABORTAR`
    - `✓`, `❌`, `µA`, `°C`

---

## Plan de Verificación

### Pruebas de Interfaz y Estilos
1. Ejecutar el menú principal y comprobar visualmente que las fuentes, dimensiones y tarjetas tienen el tamaño adecuado y no están miniaturizadas.
2. Comprobar que en Studio el panel de guardado está encima del de Keithley, la explicación de 1-1 / 1-N es clara y el panel de ejes motor/iluminación tiene todas las opciones de `iv-maker`.
3. Comprobar que Lite contiene todos los parámetros de tiempo, hoja y formato del Submodo E de `iv-maker`.
4. Comprobar que en Stress todos los botones e iconos (`▶`, `⚡`, `⚙`, `🔌`, `⏹`, `µA`) se leen nítidamente sin caracteres corruptos.
5. Ejecutar la suite de tests de importación e instanciación de los 4 modos en headless.
