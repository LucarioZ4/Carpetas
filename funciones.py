# -*- coding: utf-8 -*-
"""
funciones.py
-------------
Módulo con toda la lógica de negocio del "Renombrador automático de
soportes PDF".

Este módulo NO conoce nada de Tkinter: recibe funciones de "callback"
(log_callback, progress_callback, counters_callback) que la interfaz
gráfica (interfaz.py) le pasa, y así se mantiene desacoplado de la GUI.
Esto facilita mantenerlo, probarlo y reutilizarlo.

Para cambiar el NIT de la empresa en el futuro, basta con modificar
la constante NIT que está al inicio de este archivo.
"""

from pathlib import Path
import re

# Patrón que reconoce el sufijo de "Órdenes" generado por el módulo divisor:
# "-2", "-2-3", "-2-3-4", etc. (una o varias órdenes pegadas en un solo PDF).
_PATRON_ORDENES = re.compile(r"-2(-\d+)*$")


# =============================================================================
# CONFIGURACIÓN GLOBAL - MODIFICAR AQUÍ PARA CAMBIAR DE EMPRESA
# =============================================================================
NIT = "900926475"


# =============================================================================
# REGLAS DE RENOMBRADO
# =============================================================================
# Cada regla define:
#   - "prefijo": el prefijo que tendrá el archivo final (CRC, OPF, PDE...)
#   - "coincide": función que recibe el nombre del archivo (en minúsculas,
#                 sin extensión) y retorna True si la regla aplica.
#
# El orden de la lista IMPORTA: se evalúan de arriba hacia abajo y se
# aplica la PRIMERA regla que coincida. Por eso "reporte-autorizacion"
# va primero, ya que es la condición más específica.
# =============================================================================

def _es_reporte_autorizacion(nombre_sin_extension: str) -> bool:
    """
    Detecta archivos tipo 'reporte-autorizacion...pdf'.

    Se normalizan los guiones bajos ("_") a guiones medios ("-") antes de
    comparar, ya que en la práctica los archivos pueden llegar nombrados
    de cualquiera de las dos formas, por ejemplo:
        - reporte-autorizacion-987.pdf
        - reporte_autorizacion_1394984.pdf
        - reporte_autorizacion-987.pdf
    """
    nombre_normalizado = nombre_sin_extension.replace("_", "-")
    return "reporte-autorizacion" in nombre_normalizado


def _termina_en_menos_1(nombre_sin_extension: str) -> bool:
    """
    Detecta archivos que terminan en '-1' (ej: Scanner123-1.pdf).
    También acepta el equivalente con guion bajo (Scanner123_1.pdf).
    """
    nombre_normalizado = nombre_sin_extension.replace("_", "-")
    return nombre_normalizado.endswith("-1")


def _termina_en_menos_2(nombre_sin_extension: str) -> bool:
    """
    Detecta archivos de tipo "Órdenes", que pueden venir como:
        - Scanner123-2.pdf        (una sola orden)
        - Scanner123-2-3.pdf      (dos órdenes, páginas 2 a 3)
        - Scanner123-2-3-4.pdf    (o cualquier cantidad de órdenes pegadas)
    También acepta el equivalente con guion bajo (Scanner123_2.pdf, etc.).
    """
    nombre_normalizado = nombre_sin_extension.replace("_", "-")
    return bool(_PATRON_ORDENES.search(nombre_normalizado))


def _es_seguridad_social(nombre_sin_extension: str) -> bool:
    """
    Detecta el archivo de Seguridad Social, que siempre llega nombrado
    empezando por "SGS" (ej: SGS_900926475_.pdf, SGS-1394984.pdf, etc.).
    Este archivo no se divide ni tiene páginas de Acta/Órdenes: solo se
    "renombra a sí mismo" para garantizar que siempre quede con el NIT
    configurado y el formato final SGS_<NIT>_.pdf.
    """
    return nombre_sin_extension.startswith("sgs")


REGLAS_RENOMBRADO = [
    {"prefijo": "PDE", "coincide": _es_reporte_autorizacion},
    {"prefijo": "SGS", "coincide": _es_seguridad_social},
    {"prefijo": "CRC", "coincide": _termina_en_menos_1},
    {"prefijo": "OPF", "coincide": _termina_en_menos_2},
]


def obtener_nombre_destino(nombre_archivo: str) -> str | None:
    """
    Dado el nombre de un archivo PDF (con extensión), determina cuál
    debería ser su nuevo nombre según las reglas definidas.

    Retorna None si el archivo no coincide con ninguna regla, en cuyo
    caso el archivo NO debe tocarse.
    """
    ruta = Path(nombre_archivo)
    nombre_sin_extension = ruta.stem.lower()

    for regla in REGLAS_RENOMBRADO:
        if regla["coincide"](nombre_sin_extension):
            return f"{regla['prefijo']}_{NIT}_.pdf"

    return None


# =============================================================================
# PROCESO PRINCIPAL DE RENOMBRADO
# =============================================================================

def procesar_carpeta_principal(
    carpeta_principal: str,
    log_callback,
    progress_callback,
    counters_callback,
    detener_flag=None,
):
    """
    Recorre todas las subcarpetas de `carpeta_principal` y renombra los
    archivos PDF encontrados según las reglas de negocio.

    Parámetros
    ----------
    carpeta_principal : str
        Ruta de la carpeta principal que contiene las subcarpetas de
        autorizaciones.
    log_callback : callable(str)
        Función que recibe un mensaje de texto para mostrar en el log.
    progress_callback : callable(actual: int, total: int)
        Función que recibe el progreso actual (para la barra de progreso).
    counters_callback : callable(carpetas: int, renombrados: int, errores: int)
        Función que recibe los contadores actualizados en cada paso.
    detener_flag : threading.Event, opcional
        Si se provee y su método is_set() retorna True, el proceso se
        detiene de forma segura (permite cancelar desde la GUI).

    Retorna
    -------
    dict con las llaves: 'carpetas', 'renombrados', 'errores'
    """
    resultados = {"carpetas": 0, "renombrados": 0, "errores": 0}

    ruta_principal = Path(carpeta_principal)

    if not ruta_principal.exists() or not ruta_principal.is_dir():
        log_callback(f"⚠ La carpeta seleccionada no existe: {carpeta_principal}")
        return resultados

    # Solo se listan las subcarpetas directas (cada una es una autorización)
    subcarpetas = sorted([f for f in ruta_principal.iterdir() if f.is_dir()])
    total_subcarpetas = len(subcarpetas)

    if total_subcarpetas == 0:
        log_callback("⚠ No se encontraron subcarpetas dentro de la carpeta seleccionada.")
        return resultados

    for indice, subcarpeta in enumerate(subcarpetas, start=1):
        # Permite cancelar el proceso desde la interfaz si el usuario lo desea
        if detener_flag is not None and detener_flag.is_set():
            log_callback("⏹ Proceso detenido por el usuario.")
            break

        resultados["carpetas"] += 1
        log_callback(f"\n✔ {subcarpeta.name}")

        try:
            # Busca todos los PDF de la subcarpeta (case-insensitive)
            archivos_pdf = [
                f for f in subcarpeta.iterdir()
                if f.is_file() and f.suffix.lower() == ".pdf"
            ]
        except Exception as error:
            log_callback(f"  ⚠ Error leyendo la carpeta '{subcarpeta.name}': {error}")
            resultados["errores"] += 1
            progress_callback(indice, total_subcarpetas)
            counters_callback(**resultados)
            continue

        for archivo in archivos_pdf:
            try:
                nombre_destino = obtener_nombre_destino(archivo.name)

                # Si no coincide con ninguna regla, se ignora el archivo
                if nombre_destino is None:
                    continue

                ruta_destino = subcarpeta / nombre_destino

                # CASO ESPECIAL: el archivo YA tiene el nombre final correcto
                # (ej. el archivo de Seguridad Social suele llegar así desde
                # el origen). No es un error ni un conflicto: simplemente no
                # hay nada que renombrar.
                if archivo.name.lower() == nombre_destino.lower():
                    prefijo = nombre_destino.split("_")[0]
                    log_callback(f"  {prefijo} ya tenía el nombre correcto")
                    continue

                # SEGURIDAD: nunca sobrescribir un archivo existente
                if ruta_destino.exists():
                    prefijo = nombre_destino.split("_")[0]
                    log_callback(f"  ⚠ {prefijo} ya existía, no se sobrescribió")
                    resultados["errores"] += 1
                    continue

                archivo.rename(ruta_destino)
                prefijo = nombre_destino.split("_")[0]
                log_callback(f"  {prefijo} renombrado")
                resultados["renombrados"] += 1

            except Exception as error:
                # Nunca se detiene el proceso por un error individual
                log_callback(f"  ⚠ Error con el archivo '{archivo.name}': {error}")
                resultados["errores"] += 1

        progress_callback(indice, total_subcarpetas)
        counters_callback(**resultados)

    return resultados
