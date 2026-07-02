# -*- coding: utf-8 -*-
"""
main.py
--------
Punto de entrada de la aplicación "DAZALUD CARPETAS".

La aplicación tiene dos módulos (pestañas):
    1. Dividir PDF        -> separa el PDF combinado (Acta + Órdenes)
    2. Renombrar soportes  -> asigna el nombre final (CRC/OPF/PDE)

Ejecutar en desarrollo:
    python main.py

Compilar a .exe (ver README.md para más detalle):
    pyinstaller --noconfirm --onefile --windowed --icon=icono.ico ^
        --name "DAZALUD_CARPETAS" ^
        --add-data "icono.ico;." ^
        main.py
"""

from interfaz import AplicacionPrincipal


def main():
    app = AplicacionPrincipal()
    app.mainloop()


if __name__ == "__main__":
    main()
