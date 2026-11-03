"""Plan B: restablece la contraseña de un ADMINISTRADOR desde la terminal.

Útil si el administrador no puede recibir el código por correo (por ejemplo, el correo de
la cuenta es de ejemplo). Se ejecuta en el equipo donde está la aplicación:
    python restablecer_admin.py
"""
from getpass import getpass

import db
from validaciones import validar_contrasena

correo = input("Correo del administrador: ").strip()
nueva = getpass("Nueva contraseña: ")
confirmar = getpass("Confirmar contraseña: ")

error = validar_contrasena(nueva, confirmar)
if error:
    raise SystemExit(error)

filas = db.ejecutar(
    """UPDATE usuarios SET contrasena_hash = %s, fecha_actualizacion = CURRENT_TIMESTAMP
       WHERE lower(correo) = lower(%s) AND rol = 'admin'""",
    (db.hash_contrasena(nueva), correo))
print("Contraseña actualizada." if filas else "No existe un administrador con ese correo.")