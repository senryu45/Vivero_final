import re
import tkinter as tk
from tkinter import messagebox

import db
from comun import (ANCHO, ALTO, ANCHO_IZQ, FONDO_DERECHO, CAFE, CAFE_OSCURO,
                   CAFE_OSCURO_HOVER, BLANCO, TEXTO, FUENTE,
                   crear_panel_izquierdo, rectangulo_redondeado)

ANCHO_CAMPO, ALTO_CAMPO = 358, 46

patron_correo = re.compile(
    r"^[A-Za-z0-9._%+-]+@[A-Za-z0-9-]+(\.[A-Za-z0-9-]+)*\.[A-Za-z]{2,}$"
)


class CampoRedondeado(tk.Canvas):
    """Campo de texto con forma de píldora y texto de ayuda (placeholder)."""

    def __init__(self, master, placeholder, oculto=False, ancho=ANCHO_CAMPO):
        super().__init__(master, width=ancho, height=ALTO_CAMPO,
                         bg=FONDO_DERECHO, highlightthickness=0)
        self.ancho = ancho
        self.placeholder = placeholder
        self.oculto = oculto
        self.mostrando_placeholder = True

        rectangulo_redondeado(self, 0, 0, ancho, ALTO_CAMPO, CAFE)

        self.entrada = tk.Entry(self, bd=0, bg=CAFE, fg=BLANCO,
                                insertbackground=BLANCO, justify="center",
                                font=(FUENTE, 15), relief="flat",
                                highlightthickness=0)
        self.create_window(ancho / 2, ALTO_CAMPO / 2,
                           window=self.entrada, width=ancho - 50)

        self._poner_placeholder()
        self.entrada.bind("<FocusIn>", self._al_enfocar)
        self.entrada.bind("<FocusOut>", self._al_desenfocar)

    def _poner_placeholder(self):
        self.mostrando_placeholder = True
        self.entrada.config(show="")
        self.entrada.delete(0, tk.END)
        self.entrada.insert(0, self.placeholder)

    def _al_enfocar(self, _):
        if self.mostrando_placeholder:
            self.entrada.delete(0, tk.END)
            self.mostrando_placeholder = False
            if self.oculto:
                self.entrada.config(show="•")

    def _al_desenfocar(self, _):
        if not self.entrada.get():
            self._poner_placeholder()

    def valor(self):
        return "" if self.mostrando_placeholder else self.entrada.get()

    def limpiar(self):
        self._poner_placeholder()


class BotonRedondeado(tk.Canvas):
    """Botón con forma de píldora y efecto al pasar el mouse."""

    def __init__(self, master, texto, comando):
        super().__init__(master, width=ANCHO_CAMPO, height=ALTO_CAMPO,
                         bg=FONDO_DERECHO, highlightthickness=0, cursor="hand2")
        self.comando = comando
        rectangulo_redondeado(self, 0, 0, ANCHO_CAMPO, ALTO_CAMPO,
                              CAFE_OSCURO, tag="fondo")
        self.create_text(ANCHO_CAMPO / 2, ALTO_CAMPO / 2, text=texto,
                         fill=BLANCO, font=(FUENTE, 15))
        self.bind("<Enter>", lambda e: self.itemconfig("fondo", fill=CAFE_OSCURO_HOVER,
                                                       outline=CAFE_OSCURO_HOVER))
        self.bind("<Leave>", lambda e: self.itemconfig("fondo", fill=CAFE_OSCURO,
                                                       outline=CAFE_OSCURO))
        self.bind("<Button-1>", lambda e: self.comando())


class pantalla_login(tk.Frame):
    """Segunda pantalla: correo y contraseña para el rol elegido.

    al_entrar(correo, rol) se llama cuando las credenciales son correctas.
    al_volver() regresa a la selección de rol.
    al_registrar() abre el registro (solo se muestra para el rol Cliente).
    al_recuperar() abre la recuperación de contraseña (todos los roles).
    """

    def __init__(self, master, rol, al_entrar, al_volver, al_registrar=None, al_recuperar=None):
        super().__init__(master, width=ANCHO, height=ALTO, bg=FONDO_DERECHO)
        self.rol = rol
        self.al_entrar = al_entrar

        crear_panel_izquierdo(self)

        derecho = tk.Frame(self, bg=FONDO_DERECHO, width=ANCHO - ANCHO_IZQ, height=ALTO)
        derecho.place(x=ANCHO_IZQ, y=0)
        x_centro = (ANCHO - ANCHO_IZQ) / 2

        volver = tk.Label(derecho, text="← Cambiar rol", bg=FONDO_DERECHO, fg=TEXTO,
                          font=(FUENTE, 11), cursor="hand2")
        volver.place(x=24, y=20)
        volver.bind("<Button-1>", lambda e: al_volver())
        volver.bind("<Enter>", lambda e: volver.config(fg=CAFE))
        volver.bind("<Leave>", lambda e: volver.config(fg=TEXTO))

        tk.Label(derecho, text="Inicio de sesion", bg=FONDO_DERECHO, fg=CAFE,
                 font=(FUENTE, 26, "bold")).place(x=x_centro, y=98, anchor="center")
        tk.Label(derecho, text=f"Ingresando como: {rol}", bg=FONDO_DERECHO, fg=TEXTO,
                 font=(FUENTE, 12)).place(x=x_centro, y=135, anchor="center")

        self.campo_correo = CampoRedondeado(derecho, "CORREO")
        self.campo_correo.place(x=x_centro, y=195, anchor="center")

        self.campo_clave = CampoRedondeado(derecho, "CONTRASEÑA", oculto=True)
        self.campo_clave.place(x=x_centro, y=256, anchor="center")

        BotonRedondeado(derecho, "ENTRAR", self.iniciar_sesion).place(
            x=x_centro, y=347, anchor="center")

        # Enlace para recuperar la contraseña: todos los roles
        if al_recuperar is not None:
            olvido = tk.Label(derecho, text="¿Olvidaste tu contraseña?",
                              bg=FONDO_DERECHO, fg=TEXTO, font=(FUENTE, 11, "underline"),
                              cursor="hand2")
            olvido.place(x=x_centro, y=400, anchor="center")
            olvido.bind("<Button-1>", lambda e: al_recuperar())
            olvido.bind("<Enter>", lambda e: olvido.config(fg=CAFE))
            olvido.bind("<Leave>", lambda e: olvido.config(fg=TEXTO))

        # Enlace de registro: solo para clientes
        if al_registrar is not None and rol == "Cliente":
            crear = tk.Label(derecho, text="¿No tienes cuenta? Regístrate",
                             bg=FONDO_DERECHO, fg=TEXTO, font=(FUENTE, 11),
                             cursor="hand2")
            crear.place(x=x_centro, y=435, anchor="center")
            crear.bind("<Button-1>", lambda e: al_registrar())
            crear.bind("<Enter>", lambda e: crear.config(fg=CAFE))
            crear.bind("<Leave>", lambda e: crear.config(fg=TEXTO))

        # Enter inicia sesión (solo mientras esta pantalla existe)
        for campo in (self.campo_correo, self.campo_clave):
            campo.entrada.bind("<Return>", lambda e: self.iniciar_sesion())

    def iniciar_sesion(self):
        correo = self.campo_correo.valor().strip().lower()
        clave = self.campo_clave.valor()

        if not correo or not clave:
            messagebox.showwarning("Campos vacíos", "Escribe tu correo y contraseña.")
            return

        if not patron_correo.match(correo):
            messagebox.showwarning("Correo no válido", "Escribe un correo válido.")
            return

        # ---- Validación contra la base de datos ----
        try:
            usuario, error = db.validar_login(correo, clave, self.rol)
        except Exception as e:
            messagebox.showerror("Error de conexión",
                                 f"No se pudo consultar la base de datos:\n{e}")
            return

        if error == "credenciales":
            messagebox.showerror("Error", "Correo o contraseña incorrectos.")
            self.campo_clave.limpiar()
            return

        if error == "rol":
            messagebox.showerror(
                "Rol incorrecto",
                f"Esta cuenta no tiene el rol {self.rol}. Elige tu rol correcto.")
            self.campo_clave.limpiar()
            return

        self.al_entrar(usuario["correo"], self.rol)