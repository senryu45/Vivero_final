"""Recuperación de contraseña para cualquier rol (Administrador, Personal o Cliente).

Paso 1: la persona escribe su correo y se le envía un código de 6 dígitos.
Paso 2: escribe el código y su nueva contraseña.
"""
import re
import tkinter as tk
from tkinter import messagebox

import correo
import db
from comun import (ANCHO, ALTO, ANCHO_IZQ, FONDO_DERECHO, CAFE, TEXTO, FUENTE,
                   crear_panel_izquierdo)
from login import CampoRedondeado, BotonRedondeado, patron_correo
from validaciones import validar_contrasena


class pantalla_recuperar(tk.Frame):
    """al_terminar() se llama cuando la contraseña ya se cambió (vuelve al login).
    al_volver() regresa al login sin cambiar nada.
    """

    def __init__(self, master, rol, al_terminar, al_volver):
        super().__init__(master, width=ANCHO, height=ALTO, bg=FONDO_DERECHO)
        self.rol = rol
        self.al_terminar = al_terminar

        crear_panel_izquierdo(self)
        derecho = tk.Frame(self, bg=FONDO_DERECHO, width=ANCHO - ANCHO_IZQ, height=ALTO)
        derecho.place(x=ANCHO_IZQ, y=0)
        self.derecho = derecho
        self.x_centro = (ANCHO - ANCHO_IZQ) / 2

        volver = tk.Label(derecho, text="← Volver", bg=FONDO_DERECHO, fg=TEXTO,
                          font=(FUENTE, 11), cursor="hand2")
        volver.place(x=24, y=20)
        volver.bind("<Button-1>", lambda e: al_volver())
        volver.bind("<Enter>", lambda e: volver.config(fg=CAFE))
        volver.bind("<Leave>", lambda e: volver.config(fg=TEXTO))

        tk.Label(derecho, text="Recuperar contraseña", bg=FONDO_DERECHO, fg=CAFE,
                 font=(FUENTE, 24, "bold")).place(x=self.x_centro, y=62, anchor="center")
        tk.Label(derecho, text=f"Cuenta de: {rol}", bg=FONDO_DERECHO, fg=TEXTO,
                 font=(FUENTE, 12)).place(x=self.x_centro, y=98, anchor="center")

        # ---- Paso 1: correo ----
        self.campo_correo = CampoRedondeado(derecho, "CORREO")
        self.campo_correo.place(x=self.x_centro, y=160, anchor="center")
        self.btn_enviar = BotonRedondeado(derecho, "ENVIAR CÓDIGO", self.enviar_codigo)
        self.btn_enviar.place(x=self.x_centro, y=222, anchor="center")
        self.aviso = tk.Label(derecho, text="Te enviaremos un código de 6 dígitos al correo "
                                            "de tu cuenta.",
                              bg=FONDO_DERECHO, fg=TEXTO, font=(FUENTE, 9),
                              wraplength=340, justify="center")
        self.aviso.place(x=self.x_centro, y=250, anchor="n")

        # ---- Paso 2: código y nueva contraseña (se muestran al enviar el código) ----
        self.campo_codigo = CampoRedondeado(derecho, "CÓDIGO DE 6 DÍGITOS")
        self.campo_nueva = CampoRedondeado(derecho, "NUEVA CONTRASEÑA", oculto=True)
        self.campo_confirmar = CampoRedondeado(derecho, "CONFIRMAR CONTRASEÑA", oculto=True)
        self.btn_cambiar = BotonRedondeado(derecho, "CAMBIAR CONTRASEÑA", self.cambiar)
        self.nota = tk.Label(derecho, text="Mínimo 8 caracteres, con letras y números",
                             bg=FONDO_DERECHO, fg=TEXTO, font=(FUENTE, 9))
        self.paso2 = [(self.campo_codigo, 330), (self.campo_nueva, 384),
                      (self.campo_confirmar, 438), (self.btn_cambiar, 498),
                      (self.nota, 536)]

        self.campo_correo.entrada.bind("<Return>", lambda e: self.enviar_codigo())
        self.campo_codigo.entrada.bind("<Return>", lambda e: self.campo_nueva.entrada.focus_set())
        self.campo_nueva.entrada.bind("<Return>", lambda e: self.campo_confirmar.entrada.focus_set())
        self.campo_confirmar.entrada.bind("<Return>", lambda e: self.cambiar())

    # ---------------- Paso 1 ----------------
    def enviar_codigo(self):
        direccion = self.campo_correo.valor().strip().lower()
        if not direccion:
            messagebox.showwarning("Recuperar contraseña", "Escribe tu correo.")
            return
        if not patron_correo.match(direccion):
            messagebox.showwarning("Recuperar contraseña", "Escribe un correo válido.")
            return

        self.config(cursor="watch")
        self.update_idletasks()
        modo = None
        try:
            try:
                resultado = db.crear_codigo_recuperacion(direccion, self.rol)
            except db.CodigoReciente:
                resultado = None                      # ya se envió uno hace menos de 1 minuto
            if resultado:
                codigo, usuario = resultado
                modo = correo.enviar_codigo(usuario["correo"], usuario["nombre_completo"],
                                            codigo, db.VIGENCIA_CODIGO_MIN)
        except Exception as ex:
            self.config(cursor="")
            messagebox.showerror("Recuperar contraseña",
                                 f"No se pudo enviar el código:\n{ex}\n\n"
                                 "Espera un minuto e inténtalo de nuevo.")
            return
        self.config(cursor="")

        # Mismo mensaje exista o no la cuenta, para no revelar qué correos están registrados
        texto = (f"Si el correo pertenece a una cuenta de {self.rol}, te enviamos un código "
                 f"válido por {db.VIGENCIA_CODIGO_MIN} minutos. Si pediste uno hace menos de "
                 "un minuto, usa ese.")
        if modo == "consola":
            texto += "\n[Modo de pruebas: el código se mostró en la consola.]"
        self.aviso.config(text=texto)
        self._mostrar_paso2()

    def _mostrar_paso2(self):
        for widget, y in self.paso2:
            widget.place(x=self.x_centro, y=y, anchor="center")
        self.campo_codigo.entrada.focus_set()

    # ---------------- Paso 2 ----------------
    def cambiar(self):
        direccion = self.campo_correo.valor().strip().lower()
        codigo = self.campo_codigo.valor().strip()
        nueva = self.campo_nueva.valor()
        confirmar = self.campo_confirmar.valor()

        if not direccion or not codigo or not nueva or not confirmar:
            messagebox.showwarning("Recuperar contraseña", "Completa todos los campos.")
            return
        if not re.fullmatch(r"\d{6}", codigo):
            messagebox.showwarning("Recuperar contraseña", "El código tiene 6 dígitos.")
            return
        error = validar_contrasena(nueva, confirmar)
        if error:
            messagebox.showwarning("Recuperar contraseña", error)
            return

        try:
            estado = db.restablecer_contrasena(direccion, self.rol, codigo, nueva)
        except Exception as ex:
            messagebox.showerror("Error de base de datos", str(ex))
            return

        if estado == "ok":
            messagebox.showinfo("Recuperar contraseña",
                                "Tu contraseña se actualizó. Ya puedes iniciar sesión.")
            self.al_terminar()
        elif estado == "bloqueado":
            messagebox.showerror("Recuperar contraseña",
                                 "Demasiados intentos fallidos. Pide un código nuevo.")
            self.campo_codigo.limpiar()
        else:
            messagebox.showerror("Recuperar contraseña", "Código incorrecto o vencido.")
            self.campo_codigo.limpiar()