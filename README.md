# TMRW Lab

Suite unificada de automatización, análisis y caracterización fotovoltaica de TMRW Silicon.

## Arquitectura del Proyecto

El repositorio sigue un desacoplamiento estricto entre el núcleo compartido (`core/`) y los modos operativos (`apps/`):

```
tmrw-lab/
├── main.py                  # Punto de entrada único (lanza el menú de bienvenida)
├── requirements.txt         # Dependencias unificadas del proyecto
│
├── core/                    # Capa compartida (ningún core importa de apps)
│   ├── config/              # Esquemas de configuración reutilizables
│   ├── exceptions.py        # Excepciones de dominio unificadas
│   ├── instrument/          # Drivers de hardware y registro central
│   │   ├── keithley.py      # Driver Keithley 2450 (con verificación *IDN?)
│   │   ├── ngu401.py        # Driver R&S NGU401 (con verificación *IDN?)
│   │   ├── solar_simulator.py # Driver Simulador Solar / LEDs multicanal Ossila
│   │   ├── relay_structure.py # Relé de cambio de estructura para Studio/Lite (stub)
│   │   ├── motors/
│   │   │   └── motor_lineal.py # Driver de motor lineal Arduino Serial
│   │   └── registry.py      # Registro thread-safe de instrumentos activos
│   ├── measure/             # Medidas atómicas por SMU
│   │   ├── run_keithley.py  # Medida I-V atómica Keithley 2450
│   │   └── run_ngu401.py    # Medida I-V atómica R&S NGU401
│   ├── plot/                # Generación y guardado seguro de figuras
│   ├── postprocess/         # Análisis fotovoltaico y exportación a Excel
│   ├── ui_kit/              # Sistema de temas, escalado DPI y widgets comunes
│   └── utils.py             # Utilidades comunes y gestión de logs
│
├── apps/                    # Modos de aplicación (totalmente independientes entre sí)
│   ├── __init__.py          # Registro explícito de modos (APP_REGISTRY)
│   ├── studio/              # Modo Studio: medidas I-V multidimensionales con Keithley 2450
│   ├── lite/                # Modo Lite: carga de recetas desde Excel con vista previa
│   ├── analytics/           # Modo Analytics: visualización y análisis de Excels I-V
│   └── stress/              # Modo Stress: ensayo de degradación comparativa A/B con NGU401
│
└── tests/                   # Tests unitarios e integración
    ├── apps/
    └── core/
```

## Reglas de Arquitectura

1. **Aislamiento de Modos:** Ningún modo de `apps/` importa de otro modo de `apps/`.
2. **Importación exclusiva de `core/`:** Todos los modos importan exclusivamente de `core/` y de sus propios submódulos.
3. **Punto de Extensión:** Para añadir un nuevo modo, se crea una carpeta en `apps/<nombre>/` con su `MANIFEST` y se registra en `apps/__init__.py`.
4. **Relés Separados:** `apps/stress/relay_degradation.py` y `core/instrument/relay_structure.py` son independientes.

## Instalación y Ejecución

```bash
# Instalar dependencias
pip install -r requirements.txt

# Ejecutar TMRW Lab
python main.py
```
