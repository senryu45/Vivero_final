"""Validaciones compartidas: teléfono con selección de país.

Requiere:  pip install phonenumbers
"""
import os
import re
import socket

import phonenumbers

try:        # pip install email-validator  (revisa que el dominio exista y reciba correos)
    from email_validator import EmailNotValidError, EmailUndeliverableError, validate_email
except ImportError:         # sin la librería solo se revisa el formato y las listas
    validate_email = None
    EmailNotValidError = EmailUndeliverableError = Exception

# (nombre que ve el usuario, código ISO del país). Agrega o quita los que necesites.
PAISES = [
    ("México", "MX"), ("Estados Unidos", "US"), ("Canadá", "CA"),
    ("Guatemala", "GT"), ("Belice", "BZ"), ("El Salvador", "SV"),
    ("Honduras", "HN"), ("Nicaragua", "NI"), ("Costa Rica", "CR"),
    ("Panamá", "PA"), ("Cuba", "CU"), ("Rep. Dominicana", "DO"),
    ("Puerto Rico", "PR"), ("Colombia", "CO"), ("Venezuela", "VE"),
    ("Ecuador", "EC"), ("Perú", "PE"), ("Bolivia", "BO"), ("Chile", "CL"),
    ("Argentina", "AR"), ("Uruguay", "UY"), ("Paraguay", "PY"),
    ("Brasil", "BR"), ("España", "ES"), ("Portugal", "PT"), ("Francia", "FR"),
    ("Alemania", "DE"), ("Italia", "IT"), ("Reino Unido", "GB"),
    ("China", "CN"), ("Japón", "JP"), ("India", "IN"),
]

PAIS_POR_DEFECTO = "México (+52)"


def _etiqueta(nombre, region):
    return f"{nombre} (+{phonenumbers.country_code_for_region(region)})"


# Textos del menú desplegable: "México (+52)", "Estados Unidos (+1)", ...
ETIQUETAS_PAISES = [_etiqueta(n, r) for n, r in PAISES]
_REGION_POR_ETIQUETA = {_etiqueta(n, r): r for n, r in PAISES}


def region_de_etiqueta(etiqueta):
    """'México (+52)' -> 'MX'. Si no se reconoce, usa México."""
    return _REGION_POR_ETIQUETA.get(etiqueta, "MX")


def validar_telefono(texto, region="MX"):
    """Devuelve (telefono_e164, None) o (None, mensaje_de_error).

    texto:  lo que escribió la persona (puede traer espacios, guiones o paréntesis).
    region: país elegido en el menú ('MX', 'US', 'ES'...).
    El teléfono es opcional: texto vacío devuelve ("", None).
    Se guarda en formato internacional, por ejemplo +529621234567.
    """
    texto = texto.strip()
    if not texto:
        return "", None

    if not re.fullmatch(r"[0-9+() -]+", texto):
        return None, "El teléfono solo puede llevar números, espacios, guiones y paréntesis."

    codigo_pais = phonenumbers.country_code_for_region(region)
    try:
        if texto.startswith("+"):
            num = phonenumbers.parse(texto, None)          # ya trae su código de país
        else:
            num = phonenumbers.parse(texto, region)         # se interpreta según el país elegido
    except phonenumbers.NumberParseException:
        return None, "El teléfono no tiene un formato válido."

    if num.country_code != codigo_pais:
        return None, (f"El número empieza con +{num.country_code}, pero elegiste un país "
                      f"con código +{codigo_pais}. Cambia el país o corrige el número.")

    digitos = str(num.national_number)
    if region == "MX" and len(digitos) != 10:
        return None, "Un teléfono de México debe tener 10 dígitos."

    if not phonenumbers.is_valid_number(num):
        return None, "Ese número no existe en el plan de numeración del país elegido."

    # Descartar números de relleno: 5555555555, 1234567890, 9876543210...
    if len(digitos) >= 7 and (len(set(digitos)) <= 2
                              or digitos in "01234567890123456789"
                              or digitos in "98765432109876543210"):
        return None, "Escribe un número de teléfono real."

    return phonenumbers.format_number(num, phonenumbers.PhoneNumberFormat.E164), None


def separar_telefono(guardado):
    """'+529621234567' -> ('México (+52)', '9621234567'). Sirve para editar un registro."""
    if not guardado:
        return PAIS_POR_DEFECTO, ""
    try:
        num = phonenumbers.parse(guardado, None)
    except phonenumbers.NumberParseException:
        return PAIS_POR_DEFECTO, guardado
    region = phonenumbers.region_code_for_number(num)
    if region not in {r for _, r in PAISES}:
        region = next((r for _, r in PAISES
                       if phonenumbers.country_code_for_region(r) == num.country_code), None)
    if region is None:
        return PAIS_POR_DEFECTO, guardado          # país fuera de la lista: se deja tal cual
    nombre = next(n for n, r in PAISES if r == region)
    return _etiqueta(nombre, region), str(num.national_number)


def validar_contrasena(clave, confirmar=None):
    """Devuelve None si la contraseña es válida o el mensaje de error.

    Regla: mínimo 8 caracteres, con letras y números. Si se pasa 'confirmar', deben coincidir.
    """
    if len(clave) < 8 or not re.search(r"[A-Za-z]", clave) or not re.search(r"\d", clave):
        return "La contraseña debe tener mínimo 8 caracteres, con letras y números."
    if confirmar is not None and clave != confirmar:
        return "Las contraseñas no coinciden."
    return None


# =====================================================================================
# Correo electrónico (empleados y clientes)
# =====================================================================================
# Poner VERIFICAR_DOMINIO_CORREO=0 para saltarse la consulta DNS (por ejemplo, sin internet).
VERIFICAR_DOMINIO = os.getenv("VERIFICAR_DOMINIO_CORREO", "1") != "0"

_ETIQUETA = r"[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?"
_PATRON_CORREO = re.compile(
    rf"^[a-z0-9]+(?:[._+-][a-z0-9]+)*@(?:{_ETIQUETA}\.)+(?:[a-z]{{2,24}}|xn--[a-z0-9-]{{2,59}})$")

# Dominios de correo temporal / desechable
DOMINIOS_DESECHABLES = {
    "mailinator.com", "guerrillamail.com", "guerrillamail.net", "sharklasers.com",
    "10minutemail.com", "tempmail.com", "temp-mail.org", "yopmail.com", "trashmail.com",
    "getnada.com", "dispostable.com", "maildrop.cc", "throwawaymail.com", "fakeinbox.com",
    "mintemail.com", "mailnesia.com", "tempail.com", "emailondeck.com", "mohmal.com",
}
# Dominios de ejemplo o inexistentes
DOMINIOS_RESERVADOS = {
    "example.com", "example.org", "example.net", "test.com", "prueba.com", "ejemplo.com",
    "correo.com", "email.com", "mail.com.mx", "dominio.com", "midominio.com", "localhost",
}
SUFIJOS_RESERVADOS = (".test", ".invalid", ".local", ".localhost", ".example", ".lan", ".internal")

# Errores de escritura muy comunes -> dominio correcto
ERRORES_DOMINIO = {
    "gmial.com": "gmail.com", "gmai.com": "gmail.com", "gamil.com": "gmail.com",
    "gmail.con": "gmail.com", "gmail.cm": "gmail.com", "gnail.com": "gmail.com",
    "gmail.comm": "gmail.com", "gmali.com": "gmail.com", "gmaill.com": "gmail.com",
    "hotmial.com": "hotmail.com", "hotmai.com": "hotmail.com", "hotnail.com": "hotmail.com",
    "hotmail.con": "hotmail.com", "hotmal.com": "hotmail.com",
    "outlok.com": "outlook.com", "outlook.con": "outlook.com", "outloo.com": "outlook.com",
    "yahooo.com": "yahoo.com", "yaho.com": "yahoo.com", "yahoo.con": "yahoo.com",
    "icloud.con": "icloud.com", "iclod.com": "icloud.com", "live.con": "live.com",
}

# Parte antes de la @ que claramente no es de una persona real
USUARIOS_FALSOS = {
    "test", "tests", "prueba", "pruebas", "asdf", "asdfg", "asdfgh", "qwerty", "abc", "abcd",
    "abc123", "correo", "email", "ejemplo", "example", "nombre", "usuario", "user", "fake",
    "falso", "nadie", "xxx", "xyz", "none", "null", "noreply", "no-reply",
}


def _hay_internet():
    """True si se puede resolver un dominio conocido (para no culpar al correo si falla la red)."""
    try:
        socket.getaddrinfo("gmail.com", 443)
        return True
    except OSError:
        return False


def validar_correo(texto, verificar_dominio=True):
    """Devuelve (correo_normalizado, None) o (None, mensaje_de_error).

    Revisa, en orden: formato estricto, errores de escritura comunes (gmial.com),
    correos desechables o de ejemplo, usuarios falsos (test@, aaaa@) y, si está instalada la
    librería email-validator, que el dominio exista y reciba correos (consulta DNS/MX).
    verificar_dominio=False salta solo la consulta DNS.
    """
    correo = texto.strip().lower()
    if not correo:
        return None, "Escribe tu correo."
    if len(correo) > 254:
        return None, "El correo es demasiado largo (máximo 254 caracteres)."
    local, _, dominio = correo.partition("@")
    if len(local) > 64:
        return None, "La parte del correo antes de la @ es demasiado larga (máximo 64)."
    if not _PATRON_CORREO.match(correo):
        return None, "Escribe un correo válido, por ejemplo nombre@dominio.com."

    if dominio in ERRORES_DOMINIO:
        return None, (f"El dominio «{dominio}» parece un error de escritura. "
                      f"¿Quisiste decir {ERRORES_DOMINIO[dominio]}?")
    if dominio in DOMINIOS_DESECHABLES:
        return None, "No se aceptan correos temporales o desechables."
    if dominio in DOMINIOS_RESERVADOS or dominio.endswith(SUFIJOS_RESERVADOS):
        return None, "Ese dominio no corresponde a un correo real."
    if local in USUARIOS_FALSOS or (len(local) >= 3 and len(set(local)) == 1):
        return None, "Escribe tu correo real, no uno de prueba."

    if verificar_dominio and VERIFICAR_DOMINIO and validate_email is not None:
        try:
            validate_email(correo, check_deliverability=True)
        except EmailUndeliverableError:
            if _hay_internet():                     # sin internet no se puede comprobar: se acepta
                return None, (f"El dominio «{dominio}» no existe o no recibe correos. "
                              "Revisa que esté bien escrito.")
        except EmailNotValidError:
            return None, "Escribe un correo válido, por ejemplo nombre@dominio.com."
    return correo, None