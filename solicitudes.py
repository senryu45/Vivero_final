"""Solicitudes de eliminación.

Empleado: pide permiso para borrar un registro (con un motivo) y, cuando el administrador
          lo aprueba, puede eliminarlo. Si no lo aprueba, el registro NO se puede borrar.
Administrador: ve las solicitudes y las aprueba o rechaza.
"""
import tkinter as tk
from tkinter import ttk, messagebox

import db

VERDE_OSCURO = "#3F5A1A"
FONDO_SECCION = "#C5C7B5"
CAFE = "#99553A"
ROJO = "#A63D2F"
GRIS = "#7A7A6E"
BLANCO = "#FFFFFF"
FUENTE = "Open Sans"

ESTADOS = {"pendiente": "Pendiente", "aprobada": "Aprobada",
           "rechazada": "Rechazada", "ejecutada": "Eliminado"}


def pedir_motivo(parent, titulo, resumen, etiqueta="Motivo", obligatorio=True):
    """Ventana modal para escribir un texto.

    Devuelve el texto escrito, o None si la persona cancela.
    (Con obligatorio=False puede devolver "" si se envía vacío.)
    """
    raiz = parent.winfo_toplevel()
    ventana = tk.Toplevel(raiz)
    ventana.title(titulo)
    ventana.configure(bg=FONDO_SECCION)
    ventana.resizable(False, False)
    ventana.transient(raiz)
    resultado = {"texto": None}

    tk.Label(ventana, text=resumen, bg=FONDO_SECCION, fg=VERDE_OSCURO, justify="left",
             wraplength=400, font=(FUENTE, 10)).pack(anchor="w", padx=18, pady=(16, 8))
    tk.Label(ventana, text=etiqueta, bg=FONDO_SECCION, fg=CAFE,
             font=(FUENTE, 10, "bold")).pack(anchor="w", padx=18)
    texto = tk.Text(ventana, width=50, height=5, wrap="word", relief="flat",
                    font=(FUENTE, 10), bg=BLANCO)
    texto.pack(padx=18, pady=(2, 10))

    def enviar():
        valor = texto.get("1.0", "end").strip()
        if obligatorio and len(valor) < 5:
            messagebox.showwarning(titulo, "Escribe un motivo (mínimo 5 caracteres).",
                                   parent=ventana)
            return
        resultado["texto"] = valor
        ventana.destroy()

    botones = tk.Frame(ventana, bg=FONDO_SECCION)
    botones.pack(fill="x", padx=18, pady=(0, 16))
    tk.Button(botones, text="Enviar", command=enviar, bg=VERDE_OSCURO, fg=BLANCO,
              relief="flat", padx=18, pady=4, font=(FUENTE, 10, "bold")).pack(side="right")
    tk.Button(botones, text="Cancelar", command=ventana.destroy, bg=GRIS, fg=BLANCO,
              relief="flat", padx=14, pady=4, font=(FUENTE, 10)).pack(side="right", padx=(0, 8))

    ventana.update_idletasks()
    x = raiz.winfo_rootx() + (raiz.winfo_width() - ventana.winfo_width()) // 2
    y = raiz.winfo_rooty() + (raiz.winfo_height() - ventana.winfo_height()) // 3
    ventana.geometry(f"+{max(x, 0)}+{max(y, 0)}")
    ventana.grab_set()
    texto.focus_set()
    ventana.wait_window()
    return resultado["texto"]


class Solicitudes(tk.Frame):
    """Sección SOLICITUDES (administrador y empleados)."""

    def __init__(self, master, datos=None):
        super().__init__(master, bg=FONDO_SECCION)
        self.datos = datos
        self.es_admin = datos is not None and datos["rol"] == "admin"
        self.id_usuario = datos["id_usuario"] if datos else None
        self.filas = {}                       # id_solicitud -> dict de la consulta

        # ---------------- Encabezado ----------------
        cabecera = tk.Frame(self, bg=FONDO_SECCION)
        cabecera.pack(fill="x", padx=24, pady=(16, 4))
        self.titulo = tk.Label(cabecera, text="Solicitudes de eliminación", bg=FONDO_SECCION,
                               fg=CAFE, font=(FUENTE, 20, "bold"))
        self.titulo.pack(side="left")

        self.filtro = tk.StringVar(value="Pendientes")
        if self.es_admin:
            combo = ttk.Combobox(cabecera, textvariable=self.filtro, state="readonly",
                                 width=12, values=["Pendientes", "Todas"],
                                 font=(FUENTE, 10))
            combo.pack(side="right")
            combo.bind("<<ComboboxSelected>>", lambda e: self.cargar())

        explicacion = ("Revisa cada solicitud. Al aprobarla, el empleado podrá eliminar ese "
                       "registro una sola vez; si la rechazas, no podrá borrarlo."
                       if self.es_admin else
                       "Para eliminar un registro, pide permiso al administrador. Cuando tu "
                       "solicitud esté «Aprobada» podrás eliminarlo; si sigue «Pendiente» o fue "
                       "«Rechazada», no se puede borrar.")
        tk.Label(self, text=explicacion, bg=FONDO_SECCION, fg=VERDE_OSCURO, justify="left",
                 wraplength=940, font=(FUENTE, 10)).pack(anchor="w", padx=24, pady=(0, 6))

        # ---------------- Tabla ----------------
        marco = tk.Frame(self, bg=FONDO_SECCION)
        marco.pack(fill="both", expand=True, padx=24)
        columnas = [("Fecha", "fecha", 120), ("Solicitante", "solicitante", 150),
                    ("Tipo", "tipo", 100), ("Registro", "registro", 200),
                    ("Motivo", "motivo", 240), ("Estado", "estado", 90)]
        self.tree = ttk.Treeview(marco, show="headings", selectmode="browse",
                                 columns=[c[1] for c in columnas], height=8)
        for encabezado, clave, ancho in columnas:
            self.tree.heading(clave, text=encabezado)
            self.tree.column(clave, width=ancho, anchor="w")
        self.tree.tag_configure("pendiente", background="#F3E7B8")
        self.tree.tag_configure("aprobada", background="#CFE5B4")
        self.tree.tag_configure("rechazada", background="#EBC6C0")
        self.tree.tag_configure("ejecutada", background="#DADBD0")
        barra = ttk.Scrollbar(marco, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=barra.set)
        self.tree.pack(side="left", fill="both", expand=True)
        barra.pack(side="right", fill="y")
        self.tree.bind("<<TreeviewSelect>>", lambda e: self._mostrar_detalle())

        self.detalle = tk.Label(self, text="", bg=FONDO_SECCION, fg=VERDE_OSCURO,
                                justify="left", anchor="w", wraplength=940,
                                font=(FUENTE, 10))
        self.detalle.pack(fill="x", padx=24, pady=(6, 0))

        # ---------------- Botones ----------------
        botones = tk.Frame(self, bg=FONDO_SECCION)
        botones.pack(fill="x", padx=24, pady=10)
        if self.es_admin:
            tk.Button(botones, text="Aprobar", command=self.aprobar, bg=VERDE_OSCURO,
                      fg=BLANCO, relief="flat", padx=16, pady=4,
                      font=(FUENTE, 10, "bold")).pack(side="left")
            tk.Button(botones, text="Rechazar", command=self.rechazar, bg=ROJO, fg=BLANCO,
                      relief="flat", padx=16, pady=4,
                      font=(FUENTE, 10)).pack(side="left", padx=(8, 0))
        else:
            tk.Button(botones, text="Eliminar registro aprobado", command=self.eliminar_aprobado,
                      bg=ROJO, fg=BLANCO, relief="flat", padx=16, pady=4,
                      font=(FUENTE, 10, "bold")).pack(side="left")
        tk.Button(botones, text="Actualizar", command=self.cargar, bg=GRIS, fg=BLANCO,
                  relief="flat", padx=14, pady=4, font=(FUENTE, 10)).pack(side="right")

        self.cargar()

    # ---------------- Datos ----------------
    def cargar(self):
        try:
            if self.es_admin:
                estado = "pendiente" if self.filtro.get() == "Pendientes" else None
                filas = db.listar_solicitudes(estado=estado)
                n = db.contar_pendientes()
                self.titulo.config(text="Solicitudes de eliminación"
                                        + (f" ({n} pendiente{'s' if n != 1 else ''})" if n else ""))
            else:
                filas = db.listar_solicitudes(id_solicitante=self.id_usuario)
        except Exception as ex:
            messagebox.showerror("Error de base de datos", str(ex))
            return

        self.tree.delete(*self.tree.get_children())
        self.filas = {f["id_solicitud"]: f for f in filas}
        for f in filas:
            self.tree.insert("", "end", iid=str(f["id_solicitud"]), tags=(f["estado"],),
                             values=(f["fecha"], f["solicitante"],
                                     db.TABLAS_ELIMINABLES[f["tabla"]][1], f["descripcion"],
                                     f["motivo"].replace("\n", " "), ESTADOS[f["estado"]]))
        self.detalle.config(text="")

    def _seleccionada(self):
        sel = self.tree.selection()
        if not sel:
            messagebox.showinfo("Solicitudes", "Selecciona una solicitud de la lista.")
            return None
        return self.filas.get(int(sel[0]))

    def _mostrar_detalle(self):
        sel = self.tree.selection()
        f = self.filas.get(int(sel[0])) if sel else None
        if not f:
            self.detalle.config(text="")
            return
        texto = f"Motivo: {f['motivo']}"
        if f["respuesta"]:
            texto += f"\nRespuesta del administrador: {f['respuesta']}"
        self.detalle.config(text=texto)

    # ---------------- Administrador ----------------
    def _resolver(self, aprobar):
        f = self._seleccionada()
        if f is None:
            return
        if f["estado"] != "pendiente":
            messagebox.showinfo("Solicitudes", "Esa solicitud ya fue resuelta.")
            return
        tipo = db.TABLAS_ELIMINABLES[f["tabla"]][1]
        resumen = (f"{f['solicitante']} pide eliminar:\n{tipo}: {f['descripcion']}\n\n"
                   f"Motivo: {f['motivo']}")
        if aprobar:
            if not messagebox.askyesno(
                    "Aprobar eliminación",
                    f"{resumen}\n\n¿Concedes el permiso? El empleado podrá eliminar este "
                    "registro una sola vez."):
                return
            respuesta = ""
        else:
            respuesta = pedir_motivo(self, "Rechazar solicitud", resumen,
                                     etiqueta="Comentario para el empleado (opcional)",
                                     obligatorio=False)
            if respuesta is None:
                return
        try:
            ok = db.resolver_solicitud(f["id_solicitud"], self.id_usuario, aprobar, respuesta)
        except Exception as ex:
            messagebox.showerror("Error de base de datos", str(ex))
            return
        if not ok:
            messagebox.showwarning("Solicitudes", "La solicitud ya no estaba pendiente.")
        self.cargar()

    def aprobar(self):
        self._resolver(True)

    def rechazar(self):
        self._resolver(False)

    # ---------------- Empleado ----------------
    def eliminar_aprobado(self):
        f = self._seleccionada()
        if f is None:
            return
        if f["estado"] != "aprobada":
            mensajes = {"pendiente": "El administrador aún no ha aprobado esta solicitud.",
                        "rechazada": "El administrador rechazó esta solicitud.",
                        "ejecutada": "Este registro ya fue eliminado."}
            messagebox.showwarning("No se puede eliminar", mensajes[f["estado"]])
            return
        tipo = db.TABLAS_ELIMINABLES[f["tabla"]][1]
        if not messagebox.askyesno(
                "Eliminar", f"¿Eliminar {tipo.lower()} «{f['descripcion']}»?\n\n"
                            "Esta acción no se puede deshacer.", icon="warning"):
            return
        try:
            db.eliminar_con_permiso(self.id_usuario, f["tabla"], f["id_registro"])
        except db.PermisoDenegado:
            messagebox.showwarning("Sin permiso", "El permiso ya no está vigente.")
        except db.RegistroEnUso:
            messagebox.showwarning(
                "No se pudo eliminar",
                "Este registro tiene datos ligados (por ejemplo ventas) y no se puede borrar.\n"
                "Tu permiso sigue vigente.")
        except Exception as ex:
            messagebox.showerror("Error de base de datos", str(ex))
        else:
            messagebox.showinfo("Solicitudes", "El registro se eliminó correctamente.")
        self.cargar()