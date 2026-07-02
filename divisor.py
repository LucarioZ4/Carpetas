# -*- coding: utf-8 -*-
"""
divisor.py
-----------
Módulo con la lógica para DIVIDIR un PDF "combinado" en dos archivos,
según el flujo real de escaneo en serie de la IPS:

    El escáner produce UN solo PDF por lote con todas las páginas juntas:
        - Página 1              -> el Acta
        - Páginas 2 en adelante -> las Órdenes de medicamento (pegadas,
                                    sin importar si son 1, 2, 3, 4... páginas)

    Este módulo divide ese PDF combinado en:
        - "<serial>-1.pdf"        -> solo el Acta (página 1)
        - "<serial>-2.pdf"        -> si hay UNA sola página de órdenes
        - "<serial>-2-N.pdf"      -> si hay VARIAS páginas de órdenes,
                                      donde N es el número de la última
                                      página del PDF original.

    Estos archivos generados con sufijo "-1" y "-2"/"-2-N" son justamente
    los que luego reconoce el módulo `funciones.py` para renombrarlos a
    CRC_<NIT>.pdf y OPF_<NIT>.pdf respectivamente.

Al igual que `funciones.py`, este módulo no depende de Tkinter: recibe
callbacks (log_callback, progress_callback, counters_callback) desde la
interfaz gráfica, lo que lo mantiene desacoplado y fácil de probar.
"""

import re
from pathlib import Path

from pypdf import PdfReader, PdfWriter


# =============================================================================
# DETECCIÓN DE ARCHIVOS "CANDIDATOS" A DIVIDIR
# =============================================================================
# Un PDF es candidato a dividir cuando NO ha sido ya procesado por este
# módulo ni por el de renombrado. Es decir, se descartan:
#   - Archivos que ya terminan en "-<numero>" o "-<numero>-<numero>..."
#     (ya fueron divididos antes: serial-1.pdf, serial-2.pdf, serial-2-3.pdf)
#   - Archivos que ya fueron renombrados: CRC_*.pdf, OPF_*.pdf, PDE_*.pdf,
#     SGS_*.pdf
#   - Archivos de tipo "reporte-autorizacion" / "reporte_autorizacion"
#     (esos no se dividen, se renombran directamente a PDE)
#   - Archivos de Seguridad Social (empiezan por "SGS"): no son un PDF
#     combinado de Acta+Órdenes, así que nunca deben dividirse.
# =============================================================================

_PREFIJOS_YA_RENOMBRADOS = ("crc-", "opf-", "pde-", "sgs-")
_PATRON_SUFIJO_NUMERICO = re.compile(r"-\d+(-\d+)*$")


def es_candidato_para_dividir(nombre_archivo: str) -> bool:
    """
    Determina si un archivo PDF es el "combinado" (acta + órdenes) que
    debe dividirse, o si por el contrario debe ignorarse porque ya fue
    dividido/renombrado previamente, o porque es un tipo de archivo que
    no participa en este proceso (por ejemplo, un reporte de autorización).
    """
    ruta = Path(nombre_archivo)

    if ruta.suffix.lower() != ".pdf":
        return False

    stem_normalizado = ruta.stem.lower().replace("_", "-")

    # Ya fue renombrado a su forma final (CRC_/OPF_/PDE_...)
    if stem_normalizado.startswith(_PREFIJOS_YA_RENOMBRADOS):
        return False

    # Es un reporte de autorización: no se divide, se renombra directo a PDE
    if "reporte-autorizacion" in stem_normalizado:
        return False

    # Ya tiene sufijo tipo "-1", "-2", "-2-3", etc. -> ya fue dividido antes
    if _PATRON_SUFIJO_NUMERICO.search(stem_normalizado):
        return False

    return True


# =============================================================================
# DIVISIÓN DE UN SOLO ARCHIVO
# =============================================================================

def dividir_pdf_individual(ruta_pdf: Path, log_callback) -> dict:
    """
    Divide un único PDF combinado en Acta (-1) y Órdenes (-2 o -2-N).

    Retorna un diccionario:
        {"dividido": bool, "advertencia": bool}
    """
    resultado = {"dividido": False, "advertencia": False}

    # ---- Lectura del PDF original -------------------------------------
    try:
        lector = PdfReader(str(ruta_pdf))
        total_paginas = len(lector.pages)
    except Exception as error:
        log_callback(f"  ⚠ No se pudo leer '{ruta_pdf.name}': {error}")
        resultado["advertencia"] = True
        return resultado

    if total_paginas == 0:
        log_callback(f"  ⚠ '{ruta_pdf.name}' no tiene páginas legibles, se omite")
        resultado["advertencia"] = True
        return resultado

    serial = ruta_pdf.stem
    carpeta = ruta_pdf.parent

    nombre_acta = f"{serial}-1.pdf"
    ruta_acta = carpeta / nombre_acta

    # =====================================================================
    # CASO A: el PDF solo tiene 1 página -> solo hay Acta, no hay Órdenes
    # =====================================================================
    if total_paginas == 1:
        if ruta_acta.exists():
            log_callback(f"  ⚠ {nombre_acta} ya existía, no se sobrescribió")
            log_callback(f"  ⚠ No se eliminó el original '{ruta_pdf.name}' por seguridad")
            resultado["advertencia"] = True
            return resultado

        try:
            escritor = PdfWriter()
            escritor.add_page(lector.pages[0])
            with open(ruta_acta, "wb") as salida:
                escritor.write(salida)
            log_callback(f"  Dividido: {nombre_acta}  (solo Acta, sin Órdenes)")
        except Exception as error:
            log_callback(f"  ⚠ Error creando {nombre_acta}: {error}")
            resultado["advertencia"] = True
            return resultado

        _eliminar_original(ruta_pdf, log_callback)
        resultado["dividido"] = True
        return resultado

    # =====================================================================
    # CASO B: hay Acta (página 1) + Órdenes (páginas 2..N)
    # =====================================================================
    paginas_ordenes = total_paginas - 1

    if paginas_ordenes == 1:
        nombre_ordenes = f"{serial}-2.pdf"
    else:
        nombre_ordenes = f"{serial}-2-{total_paginas}.pdf"

    ruta_ordenes = carpeta / nombre_ordenes

    # SEGURIDAD: nunca sobrescribir archivos destino ya existentes
    hay_conflicto = False
    if ruta_acta.exists():
        log_callback(f"  ⚠ {nombre_acta} ya existía, no se sobrescribió")
        hay_conflicto = True
    if ruta_ordenes.exists():
        log_callback(f"  ⚠ {nombre_ordenes} ya existía, no se sobrescribió")
        hay_conflicto = True

    if hay_conflicto:
        log_callback(f"  ⚠ No se eliminó el original '{ruta_pdf.name}' por seguridad")
        resultado["advertencia"] = True
        return resultado

    try:
        # -- Escribe el Acta (página 1) --
        escritor_acta = PdfWriter()
        escritor_acta.add_page(lector.pages[0])
        with open(ruta_acta, "wb") as salida:
            escritor_acta.write(salida)

        # -- Escribe las Órdenes (páginas 2..N, todas juntas) --
        escritor_ordenes = PdfWriter()
        for pagina in lector.pages[1:]:
            escritor_ordenes.add_page(pagina)
        with open(ruta_ordenes, "wb") as salida:
            escritor_ordenes.write(salida)

        log_callback(
            f"  Dividido: {nombre_acta}  (Acta)  +  {nombre_ordenes}  "
            f"({paginas_ordenes} página(s) de Órdenes)"
        )
    except Exception as error:
        log_callback(f"  ⚠ Error dividiendo '{ruta_pdf.name}': {error}")
        resultado["advertencia"] = True
        return resultado

    _eliminar_original(ruta_pdf, log_callback)
    resultado["dividido"] = True
    return resultado


def _eliminar_original(ruta_pdf: Path, log_callback):
    """Elimina el PDF combinado original una vez dividido exitosamente."""
    try:
        ruta_pdf.unlink()
    except Exception as error:
        log_callback(f"  ⚠ No se pudo eliminar el original '{ruta_pdf.name}': {error}")


# =============================================================================
# PROCESO PRINCIPAL: RECORRE TODAS LAS SUBCARPETAS
# =============================================================================

def dividir_carpeta_principal(
    carpeta_principal: str,
    log_callback,
    progress_callback,
    counters_callback,
    detener_flag=None,
):
    """
    Recorre todas las subcarpetas de `carpeta_principal` y divide el PDF
    combinado (Acta + Órdenes) que encuentre en cada una.

    Firma de callbacks idéntica a `funciones.procesar_carpeta_principal`,
    pero counters_callback recibe las llaves: carpetas, divididos, errores.
    """
    resultados = {"carpetas": 0, "divididos": 0, "errores": 0}

    ruta_principal = Path(carpeta_principal)

    if not ruta_principal.exists() or not ruta_principal.is_dir():
        log_callback(f"⚠ La carpeta seleccionada no existe: {carpeta_principal}")
        return resultados

    subcarpetas = sorted([f for f in ruta_principal.iterdir() if f.is_dir()])
    total_subcarpetas = len(subcarpetas)

    if total_subcarpetas == 0:
        log_callback("⚠ No se encontraron subcarpetas dentro de la carpeta seleccionada.")
        return resultados

    for indice, subcarpeta in enumerate(subcarpetas, start=1):
        if detener_flag is not None and detener_flag.is_set():
            log_callback("⏹ Proceso detenido por el usuario.")
            break

        resultados["carpetas"] += 1
        log_callback(f"\n✔ {subcarpeta.name}")

        try:
            candidatos = [
                f for f in subcarpeta.iterdir()
                if f.is_file() and es_candidato_para_dividir(f.name)
            ]
        except Exception as error:
            log_callback(f"  ⚠ Error leyendo la carpeta '{subcarpeta.name}': {error}")
            resultados["errores"] += 1
            progress_callback(indice, total_subcarpetas)
            counters_callback(**resultados)
            continue

        if not candidatos:
            log_callback("  (No se encontró un PDF combinado para dividir)")

        for candidato in candidatos:
            resultado_archivo = dividir_pdf_individual(candidato, log_callback)
            if resultado_archivo["dividido"]:
                resultados["divididos"] += 1
            if resultado_archivo["advertencia"]:
                resultados["errores"] += 1

        progress_callback(indice, total_subcarpetas)
        counters_callback(**resultados)

    return resultados
