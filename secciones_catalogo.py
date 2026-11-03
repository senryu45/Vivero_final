"""Implementación de Diap. 7 (CATÁLOGO por secciones) y Diap. 8 (Agregar sección)."""
import tkinter as tk
from tkinter import messagebox
from decimal import Decimal
import psycopg2.errors
import db
import catalogo

# ----------------------------- Constantes de Diseño -----------------------------
VERDE_OSCURO = "#3F5A1A"
VERDE_CLARO = "#8BCB4E"
VERDE_BUSCADOR = "#587A2D"
FONDO_SECCION = "#C5C7B5"
FONDO_TARJETA = "#E6E8DF"
FONDO_IMAGEN = "#DDE3CC"
CAFE = "#99553A"
CAFE_HOVER = "#7A4029"
BLANCO = "#FFFFFF"
TEXTO = "#4A3B33"
TEXTO_CLARO = "#E3E8D3"
FUENTE = "Open Sans"

ANCHO_CELDA, ALTO_CELDA = 150, 138
LADO, RADIO = 96, 18
ALTO_FILA = 78


class CatalogoSecciones(tk.Frame):
    """Diapositiva 7: Muestra las categorías/secciones como pestañas con íconos vectoriales

    y abajo la cuadrícula de plantas filtradas por dicha sección.
    """
    def __init__(self, master, datos=None):
        super().__init__(master, bg=FONDO_SECCION)
        self.datos = datos
        self.es_staff = (datos is None) or datos["rol"] in ("admin", "vendedor")
        self.seccion_activa = None
        self.categorias = []
        self.plantas = []

        # Cabecera superior interna
        self.fila_cabecera = tk.Frame(self, bg=FONDO_SECCION)
        self.fila_cabecera.pack(fill="x", padx=28, pady=(10, 0))
        
        tk.Label(self.fila_cabecera, text="CATÁLOGO", bg=FONDO_SECCION, fg=CAFE,
                 font=(FUENTE, 24, "bold")).pack(side="left")
                 
        if self.es_staff:
            self.lbl_agregar = tk.Label(self.fila_cabecera, text="+ Agregar sección", bg=FONDO_SECCION, fg=CAFE,
                                       font=(FUENTE, 14, "underline"), cursor="hand2")
            self.lbl_agregar.pack(side="right", padx=(0, 20))
            self.lbl_agregar.bind("<Button-1>", lambda e: self._ir_a_agregar_seccion())

        # Contenedor de pestañas/secciones
        self.marco_pestas = tk.Frame(self, bg=FONDO_SECCION)
        self.marco_pestas.pack(fill="x", padx=28, pady=15)

        # Contenedor de cuadrícula de plantas
        self.zona_plantas = tk.Frame(self, bg=FONDO_SECCION)
        self.zona_plantas.pack(fill="both", expand=True, padx=28, pady=5)
        
        self.cargar_datos()

    def cargar_datos(self):
        try:
            self.categorias = db.consultar("SELECT id_categoria, nombre, tipo_plantas, descripcion FROM categorias ORDER BY id_categoria")
        except Exception as e:
            messagebox.showerror("Error de base de datos", f"No se pudieron cargar las secciones:\n{e}")
            return
        
        if self.categorias and len(self.categorias) > 0:
            self.seccion_activa = self.categorias[0]["nombre"]
            self._dibujar_pestañas()
            self._cargar_plantas_de_seccion()
        else:
            tk.Label(self.marco_pestas, text="No hay secciones registradas.",
                     bg=FONDO_SECCION, fg=TEXTO, font=(FUENTE, 12, "italic")).pack(pady=10)

    def _dibujar_pestañas(self):
        for h in self.marco_pestas.winfo_children():
            h.destroy()

        if not self.categorias:
            return

        self.marco_pestas.columnconfigure(tuple(range(len(self.categorias))), weight=1)
        
        for idx, cat in enumerate(self.categorias):
            btn_marco = tk.Frame(self.marco_pestas, bg=FONDO_SECCION, cursor="hand2")
            btn_marco.grid(row=0, column=idx, sticky="nsew", padx=10)
            
            es_activa = (cat["nombre"] == self.seccion_activa)
            font_estilo = (FUENTE, 16, "bold" if es_activa else "normal")
            
            lbl_txt = tk.Label(btn_marco, text=cat["nombre"], bg=FONDO_SECCION, fg=CAFE, font=font_estilo)
            lbl_txt.pack(pady=(0, 2))
            
            canvas_ico = tk.Canvas(btn_marco, width=60, height=60, bg=FONDO_SECCION, highlightthickness=0)
            canvas_ico.pack()
            self._dibujar_icono_categoria(canvas_ico, cat["nombre"].lower())
            
            if es_activa:
                linea = tk.Frame(btn_marco, bg=CAFE, height=2)
                linea.pack(fill="x", pady=(2, 0))

            for w in (btn_marco, lbl_txt, canvas_ico):
                w.bind("<Button-1>", lambda e, name=cat["nombre"]: self._activar_seccion(name))

    @staticmethod
    def _dibujar_icono_categoria(canvas, nombre):
        if "med" in nombre: 
            canvas.create_rectangle(18, 38, 42, 58, fill="#B37453", outline="")
            canvas.create_polygon(22, 38, 15, 12, 26, 16, fill="#619E45", outline="", smooth=True)
            canvas.create_polygon(30, 38, 30, 8, 38, 14, fill="#4D8733", outline="", smooth=True)
            canvas.create_polygon(38, 38, 45, 15, 35, 20, fill="#74B855", outline="", smooth=True)
        elif "frut" in nombre: 
            canvas.create_polygon(12, 28, 48, 28, 42, 54, 18, 54, fill="#D1A16E", outline="")
            canvas.create_oval(16, 18, 32, 32, fill="#E64A19", outline="") 
            canvas.create_oval(28, 16, 44, 30, fill="#FFA000", outline="") 
        elif "arb" in nombre: 
            canvas.create_rectangle(26, 36, 34, 58, fill="#795548", outline="")
            canvas.create_oval(12, 10, 48, 42, fill="#4CAF50", outline="")
            canvas.create_oval(20, 6, 40, 26, fill="#81C784", outline="")
        else: 
            canvas.create_oval(22, 22, 38, 38, fill="#FFEB3B", outline="") 
            for cx, cy in [(14,22), (38,22), (14,38), (38,38), (26,12), (26,46)]:
                canvas.create_oval(cx, cy, cx+14, cy+14, fill="#E91E63", outline="") 
            canvas.create_oval(23, 23, 37, 37, fill="#FFEB3B", outline="")

    def _activar_seccion(self, nombre):
        self.seccion_activa = nombre
        self._dibujar_pestañas()
        self._cargar_plantas_de_seccion()

    def _cargar_plantas_de_seccion(self):
        for h in self.zona_plantas.winfo_children():
            h.destroy()

        if not self.seccion_activa:
            return

        sql = """SELECT p.id_planta, p.nombre_comun, p.precio, p.cantidad, p.disponible
                 FROM plantas p 
                 JOIN categorias c USING (id_categoria)
                 WHERE c.nombre = %s"""
        if not self.es_staff:
            sql += " AND p.disponible = TRUE"
        sql += " ORDER BY p.nombre_comun"

        try:
            self.plantas = db.consultar(sql, (self.seccion_activa,))
        except Exception as e:
            messagebox.showerror("Error", f"Error al cargar elementos:\n{e}")
            return

        self.zona_plantas.columnconfigure((0, 1, 2, 3, 4, 5), weight=1)
        if not self.plantas:
            tk.Label(self.zona_plantas, text="No hay plantas registradas en esta sección.",
                     bg=FONDO_SECCION, fg=VERDE_OSCURO, font=(FUENTE, 12, "italic")).pack(pady=30)
            return

        for idx, p in enumerate(self.plantas):
            celda = tk.Frame(self.zona_plantas, bg=FONDO_SECCION, width=ANCHO_CELDA, height=ALTO_CELDA)
            celda.pack_propagate(False)
            
            lienzo = tk.Canvas(celda, width=LADO, height=LADO, bg=FONDO_SECCION, highlightthickness=0)
            lienzo.pack(pady=(2, 4))
            
            foto = catalogo.foto_redondeada(p, LADO, RADIO)
            if foto:
                lienzo.create_image(0, 0, anchor="nw", image=foto)
            else:
                catalogo.rectangulo_redondeado(lienzo, 0, 0, LADO, LADO, RADIO, FONDO_IMAGEN)
                catalogo.dibujar_planta(lienzo, LADO / 2, LADO - 10, 0.8)

            tk.Label(celda, text=p["nombre_comun"], bg=FONDO_SECCION, fg=TEXTO, font=(FUENTE, 10, "bold")).pack()
            tk.Label(celda, text=catalogo.dinero(p["precio"]), bg=FONDO_SECCION, fg=CAFE, font=(FUENTE, 9)).pack()
            
            estado_disp = "Disponible" if p["cantidad"] > 0 else "Agotado"
            tk.Label(celda, text=estado_disp, bg=FONDO_SECCION, fg=VERDE_OSCURO, font=(FUENTE, 8, "bold")).pack()
            celda.grid(row=idx // 6, column=idx % 6, padx=5, pady=5)

    def _ir_a_agregar_seccion(self):
        master_panel = self.master
        self.destroy()
        nuevo_form = AgregarSeccion(master_panel, self.datos)
        nuevo_form.place(x=0, y=0, width=1000, height=490)


class AgregarSeccion(tk.Frame):
    """Diapositiva 8: Formulario administrativo para la gestión de las secciones."""
    def __init__(self, master, datos=None):
        super().__init__(master, bg=FONDO_SECCION)
        self.datos = datos
        self.editando_id = None
        self.marcadas = set()
        self.lista_secciones = []

        izq = tk.Frame(self, bg=FONDO_SECCION)
        izq.place(x=0, y=0, width=420, height=490)

        lbl_volver = tk.Label(izq, text="← Volver al catálogo", bg=FONDO_SECCION, fg=VERDE_OSCURO, font=(FUENTE, 10, "underline"), cursor="hand2")
        lbl_volver.place(x=24, y=10)
        lbl_volver.bind("<Button-1>", lambda e: self._regresar())

        self.lbl_titulo_form = tk.Label(izq, text="Agregar seccion", bg=FONDO_SECCION, fg=CAFE, font=(FUENTE, 20, "bold"))
        self.lbl_titulo_form.place(x=24, y=36)

        self.e_nombre = self._crear_campo_pildora(izq, 24, 95, 360, "Nombre de la sección:")
        self.e_categoria = self._crear_campo_pildora(izq, 24, 155, 360, "Categoría:")
        self.e_tipo = self._crear_campo_pildora(izq, 24, 215, 360, "tipo de plantas:")
        
        tk.Label(izq, text="Descripción:", bg=FONDO_SECCION, fg=TEXTO, font=(FUENTE, 10)).place(x=24, y=275)
        canvas_desc = tk.Canvas(izq, width=360, height=75, bg=FONDO_SECCION, highlightthickness=0)
        canvas_desc.place(x=24, y=295)
        catalogo.rectangulo_redondeado(canvas_desc, 0, 0, 360, 75, 20, CAFE)
        self.e_desc = tk.Text(canvas_desc, bd=0, bg=CAFE, fg=BLANCO, insertbackground=BLANCO, font=(FUENTE, 10), wrap="word", relief="flat")
        canvas_desc.create_window(180, 37, window=self.e_desc, width=320, height=55)

        self.btn_guardar = tk.Canvas(izq, width=240, height=36, bg=FONDO_SECCION, highlightthickness=0, cursor="hand2")
        self.btn_guardar.place(x=84, y=395)
        self.r_btn = catalogo.rectangulo_redondeado(self.btn_guardar, 0, 0, 240, 36, 18, CAFE)
        self.txt_btn = self.btn_guardar.create_text(120, 18, text="AGREGAR SECCION", fill=BLANCO, font=(FUENTE, 11, "bold"))
        
        # Corrección de strings vacíos por eventos de Tkinter válidos
        self.btn_guardar.bind("<Button-1>", lambda e: self._procesar_guardado())
        self.btn_guardar.bind("<Enter>", lambda e: self.btn_guardar.itemconfig(self.r_btn, fill=CAFE_HOVER, outline=CAFE_HOVER))
        self.btn_guardar.bind("<Leave>", lambda e: self.btn_guardar.itemconfig(self.r_btn, fill=CAFE, outline=CAFE))

        self._construir_panel_lista()
        self.recargar_lista()

    def _crear_campo_pildora(self, master, x, y, ancho, titulo):
        tk.Label(master, text=titulo, bg=FONDO_SECCION, fg=TEXTO, font=(FUENTE, 10)).place(x=x, y=y)
        canvas_fnd = tk.Canvas(master, width=ancho, height=28, bg=FONDO_SECCION, highlightthickness=0)
        canvas_fnd.place(x=x, y=y+20)
        catalogo.rectangulo_redondeado(canvas_fnd, 0, 0, ancho, 28, 14, CAFE)
        entrada = tk.Entry(canvas_fnd, bd=0, bg=CAFE, fg=BLANCO, insertbackground=BLANCO, font=(FUENTE, 10), relief="flat")
        canvas_fnd.create_window(ancho/2, 14, window=entrada, width=ancho-24)
        return entrada

    def _construir_panel_lista(self):
        der = tk.Canvas(self, width=540, height=430, bg=FONDO_SECCION, highlightthickness=0)
        der.place(x=435, y=15)
        catalogo.rectangulo_redondeado(der, 0, 0, 540, 430, 28, VERDE_OSCURO)

        canvas_search = tk.Canvas(der, width=500, height=28, bg=VERDE_OSCURO, highlightthickness=0)
        der.create_window(20, 15, window=canvas_search, anchor="nw")
        catalogo.rectangulo_redondeado(canvas_search, 0, 0, 500, 28, 14, VERDE_BUSCADOR)
        canvas_search.create_oval(15, 6, 25, 16, outline=TEXTO_CLARO, width=2)
        canvas_search.create_line(24, 15, 30, 21, fill=TEXTO_CLARO, width=2)
        self.e_buscar = tk.Entry(canvas_search, bd=0, bg=VERDE_BUSCADOR, fg=TEXTO_CLARO, insertbackground=TEXTO_CLARO, font=(FUENTE, 9), relief="flat")
        canvas_search.create_window(260, 14, window=self.e_buscar, width=420)
        self.e_buscar.bind("<KeyRelease>", lambda e: self.recargar_lista())

        der.create_text(24, 60, text="Lista de secciones", anchor="w", fill=TEXTO_CLARO, font=(FUENTE, 11, "bold"))
        lbl_del = der.create_text(516, 60, text="eliminar seleccionado", anchor="e", fill=TEXTO_CLARO, font=(FUENTE, 10, "underline"), cursor="hand2")
        der.tag_bind(lbl_del, "<Button-1>", lambda e: self._eliminar_marcados())
        
        der.create_text(130, 85, text="informacion", anchor="w", fill=TEXTO_CLARO, font=(FUENTE, 9, "bold"))
        der.create_text(480, 85, text="Acciones", fill=TEXTO_CLARO, font=(FUENTE, 9, "bold"))

        self.frame_scroll = tk.Frame(der, bg=VERDE_OSCURO)
        der.create_window(10, 100, window=self.frame_scroll, anchor="nw", width=520, height=315)
        self.canvas_rows = tk.Canvas(self.frame_scroll, bg=VERDE_OSCURO, highlightthickness=0)
        scr = tk.Scrollbar(self.frame_scroll, orient="vertical", command=self.canvas_rows.yview)
        self.canvas_rows.configure(yscrollcommand=scr.set)
        scr.pack(side="right", fill="y")
        self.canvas_rows.pack(side="left", fill="both", expand=True)
        self.interior_lista = tk.Frame(self.canvas_rows, bg=VERDE_OSCURO)
        self.canvas_rows.create_window(0, 0, window=self.interior_lista, anchor="nw", width=495)
        self.interior_lista.bind("<Configure>", lambda e: self.canvas_rows.configure(scrollregion=self.canvas_rows.bbox("all")))

    def recargar_lista(self):
        for h in self.interior_lista.winfo_children():
            h.destroy()
        sql = "SELECT id_categoria, nombre, tipo_plantas FROM categorias"
        txt = self.e_buscar.get().strip()
        params = []
        if txt:
            sql += " WHERE nombre ILIKE %s OR tipo_plantas ILIKE %s"
            params = [f"%{txt}%", f"%{txt}%"]
        sql += " ORDER BY id_categoria"
        try:
            self.lista_secciones = db.consultar(sql, params)
        except Exception as e:
            messagebox.showerror("Error", str(e))
            return

        for s in self.lista_secciones:
            row = tk.Frame(self.interior_lista, bg=VERDE_OSCURO, height=ALTO_FILA)
            row.pack(fill="x")
            row.pack_propagate(False)

            cid = s["id_categoria"]
            chk_txt = "☑" if cid in self.marcadas else "☐"
            lbl_chk = tk.Label(row, text=chk_txt, bg=VERDE_OSCURO, fg=TEXTO_CLARO, font=(FUENTE, 16), cursor="hand2")
            lbl_chk.place(x=8, y=ALTO_FILA/2, anchor="w")
            lbl_chk.bind("<Button-1>", lambda e, id_cat=cid, l=lbl_chk: self._alternar_marca(id_cat, l))

            ico_canvas = tk.Canvas(row, width=45, height=45, bg=VERDE_OSCURO, highlightthickness=0)
            ico_canvas.place(x=40, y=(ALTO_FILA-45)/2)
            CatalogoSecciones._dibujar_icono_categoria(ico_canvas, s["nombre"].lower())

            tk.Label(row, text=s["nombre"], bg=VERDE_OSCURO, fg=BLANCO, font=(FUENTE, 10, "bold"), anchor="w").place(x=105, y=15)
            tk.Label(row, text=s["tipo_plantas"] or "General", bg=VERDE_OSCURO, fg=TEXTO_CLARO, font=(FUENTE, 9), anchor="w").place(x=105, y=38)

            btn_edit = tk.Canvas(row, width=20, height=20, bg=VERDE_OSCURO, highlightthickness=0, cursor="hand2")
            btn_edit.place(x=455, y=ALTO_FILA/2, anchor="center")
            catalogo.icono_editar(btn_edit)
            btn_edit.bind("<Button-1>", lambda e, cat_item=s: self._cargar_edicion(cat_item))
            
            btn_del = tk.Canvas(row, width=20, height=20, bg=VERDE_OSCURO, highlightthickness=0, cursor="hand2")
            btn_del.place(x=490, y=ALTO_FILA/2, anchor="center")
            catalogo.icono_papelera(btn_del)
            btn_del.bind("<Button-1>", lambda e, id_cat=cid: self._eliminar_secciones_db([id_cat]))
            
            tk.Frame(self.interior_lista, bg=VERDE_BUSCADOR, height=1).pack(fill="x", padx=10)

    def _alternar_marca(self, cid, label):
        if cid in self.marcadas:
            self.marcadas.remove(cid)
            label.config(text="☐")
        else:
            self.marcadas.add(cid)
            label.config(text="☑")

    def _cargar_edicion(self, s):
        try:
            completo = db.consultar("SELECT * FROM categorias WHERE id_categoria = %s", (s["id_categoria"],), uno=True)
        except Exception as e:
            messagebox.showerror("Error", str(e))
            return
        self.editando_id = completo["id_categoria"]
        self.e_nombre.delete(0, tk.END)
        self.e_nombre.insert(0, completo["nombre"])
        self.e_categoria.delete(0, tk.END)
        self.e_categoria.insert(0, completo["nombre"])
        self.e_tipo.delete(0, tk.END)
        self.e_tipo.insert(0, completo["tipo_plantas"] or "")
        self.e_desc.delete("1.0", tk.END)
        self.e_desc.insert("1.0", completo["descripcion"] or "")
        self.lbl_titulo_form.config(text="Editar seccion")
        self.btn_guardar.itemconfig(self.txt_btn, text="GUARDAR CAMBIOS")

    def _procesar_guardado(self):
        nom = self.e_nombre.get().strip()
        tipo = self.e_tipo.get().strip()
        desc = self.e_desc.get("1.0", tk.END).strip()
        if not nom:
            messagebox.showwarning("Campos incompletos", "Por favor introduce el nombre de la sección.")
            return
        try:
            if self.editando_id is None:
                db.ejecutar("INSERT INTO categorias (nombre, tipo_plantas, descripcion) VALUES (%s, %s, %s)", (nom, tipo or None, desc or None))
                msg = "Sección agregada con éxito."
            else:
                db.ejecutar("UPDATE categorias SET nombre=%s, tipo_plantas=%s, descripcion=%s WHERE id_categoria=%s", (nom, tipo or None, desc or None, self.editando_id))
                msg = "Sección actualizada con éxito."
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo guardar la información:\n{e}")
            return
        # (Continuación exacta dentro del método _procesar_guardado)
        messagebox.showinfo("Éxito", msg)
        self._limpiar_campos()
        self.recargar_lista()

    def _limpiar_campos(self):
        self.editando_id = None
        self.e_nombre.delete(0, tk.END)
        self.e_categoria.delete(0, tk.END)
        self.e_tipo.delete(0, tk.END)
        self.e_desc.delete("1.0", tk.END)
        self.lbl_titulo_form.config(text="Agregar seccion")
        self.btn_guardar.itemconfig(self.txt_btn, text="AGREGAR SECCION")

    def _eliminar_marcados(self):
        if not self.marcadas:
            messagebox.showinfo("Eliminar", "Selecciona las casillas de las secciones que deseas eliminar.")
            return
        self._eliminar_secciones_db(list(self.marcadas))

    def _eliminar_secciones_db(self, ids):
        if not messagebox.askyesno("Confirmar", f"¿Estás seguro de que deseas eliminar {len(ids)} sección(es)?\nEsto podría desvincular plantas asignadas."):
            return
        for cid in ids:
            try:
                db.ejecutar("DELETE FROM categorias WHERE id_categoria = %s", (cid,))
                self.marcadas.discard(cid)
            except psycopg2.errors.ForeignKeyViolation:
                messagebox.showerror("Error", "No se puede eliminar la sección porque tiene plantas activas asociadas. Elimina o reubica las plantas primero.")
            except Exception as e:
                messagebox.showerror("Error", str(e))
                break
        self.recargar_lista()

    def _regresar(self):
        master_panel = self.master
        self.destroy()
        back = CatalogoSecciones(master_panel, self.datos)
        back.place(x=0, y=0, width=1000, height=490)

        