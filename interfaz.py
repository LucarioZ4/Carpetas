# -*- coding: utf-8 -*-
"""
interfaz.py
------------
Interfaz gráfica (Tkinter) de la aplicación "Gestor de Soportes PDF".

La aplicación tiene DOS módulos, organizados en pestañas:

    1) "Dividir PDF"        -> usa divisor.py
       Divide el PDF combinado (Acta + Órdenes) que produce el escáner
       en dos archivos: uno para el Acta (-1) y otro para las Órdenes
       (-2 o -2-N).

    2) "Renombrar soportes" -> usa funciones.py
       Toma los archivos ya divididos (o que ya vinieran nombrados así)
       y les asigna su nombre final: CRC_<NIT>.pdf, OPF_<NIT>.pdf,
       PDE_<NIT>.pdf.

El flujo normal de trabajo es: primero "Dividir PDF" y luego "Renombrar
soportes", sobre la misma carpeta principal.

Ambas pestañas comparten la misma estructura visual (seleccionar carpeta,
botón de acción, barra de progreso, contadores, log, abrir carpeta), por
lo que se implementan con una única clase reutilizable: `PantallaProceso`.
La comunicación entre el hilo de trabajo y la GUI se hace con una
`queue.Queue`, que es la forma segura de actualizar Tkinter desde otro hilo.
"""

import os
import sys
import threading
import queue
import tkinter as tk
from tkinter import ttk, filedialog, messagebox

import funciones
import divisor


# =============================================================================
# PALETA DE COLORES / ESTILO (interfaz moderna y sencilla)
# =============================================================================
COLOR_FONDO = "#1e1e2e"
COLOR_PANEL = "#282a3a"
COLOR_TEXTO = "#e6e6e6"
COLOR_ACENTO = "#4f8cff"
COLOR_ACENTO_HOVER = "#3a6fd6"
COLOR_EXITO = "#3ddc97"
COLOR_ADVERTENCIA = "#ffb454"
COLOR_LOG_FONDO = "#12131c"


def _ruta_recurso(nombre_archivo: str) -> str:
    """
    Obtiene la ruta absoluta de un recurso (por ejemplo, el ícono),
    funcionando tanto en modo desarrollo como empaquetado con
    PyInstaller (que descomprime los recursos en una carpeta temporal
    referenciada por sys._MEIPASS).
    """
    if hasattr(sys, "_MEIPASS"):
        base_path = sys._MEIPASS  # type: ignore[attr-defined]
    else:
        base_path = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base_path, nombre_archivo)


# =============================================================================
# COMPONENTE REUTILIZABLE: UNA PANTALLA DE PROCESO (una pestaña completa)
# =============================================================================
class PantallaProceso(tk.Frame):
    """
    Pantalla genérica para un proceso de tipo "seleccionar carpeta ->
    procesar subcarpetas -> ver progreso/contadores/log". Se reutiliza
    tanto para "Dividir PDF" como para "Renombrar soportes", pasando la
    función de procesamiento y los textos correspondientes.
    """

    def __init__(
        self,
        parent,
        titulo: str,
        descripcion: str,
        texto_boton_accion: str,
        etiqueta_contador_secundario: str,
        clave_contador_secundario: str,
        funcion_proceso,
    ):
        """
        Parámetros
        ----------
        titulo, descripcion : textos que se muestran arriba de la pantalla.
        texto_boton_accion : texto del botón principal (ej. "Dividir PDF").
        etiqueta_contador_secundario : título de la segunda tarjeta de
            contador (ej. "Archivos divididos" o "Archivos renombrados").
            También se usa como etiqueta en el resumen final.
        clave_contador_secundario : nombre de la llave dentro del diccionario
            de resultados/contadores que corresponde al contador secundario
            (ej. "divididos" o "renombrados").
        funcion_proceso : función con la firma
            (carpeta_principal, log_callback, progress_callback,
             counters_callback, detener_flag) -> dict
            proveniente de divisor.py o funciones.py.
        """
        super().__init__(parent, bg=COLOR_FONDO)

        self.clave_contador_secundario = clave_contador_secundario
        self.titulo_contador_secundario = etiqueta_contador_secundario
        self.funcion_proceso = funcion_proceso

        self.carpeta_seleccionada = None
        self.hilo_proceso = None
        self.detener_flag = threading.Event()
        self.cola_mensajes = queue.Queue()
        self.procesando = False

        self._crear_widgets(titulo, descripcion, texto_boton_accion, etiqueta_contador_secundario)

        # Revisa periódicamente si hay mensajes nuevos desde el hilo de trabajo
        self.after(100, self._procesar_cola_mensajes)

    # =================================================================
    # CONSTRUCCIÓN DE WIDGETS
    # =================================================================
    def _crear_widgets(self, titulo, descripcion, texto_boton_accion, etiqueta_contador_secundario):
        # ---- Encabezado -------------------------------------------------
        marco_encabezado = tk.Frame(self, bg=COLOR_FONDO)
        marco_encabezado.pack(fill="x", padx=24, pady=(20, 6))

        tk.Label(
            marco_encabezado,
            text=titulo,
            font=("Segoe UI", 14, "bold"),
            bg=COLOR_FONDO,
            fg=COLOR_TEXTO,
        ).pack(anchor="w")

        tk.Label(
            marco_encabezado,
            text=descripcion,
            font=("Segoe UI", 9),
            bg=COLOR_FONDO,
            fg="#9a9ab0",
            wraplength=680,
            justify="left",
        ).pack(anchor="w", pady=(4, 0))

        # ---- Selección de carpeta ---------------------------------------
        marco_carpeta = tk.Frame(self, bg=COLOR_PANEL)
        marco_carpeta.pack(fill="x", padx=24, pady=10)

        contenido_carpeta = tk.Frame(marco_carpeta, bg=COLOR_PANEL)
        contenido_carpeta.pack(fill="x", padx=14, pady=14)

        self.boton_seleccionar = ttk.Button(
            contenido_carpeta,
            text="📁  Seleccionar carpeta",
            style="Acento.TButton",
            command=self._seleccionar_carpeta,
        )
        self.boton_seleccionar.pack(side="left")

        self.etiqueta_ruta = tk.Label(
            contenido_carpeta,
            text="Ninguna carpeta seleccionada",
            font=("Segoe UI", 9),
            bg=COLOR_PANEL,
            fg="#9a9ab0",
            anchor="w",
            wraplength=480,
            justify="left",
        )
        self.etiqueta_ruta.pack(side="left", padx=14, fill="x", expand=True)

        # ---- Botón de acción principal ----------------------------------
        marco_accion = tk.Frame(self, bg=COLOR_FONDO)
        marco_accion.pack(fill="x", padx=24, pady=(0, 10))

        self.boton_accion = ttk.Button(
            marco_accion,
            text=texto_boton_accion,
            style="Acento.TButton",
            command=self._iniciar_proceso,
            state="disabled",
        )
        self.boton_accion.pack(side="left")

        self.boton_abrir_carpeta = ttk.Button(
            marco_accion,
            text="📂  Abrir carpeta",
            style="Secundario.TButton",
            command=self._abrir_carpeta,
            state="disabled",
        )
        self.boton_abrir_carpeta.pack(side="left", padx=10)

        # ---- Barra de progreso -------------------------------------------
        marco_progreso = tk.Frame(self, bg=COLOR_FONDO)
        marco_progreso.pack(fill="x", padx=24, pady=(6, 4))

        self.barra_progreso = ttk.Progressbar(
            marco_progreso,
            style="Horizontal.TProgressbar",
            orient="horizontal",
            mode="determinate",
        )
        self.barra_progreso.pack(fill="x")

        # ---- Contadores ----------------------------------------------------
        marco_contadores = tk.Frame(self, bg=COLOR_FONDO)
        marco_contadores.pack(fill="x", padx=24, pady=(10, 10))

        self.etiqueta_carpetas = self._crear_tarjeta_contador(
            marco_contadores, "Carpetas procesadas", "0"
        )
        self.etiqueta_contador_secundario = self._crear_tarjeta_contador(
            marco_contadores, etiqueta_contador_secundario, "0"
        )
        self.etiqueta_errores = self._crear_tarjeta_contador(
            marco_contadores, "Errores / advertencias", "0"
        )

        # ---- Área de registro (log) ----------------------------------------
        marco_log = tk.Frame(self, bg=COLOR_FONDO)
        marco_log.pack(fill="both", expand=True, padx=24, pady=(0, 20))

        tk.Label(
            marco_log,
            text="Registro de actividad",
            font=("Segoe UI", 10, "bold"),
            bg=COLOR_FONDO,
            fg=COLOR_TEXTO,
        ).pack(anchor="w", pady=(0, 6))

        marco_texto = tk.Frame(marco_log, bg=COLOR_LOG_FONDO)
        marco_texto.pack(fill="both", expand=True)

        barra_scroll = tk.Scrollbar(marco_texto)
        barra_scroll.pack(side="right", fill="y")

        self.area_log = tk.Text(
            marco_texto,
            bg=COLOR_LOG_FONDO,
            fg=COLOR_TEXTO,
            insertbackground=COLOR_TEXTO,
            font=("Consolas", 9),
            wrap="word",
            yscrollcommand=barra_scroll.set,
            state="disabled",
            borderwidth=0,
            highlightthickness=0,
        )
        self.area_log.pack(fill="both", expand=True, padx=8, pady=8)
        barra_scroll.config(command=self.area_log.yview)

        # Etiquetas de color dentro del log
        self.area_log.tag_config("exito", foreground=COLOR_EXITO)
        self.area_log.tag_config("advertencia", foreground=COLOR_ADVERTENCIA)
        self.area_log.tag_config("normal", foreground=COLOR_TEXTO)

    def _crear_tarjeta_contador(self, contenedor, titulo, valor_inicial):
        tarjeta = tk.Frame(contenedor, bg=COLOR_PANEL)
        tarjeta.pack(side="left", expand=True, fill="both", padx=(0, 10))

        etiqueta_valor = tk.Label(
            tarjeta,
            text=valor_inicial,
            font=("Segoe UI", 20, "bold"),
            bg=COLOR_PANEL,
            fg=COLOR_ACENTO,
        )
        etiqueta_valor.pack(pady=(14, 0))

        tk.Label(
            tarjeta,
            text=titulo,
            font=("Segoe UI", 9),
            bg=COLOR_PANEL,
            fg="#9a9ab0",
        ).pack(pady=(0, 14))

        return etiqueta_valor

    # =================================================================
    # EVENTOS DE LA INTERFAZ
    # =================================================================
    def _seleccionar_carpeta(self):
        if self.procesando:
            return

        ruta = filedialog.askdirectory(title="Selecciona la carpeta principal")
        if not ruta:
            return

        self.carpeta_seleccionada = ruta
        self.etiqueta_ruta.config(text=ruta, fg=COLOR_TEXTO)
        self.boton_accion.config(state="normal")
        self.boton_abrir_carpeta.config(state="normal")

    def _abrir_carpeta(self):
        if not self.carpeta_seleccionada:
            return
        try:
            os.startfile(self.carpeta_seleccionada)  # Específico de Windows
        except Exception as error:
            messagebox.showerror("Error", f"No se pudo abrir la carpeta:\n{error}")

    def _iniciar_proceso(self):
        if not self.carpeta_seleccionada:
            messagebox.showwarning("Atención", "Primero selecciona una carpeta.")
            return

        if self.procesando:
            return

        # Reinicia estado visual
        self._reiniciar_contadores()
        self._limpiar_log()
        self.barra_progreso["value"] = 0
        self.detener_flag.clear()
        self.procesando = True
        self.boton_seleccionar.config(state="disabled")
        self.boton_accion.config(state="disabled")

        self._escribir_log(f"Iniciando proceso en: {self.carpeta_seleccionada}", "normal")
        self._escribir_log(f"NIT configurado: {funciones.NIT}\n", "normal")

        # El procesamiento se ejecuta en un hilo aparte para no congelar la GUI
        self.hilo_proceso = threading.Thread(
            target=self._ejecutar_proceso_en_hilo, daemon=True
        )
        self.hilo_proceso.start()

    # =================================================================
    # HILO DE TRABAJO (se ejecuta fuera del hilo principal de Tkinter)
    # =================================================================
    def _ejecutar_proceso_en_hilo(self):
        """
        Ejecuta la función de procesamiento (divisor o funciones) y envía
        todos los resultados a través de la cola de mensajes para que la
        GUI los procese de forma segura en el hilo principal.
        """

        def log_callback(mensaje):
            self.cola_mensajes.put(("log", mensaje))

        def progress_callback(actual, total):
            self.cola_mensajes.put(("progreso", (actual, total)))

        def counters_callback(**kwargs):
            self.cola_mensajes.put(("contadores", kwargs))

        try:
            resultados = self.funcion_proceso(
                self.carpeta_seleccionada,
                log_callback,
                progress_callback,
                counters_callback,
                self.detener_flag,
            )
            self.cola_mensajes.put(("finalizado", resultados))
        except Exception as error:
            self.cola_mensajes.put(("error_critico", str(error)))

    # =================================================================
    # PROCESAMIENTO DE LA COLA DE MENSAJES (hilo principal)
    # =================================================================
    def _procesar_cola_mensajes(self):
        try:
            while True:
                tipo, dato = self.cola_mensajes.get_nowait()

                if tipo == "log":
                    tag = "normal"
                    if dato.strip().startswith("⚠"):
                        tag = "advertencia"
                    elif dato.strip().startswith("✔"):
                        tag = "exito"
                    self._escribir_log(dato, tag)

                elif tipo == "progreso":
                    actual, total = dato
                    porcentaje = (actual / total) * 100 if total else 0
                    self.barra_progreso["value"] = porcentaje

                elif tipo == "contadores":
                    self.etiqueta_carpetas.config(text=str(dato.get("carpetas", 0)))
                    self.etiqueta_contador_secundario.config(
                        text=str(dato.get(self.clave_contador_secundario, 0))
                    )
                    self.etiqueta_errores.config(text=str(dato.get("errores", 0)))

                elif tipo == "finalizado":
                    self._finalizar_proceso(dato)

                elif tipo == "error_critico":
                    self.procesando = False
                    self.boton_seleccionar.config(state="normal")
                    self.boton_accion.config(state="normal")
                    messagebox.showerror(
                        "Error inesperado",
                        f"Ocurrió un error crítico durante el proceso:\n{dato}",
                    )

        except queue.Empty:
            pass

        # Se vuelve a programar para seguir revisando la cola
        self.after(100, self._procesar_cola_mensajes)

    def _finalizar_proceso(self, resultados):
        self.procesando = False
        self.boton_seleccionar.config(state="normal")
        self.boton_accion.config(state="normal")
        self.barra_progreso["value"] = 100

        valor_secundario = resultados.get(self.clave_contador_secundario, 0)

        resumen = (
            f"\n========== RESUMEN ==========\n"
            f"Carpetas procesadas: {resultados.get('carpetas', 0)}\n"
            f"{self.titulo_contador_secundario}: {valor_secundario}\n"
            f"Errores: {resultados.get('errores', 0)}\n"
            f"=============================="
        )
        self._escribir_log(resumen, "normal")

        messagebox.showinfo(
            "Proceso finalizado",
            "El proceso ha finalizado.\n\n"
            f"Carpetas procesadas: {resultados.get('carpetas', 0)}\n"
            f"{self.titulo_contador_secundario}: {valor_secundario}\n"
            f"Errores: {resultados.get('errores', 0)}",
        )

    # =================================================================
    # UTILIDADES DE INTERFAZ
    # =================================================================
    def _escribir_log(self, mensaje, tag="normal"):
        self.area_log.config(state="normal")
        self.area_log.insert("end", mensaje + "\n", tag)
        self.area_log.see("end")
        self.area_log.config(state="disabled")

    def _limpiar_log(self):
        self.area_log.config(state="normal")
        self.area_log.delete("1.0", "end")
        self.area_log.config(state="disabled")

    def _reiniciar_contadores(self):
        self.etiqueta_carpetas.config(text="0")
        self.etiqueta_contador_secundario.config(text="0")
        self.etiqueta_errores.config(text="0")


# =============================================================================
# VENTANA PRINCIPAL: contiene las pestañas (Notebook) de cada módulo
# =============================================================================
class AplicacionPrincipal(tk.Tk):
    """Ventana principal de la aplicación, con pestañas para cada módulo."""

    def __init__(self):
        super().__init__()

        self.title(f"DAZALUD CARPETAS - NIT {funciones.NIT}")
        self.geometry("780x680")
        self.minsize(700, 580)
        self.configure(bg=COLOR_FONDO)

        try:
            self.iconbitmap(_ruta_recurso("icono.ico"))
        except Exception:
            pass

        self._configurar_estilos()

        # ---- Encabezado con el nombre de la aplicación --------------------
        marco_marca = tk.Frame(self, bg=COLOR_PANEL)
        marco_marca.pack(fill="x")

        tk.Label(
            marco_marca,
            text="DAZALUD CARPETAS",
            font=("Segoe UI", 13, "bold"),
            bg=COLOR_PANEL,
            fg=COLOR_TEXTO,
        ).pack(side="left", padx=20, pady=10)

        tk.Label(
            marco_marca,
            text=f"NIT configurado: {funciones.NIT}",
            font=("Segoe UI", 9),
            bg=COLOR_PANEL,
            fg="#9a9ab0",
        ).pack(side="right", padx=20)

        # ---- Pestañas (Notebook) -----------------------------------------
        notebook = ttk.Notebook(self, style="App.TNotebook")
        notebook.pack(fill="both", expand=True)

        pestana_dividir = PantallaProceso(
            notebook,
            titulo="✂️  Dividir PDF (Acta + Órdenes)",
            descripcion=(
                "Toma el PDF combinado que produce el escáner (página 1 = Acta, "
                "páginas siguientes = Órdenes de medicamento pegadas) y lo separa "
                "en dos archivos: uno para el Acta y otro para las Órdenes."
            ),
            texto_boton_accion="✂️  Dividir PDF",
            etiqueta_contador_secundario="Archivos divididos",
            clave_contador_secundario="divididos",
            funcion_proceso=divisor.dividir_carpeta_principal,
        )

        pestana_renombrar = PantallaProceso(
            notebook,
            titulo="🔄  Renombrar soportes",
            descripcion=(
                "Recorre todas las subcarpetas y renombra los PDF según las "
                "reglas de negocio: Acta -> CRC, Órdenes -> OPF, "
                "reporte de autorización -> PDE."
            ),
            texto_boton_accion="🔄  Renombrar soportes",
            etiqueta_contador_secundario="Archivos renombrados",
            clave_contador_secundario="renombrados",
            funcion_proceso=funciones.procesar_carpeta_principal,
        )

        notebook.add(pestana_dividir, text="  1. Dividir PDF  ")
        notebook.add(pestana_renombrar, text="  2. Renombrar soportes  ")

    # =================================================================
    # ESTILOS
    # =================================================================
    def _configurar_estilos(self):
        estilo = ttk.Style(self)
        estilo.theme_use("clam")

        estilo.configure(
            "Acento.TButton",
            background=COLOR_ACENTO,
            foreground="white",
            font=("Segoe UI", 10, "bold"),
            padding=10,
            borderwidth=0,
        )
        estilo.map(
            "Acento.TButton",
            background=[("active", COLOR_ACENTO_HOVER), ("disabled", "#555568")],
        )

        estilo.configure(
            "Secundario.TButton",
            background=COLOR_PANEL,
            foreground=COLOR_TEXTO,
            font=("Segoe UI", 10),
            padding=8,
            borderwidth=0,
        )
        estilo.map("Secundario.TButton", background=[("active", "#3a3c52")])

        estilo.configure(
            "Horizontal.TProgressbar",
            troughcolor=COLOR_PANEL,
            background=COLOR_ACENTO,
            thickness=16,
        )

        estilo.configure(
            "App.TNotebook",
            background=COLOR_FONDO,
            borderwidth=0,
        )
        estilo.configure(
            "App.TNotebook.Tab",
            background=COLOR_PANEL,
            foreground=COLOR_TEXTO,
            font=("Segoe UI", 10, "bold"),
            padding=(16, 10),
            borderwidth=0,
        )
        estilo.map(
            "App.TNotebook.Tab",
            background=[("selected", COLOR_ACENTO)],
            foreground=[("selected", "white")],
        )


# Alias por compatibilidad con versiones anteriores del proyecto
AplicacionRenombrador = AplicacionPrincipal
