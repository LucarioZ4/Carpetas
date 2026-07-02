# DAZALUD CARPETAS

Aplicación de escritorio para Windows (con interfaz gráfica en Tkinter) para
IPS que manejan escaneo en serie de actas y órdenes de medicamento. Tiene
**dos módulos** organizados en pestañas:

1. **Dividir PDF** — separa el PDF combinado que produce el escáner (Acta +
   Órdenes) en dos archivos independientes.
2. **Renombrar soportes** — recorre las subcarpetas de autorizaciones y
   renombra los PDF ya divididos a su nombre final (`CRC_`, `OPF_`, `PDE_`).

El flujo normal de trabajo es: **1) Dividir PDF → 2) Renombrar soportes**,
sobre la misma carpeta principal.

---

## 1. Estructura del proyecto

```
renombrador_pdf/
├── main.py            # Punto de entrada de la aplicación
├── interfaz.py         # Interfaz gráfica (Tkinter, con pestañas)
├── funciones.py         # Lógica de negocio: RENOMBRADO
├── divisor.py            # Lógica de negocio: DIVISIÓN de PDFs
├── requirements.txt     # Dependencias (pypdf + PyInstaller)
├── compilar_exe.bat    # Script para compilar el .exe en Windows
├── icono.ico             # Icono de la aplicación / del .exe
└── README.md              # Este archivo
```

## 2. Módulo 1: Dividir PDF (Acta + Órdenes)

### El problema que resuelve

El escáner trabaja en serie: primero se pone el **Acta** y después, pegadas,
las **Órdenes de medicamento** (pueden ser 1, 2, 3 o más). El escáner
entrega **un solo PDF combinado** con todas esas páginas juntas. Este módulo
separa ese PDF en dos:

| Contenido del PDF original                        | Archivo generado                        |
|-----------------------------------------------------|--------------------------------------------|
| Página 1 (Acta)                                       | `<serial>-1.pdf`                            |
| Páginas 2..N si solo hay **1** página de Órdenes     | `<serial>-2.pdf`                            |
| Páginas 2..N si hay **varias** páginas de Órdenes    | `<serial>-2-N.pdf` (N = última página)     |

Ejemplo con un PDF original `12839128394.pdf` de 3 páginas (1 Acta + 2
Órdenes):

```
12839128394.pdf (3 páginas)
        │
        ├── Página 1             -> 12839128394-1.pdf
        └── Páginas 2 y 3 juntas -> 12839128394-2-3.pdf
```

Si el PDF original solo tiene 2 páginas (1 Acta + 1 Orden):

```
123482138458.pdf (2 páginas)
        │
        ├── Página 1 -> 123482138458-1.pdf
        └── Página 2 -> 123482138458-2.pdf
```

### Qué archivos toma en cuenta

En cada subcarpeta, el módulo busca el **PDF combinado** (el que aún no ha
sido dividido ni renombrado) e ignora automáticamente:

- Archivos que ya terminan en `-1`, `-2`, `-2-3`, etc. (ya fueron divididos).
- Archivos que ya fueron renombrados (`CRC_...`, `OPF_...`, `PDE_...`).
- Archivos de tipo `reporte-autorizacion` / `reporte_autorizacion` (esos no
  se dividen; van directo al módulo de renombrado).

### Seguridad

- Si el archivo destino (`-1` o `-2`/`-2-N`) ya existe, **no se sobrescribe**
  y se muestra una advertencia (⚠) en el log.
- El PDF original **solo se elimina** si la división fue exitosa (ambos
  archivos nuevos se crearon sin conflictos). Si hubo algún conflicto, el
  original se conserva para revisión manual.
- Cualquier error individual se registra y **no detiene** el proceso general.

## 3. Módulo 2: Renombrar soportes

Dentro de cada subcarpeta se buscan archivos `.pdf` y se renombran así (el
NIT es configurable, ver sección 5):

| Coincidencia en el nombre original                            | Nuevo nombre     |
|-------------------------------------------------------------------|--------------------|
| Contiene `reporte-autorizacion` o `reporte_autorizacion`          | `PDE_<NIT>_.pdf`   |
| Termina en `-1`                                                     | `CRC_<NIT>_.pdf`   |
| Termina en `-2`, `-2-3`, `-2-3-4`... (una o varias Órdenes)         | `OPF_<NIT>_.pdf`   |
| Cualquier otro archivo                                               | No se modifica     |

Ejemplo con `NIT = 900926475`:

```
Autorizacion001/
├── 12839128394-1.pdf                -> CRC_900926475_.pdf
├── 12839128394-2-3.pdf              -> OPF_900926475_.pdf
└── reporte_autorizacion_1394984.pdf -> PDE_900926475_.pdf
```

### Seguridad

- Si el archivo destino ya existe, **no se sobrescribe**: se registra una
  advertencia (⚠) en el log y se continúa con el resto de archivos.
- Cualquier error individual se registra y **no detiene** el proceso general.
- Solo se tocan archivos con extensión `.pdf` (o `.PDF`).

## 4. Requisitos

- Python 3.9 o superior (recomendado 3.10+)
- Windows 10/11 (para ejecutar el `.exe` final)
- Tkinter (incluido por defecto en la instalación estándar de Python en
  Windows, no requiere instalación aparte)

## 5. Ejecutar en modo desarrollo

```bash
# 1. (Opcional) Crear entorno virtual
python -m venv venv
venv\Scripts\activate

# 2. Instalar dependencias
pip install -r requirements.txt

# 3. Ejecutar la aplicación
python main.py
```

## 6. Cambiar el NIT (para reutilizar en otra empresa)

Abrir `funciones.py` y modificar la constante al inicio del archivo:

```python
NIT = "900926475"
```

Cambiar ese valor por el NIT de la nueva empresa y volver a compilar. No es
necesario tocar ninguna otra parte del código (`divisor.py` no depende del
NIT, ya que solo divide archivos, no los renombra).

## 7. Compilar el ejecutable (.exe)

### Opción A: usando el script incluido

Desde Windows, dentro de la carpeta del proyecto:

```bat
compilar_exe.bat
```

### Opción B: comando manual de PyInstaller

```bash
pip install -r requirements.txt

pyinstaller --noconfirm --onefile --windowed ^
    --icon=icono.ico ^
    --name "DAZALUD_CARPETAS" ^
    --add-data "icono.ico;." ^
    main.py
```

> Nota: en Windows el separador para `--add-data` es `;`, mientras que en
> macOS/Linux sería `:` (este proyecto está pensado para Windows).

Al finalizar, el ejecutable quedará en:

```
dist\DAZALUD_CARPETAS.exe
```

Ese archivo `.exe` es autónomo (`--onefile`): puede copiarse y ejecutarse en
cualquier equipo Windows sin necesidad de tener Python instalado.

### Parámetros usados

- `--onefile`: empaqueta todo en un único `.exe`.
- `--windowed`: evita que se abra una consola negra detrás de la GUI.
- `--icon=icono.ico`: usa el ícono personalizado para el `.exe`.
- `--add-data "icono.ico;."`: incluye el ícono dentro del paquete para que
  la ventana también lo muestre en tiempo de ejecución.

## 8. Uso de la aplicación

1. Abrir la aplicación (`python main.py` o el `.exe` compilado).
2. En la pestaña **"1. Dividir PDF"**:
   - Clic en **"Seleccionar carpeta"** y elegir la carpeta principal.
   - Clic en **"Dividir PDF"** para separar los PDF combinados en Acta y
     Órdenes.
3. En la pestaña **"2. Renombrar soportes"**:
   - Selecciona la misma carpeta principal.
   - Clic en **"Renombrar soportes"** para asignar los nombres finales.
4. En cualquiera de las dos pestañas puedes observar en tiempo real:
   - La barra de progreso.
   - El contador de carpetas procesadas.
   - El contador de archivos divididos/renombrados.
   - El área de registro (log) con el detalle de cada operación.
5. Al finalizar aparece un resumen y puedes usar **"Abrir carpeta"** para
   revisar los resultados directamente en el explorador de Windows.

## 9. Notas de diseño del código

- `funciones.py` y `divisor.py` no dependen de Tkinter: contienen solo
  lógica pura, lo que facilita probarla o reutilizarla en otro contexto.
- `interfaz.py` define una clase reutilizable `PantallaProceso` que se usa
  para ambas pestañas (Dividir y Renombrar), evitando duplicar código de la
  interfaz. Cada pestaña recibe su propia función de procesamiento
  (`divisor.dividir_carpeta_principal` o
  `funciones.procesar_carpeta_principal`).
- El procesamiento se ejecuta en un **hilo secundario** (`threading.Thread`)
  por cada pestaña, para que la ventana no se congele mientras se procesan
  muchas carpetas. La comunicación entre el hilo y la interfaz se hace de
  forma segura mediante una `queue.Queue`.
- Todas las reglas de renombrado están centralizadas en
  `funciones.REGLAS_RENOMBRADO`, lo que permite agregar nuevas reglas en el
  futuro sin reescribir el resto del programa.
- La detección de archivos "candidatos" a dividir (`divisor.py`) y las
  reglas de renombrado (`funciones.py`) están sincronizadas: ambas
  reconocen el mismo patrón de sufijos (`-1`, `-2`, `-2-3`, `-2-3-4`...),
  para que el resultado de un módulo siempre sea compatible con el otro.
