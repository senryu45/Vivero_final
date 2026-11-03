"""Conexión y utilidades de PostgreSQL (viveros_db)."""
import os
import secrets
from contextlib import closing

import bcrypt
import psycopg2
import psycopg2.errors
from psycopg2.extras import RealDictCursor

CONFIG = {
    "host":     os.getenv("DB_HOST", "localhost"),
    "port":     int(os.getenv("DB_PORT", "5432")),
    "dbname":   os.getenv("DB_NAME", "vivero_db"),
    "user":     os.getenv("DB_USER", "postgres"),
    "password": os.getenv("DB_PASSWORD", "1234"),   # <-- cámbiala
}

# Texto de la pantalla de roles -> valor del ENUM rol_usuario
ROLES = {
    "Administrador": "admin",
    "Personal": "vendedor",
    "Cliente": "cliente",
}


class CorreoDuplicado(Exception):
    """El correo ya existe en la tabla usuarios."""


def conectar():
    return psycopg2.connect(**CONFIG)


def consultar(sql, params=None, uno=False):
    """SELECT (o INSERT ... RETURNING). Devuelve lista de dicts, o un dict/None si uno=True."""
    with closing(conectar()) as con:
        with con, con.cursor(cursor_factory=RealDictCursor) as cur:   # 'with con' hace commit
            cur.execute(sql, params)
            return cur.fetchone() if uno else cur.fetchall()


def ejecutar(sql, params=None):
    """INSERT / UPDATE / DELETE. Devuelve las filas afectadas."""
    with closing(conectar()) as con:
        with con, con.cursor() as cur:
            cur.execute(sql, params)
            return cur.rowcount


def hash_contrasena(texto):
    return bcrypt.hashpw(texto.encode(), bcrypt.gensalt()).decode()


def validar_login(correo, contrasena, rol_pantalla):
    """Devuelve (usuario, error). error es None, 'credenciales' o 'rol'."""
    u = consultar(
        """SELECT id_usuario, nombre_completo, correo, contrasena_hash, rol
           FROM usuarios
           WHERE lower(correo) = lower(%s) AND activo""",
        (correo.strip(),), uno=True)
    if not u or not bcrypt.checkpw(contrasena.encode(), u["contrasena_hash"].encode()):
        return None, "credenciales"
    if u["rol"] != ROLES.get(rol_pantalla, rol_pantalla):
        return None, "rol"
    return u, None


def registrar_cliente(nombre, correo, contrasena, telefono=None):
    """Crea el usuario (rol cliente) y su fila en clientes en UNA transacción.

    Si algo falla, no se guarda nada. Lanza CorreoDuplicado si el correo ya existe.
    """
    con = conectar()
    try:
        with con:                                   # commit al salir, rollback si hay error
            with con.cursor() as cur:
                cur.execute(
                    """INSERT INTO usuarios (nombre_completo, correo, contrasena_hash,
                                             rol, telefono)
                       VALUES (%s, %s, %s, 'cliente', %s)
                       RETURNING id_usuario""",
                    (nombre.strip(), correo.strip(), hash_contrasena(contrasena),
                     telefono or None))
                id_usuario = cur.fetchone()[0]
                cur.execute("INSERT INTO clientes (id_usuario) VALUES (%s)",
                            (id_usuario,))
    except psycopg2.errors.UniqueViolation:
        raise CorreoDuplicado()
    finally:
        con.close()


def registrar_empleado(nombre, correo, contrasena, cargo=None, salario=None, telefono=None):
    """Crea el usuario (rol vendedor) y su fila en empleados en UNA transacción.

    Lanza CorreoDuplicado si el correo ya existe.
    """
    con = conectar()
    try:
        with con:
            with con.cursor() as cur:
                cur.execute(
                    """INSERT INTO usuarios (nombre_completo, correo, contrasena_hash,
                                             rol, telefono)
                       VALUES (%s, %s, %s, 'vendedor', %s)
                       RETURNING id_usuario""",
                    (nombre.strip(), correo.strip(), hash_contrasena(contrasena),
                     telefono or None))
                id_usuario = cur.fetchone()[0]
                cur.execute(
                    "INSERT INTO empleados (id_usuario, cargo, salario) VALUES (%s, %s, %s)",
                    (id_usuario, cargo or None, salario))
    except psycopg2.errors.UniqueViolation:
        raise CorreoDuplicado()
    finally:
        con.close()

class EmpleadoConRegistros(Exception):
    """El empleado tiene ventas u otros registros y no se puede borrar."""


def actualizar_empleado(id_usuario, nombre, correo, contrasena=None,
                        cargo=None, salario=None, telefono=None):
    """Actualiza usuarios + empleados en UNA transacción (solo rol vendedor).

    Si contrasena viene vacía se conserva la actual.
    Lanza CorreoDuplicado si el correo ya lo usa otra cuenta.
    """
    con = conectar()
    try:
        with con:
            with con.cursor() as cur:
                if contrasena:
                    cur.execute(
                        """UPDATE usuarios
                           SET nombre_completo = %s, correo = %s, telefono = %s,
                               contrasena_hash = %s, fecha_actualizacion = CURRENT_TIMESTAMP
                           WHERE id_usuario = %s AND rol = 'vendedor'""",
                        (nombre.strip(), correo.strip(), telefono or None,
                         hash_contrasena(contrasena), id_usuario))
                else:
                    cur.execute(
                        """UPDATE usuarios
                           SET nombre_completo = %s, correo = %s, telefono = %s,
                               fecha_actualizacion = CURRENT_TIMESTAMP
                           WHERE id_usuario = %s AND rol = 'vendedor'""",
                        (nombre.strip(), correo.strip(), telefono or None, id_usuario))
                if cur.rowcount == 0:
                    raise LookupError("El empleado ya no existe o no es personal (vendedor).")
                cur.execute(
                    "UPDATE empleados SET cargo = %s, salario = %s WHERE id_usuario = %s",
                    (cargo or None, salario, id_usuario))
    except psycopg2.errors.UniqueViolation:
        raise CorreoDuplicado()
    finally:
        con.close()


def eliminar_empleado(id_usuario):
    """Borra empleados + usuarios en UNA transacción (solo rol vendedor).

    Lanza EmpleadoConRegistros si tiene ventas u otros datos ligados.
    Devuelve True si se borró, False si no existía.
    """
    con = conectar()
    try:
        with con:
            with con.cursor() as cur:
                cur.execute(
                    """DELETE FROM empleados
                       WHERE id_usuario = %s
                         AND id_usuario IN (SELECT id_usuario FROM usuarios
                                            WHERE rol = 'vendedor')""",
                    (id_usuario,))
                cur.execute("DELETE FROM usuarios WHERE id_usuario = %s AND rol = 'vendedor'",
                            (id_usuario,))
                return cur.rowcount > 0
    except psycopg2.errors.ForeignKeyViolation:
        raise EmpleadoConRegistros()
    finally:
        con.close()


# =====================================================================================
# Eliminación con permiso del administrador
# =====================================================================================
# tabla -> (columna id, nombre que se muestra). La tabla y la columna se insertan en el
# SQL, por eso SOLO se aceptan las de esta lista (nunca texto que venga de la interfaz).
TABLAS_ELIMINABLES = {
    "plantas":        ("id_planta", "Planta"),
    "plagas":         ("id_plaga", "Plaga"),
    "enfermedades":   ("id_enfermedad", "Enfermedad"),
    "capacitaciones": ("id_capacitacion", "Capacitación"),
}


class SolicitudDuplicada(Exception):
    """Ya hay una solicitud pendiente o aprobada de ese registro."""


class PermisoDenegado(Exception):
    """El administrador no ha aprobado la eliminación de ese registro."""


class RegistroEnUso(Exception):
    """El registro tiene datos ligados (por ejemplo ventas) y no se puede borrar."""


def _columna_id(tabla):
    if tabla not in TABLAS_ELIMINABLES:
        raise ValueError(f"Tabla no permitida: {tabla}")
    return TABLAS_ELIMINABLES[tabla][0]


def estado_solicitud(id_usuario, tabla, id_registro):
    """Estado de la solicitud MÁS RECIENTE del empleado para ese registro, o None."""
    _columna_id(tabla)
    fila = consultar(
        """SELECT estado FROM solicitudes_eliminacion
           WHERE id_solicitante = %s AND tabla = %s AND id_registro = %s
           ORDER BY id_solicitud DESC LIMIT 1""",
        (id_usuario, tabla, id_registro), uno=True)
    return fila["estado"] if fila else None


def crear_solicitud_eliminacion(id_usuario, tabla, id_registro, descripcion, motivo):
    """Registra una solicitud 'pendiente'. Lanza SolicitudDuplicada si ya hay una activa."""
    _columna_id(tabla)
    try:
        fila = consultar(
            """INSERT INTO solicitudes_eliminacion
                   (id_solicitante, tabla, id_registro, descripcion, motivo)
               VALUES (%s, %s, %s, %s, %s) RETURNING id_solicitud""",
            (id_usuario, tabla, id_registro, descripcion[:200], motivo.strip()), uno=True)
    except psycopg2.errors.UniqueViolation:
        raise SolicitudDuplicada()
    return fila["id_solicitud"]


def listar_solicitudes(estado=None, id_solicitante=None):
    """Solicitudes, de la más reciente a la más antigua. Filtros opcionales."""
    condiciones, params = [], []
    if estado:
        condiciones.append("s.estado = %s")
        params.append(estado)
    if id_solicitante is not None:
        condiciones.append("s.id_solicitante = %s")
        params.append(id_solicitante)
    donde = ("WHERE " + " AND ".join(condiciones)) if condiciones else ""
    return consultar(
        f"""SELECT s.id_solicitud, s.tabla, s.id_registro, s.descripcion, s.motivo,
                   s.estado, s.respuesta, u.nombre_completo AS solicitante,
                   to_char(s.fecha_solicitud, 'YYYY-MM-DD HH24:MI') AS fecha
            FROM solicitudes_eliminacion s
            JOIN usuarios u ON u.id_usuario = s.id_solicitante
            {donde}
            ORDER BY s.fecha_solicitud DESC""", params or None)


def contar_pendientes():
    fila = consultar("SELECT count(*) AS n FROM solicitudes_eliminacion WHERE estado = 'pendiente'",
                     uno=True)
    return fila["n"]


def resolver_solicitud(id_solicitud, id_admin, aprobar, respuesta=None):
    """El ADMINISTRADOR aprueba o rechaza una solicitud pendiente.

    Aprobar solo concede el permiso: el registro NO se borra aquí.
    Devuelve True si se resolvió, False si ya no estaba pendiente o quien llama no es admin.
    """
    filas = ejecutar(
        """UPDATE solicitudes_eliminacion
           SET estado = %s, id_admin = %s, respuesta = %s,
               fecha_resolucion = CURRENT_TIMESTAMP
           WHERE id_solicitud = %s AND estado = 'pendiente'
             AND EXISTS (SELECT 1 FROM usuarios
                         WHERE id_usuario = %s AND rol = 'admin' AND activo)""",
        ("aprobada" if aprobar else "rechazada", id_admin, respuesta or None,
         id_solicitud, id_admin))
    return filas > 0


def eliminar_con_permiso(id_usuario, tabla, id_registro):
    """Borra el registro SOLO si el administrador aprobó la solicitud de este empleado.

    El permiso es de un solo uso: al borrar, la solicitud pasa a 'ejecutada'.
    Todo ocurre en UNA transacción; si el borrado falla, el permiso se conserva.
    Lanza PermisoDenegado (sin aprobación) o RegistroEnUso (datos ligados).
    """
    columna = _columna_id(tabla)
    con = conectar()
    try:
        with con:
            with con.cursor() as cur:
                cur.execute(
                    """SELECT id_solicitud FROM solicitudes_eliminacion
                       WHERE id_solicitante = %s AND tabla = %s AND id_registro = %s
                         AND estado = 'aprobada'
                       FOR UPDATE""",
                    (id_usuario, tabla, id_registro))
                permiso = cur.fetchone()
                if permiso is None:
                    raise PermisoDenegado()
                cur.execute(f"DELETE FROM {tabla} WHERE {columna} = %s", (id_registro,))
                borrado = cur.rowcount > 0
                cur.execute(
                    """UPDATE solicitudes_eliminacion
                       SET estado = 'ejecutada', fecha_ejecucion = CURRENT_TIMESTAMP
                       WHERE id_solicitud = %s""", (permiso[0],))
                return borrado
    except psycopg2.errors.ForeignKeyViolation:
        raise RegistroEnUso()
    finally:
        con.close()


# =====================================================================================
# Recuperación de contraseña (código de 6 dígitos enviado al correo)
# =====================================================================================
VIGENCIA_CODIGO_MIN = 10        # minutos que dura el código
ESPERA_CODIGO_SEG = 60          # segundos mínimos entre un código y otro
MAX_INTENTOS_CODIGO = 5


class CodigoReciente(Exception):
    """Ya se envió un código hace menos de ESPERA_CODIGO_SEG segundos."""


def crear_codigo_recuperacion(correo, rol_pantalla):
    """Genera un código para la cuenta con ese correo y ese rol.

    Devuelve (codigo, usuario) o None si no existe una cuenta activa con ese correo y rol.
    Anula los códigos anteriores. Lanza CodigoReciente si se pidió otro hace poco.
    """
    rol = ROLES.get(rol_pantalla, rol_pantalla)
    con = conectar()
    try:
        with con:
            with con.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(
                    """SELECT id_usuario, nombre_completo, correo FROM usuarios
                       WHERE lower(correo) = lower(%s) AND rol = %s AND activo""",
                    (correo.strip(), rol))
                usuario = cur.fetchone()
                if usuario is None:
                    return None
                cur.execute(
                    """SELECT EXTRACT(EPOCH FROM (CURRENT_TIMESTAMP - max(fecha_creacion))) AS seg
                       FROM recuperacion_contrasena WHERE id_usuario = %s""",
                    (usuario["id_usuario"],))
                seg = cur.fetchone()["seg"]
                if seg is not None and seg < ESPERA_CODIGO_SEG:
                    raise CodigoReciente()
                cur.execute("UPDATE recuperacion_contrasena SET usado = TRUE "
                            "WHERE id_usuario = %s AND NOT usado", (usuario["id_usuario"],))
                codigo = f"{secrets.randbelow(10 ** 6):06d}"
                cur.execute(
                    """INSERT INTO recuperacion_contrasena (id_usuario, codigo_hash, expira)
                       VALUES (%s, %s, CURRENT_TIMESTAMP + (%s * INTERVAL '1 minute'))""",
                    (usuario["id_usuario"], hash_contrasena(codigo), VIGENCIA_CODIGO_MIN))
                return codigo, usuario
    finally:
        con.close()


def restablecer_contrasena(correo, rol_pantalla, codigo, nueva_contrasena):
    """Cambia la contraseña si el código es correcto, vigente y no usado.

    Devuelve 'ok', 'invalido' (incorrecto, vencido o inexistente) o 'bloqueado'
    (demasiados intentos fallidos: hay que pedir un código nuevo).
    """
    rol = ROLES.get(rol_pantalla, rol_pantalla)
    con = conectar()
    try:
        with con:
            with con.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(
                    """SELECT id_usuario FROM usuarios
                       WHERE lower(correo) = lower(%s) AND rol = %s AND activo""",
                    (correo.strip(), rol))
                usuario = cur.fetchone()
                if usuario is None:
                    return "invalido"
                cur.execute(
                    """SELECT id_recuperacion, codigo_hash, intentos,
                              expira < CURRENT_TIMESTAMP AS vencido
                       FROM recuperacion_contrasena
                       WHERE id_usuario = %s AND NOT usado
                       ORDER BY id_recuperacion DESC LIMIT 1 FOR UPDATE""",
                    (usuario["id_usuario"],))
                fila = cur.fetchone()
                if fila is None or fila["vencido"]:
                    return "invalido"
                if fila["intentos"] >= MAX_INTENTOS_CODIGO:
                    return "bloqueado"
                if not bcrypt.checkpw(codigo.encode(), fila["codigo_hash"].encode()):
                    cur.execute("UPDATE recuperacion_contrasena SET intentos = intentos + 1 "
                                "WHERE id_recuperacion = %s", (fila["id_recuperacion"],))
                    return "bloqueado" if fila["intentos"] + 1 >= MAX_INTENTOS_CODIGO else "invalido"
                cur.execute(
                    """UPDATE usuarios SET contrasena_hash = %s,
                                           fecha_actualizacion = CURRENT_TIMESTAMP
                       WHERE id_usuario = %s""",
                    (hash_contrasena(nueva_contrasena), usuario["id_usuario"]))
                cur.execute("UPDATE recuperacion_contrasena SET usado = TRUE "
                            "WHERE id_usuario = %s", (usuario["id_usuario"],))
                return "ok"
    finally:
        con.close()