"""Crea el primer administrador. Ejecutar una sola vez: python crear_admin.py"""
import db

CORREO = "admin@gmail.com"
PASSWORD = "admin123"          # cámbiala después

usuario = db.consultar(
    """INSERT INTO usuarios (nombre_completo, correo, contrasena_hash, rol)
       VALUES (%s, %s, %s, 'admin') RETURNING id_usuario""",
    ("Administrador", CORREO, db.hash_contrasena(PASSWORD)), uno=True)

db.ejecutar("INSERT INTO empleados (id_usuario, cargo) VALUES (%s, 'Administrador')",
            (usuario["id_usuario"],))
print(f"Admin creado: {CORREO} / {PASSWORD}")