"""Envío del código de recuperación por correo (SMTP).

Se configura con variables de entorno:
    SMTP_HOST      servidor, por ejemplo smtp.gmail.com
    SMTP_PORT      587 (STARTTLS, por defecto) o 465 (SSL)
    SMTP_USER      usuario / correo que envía
    SMTP_PASSWORD  contraseña (en Gmail: "contraseña de aplicación")
    SMTP_FROM      remitente (opcional; por defecto SMTP_USER)

Si SMTP_HOST no está definido se trabaja en MODO DE PRUEBAS: el código se imprime en la
consola donde se ejecutó la app. Úsalo solo para desarrollar, no en producción.
"""
import os
import smtplib
import ssl
from email.message import EmailMessage


def configurado():
    return bool(os.getenv("SMTP_HOST"))


def enviar_codigo(destino, nombre, codigo, vigencia_min=10):
    """Envía el código. Devuelve 'correo' (enviado) o 'consola' (modo de pruebas)."""
    if not configurado():
        print(f"[MODO DE PRUEBAS] Código de recuperación para {destino}: {codigo}")
        return "consola"

    host = os.getenv("SMTP_HOST")
    puerto = int(os.getenv("SMTP_PORT", "587"))
    usuario = os.getenv("SMTP_USER", "")
    clave = os.getenv("SMTP_PASSWORD", "")
    remitente = os.getenv("SMTP_FROM", usuario)

    msg = EmailMessage()
    msg["Subject"] = "Vivero: código para recuperar tu contraseña"
    msg["From"] = remitente
    msg["To"] = destino
    msg.set_content(
        f"Hola {nombre},\n\n"
        f"Tu código para restablecer la contraseña es: {codigo}\n\n"
        f"Es válido por {vigencia_min} minutos y solo se puede usar una vez.\n"
        "Si no lo pediste tú, ignora este mensaje: tu contraseña no ha cambiado.\n")

    contexto = ssl.create_default_context()
    if puerto == 465:
        servidor = smtplib.SMTP_SSL(host, puerto, timeout=15, context=contexto)
    else:
        servidor = smtplib.SMTP(host, puerto, timeout=15)
    with servidor:
        if puerto != 465:
            servidor.starttls(context=contexto)
        if usuario:
            servidor.login(usuario, clave)
        servidor.send_message(msg)
    return "correo"