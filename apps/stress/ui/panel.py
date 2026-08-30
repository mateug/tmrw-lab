"""Panel de control e interfaz gráfica para el Modo Stress (degradación A/B)."""
from __future__ import annotations

import queue
import threading
import tkinter as tk
from tkinter import messagebox, ttk
from tkinter.scrolledtext import ScrolledText

from core.exceptions import MedidaAbortadaPorUsuario
from core.instrument.ngu401 import (
    NGU401,
    close_ngu401,
    connect_ngu401,
    liberar_control_manual_ngu401,
    recuperar_control_automatico_ngu401,
)
from core.plot.plotter import generar_imagen_tk_curvas_iv_pv
from core.ui_kit.scaler import (
    UIConfig,
    ui,
    ui_font,
    ui_font_console,
    ui_font_label,
    ui_font_section_header,
)
from core.ui_kit.shared import (
    crear_barra_superior,
    crear_campo_directorio,
    crear_seccion_frame as section,
    mostrar_error,
    mostrar_info,
)
from core.ui_kit.theme import theme_mgr

from apps.stress.config import get_default_config
from apps.stress.hardware_test import test_relays_and_devices
from apps.stress.sequence import run_cycle, run_sequence


class StressFrame(ttk.Frame):
    """Panel principal de degradación comparativa A/B."""

    def __init__(self, master: tk.Misc, callback_volver=None, **kwargs) -> None:
        super().__init__(master, **kwargs)
        self.callback_volver = callback_volver
        self.cfg = get_default_config()
        self.q: queue.Queue[tuple[str, object]] = queue.Queue()
        self.time_rules: list[tuple[tk.StringVar, tk.StringVar]] = []
        self.slope_rules: list[tuple[tk.StringVar, tk.StringVar]] = []
        self.modo_automatico = True
        self._operacion_activa = False
        self._boton_modo: ttk.Button | None = None
        self.fig_actual = None
        self.v: dict[str, tk.Variable] = {}

        self._init_variables()
        self._create_ui()
        self.after(100, self.poll)

    @property
    def operacion_activa(self) -> bool:
        """Indica si existe una operación de hardware en curso."""
        return self._operacion_activa

    def _init_variables(self) -> None:
        c = self.cfg
        self.v = {
            "folder": tk.StringVar(value=c.get("carpeta_salida", "")),
            "cycle_name": tk.StringVar(value=c.get("nombre_carpeta_medida", "")),
            "port": tk.StringVar(value=c.get("rele", {}).get("puerto_serie", "COM5")),
            "visa": tk.StringVar(value=c.get("smu", {}).get("recurso_visa", "")),
            "fallback_interval": tk.StringVar(
                value=str(c.get("programacion", {}).get("intervalo_fallback_s", 60.0))
            ),
            "window_size": tk.StringVar(
                value=str(c.get("programacion", {}).get("ventana_muestras_pendiente", 3))
            ),
        }
        for prefix in ("a", "b"):
            block = c.get(f"dispositivo_{prefix}", {})
            directa = block.get("directa", {})
            inversa = block.get("inversa", {})
            self.v[f"{prefix}_v_ini_dir_mV"] = tk.StringVar(value=str(directa.get("v_inicial_mV", 0.0)))
            self.v[f"{prefix}_v_fin_dir_mV"] = tk.StringVar(value=str(directa.get("v_final_mV", 600.0)))
            self.v[f"{prefix}_paso_dir_mV"] = tk.StringVar(value=str(directa.get("paso_mV", 10.0)))
            self.v[f"{prefix}_v_ini_inv_mV"] = tk.StringVar(value=str(inversa.get("v_inicial_mV", 0.0)))
            self.v[f"{prefix}_v_fin_inv_V"] = tk.StringVar(value=str(inversa.get("v_final_V", -0.5)))
            self.v[f"{prefix}_paso_inv_mV"] = tk.StringVar(value=str(inversa.get("paso_mV", 10.0)))
            self.v[f"{prefix}_i_max_uA"] = tk.StringVar(value=str(block.get("i_max_uA", 10.0)))

    def _create_ui(self) -> None:
        crear_barra_superior(
            self,
            "Modo 4: Stress — Degradación Comparativa A/B",
            self.callback_volver,
        )

        body = ttk.Frame(self, style="Window.TFrame")
        body.pack(fill="both", expand=True, padx=ui(6), pady=ui(4))

        left = ttk.Frame(body, style="Window.TFrame")
        left.pack(side="left", fill="both", expand=True, padx=(0, ui(4)))

        right = ttk.Frame(body, width=ui(460), style="Window.TFrame")
        right.pack(side="right", fill="both", expand=False, padx=(ui(4), 0))
        right.pack_propagate(False)

        # [1] Guardado de Datos
        self.save = section(left, "[1] Configuración de guardado de medidas", "keithley")
        crear_campo_directorio(self.save, self.v["folder"], 0, "Carpeta de salida:")
        f_sub = ttk.Frame(self.save, style="Window.TFrame")
        f_sub.grid(row=1, column=0, columnspan=3, sticky="w", padx=ui(6), pady=ui(2))
        ttk.Label(f_sub, text="Nombre del ciclo:").pack(side="left")
        ttk.Entry(f_sub, textvariable=self.v["cycle_name"], width=20).pack(side="left", padx=ui(4))

        # [2] y [3] Paneles A y B
        self._device_panel(left, "A", "[2] Curva IV — Estructura A (Entradas NC de los relés)")
        self._device_panel(left, "B", "[3] Curva IV — Estructura B (Entradas NO de los relés)")

        # [4] Intervalos
        self._intervals_panel(left)

        # [5] Control
        self._control_panel(left)

        # Panel Derecho: Consola y Gráfica
        self._results_panel(right)

    def _device_panel(self, parent: tk.Misc, key: str, title: str) -> None:
        prefix = key.lower()
        panel = section(parent, title, "params")
        f_grid = ttk.Frame(panel, style="Window.TFrame")
        f_grid.pack(fill="x", padx=ui(6), pady=ui(3))

        fields = [
            ("V ini directa (mV):", f"{prefix}_v_ini_dir_mV"),
            ("V fin directa (mV):", f"{prefix}_v_fin_dir_mV"),
            ("Paso directa (mV):", f"{prefix}_paso_dir_mV"),
            ("V ini inversa (mV):", f"{prefix}_v_ini_inv_mV"),
            ("V final inversa (V):", f"{prefix}_v_fin_inv_V"),
            ("Paso inversa (mV):", f"{prefix}_paso_inv_mV"),
            ("I máxima (µA):", f"{prefix}_i_max_uA"),
        ]

        for idx, (label_txt, var_name) in enumerate(fields):
            r = idx // 3
            c = (idx % 3) * 2
            ttk.Label(f_grid, text=label_txt).grid(row=r, column=c, sticky="w", padx=ui(3), pady=ui(1))
            ttk.Entry(f_grid, textvariable=self.v[var_name], width=9).grid(row=r, column=c + 1, sticky="w", padx=ui(3), pady=ui(1))

    def _intervals_panel(self, parent: tk.Misc) -> None:
        panel = section(parent, "[4] Selección de intervalos temporales", "params")
        prog = self.cfg.get("programacion", {})

        self.time_rules = [
            (tk.StringVar(value=str(r.get("hasta_min", 60))), tk.StringVar(value=str(r.get("intervalo_s", 30))))
            for r in prog.get("intervalos_por_tiempo", [{"hasta_min": 60, "intervalo_s": 30}])
        ]
        self.slope_rules = [
            (tk.StringVar(value=str(r.get("umbral_dvoc_dt", 0.005))), tk.StringVar(value=str(r.get("intervalo_s", 20))))
            for r in prog.get("intervalos_por_pendiente_voc", [{"umbral_dvoc_dt": 0.005, "intervalo_s": 20}])
        ]

        self.tabs = ttk.Notebook(panel)
        self.tabs.pack(fill="x", padx=ui(4), pady=ui(2))

        # Tab tiempo
        t_tab = ttk.Frame(self.tabs, style="Window.TFrame")
        self.tabs.add(t_tab, text="Intervalos por tiempo")
        self.time_rows = ttk.Frame(t_tab, style="Window.TFrame")
        self.time_rows.pack(fill="x", padx=ui(4), pady=ui(2))
        self._render_rule_rows(self.time_rows, self.time_rules, "Límite (min)", "Intervalo (s)")
        ttk.Button(t_tab, text="+ Añadir tramo", command=lambda: self._add_rule(self.time_rules, self.time_rows, "Límite (min)", "Intervalo (s)")).pack(anchor="w", padx=ui(4), pady=ui(2))

        # Tab pendiente
        s_tab = ttk.Frame(self.tabs, style="Window.TFrame")
        self.tabs.add(s_tab, text="Intervalos por estabilización (dVoc/dt)")
        self.slope_rows = ttk.Frame(s_tab, style="Window.TFrame")
        self.slope_rows.pack(fill="x", padx=ui(4), pady=ui(2))
        self._render_rule_rows(self.slope_rows, self.slope_rules, "Umbral Voc (V/min)", "Intervalo (s)")
        ttk.Button(s_tab, text="+ Añadir umbral", command=lambda: self._add_rule(self.slope_rules, self.slope_rows, "Umbral Voc (V/min)", "Intervalo (s)")).pack(anchor="w", padx=ui(4), pady=ui(2))

    def _render_rule_rows(self, parent: ttk.Frame, rules: list, first_lbl: str, sec_lbl: str) -> None:
        for w in parent.winfo_children():
            w.destroy()
        for idx, (v1, v2) in enumerate(rules):
            row = ttk.Frame(parent, style="Window.TFrame")
            row.pack(fill="x", pady=ui(1))
            ttk.Label(row, text=f"{first_lbl}:").pack(side="left", padx=ui(2))
            ttk.Entry(row, textvariable=v1, width=8).pack(side="left", padx=ui(2))
            ttk.Label(row, text=f"{sec_lbl}:").pack(side="left", padx=(ui(8), ui(2)))
            ttk.Entry(row, textvariable=v2, width=8).pack(side="left", padx=ui(2))
            if len(rules) > 1:
                ttk.Button(row, text="✕", width=3, command=lambda i=idx: self._del_rule(parent, rules, i, first_lbl, sec_lbl)).pack(side="left", padx=ui(4))

    def _add_rule(self, rules: list, parent: ttk.Frame, f_lbl: str, s_lbl: str) -> None:
        rules.append((tk.StringVar(value="120"), tk.StringVar(value="60")))
        self._render_rule_rows(parent, rules, f_lbl, s_lbl)

    def _del_rule(self, parent: ttk.Frame, rules: list, idx: int, f_lbl: str, s_lbl: str) -> None:
        if len(rules) > 1:
            rules.pop(idx)
            self._render_rule_rows(parent, rules, f_lbl, s_lbl)

    def _control_panel(self, parent: tk.Misc) -> None:
        t = theme_mgr.get_current_theme()
        panel = section(parent, "[5] Control de Medida", "control")

        f_conns = ttk.Frame(panel, style="Window.TFrame")
        f_conns.pack(fill="x", padx=ui(6), pady=ui(2))
        ttk.Label(f_conns, text="Arduino (COM):").pack(side="left")
        ttk.Entry(f_conns, textvariable=self.v["port"], width=8).pack(side="left", padx=(ui(2), ui(12)))
        ttk.Label(f_conns, text="NGU401 (VISA):").pack(side="left")
        ttk.Entry(f_conns, textvariable=self.v["visa"], width=22).pack(side="left", padx=ui(2))

        f_btns = ttk.Frame(panel, style="Window.TFrame")
        f_btns.pack(fill="x", padx=ui(4), pady=ui(4))

        self.btn_iniciar = tk.Button(
            f_btns, text="▶ INICIAR SECUENCIA",
            bg=t["buttons"]["primary_bg"], fg=t["buttons"]["primary_fg"],
            activebackground=t["buttons"]["primary_hover"], activeforeground="#ffffff",
            font=ui_font("Segoe UI", UIConfig.SIZE_LABEL, "bold"),
            command=self.start_measurement, padx=ui(10), pady=ui(4), relief="flat", cursor="hand2",
        )
        self.btn_iniciar.pack(side="left", padx=ui(3))

        self.btn_rapida = tk.Button(
            f_btns, text="⚡ MEDIDA RÁPIDA",
            bg=t["buttons"]["quick_bg"], fg=t["buttons"]["quick_fg"],
            activebackground=t["buttons"]["quick_hover"], activeforeground="#ffffff",
            font=ui_font("Segoe UI", UIConfig.SIZE_LABEL, "bold"),
            command=self.quick_measurement, padx=ui(8), pady=ui(4), relief="flat", cursor="hand2",
        )
        self.btn_rapida.pack(side="left", padx=ui(3))

        self.btn_abortar = tk.Button(
            f_btns, text="⏹ DETENER / ABORTAR",
            bg=t["buttons"]["danger_bg"], fg=t["buttons"]["danger_fg"],
            activebackground=t["buttons"]["danger_hover"], activeforeground="#ffffff",
            font=ui_font("Segoe UI", UIConfig.SIZE_LABEL, "bold"),
            command=self.abort, padx=ui(8), pady=ui(4), relief="flat", cursor="hand2",
            state="disabled",
        )
        self.btn_abortar.pack(side="left", padx=ui(3))

        self._boton_modo = tk.Button(
            f_btns, text="⚙ Modo manual / automático",
            bg=t["buttons"]["tool_bg"], fg=t["buttons"]["tool_fg"],
            activebackground=t["buttons"]["tool_hover"], activeforeground="#ffffff",
            font=ui_font("Segoe UI", UIConfig.SIZE_LABEL),
            command=self.toggle_manual, padx=ui(6), pady=ui(4), relief="flat", cursor="hand2",
        )
        self._boton_modo.pack(side="left", padx=ui(3))

        self.btn_test = tk.Button(
            f_btns, text="🔌 TESTEAR RELÉS Y ESTRUCTURAS",
            bg=t["buttons"]["tool_bg"], fg=t["buttons"]["tool_fg"],
            activebackground=t["buttons"]["tool_hover"], activeforeground="#ffffff",
            font=ui_font("Segoe UI", UIConfig.SIZE_LABEL),
            command=self.test, padx=ui(6), pady=ui(4), relief="flat", cursor="hand2",
        )
        self.btn_test.pack(side="left", padx=ui(3))

    def _results_panel(self, parent: tk.Misc) -> None:
        t = theme_mgr.get_current_theme()
        res_c = t.get("results", {})
        f_res = section(parent, "Resultados y Progreso", "results")
        f_res.pack(fill="both", expand=True)

        self.txt_log = ScrolledText(
            f_res,
            font=ui_font_console(),
            bg=res_c.get("bg_console", "#1e293b"),
            fg=res_c.get("fg_console", "#f8fafc"),
            insertbackground="#0284c7",
            borderwidth=1,
            relief="solid",
            height=UIConfig.CONSOLE_HEIGHT,
        )
        self.txt_log.pack(fill="both", expand=True, pady=ui(4))
        self.txt_log.insert("end", "Modo Stress preparado. Configura los parámetros y pulsa ▶ INICIAR SECUENCIA o 🔌 TESTEAR.\n")

    def log_msg(self, msg: str) -> None:
        self.q.put(("log", msg))

    def recoger_configuracion(self) -> None:
        c = self.cfg
        c["carpeta_salida"] = self.v["folder"].get().strip()
        c["nombre_carpeta_medida"] = self.v["cycle_name"].get().strip()
        c["rele"]["puerto_serie"] = self.v["port"].get().strip()
        c["smu"]["recurso_visa"] = self.v["visa"].get().strip()

        for key in ("a", "b"):
            prefix = key.lower()
            block = c[f"dispositivo_{prefix}"]
            block["directa"]["v_inicial_mV"] = float(self.v[f"{prefix}_v_ini_dir_mV"].get() or 0.0)
            block["directa"]["v_final_mV"] = float(self.v[f"{prefix}_v_fin_dir_mV"].get() or 600.0)
            block["directa"]["paso_mV"] = float(self.v[f"{prefix}_paso_dir_mV"].get() or 10.0)
            block["inversa"]["v_inicial_mV"] = float(self.v[f"{prefix}_v_ini_inv_mV"].get() or 0.0)
            block["inversa"]["v_final_V"] = float(self.v[f"{prefix}_v_fin_inv_V"].get() or -0.5)
            block["inversa"]["paso_mV"] = float(self.v[f"{prefix}_paso_inv_mV"].get() or 10.0)
            block["i_max_uA"] = float(self.v[f"{prefix}_i_max_uA"].get() or 10.0)

    def start_measurement(self) -> None:
        if not self.modo_automatico or self._operacion_activa:
            return
        self.recoger_configuracion()
        self.cfg["evento_aborto"] = threading.Event()
        self.cfg["log_callback"] = self.log_msg
        self._operacion_activa = True
        self.btn_iniciar.configure(state="disabled")
        self.btn_rapida.configure(state="disabled")
        self.btn_abortar.configure(state="normal")
        self.log_msg("Iniciando secuencia de degradación...")
        threading.Thread(target=self._run_sequence, daemon=True).start()

    def _run_sequence(self) -> None:
        try:
            run_sequence(self.cfg)
        except MedidaAbortadaPorUsuario as exc:
            self.log_msg(f"[⏹] Secuencia abortada: {exc}")
        except Exception as exc:
            self.log_msg(f"[ERROR] Fallo en secuencia: {exc}")
        finally:
            self.q.put(("seq_done", None))

    def quick_measurement(self) -> None:
        if not self.modo_automatico or self._operacion_activa:
            return
        self.recoger_configuracion()
        self.cfg["evento_aborto"] = threading.Event()
        self.cfg["log_callback"] = self.log_msg
        self._operacion_activa = True
        self.btn_iniciar.configure(state="disabled")
        self.btn_rapida.configure(state="disabled")
        self.btn_abortar.configure(state="normal")
        self.log_msg("Iniciando medida rápida (ciclo diagnóstico puntual)...")
        threading.Thread(target=self._run_quick, daemon=True).start()

    def _run_quick(self) -> None:
        try:
            run_cycle(self.cfg, guardar_archivos=False)
            self.log_msg("[✓] Medida rápida completada.")
        except Exception as exc:
            self.log_msg(f"[ERROR] Medida rápida: {exc}")
        finally:
            self.q.put(("seq_done", None))

    def test(self) -> None:
        if not self.modo_automatico or self._operacion_activa:
            return
        self.recoger_configuracion()
        self.cfg["evento_aborto"] = threading.Event()
        self.cfg["log_callback"] = self.log_msg
        self._operacion_activa = True
        self.btn_test.configure(state="disabled")
        self.log_msg("Iniciando test de relés y estructuras...")
        threading.Thread(target=self._run_test, daemon=True).start()

    def _run_test(self) -> None:
        try:
            test_relays_and_devices(self.cfg)
            self.log_msg("[✓] Test completado con éxito.")
        except Exception as exc:
            self.log_msg(f"[ERROR] Test: {exc}")
        finally:
            self.q.put(("test_done", None))

    def abort(self) -> None:
        if "evento_aborto" in self.cfg:
            self.cfg["evento_aborto"].set()
        self.log_msg("[⏹] Solicitud de aborto enviada...")

    def toggle_manual(self) -> None:
        try:
            if self.modo_automatico:
                liberar_control_manual_ngu401(self.v["visa"].get().strip())
                self.modo_automatico = False
                if self._boton_modo:
                    self._boton_modo.configure(text="↩ Volver a modo automático")
                self.log_msg("NGU401 liberado para control manual local.")
            else:
                recuperar_control_automatico_ngu401(self.v["visa"].get().strip())
                self.modo_automatico = True
                if self._boton_modo:
                    self._boton_modo.configure(text="⚙ Modo manual / automático")
                self.log_msg("Control automático recuperado.")
        except Exception as exc:
            mostrar_error("Error", f"No se pudo cambiar modo:\n{exc}")

    def poll(self) -> None:
        while not self.q.empty():
            kind, data = self.q.get_nowait()
            if kind == "log":
                self.txt_log.insert("end", f"{data}\n")
                self.txt_log.see("end")
            elif kind in ("seq_done", "test_done"):
                self._operacion_activa = False
                self.btn_iniciar.configure(state="normal")
                self.btn_rapida.configure(state="normal")
                self.btn_abortar.configure(state="disabled")
                self.btn_test.configure(state="normal")

        self.after(100, self.poll)
