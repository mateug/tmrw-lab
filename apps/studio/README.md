# Apps / Studio

Modo de medida I-V multidimensional con Keithley 2450.

## Funcionalidades
- **Medida I-V:** Barridos completos, directos e inversos con control de NPLC, límites de corriente (I_max) y potencia (20 W).
- **Ejes combinables e independientes:**
  - **Eje Estructura:** Selección de estructura mediante relé físico (`core/instrument/relay_structure.py`).
  - **Eje Motor:** Posicionamiento espacial y barrido lineal con Arduino Serial (`core/instrument/motors/motor_lineal.py`).
  - **Eje Iluminación:** Simulador solar / LEDs multicanal Ossila (`core/instrument/solar_simulator.py`).
- **Motor de combinatoria (`plan_engine.py`):**
  - Si ningún eje está activo: ejecuta una medida estática única.
  - Si múltiples ejes están activos: los combina por emparejamiento directo (`1-1`) o producto cartesiano (`1-N`).
  - Excluye el submodo de lectura desde Excel (función exclusiva de Lite).
- **Consola y Gráficas en tiempo real:** Registro visual y generación de miniaturas al vuelo.

## Estructura interna
- `plan_engine.py`: Generador y validador de planes y recetas de ejes.
- `config.py`: Esquema de configuración de Studio.
- `ui/`:
  - `frame.py`: Marco principal de Studio y orquestador multihilo.
  - `panel_medida.py`: Panel de configuración de Keithley 2450 y barrido I-V.
  - `panel_motor.py`: Panel de eje de motor lineal y herramientas de jogging.
  - `panel_led.py`: Panel de eje de simulador solar y submodos manuales.
  - `panel_estructura.py`: Panel de selección de estructura.
