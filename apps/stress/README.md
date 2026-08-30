# Apps / Stress

Modo de ensayo y medida de degradación comparativa I-V de dos estructuras (A / B).

## Funcionalidades
- **Instrumento SMU:** R&S NGU401 (`core/instrument/ngu401.py` y `core/measure/run_ngu401.py`).
- **Conmutación física A/B:** Control de relé con Arduino Serial específico de degradación (`apps/stress/relay_degradation.py`).
- **Orquestación y programación temporal (`scheduler.py`, `sequence.py`):**
  - **Modo por tiempo:** Tramos temporales con intervalos progresivos.
  - **Modo por pendiente de Voc:** Adaptación dinámica del intervalo de muestreo en función de la derivada de Voc de ambas estructuras.
- **Comprobación de hardware (`hardware_test.py`):** Detección previa de contacto eléctrico y confirmación de conmutación de relés.
- **Salida de datos:** Generación automática de Excels individuales por ciclo, figuras comparativas IV y resumen conjunto (`*_resumen_comparativo.xlsx`).

## Estructura interna
- `relay_degradation.py`: Driver de conmutación de relés A/B (independiente de `core/instrument/relay_structure.py`).
- `scheduler.py`: Lógica de cálculo de intervalos fijos y por derivada de Voc.
- `sequence.py`: Orquestador temporal de ciclos de degradación.
- `plan_engine.py`: Planificación de barridos para NGU401.
- `hardware_test.py`: Rutina de verificación de relés y detección de dispositivo.
- `config.py`: Esquema de configuración de Stress.
- `ui/panel.py`: Panel gráfico `StressFrame` con controles de ciclo, log y gráficas.
