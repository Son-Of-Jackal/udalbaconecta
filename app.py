import streamlit as st
import sqlite3
import pandas as pd
import time
import hashlib

# ==========================================
#           CONFIGURACIÓN INICIAL
# ==========================================
st.set_page_config(page_title="Udalba Conecta", page_icon="🎓", layout="centered")

# Estilos CSS (Modo Udalba)
st.markdown("""
<style>
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    
    /* Botones principales azules */
    div.stButton > button:first-child {
        background-color: #002e6e; 
        color: white;
        border-radius: 8px;
        border: none;
        font-weight: bold;
    }
    div.stButton > button:first-child:hover {
        background-color: #001a40;
        color: white;
    }
    
    /* Botones de borrar (rojos) - Truco CSS */
    div[data-testid="stForm"] + div div.stButton > button {
        background-color: #ff4b4b;
        color: white;
    }
    /* El segundo botón rojo (para solicitudes) necesita especificidad extra */
    div.stButton > button:contains("Eliminar") {
         background-color: #ff4b4b !important;
         color: white !important;
    }
</style>
""", unsafe_allow_html=True)

# ==========================================
#           BASE DE DATOS
# ==========================================
def make_hashes(password):
    return hashlib.sha256(str.encode(password)).hexdigest()

def init_db():
    conn = sqlite3.connect('arriendos_udalba.db')
    c = conn.cursor()
    
    # Tabla USUARIOS
    c.execute('''CREATE TABLE IF NOT EXISTS usuarios (
                    email TEXT PRIMARY KEY,
                    nombre TEXT,
                    password TEXT,
                    whatsapp TEXT,
                    carrera TEXT)''')
    
    # Tabla PRODUCTOS
    c.execute('''CREATE TABLE IF NOT EXISTS productos (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    nombre TEXT,
                    descripcion TEXT,
                    precio INTEGER,
                    estado TEXT,
                    email_dueño TEXT,
                    foto BLOB,
                    FOREIGN KEY(email_dueño) REFERENCES usuarios(email))''')
    
    # Tabla SOLICITUDES
    c.execute('''CREATE TABLE IF NOT EXISTS solicitudes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    titulo TEXT,
                    presupuesto INTEGER,
                    descripcion TEXT,
                    email_solicitante TEXT,
                    FOREIGN KEY(email_solicitante) REFERENCES usuarios(email))''')
    
    conn.commit()
    conn.close()

def run_query(query, params=(), return_data=False):
    conn = sqlite3.connect('arriendos_udalba.db')
    c = conn.cursor()
    try:
        c.execute(query, params)
        conn.commit()
        if return_data:
            return c.fetchall()
    except Exception as e:
        st.error(f"Error en BD: {e}")
    finally:
        conn.close()
    return None

init_db()

# ==========================================
#           LÓGICA DE SESIÓN
# ==========================================
if 'usuario_actual' not in st.session_state:
    st.session_state['usuario_actual'] = None

def login_user(email, password):
    hashed_pswd = make_hashes(password)
    result = run_query("SELECT * FROM usuarios WHERE email = ? AND password = ?", (email, hashed_pswd), return_data=True)
    return result

def register_user(email, nombre, password, whatsapp, carrera):
    try:
        hashed_pswd = make_hashes(password)
        run_query("INSERT INTO usuarios (email, nombre, password, whatsapp, carrera) VALUES (?,?,?,?,?)", 
                 (email, nombre, hashed_pswd, whatsapp, carrera))
        return True
    except:
        return False

# ==========================================
#           INTERFAZ GRÁFICA
# ==========================================

# --- ESCENARIO A: NO ESTÁ LOGUEADO ---
if st.session_state['usuario_actual'] is None:
    try:
        st.sidebar.image("logo.png", use_container_width=True)
    except:
        st.sidebar.title("🎓 UDALBA")
        
    st.markdown("<h1 style='text-align: center; color: #e6b800;'>🎓 Udalba Conecta</h1>", unsafe_allow_html=True)
    
    menu_login = st.sidebar.selectbox("Bienvenido", ["Iniciar Sesión", "Registrarse"])
    
    if menu_login == "Iniciar Sesión":
        st.subheader("Ingresa a tu cuenta")
        email = st.text_input("Correo Institucional")
        password = st.text_input("Contraseña", type='password')
        
        if st.button("Entrar"):
            user = login_user(email, password)
            if user:
                st.session_state['usuario_actual'] = user[0] 
                st.success(f"Bienvenido {user[0][1]}")
                st.rerun()
            else:
                st.error("Correo o contraseña incorrectos")
                
    elif menu_login == "Registrarse":
        st.subheader("Crea tu cuenta nueva")
        new_email = st.text_input("Correo (@udalba.cl)")
        new_name = st.text_input("Nombre Completo")
        new_pass = st.text_input("Contraseña", type='password')
        new_wsp = st.text_input("WhatsApp (Ej: 56912345678)")
        new_carrera = st.selectbox("Carrera", ["Ing. Civil Minas", "Enfermería", "Derecho", "Otras"])
        
        if st.button("Crear Cuenta"):
            if "@udalba.cl" in new_email:
                exito = register_user(new_email, new_name, new_pass, new_wsp, new_carrera)
                if exito:
                    st.success("¡Cuenta creada! Ahora inicia sesión.")
                else:
                    st.error("Ese correo ya está registrado.")
            else:
                st.warning("Debes usar un correo institucional.")

# --- ESCENARIO B: USUARIO LOGUEADO ---
else:
    usuario = st.session_state['usuario_actual']
    
    try:
        st.sidebar.image("logo.png", use_container_width=True)
    except:
        pass
        
    st.sidebar.write(f"Hola, **{usuario[1]}**")
    st.sidebar.caption(f"{usuario[4]}")
    
    if st.sidebar.button("Cerrar Sesión"):
        st.session_state['usuario_actual'] = None
        st.rerun()
    
    st.sidebar.divider()
    
    opcion = st.sidebar.radio("Navegación", ["Catálogo", "Publicar Aviso", "Muro de Solicitudes", "Mi Perfil"])

    # 1. PANTALLA CATÁLOGO
    if opcion == "Catálogo":
        st.title("🛒 Catálogo General")
        
        sql = """SELECT p.nombre, p.descripcion, p.precio, p.foto, u.nombre, u.whatsapp 
                 FROM productos p 
                 JOIN usuarios u ON p.email_dueño = u.email 
                 WHERE p.estado='Disponible'"""
        items = run_query(sql, return_data=True)
        
        if items:
            for item in items:
                with st.container(border=True):
                    c1, c2 = st.columns([1, 2])
                    with c1:
                        if item[3]:
                            st.image(item[3], use_container_width=True)
                        else:
                            st.text("📷 Sin foto")
                    with c2:
                        st.subheader(item[0])
                        st.write(f"_{item[1]}_")
                        st.write(f"**Vendedor:** {item[4]}")
                        st.metric("Precio", f"${item[2]}")
                        msg = f"Hola {item[4]}, me interesa tu {item[0]}"
                        link = f"https://wa.me/{item[5]}?text={msg.replace(' ', '%20')}"
                        st.link_button("Contactar 💬", link)
        else:
            st.info("No hay productos disponibles.")

    # 2. PANTALLA PUBLICAR AVISO
    elif opcion == "Publicar Aviso":
        st.title("📢 Publicar Artículo")
        with st.form("form_prod"):
            nombre = st.text_input("¿Qué arriendas?")
            desc = st.text_area("Descripción")
            precio = st.number_input("Precio diario", min_value=0, step=500)
            foto = st.file_uploader("Foto del producto", type=['jpg','png'])
            
            if st.form_submit_button("Publicar"):
                foto_blob = foto.getvalue() if foto else None
                run_query("INSERT INTO productos (nombre, descripcion, precio, estado, email_dueño, foto) VALUES (?,?,?,?,?,?)",
                         (nombre, desc, precio, "Disponible", usuario[0], foto_blob))
                st.success("¡Publicado!")
                time.sleep(1)
                st.rerun()

    # 3. PANTALLA MURO DE SOLICITUDES
    elif opcion == "Muro de Solicitudes":
        st.title("🙋‍♂️ Muro de Solicitudes")
        st.caption("¿Necesitas algo que no está en el catálogo? Pídelo aquí.")
        
        with st.expander("➕ Crear nueva solicitud"):
            with st.form("form_solicitud"):
                titulo = st.text_input("¿Qué necesitas? (Ej: Bata Talla S)")
                presupuesto = st.number_input("¿Cuánto ofreces pagar? ($)", min_value=0, step=500)
                desc_sol = st.text_area("Detalles adicionales")
                
                if st.form_submit_button("Publicar Solicitud"):
                    run_query("INSERT INTO solicitudes (titulo, presupuesto, descripcion, email_solicitante) VALUES (?,?,?,?)",
                             (titulo, presupuesto, desc_sol, usuario[0]))
                    st.success("¡Solicitud publicada!")
                    time.sleep(1)
                    st.rerun()
        
        st.divider()
        sql_sol = """SELECT s.titulo, s.presupuesto, s.descripcion, u.nombre, u.whatsapp 
                     FROM solicitudes s 
                     JOIN usuarios u ON s.email_solicitante = u.email 
                     ORDER BY s.id DESC"""
        solicitudes = run_query(sql_sol, return_data=True)
        
        if solicitudes:
            for sol in solicitudes:
                with st.container(border=True):
                    c1, c2 = st.columns([3, 1])
                    with c1:
                        st.markdown(f"### 🔍 Busco: {sol[0]}")
                        st.write(f"_{sol[2]}_")
                        st.caption(f"Solicitado por: {sol[3]}")
                    with c2:
                        st.metric("Ofrece pagar", f"${sol[1]}")
                        msg = f"Hola {sol[3]}, vi que buscas un {sol[0]}, yo tengo uno."
                        link = f"https://wa.me/{sol[4]}?text={msg.replace(' ', '%20')}"
                        st.link_button("¡Yo lo tengo! 🙋‍♂️", link, type="primary")
        else:
            st.info("Nadie está buscando nada por ahora.")

    # 4. PANTALLA MI PERFIL (GESTIÓN COMPLETA)
    elif opcion == "Mi Perfil":
        st.title("👤 Gestión de Perfil")
        
        with st.container(border=True):
            col_a, col_b = st.columns(2)
            col_a.write(f"**Nombre:** {usuario[1]}")
            col_a.write(f"**Email:** {usuario[0]}")
            col_b.write(f"**WhatsApp:** {usuario[3]}")
            col_b.write(f"**Carrera:** {usuario[4]}")

        # === SECCIÓN 1: MIS PRODUCTOS ===
        st.divider()
        st.subheader("📦 Mis Publicaciones (Ventas)")

        mis_items = run_query("SELECT id, nombre, descripcion, precio FROM productos WHERE email_dueño = ?", (usuario[0],), return_data=True)

        if mis_items:
            # Diccionario: "Nombre ($Precio)" -> Datos
            dict_prods = {f"{item[1]} (${item[3]})": item for item in mis_items}
            sel_prod = st.selectbox("Selecciona un producto para editar:", list(dict_prods.keys()))
            
            dat_prod = dict_prods[sel_prod] # Recuperar datos reales
            
            with st.form("edit_producto"):
                st.write(f"Editando: **{dat_prod[1]}**")
                n_nom = st.text_input("Nombre", value=dat_prod[1])
                n_desc = st.text_area("Descripción", value=dat_prod[2])
                n_pre = st.number_input("Precio", value=dat_prod[3], step=500)
                
                if st.form_submit_button("💾 Guardar Cambios Producto"):
                    run_query("UPDATE productos SET nombre=?, descripcion=?, precio=? WHERE id=?", 
                             (n_nom, n_desc, n_pre, dat_prod[0]))
                    st.success("Producto actualizado.")
                    time.sleep(1)
                    st.rerun()

            if st.button("🗑️ Eliminar Producto", key="borrar_prod"):
                run_query("DELETE FROM productos WHERE id=?", (dat_prod[0],))
                st.warning("Producto eliminado.")
                time.sleep(1)
                st.rerun()
        else:
            st.info("No tienes productos publicados.")

        # === SECCIÓN 2: MIS SOLICITUDES (NUEVO) ===
        st.divider()
        st.subheader("🙋‍♂️ Mis Solicitudes (Búsquedas)")
        
        mis_sols = run_query("SELECT id, titulo, descripcion, presupuesto FROM solicitudes WHERE email_solicitante = ?", (usuario[0],), return_data=True)
        
        if mis_sols:
            # Diccionario: "Titulo ($Presupuesto)" -> Datos
            dict_sols = {f"{s[1]} (${s[3]})": s for s in mis_sols}
            sel_sol = st.selectbox("Selecciona una solicitud para editar:", list(dict_sols.keys()))
            
            dat_sol = dict_sols[sel_sol]
            
            with st.form("edit_solicitud"):
                st.write(f"Editando: **{dat_sol[1]}**")
                n_tit = st.text_input("Título", value=dat_sol[1])
                n_det = st.text_area("Detalles", value=dat_sol[2])
                n_pres = st.number_input("Presupuesto", value=dat_sol[3], step=500)
                
                if st.form_submit_button("💾 Guardar Cambios Solicitud"):
                    run_query("UPDATE solicitudes SET titulo=?, descripcion=?, presupuesto=? WHERE id=?", 
                             (n_tit, n_det, n_pres, dat_sol[0]))
                    st.success("Solicitud actualizada.")
                    time.sleep(1)
                    st.rerun()
            
            if st.button("🗑️ Eliminar Solicitud", key="borrar_sol"):
                run_query("DELETE FROM solicitudes WHERE id=?", (dat_sol[0],))
                st.warning("Solicitud eliminada.")
                time.sleep(1)
                st.rerun()
        else:
            st.info("No tienes solicitudes activas.")