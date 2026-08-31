"""Panel de control e interfaz gráfica para el Modo Stress (degradación A/B)."""
from __future__ import annotations

from collections.abc import Callable
import queue
import threading
import time
import tkinter as tk
from tkinter import ttk
from typing import Any

from core.exceptions import MedidaAbortadaPorUsuario
from core.instrument.ngu401 import NGU401
from core.instrument import registry
from core.plot.plotter import generar_imagen_tk_curvas_iv_pv
from core.ui_kit.scaler import UIConfig, scaler, ui, ui_font_console
from core.ui_kit.shared import (
    crear_barra_superior,
    crear_campo_directorio,
    crear_seccion_frame as section,
    mostrar_error,
    mostrar_info,
)
from core.ui_kit.theme import theme_mgr

from apps.stress.config import get_default_config
from apps.stress.hardware_test import probar_reles_y_dispositivos
from apps.stress.sequence import run_comparison_cycle, run_degradation_sequence


Config = dict[str, Any]
Message = tuple[str, Any]
LogCallback = Callable[[str], None]


class StressFrame(ttk.Frame):
    """Panel principal de degradación comparativa A/B."""

    def __init__(self, master: tk.Misc, callback_volver=None, **kwargs) -> None:
        super().__init__(master, **kwargs)
        self.callback_volver = callback_volver
        self.cfg: Config = get_default_config()
        self.q: queue.Queue[Message] = queue.Queue()
        self.time_rules: list[tuple[tk.StringVar, tk.StringVar]] = []
        self.slope_rules: list[tuple[tk.StringVar, tk.StringVar]] = []
        self.modo_automatico = True
        self._operacion_activa = False
        self._boton_modo: ttk.Button | None = None
        self._imagenes_log: list[Any] = []
        self._poll_job: str | None = None
        self.v: dict[str, tk.StringVar] = {}
        self.dev: dict[str, dict[str, tk.StringVar]] = {}

        self._vars()
        self._create_ui()
        self._poll_job = self.after(100, self.poll)

    def destroy(self) -> None:
        if self._poll_job is not None:
            try:
                self.after_cancel(self._poll_job)
            except tk.TclError:
                pass
            self._poll_job = None
        super().destroy()

    @property
    def operacion_activa(self) -> bool:
        """Indica si existe una operación de hardware en curso."""
        return self._operacion_activa

    def apply_responsive_scaling(self) -> None:
        """Actualiza los widgets que no dependen del reflow completo de la vista."""
        try:
            if hasattr(self, "log") and self.log.winfo_exists():
                self.log.configure(
                    font=ui_font_console(),
                    height=max(6, scaler.scale(UIConfig.CONSOLE_HEIGHT)),
                )
        except tk.TclError:
            pass

    def _vars(self) -> None:
        cfg = self.cfg

        def create_variable(value: Any) -> tk.StringVar:
            return tk.StringVar(value=str(value if value is not None else ""))

        self.v = {
            "folder": create_variable(cfg.get("carpeta_salida", "")),
            "exp": create_variable(cfg.get("nombre_experimento", "test_mateu")),
            "visa": create_variable(cfg.get("smu", {}).get("recurso_visa", "AUTO")),
            "port": create_variable(cfg.get("rele", {}).get("puerto_serie", "COM3")),
            "mode": create_variable(cfg.get("modo_medida", "completa")),
            "invertir_eje_y": create_variable(cfg.get("invertir_eje_y_graficas", True)),
            "medir_tension_real": create_variable(cfg.get("medir_tension_real", False)),
        }
        self.dev = {}
        for device in ("A", "B"):
            curve = cfg.get("curva_iv", {}).get(device, {})
            self.dev[device] = {
                key: create_variable(value) for key, value in curve.items()
            }
            self.dev[device]["nombre"] = create_variable(
                cfg.get("dispositivos", {}).get(device, {}).get("nombre", f"Estructura {device}")
            )

    def field(
        self,
        parent: tk.Misc,
        label: str,
        variable: tk.StringVar,
        row: int,
        column: int,
    ) -> None:
        ttk.Label(parent, text=label).grid(
            row=row,
            column=column,
            sticky="w",
            pady=ui(UIConfig.PADDING_GRID_VERTICAL),
        )
        ttk.Entry(parent, textvariable=variable, width=10).grid(
            row=row,
            column=column + 1,
            sticky="w",
            padx=(ui(UIConfig.PADDING_ENTRY_HORIZONTAL), ui(UIConfig.PADDING_NOTE_BOTTOM)),
            pady=ui(UIConfig.PADDING_GRID_VERTICAL),
        )

    def _create_ui(self) -> None:
        crear_barra_superior(
            self,
            "Modo 4: Stress — Degradación Comparativa A/B",
            self.callback_volver,
        )

        parent = ttk.Frame(self)
        parent.pack(fill="both", expand=True, padx=ui(6), pady=ui(4))

        parent.columnconfigure(0, weight=3)
        parent.columnconfigure(1, weight=2)
        parent.rowconfigure(0, weight=1)

        left = ttk.Frame(parent)
        left.grid(row=0, column=0, sticky="nsew", padx=(0, ui(UIConfig.PADDING_GRID_HORIZONTAL)))
        right = ttk.Frame(parent)
        right.grid(row=0, column=1, sticky="nsew", padx=(ui(UIConfig.PADDING_GRID_HORIZONTAL), 0))

        # [1] Guardado de Datos
        self.save = section(
            left,
            "[1] Configuración de guardado de medidas",
            "keithley",
        )
        crear_campo_directorio(self.save, self.v["folder"], 0, "Carpeta de salida:")
        ttk.Label(self.save, text="Nombre de carpeta:").grid(
            row=1,
            column=0,
            sticky="w",
            padx=ui(UIConfig.PADDING_FIELD_HORIZONTAL),
        )
        ttk.Entry(self.save, textvariable=self.v["exp"]).grid(
            row=1,
            column=1,
            columnspan=2,
            sticky="ew",
            padx=ui(UIConfig.PADDING_FIELD_HORIZONTAL),
        )

        # [2] y [3] Paneles A y B
        self._device_panel(
            left,
            "A",
            "[2] Curva IV — Estructura A (entradas NC de los relés)",
        )
        self._device_panel(
            left,
            "B",
            "[3] Curva IV — Estructura B (entradas NO de los relés)",
        )

        # [4] Intervalos
        self._intervals_panel(left)

        # [5] Control
        self._control_panel(left)

        # [6] Terminal y visualización
        self._terminal_panel(right)

    def _device_panel(self, parent: tk.Misc, device: str, title: str) -> None:
        panel = section(parent, title, "params")
        variables = self.dev[device]
        ttk.Label(panel, text="Nombre:").grid(
            row=0,
            column=0,
            sticky="w",
        )
        ttk.Entry(
            panel,
            textvariable=variables["nombre"],
            width=26,
        ).grid(row=0, column=1, sticky="w", padx=ui(UIConfig.PADDING_GRID_HORIZONTAL))
        ttk.Label(panel, text="Modo:").grid(
            row=0,
            column=2,
            sticky="w",
        )
        ttk.Combobox(
            panel,
            textvariable=self.v["mode"],
            values=["completa", "directa", "inversa"],
            state="readonly",
            width=10,
        ).grid(row=0, column=3, sticky="w")
        self.field(panel, "V ini directa (mV):", variables["v_ini_dir_mV"], 1, 0)
        self.field(panel, "V final directa (mV):", variables["v_fin_dir_mV"], 1, 2)
        self.field(panel, "Paso directa (mV):", variables["paso_dir_mV"], 1, 4)
        self.field(panel, "V ini inversa (mV):", variables["v_ini_inv_mV"], 2, 0)
        self.field(panel, "V final inversa (V):", variables["v_fin_inv_V"], 2, 2)
        self.field(panel, "Paso inversa (mV):", variables["paso_inv_mV"], 2, 4)
        self.field(panel, "I máxima (µA):", variables["i_max_uA"], 3, 0)

        f_opts = ttk.Frame(panel, style="Params.TLabel")
        f_opts.grid(row=4, column=0, columnspan=5, sticky="ew", pady=ui(2))
        f_opts.columnconfigure(0, weight=1)
        f_opts.columnconfigure(1, weight=1)
        ttk.Checkbutton(f_opts, text="Invertir eje Y", variable=self.v["invertir_eje_y"], style="Keithley.TCheckbutton").pack(side="left", padx=ui(4))
        ttk.Checkbutton(f_opts, text="Medir tensión real", variable=self.v["medir_tension_real"], style="Keithley.TCheckbutton").pack(side="left", padx=ui(4))

    def _intervals_panel(self, parent: tk.Misc) -> None:
        panel = section(parent, "[4] Selección de intervalos temporales", "params")
        programming = self.cfg.get("programacion", {})
        self.time_rules = [
            (
                tk.StringVar(value=str(rule["intervalo_s"])),
                tk.StringVar(value=str(rule["hasta_min"])),
            )
            for rule in programming.get("tramos_tiempo", [])
        ]
        self.slope_rules = [
            (
                tk.StringVar(value=str(rule["umbral_V_por_min"])),
                tk.StringVar(value=str(rule["intervalo_s"])),
            )
            for rule in programming.get("tramos_pendiente_voc", [])
        ]
        self.tabs = ttk.Notebook(panel)
        self.tabs.pack(fill="x", expand=True, pady=ui(UIConfig.PADDING_TAB_CONTAINER_VERTICAL))
        time_tab = ttk.Frame(
            self.tabs,
            padding=ui(UIConfig.PADDING_TAB),
            style="Params.TFrame",
        )
        stabilization_tab = ttk.Frame(
            self.tabs,
            padding=ui(UIConfig.PADDING_TAB),
            style="Params.TFrame",
        )
        self.tabs.add(time_tab, text="Intervalos por tiempo")
        self.tabs.add(stabilization_tab, text="Intervalos por estabilización (dVoc/dt)")
        ttk.Label(
            time_tab,
            text=(
                "• Modo por tiempo: El intervalo se aplica hasta alcanzar cada límite temporal.\n"
                "  El último límite marca el tiempo final del experimento; cuando termine la medida "
                "que esté en curso después de superarlo, la secuencia se detiene."
            ),
            style="Params.TLabel",
            wraplength=ui(UIConfig.WRAPLENGTH_SECTION),
        ).grid(
            row=0, column=0, columnspan=3, sticky="w", pady=(0, ui(UIConfig.PADDING_NOTE_BOTTOM))
        )

        # Frame común para cabeceras + filas
        time_table = ttk.Frame(time_tab, style="Params.TFrame")
        time_table.grid(row=1, column=0, columnspan=3, sticky="ew")

        # Cabeceras
        ttk.Label(time_table, text="Intervalo (s)", style="Params.TLabel").grid(
            row=0, column=0, sticky="w",
        )
        ttk.Label(time_table, text="Límite máximo (min)", style="Params.TLabel").grid(
            row=0, column=1, sticky="w",
        )

        # Frame SOLO para las filas dinámicas
        self.time_rows = ttk.Frame(time_table, style="Params.TFrame")
        self.time_rows.grid(row=1, column=0, columnspan=3, sticky="ew")

        self._render_rule_rows(self.time_rows, self.time_rules, "Intervalo", "Límite")

        ttk.Button(
            time_tab,
            text="+ Añadir tramo",
            command=lambda: self._add_rule(self.time_rules, self.time_rows, "Intervalo", "Límite"),
            style="Tool.TButton",
        ).grid(
            row=2,
            column=0,
            columnspan=2,
            sticky="w",
            pady=ui(UIConfig.PADDING_GRID_HORIZONTAL),
        )

        ttk.Label(
            stabilization_tab,
            text=(
                "• Modo por pendiente de Voc: el intervalo se selecciona según la velocidad de cambio de Voc.\n"
                "  El cambio se aplica cuando ambas estructuras alcanzan el umbral."
            ),
            style="Params.TLabel",
            wraplength=ui(UIConfig.WRAPLENGTH_SECTION),
        ).grid(row=0, column=0, columnspan=3, sticky="w", pady=(0, ui(UIConfig.PADDING_NOTE_BOTTOM)))

        # Frame común para cabeceras + filas
        stabilization_table = ttk.Frame(stabilization_tab, style="Params.TFrame")
        stabilization_table.grid(row=1, column=0, columnspan=3, sticky="ew")

        ttk.Label(stabilization_table, text="Umbral |dVoc/dt| (V/min)").grid(
            row=1, column=0, sticky="w"
        )
        ttk.Label(stabilization_table, text="Intervalo (s)").grid(
            row=1, column=1, sticky="w"
        )
        self.slope_rows = ttk.Frame(stabilization_table,  style="Params.TLabel")
        self.slope_rows.grid(row=2, column=0, columnspan=3, sticky="ew")
        self._render_rule_rows(
            self.slope_rows,
            self.slope_rules,
            "Umbral",
            "Intervalo",
        )
        ttk.Button(
            stabilization_tab,
            text="+ Añadir umbral",
            command=lambda: self._add_rule(
                self.slope_rules,
                self.slope_rows,
                "Umbral",
                "Intervalo",
            ),
            style="Tool.TButton",
        ).grid(row=3, column=0, columnspan=2, sticky="w", pady=ui(UIConfig.PADDING_GRID_HORIZONTAL))
        ttk.Label(
            stabilization_tab,
            text="La pendiente se calcula en V/min sobre las últimas muestras válidas.",
            style="Params.TLabel",
            wraplength=ui(UIConfig.WRAPLENGTH_SECTION),
        ).grid(row=4, column=0, columnspan=3, sticky="w", pady=(ui(UIConfig.PADDING_GRID_HORIZONTAL), 0))

    def _render_rule_rows(
        self,
        parent: tk.Misc,
        rules: list[tuple[tk.StringVar, tk.StringVar]],
        first_label: str,
        second_label: str,
    ) -> None:
        for child in parent.winfo_children():
            child.destroy()
        for row, (first, second) in enumerate(rules):
            ttk.Entry(parent, textvariable=first, width=14).grid(
                row=row, column=0, sticky="w", padx=(0, ui(UIConfig.PADDING_GRID_HORIZONTAL)), pady=ui(UIConfig.PADDING_GRID_VERTICAL)
            )
            ttk.Entry(parent, textvariable=second, width=14).grid(
                row=row, column=1, sticky="w", padx=(0, ui(UIConfig.PADDING_GRID_HORIZONTAL)), pady=ui(UIConfig.PADDING_GRID_VERTICAL)
            )
            if len(rules) > 1:
                ttk.Button(
                    parent,
                    text="✕",
                    width=3,
                    command=lambda index=row: self._remove_rule(
                        rules, parent, index, first_label, second_label
                    ),
                    style="Tool.TButton",
                ).grid(row=row, column=2, sticky="w", pady=ui(UIConfig.PADDING_GRID_VERTICAL))

    def _add_rule(
        self,
        rules: list[tuple[tk.StringVar, tk.StringVar]],
        parent: ttk.Frame,
        first_label: str,
        second_label: str,
    ) -> None:
        rules.append((tk.StringVar(value=""), tk.StringVar(value="")))
        if parent is not None:
            self._render_rule_rows(parent, rules, first_label, second_label)

    def _remove_rule(
        self,
        rules: list[tuple[tk.StringVar, tk.StringVar]],
        parent: tk.Misc,
        index: int,
        first_label: str,
        second_label: str,
    ) -> None:
        if len(rules) <= 1:
            return
        rules.pop(index)
        self._render_rule_rows(parent, rules, first_label, second_label)

    def _control_panel(self, parent: tk.Misc) -> None:
        panel = section(parent, "[5] Control de medida", "control")
        ttk.Label(panel, text="Arduino (COM):").grid(
            row=0,
            column=0,
            sticky="w",
        )
        ttk.Entry(
            panel,
            textvariable=self.v["port"],
            width=12,
        ).grid(row=0, column=1, sticky="w", padx=ui(UIConfig.PADDING_GRID_HORIZONTAL))
        ttk.Label(panel, text="NGU401 (VISA):").grid(
            row=0,
            column=2,
            sticky="w",
        )
        ttk.Entry(
            panel,
            textvariable=self.v["visa"],
            width=28,
        ).grid(row=0, column=3, sticky="w", padx=ui(UIConfig.PADDING_GRID_HORIZONTAL))
        self.startb = ttk.Button(
            panel,
            text="▶ INICIAR SECUENCIA",
            style="Primary.TButton",
            command=self.start_measurement,
        )
        self.startb.grid(row=1, column=0, pady=ui(UIConfig.PADDING_CONTROL_VERTICAL), sticky="w")
        self.btn_abortar = ttk.Button(
            panel,
            text="⏹ DETENER / ABORTAR",
            style="Danger.TButton",
            command=self.abort,
            state="disabled",
        )
        self.btn_abortar.grid(row=1, column=1, pady=ui(UIConfig.PADDING_CONTROL_VERTICAL), padx=ui(UIConfig.PADDING_GRID_HORIZONTAL))
        self.btn_rapida = ttk.Button(
            panel,
            text="⚡ MEDIDA RÁPIDA",
            style="Quick.TButton",
            command=self.quick_measurement,
        )
        self.btn_rapida.grid(row=1, column=2, pady=ui(UIConfig.PADDING_CONTROL_VERTICAL), padx=ui(UIConfig.PADDING_GRID_HORIZONTAL))
        self._boton_modo = ttk.Button(
            panel,
            text="⚙ Modo manual / automático",
            style="Tool.TButton",
            command=self.toggle_manual,
        )
        self._boton_modo.grid(row=1, column=3, pady=ui(UIConfig.PADDING_CONTROL_VERTICAL), padx=ui(UIConfig.PADDING_GRID_HORIZONTAL))
        self.testb = ttk.Button(
            panel,
            text="🔌 TESTEAR RELÉS Y ESTRUCTURAS",
            style="Tool.TButton",
            command=self.test,
        )
        self.testb.grid(row=1, column=4, pady=ui(UIConfig.PADDING_CONTROL_VERTICAL), padx=ui(UIConfig.PADDING_GRID_HORIZONTAL))

    def _terminal_panel(self, parent: tk.Misc) -> None:
        parent.columnconfigure(0, weight=1)
        parent.rowconfigure(0, weight=1)
        panel = ttk.LabelFrame(
            parent,
            text=" [6] Terminal de salida y curvas ",
            padding=ui(UIConfig.PADDING_SECTION),
            style="Results.TLabelframe",
        )
        panel.grid(
            row=0,
            column=0,
            sticky="nsew",
            padx=ui(UIConfig.PADDING_SECTION_OUTER_HORIZONTAL),
            pady=ui(UIConfig.PADDING_SECTION_OUTER_VERTICAL),
        )
        theme = theme_mgr.get_current_theme()
        self.log = tk.Text(
            panel,
            height=max(6, scaler.scale(UIConfig.CONSOLE_HEIGHT)),
            bg=theme["results"]["bg_console"],
            fg=theme["results"]["fg_console"],
            insertbackground=theme["results"]["fg_console"],
            font=ui_font_console(),
            wrap="word",
            state="disabled",
        )
        self.log.pack(fill="both", expand=True)
        self.log_msg(
            "Modo Stress preparado. Configura los parámetros y, si procede, "
            "ejecuta el test de relés."
        )

    def log_msg(self, message: str) -> None:
        self.q.put(("log", str(message)))

    def _mostrar_grafica(self, datos: Any, cfg: Config) -> None:
        try:
            imagen = generar_imagen_tk_curvas_iv_pv(datos, cfg)
            if imagen is None:
                return
            self._imagenes_log.append(imagen)
            self.log.configure(state="normal")
            self.log.insert("end", "\n")
            self.log.image_create("end", image=imagen)
            self.log.insert("end", "\n")
            self.log.see("end")
            self.log.configure(state="disabled")
        except Exception as error:
            self.log_msg(f"Aviso: no se pudo mostrar la curva en la terminal: {error}")

    def recoger_configuracion(self) -> None:
        cfg = self.cfg
        programming = cfg.setdefault("programacion", {})
        cfg["carpeta_salida"] = self.v["folder"].get().strip()
        cfg["nombre_experimento"] = self.v["exp"].get().strip()
        cfg["smu"]["recurso_visa"] = self.v["visa"].get().strip() or "AUTO"
        cfg["rele"]["puerto_serie"] = self.v["port"].get().strip()
        cfg["modo_medida"] = self.v["mode"].get().strip()
        programming["modo"] = (
            "por_tiempo" if self.tabs.index("current") == 0 else "por_pendiente_voc"
        )
        tramos_tiempo = []
        for first, second in self.time_rules:
            if first.get().strip() and second.get().strip():
                tramos_tiempo.append({
                    "intervalo_s": float(first.get()),
                    "hasta_min": float(second.get())
                })
        programming["tramos_tiempo"] = tramos_tiempo

        tramos_pendiente = []
        for first, second in self.slope_rules:
            if first.get().strip() and second.get().strip():
                tramos_pendiente.append({
                    "umbral_V_por_min": float(first.get()),
                    "intervalo_s": float(second.get())
                })
        programming["tramos_pendiente_voc"] = tramos_pendiente

        for device in ("A", "B"):
            cfg["dispositivos"][device]["nombre"] = self.dev[device]["nombre"].get().strip()
            for key, variable in self.dev[device].items():
                if key != "nombre":
                    cfg["curva_iv"][device][key] = variable.get().strip()

    def start_measurement(self) -> None:
        self._launch_cycle(guardar_archivos=True)

    def quick_measurement(self) -> None:
        self._launch_cycle(guardar_archivos=False)

    def _launch_cycle(self, guardar_archivos: bool) -> None:
        if not self.modo_automatico or self._operacion_activa:
            self.log_msg("Activa el modo automático y espera a que termine la operación actual.")
            return
        self.recoger_configuracion()
        # El tiempo del experimento empieza exactamente al pulsar Iniciar.
        self.cfg["t0_experimento"] = time.perf_counter()
        self.cfg["evento_aborto"] = threading.Event()
        self.cfg["log_callback"] = self.log_msg
        self.cfg["grafica_callback"] = lambda datos, cfg: self.q.put(("grafica", (datos, cfg)))
        self._operacion_activa = True
        self.startb.configure(state="disabled")
        self.btn_rapida.configure(state="disabled")
        self.testb.configure(state="disabled")
        self.btn_abortar.configure(state="normal")
        threading.Thread(
            target=self._run_cycle,
            args=(guardar_archivos,),
            daemon=True,
        ).start()

    def _run_cycle(self, guardar_archivos: bool) -> None:
        try:
            if guardar_archivos:
                run_degradation_sequence(self.cfg, guardar_archivos=True)
            else:
                run_comparison_cycle(self.cfg, ciclo=1, guardar_archivos=False)
        except Exception as exc:
            self.log_msg(f"ERROR durante el ciclo comparativo: {exc}")
        finally:
            self.q.put(("cycle_done", ""))

    def test(self) -> None:
        if not self.modo_automatico or self._operacion_activa:
            self.log_msg("Activa el modo automático y espera a que termine la operación actual.")
            return
        self.recoger_configuracion()
        self.cfg["evento_aborto"] = threading.Event()
        self.cfg["log_callback"] = self.log_msg
        self.cfg["grafica_callback"] = lambda datos, cfg: self.q.put(("grafica", (datos, cfg)))
        self._operacion_activa = True
        self.testb.configure(state="disabled")
        self.btn_abortar.configure(state="normal")
        self.log_msg("Iniciando prueba de relés y estructuras…")
        threading.Thread(target=self._test, daemon=True).start()

    def _test(self) -> None:
        try:
            result = probar_reles_y_dispositivos(self.cfg)
            self.q.put(("log", f"Resultado de la prueba: {result.get('estado', 'desconocido')}"))
        except MedidaAbortadaPorUsuario as error:
            self.q.put(("log", f"Prueba abortada: {error}"))
        except Exception as error:
            self.q.put(("log", f"ERROR en prueba de relés: {error}"))
        finally:
            self.q.put(("test_done", ""))

    def toggle_manual(self) -> None:
        if self._operacion_activa:
            self.log_msg("Espera a que termine la operación actual.")
            return
        self.recoger_configuracion()
        if not self.modo_automatico:
            self._operacion_activa = True
            self.log_msg("Recuperando control automático del NGU401…")
            threading.Thread(target=self._recover_automatic, daemon=True).start()
            return

        self._operacion_activa = True
        self.log_msg("Liberando el NGU401 para control manual…")
        threading.Thread(target=self._release_manual, daemon=True).start()

    def _release_manual(self) -> None:
        instrument = None
        try:
            instrument = NGU401(self.cfg).connect()
            instrument.liberar_control_manual()
            self.q.put(("manual_done", "manual"))
        except Exception as error:
            self.q.put(("operation_error", str(error)))
        finally:
            if instrument:
                instrument.close()

    def _recover_automatic(self) -> None:
        instrument = None
        try:
            instrument = NGU401(self.cfg).connect()
            instrument.recuperar_control_automatico()
            self.q.put(("manual_done", "automatico"))
        except Exception as error:
            self.q.put(("operation_error", str(error)))
        finally:
            if instrument:
                instrument.close()

    def abort(self) -> None:
        event = self.cfg.get("evento_aborto")
        if event:
            event.set()
        registry.abortar_instrumento_activo()
        self.log_msg("Solicitud de aborto registrada.")

    def poll(self) -> None:
        try:
            if not self.winfo_exists():
                return
            while True:
                message_type, message = self.q.get_nowait()
                if message_type == "log":
                    self.log.configure(state="normal")
                    self.log.insert("end", message + "\n")
                    self.log.see("end")
                    self.log.configure(state="disabled")
                elif message_type == "grafica":
                    datos, cfg = message
                    self._mostrar_grafica(datos, cfg)
                elif message_type == "test_done":
                    self._operacion_activa = False
                    self.testb.configure(state="normal")
                    self.btn_abortar.configure(state="disabled")
                    if hasattr(self.winfo_toplevel(), "process_pending_resize"):
                        self.winfo_toplevel().process_pending_resize()
                elif message_type == "cycle_done":
                    self._operacion_activa = False
                    self.startb.configure(state="normal")
                    self.btn_rapida.configure(state="normal")
                    self.testb.configure(state="normal")
                    self.btn_abortar.configure(state="disabled")
                    if hasattr(self.winfo_toplevel(), "process_pending_resize"):
                        self.winfo_toplevel().process_pending_resize()
                elif message_type == "manual_done":
                    self._operacion_activa = False
                    if hasattr(self.winfo_toplevel(), "process_pending_resize"):
                        self.winfo_toplevel().process_pending_resize()
                    self.modo_automatico = message == "automatico"
                    if self._boton_modo:
                        self._boton_modo.configure(
                            text=("⚙ Modo manual / automático" if self.modo_automatico else "↩ Volver a modo automático")
                        )
                    self.log_msg(
                        "Control automático recuperado."
                        if self.modo_automatico
                        else "NGU401 liberado para control manual."
                    )
                elif message_type == "operation_error":
                    self._operacion_activa = False
                    if hasattr(self.winfo_toplevel(), "process_pending_resize"):
                        self.winfo_toplevel().process_pending_resize()
                    self.log_msg(f"ERROR cambiando el modo del NGU401: {message}")
        except queue.Empty:
            pass

        self._poll_job = self.after(100, self.poll)
