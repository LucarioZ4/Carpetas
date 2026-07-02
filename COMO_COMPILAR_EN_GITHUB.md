# Cómo generar el .exe sin instalar Python (usando GitHub)

Esta guía te permite obtener el archivo `DAZALUD_CARPETAS.exe` sin instalar
absolutamente nada en tu computador. GitHub compila el programa por ti, en
una máquina Windows en la nube (gratis), y tú solo descargas el resultado.

---

## Paso 1: Crear una cuenta de GitHub (si no tienes una)

1. Entra a https://github.com/signup
2. Crea una cuenta gratuita con tu correo.

## Paso 2: Crear un repositorio nuevo

1. Ya iniciada sesión, entra a https://github.com/new
2. En "Repository name" escribe: `dazalud-carpetas`
3. Puedes dejarlo como **Private** (privado) si no quieres que otros lo vean.
4. Clic en **"Create repository"**.

## Paso 3: Subir los archivos del proyecto

En la página del repositorio recién creado:

1. Clic en el enlace **"uploading an existing file"** (o el botón
   **"Add file" -> "Upload files"**).
2. Arrastra **TODOS** los archivos y carpetas del proyecto que te entregué:
   - `main.py`
   - `interfaz.py`
   - `funciones.py`
   - `divisor.py`
   - `requirements.txt`
   - `icono.ico`
   - `compilar_exe.bat`
   - `README.md`
   - La carpeta `.github` completa (incluye el archivo que compila el .exe
     automáticamente). **Importante:** si al arrastrar la carpeta `.github`
     GitHub no la reconoce por empezar con un punto, sube el archivo
     `.github/workflows/build-exe.yml` manualmente, respetando esa misma
     ruta de carpetas (puedes escribir la ruta completa en el cuadro de
     texto que aparece al subir el archivo).
3. Baja hasta el final de la página y clic en **"Commit changes"**.

## Paso 4: Ver cómo se compila automáticamente

1. En el repositorio, ve a la pestaña **"Actions"** (arriba, junto a "Code").
2. Verás una ejecución llamada **"Compilar DAZALUD CARPETAS (.exe)"** ya
   corriendo (se dispara sola al subir los archivos). Si no aparece
   automáticamente, haz clic en el flujo de trabajo a la izquierda y luego
   en el botón **"Run workflow"**.
3. Espera unos 2-4 minutos mientras el ícono amarillo (en progreso) cambia
   a un check verde ✅ (completado).

## Paso 5: Descargar el .exe

1. Haz clic sobre la ejecución ya terminada (la que tiene el check verde).
2. Baja hasta la sección **"Artifacts"**, al final de la página.
3. Haz clic en **"DAZALUD_CARPETAS-exe"** para descargar un archivo `.zip`.
4. Descomprime ese `.zip`: adentro está `DAZALUD_CARPETAS.exe`, listo para
   usar. Puedes copiarlo a cualquier computador con Windows y ejecutarlo
   con doble clic — no necesita tener Python instalado.

---

## ¿Y si actualizo el código más adelante?

Cada vez que subas cambios a los archivos del repositorio (por ejemplo, si
te envío una corrección), el flujo se vuelve a ejecutar solo y genera un
`.exe` nuevo automáticamente en la pestaña "Actions". Solo repites el
Paso 5 para descargar la versión más reciente.

## ¿Qué pasa si algo falla en la compilación?

Haz clic en la ejecución fallida (ícono ❌) y luego en el paso que falló
para ver el detalle del error en texto. Copia ese mensaje y compártelo para
poder ayudarte a corregirlo.
