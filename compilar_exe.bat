@echo off
REM =============================================================
REM  compilar_exe.bat
REM  Script de conveniencia para compilar el proyecto a un .exe
REM  usando PyInstaller. Ejecutar desde la carpeta del proyecto.
REM =============================================================

echo Instalando/actualizando dependencias...
pip install -r requirements.txt

echo.
echo Compilando la aplicacion con PyInstaller...
pyinstaller --noconfirm --onefile --windowed ^
    --icon=icono.ico ^
    --name "DAZALUD_CARPETAS" ^
    --add-data "icono.ico;." ^
    main.py

echo.
echo =============================================================
echo  Listo. El ejecutable se encuentra en la carpeta dist\
echo  Archivo: dist\DAZALUD_CARPETAS.exe
echo =============================================================
pause
