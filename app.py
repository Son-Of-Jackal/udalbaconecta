import streamlit as st
import sqlite3
import pandas as pd
import time
import hashlib
from datetime import datetime

# ==========================================
#           CONFIGURACIÓN INICIAL
# ==========================================
st.set_page_config(page_title="Alba Conecta", page_icon="🎓", layout="centered")

# Estilos CSS
st.markdown("""
<style>
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    
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
    
    /* Estilo para mensajes de chat */
    .stChatMessage {
        border-radius: 10px;
        padding: 10px;
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
                    fecha TEXT,
                    FOREIGN KEY(email_dueño) REFERENCES usuarios(email))''')
    
    # Tabla SOLICITUDES
    c.execute('''CREATE TABLE IF NOT EXISTS solicitudes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    titulo TEXT,
                    presupuesto INTEGER,
                    descripcion TEXT,
                    email_solicitante TEXT,
                    fecha TEXT,
                    FOREIGN KEY(email_solicitante) REFERENCES usuarios(email))''')
    
    # --- NUEVA TABLA: MENSAJES ---
    c.execute('''CREATE TABLE IF NOT EXISTS mensajes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    remitente TEXT,
                    destinatario TEXT,
                    mensaje TEXT,
                    fecha_hora TEXT,
                    FOREIGN KEY(remitente) REFERENCES usuarios(email),
                    FOREIGN KEY(destinatario) REFERENCES usuarios(email))''')
    
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

LISTA_CARRERAS = ["Ing. Civil Minas", "Ing. Civil Industrial", "Enfermería", "Derecho", "Geología", "Otras"]

# ==========================================
#           INTERFAZ GRÁFICA
# ==========================================

# --- ESCENARIO A: NO ESTÁ LOGUEADO ---
if st.session_state['usuario_actual'] is None:
    try:
        st.sidebar.image("logo.png", use_container_width=True)
    except:
        st.sidebar.title("🎓 ALBA")
    st.markdown("<h1 style='text-align: center; color: #e6b800;'>🎓 Alba Conecta</h1>", unsafe_allow_html=True)
    
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
        new_carrera = st.selectbox("Carrera", LISTA_CARRERAS)
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
    
    # Notificación de mensajes nuevos (Contar mensajes recibidos hoy)
    hoy = datetime.now().strftime("%Y-%m-%d")
    msg_nuevos = run_query("SELECT COUNT(*) FROM mensajes WHERE destinatario = ? AND fecha_hora LIKE ?", (usuario[0], f"{hoy}%"), return_data=True)[0][0]
    if msg_nuevos > 0:
        st.sidebar.info(f"📩 Tienes mensajes de hoy")

    if st.sidebar.button("Cerrar Sesión"):
        st.session_state['usuario_actual'] = None
        st.rerun()
    st.sidebar.divider()
    
    # MENU CON CHAT
    opcion = st.sidebar.radio("Navegación", ["Catálogo", "Publicar Aviso", "Muro de Solicitudes", "💬 Mensajería", "Mi Perfil"])

    # 1. CATÁLOGO
    if opcion == "Catálogo":
        st.title("🛒 Catálogo General")
        sql = """SELECT p.nombre, p.descripcion, p.precio, p.foto, u.nombre, p.email_dueño, p.fecha 
                 FROM productos p 
                 JOIN usuarios u ON p.email_dueño = u.email 
                 WHERE p.estado='Disponible' ORDER BY p.id DESC"""
        items = run_query(sql, return_data=True)
        
        if items:
            for item in items:
                # item: 0:nom, 1:desc, 2:pre, 3:foto, 4:nom_dueño, 5:email_dueño, 6:fecha
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
                        st.caption(f"📅 {item[6]} | Vendedor: {item[4]}")
                        st.metric("Precio", f"${item[2]}")
                        
                        # --- BOTÓN DE CHAT INTERNO ---
                        # Si soy el dueño, no me muestro el botón
                        if item[5] != usuario[0]:
                            with st.popover(f"📩 Enviar mensaje a {item[4]}"):
                                with st.form(f"msg_form_{item[0]}"):
                                    txt_msg = st.text_area("Escribe tu consulta:")
                                    if st.form_submit_button("Enviar"):
                                        ahora = datetime.now().strftime("%Y-%m-%d %H:%M")
                                        msg_final = f"Hola, me interesa tu producto '{item[0]}'. {txt_msg}"
                                        run_query("INSERT INTO mensajes (remitente, destinatario, mensaje, fecha_hora) VALUES (?,?,?,?)",
                                                 (usuario[0], item[5], msg_final, ahora))
                                        st.success("Mensaje enviado! Revisa tu buzón.")
        else:
            st.info("No hay productos disponibles.")

    # 2. PUBLICAR
    elif opcion == "Publicar Aviso":
        st.title("📢 Publicar Artículo")
        with st.form("form_prod"):
            nombre = st.text_input("¿Qué arriendas?")
            desc = st.text_area("Descripción")
            precio = st.number_input("Precio diario", min_value=0, step=500)
            foto = st.file_uploader("Foto del producto", type=['jpg','png'])
            if st.form_submit_button("Publicar"):
                fecha_hoy = datetime.now().strftime("%d-%m-%Y")
                foto_blob = foto.getvalue() if foto else None
                run_query("INSERT INTO productos (nombre, descripcion, precio, estado, email_dueño, foto, fecha) VALUES (?,?,?,?,?,?,?)",
                         (nombre, desc, precio, "Disponible", usuario[0], foto_blob, fecha_hoy))
                st.success("¡Publicado!")
                time.sleep(1)
                st.rerun()

    # 3. SOLICITUDES
    elif opcion == "Muro de Solicitudes":
        st.title("🙋‍♂️ Muro de Solicitudes")
        with st.expander("➕ Crear nueva solicitud"):
            with st.form("form_solicitud"):
                titulo = st.text_input("¿Qué necesitas?")
                presupuesto = st.number_input("¿Cuánto ofreces? ($)", min_value=0, step=500)
                desc_sol = st.text_area("Detalles")
                if st.form_submit_button("Publicar Solicitud"):
                    fecha_hoy = datetime.now().strftime("%d-%m-%Y")
                    run_query("INSERT INTO solicitudes (titulo, presupuesto, descripcion, email_solicitante, fecha) VALUES (?,?,?,?,?)",
                             (titulo, presupuesto, desc_sol, usuario[0], fecha_hoy))
                    st.success("¡Solicitud publicada!")
                    time.sleep(1)
                    st.rerun()
        st.divider()
        sql_sol = """SELECT s.titulo, s.presupuesto, s.descripcion, u.nombre, s.email_solicitante, s.fecha 
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
                        st.caption(f"📅 {sol[5]} | Solicitado por: {sol[3]}")
                    with c2:
                        st.metric("Ofrece", f"${sol[1]}")
                        # --- CHAT INTERNO EN SOLICITUDES ---
                        if sol[4] != usuario[0]:
                            with st.popover(f"📩 Responder a {sol[3]}"):
                                with st.form(f"sol_form_{sol[0]}"):
                                    txt_msg = st.text_area("Mensaje:")
                                    if st.form_submit_button("Enviar"):
                                        ahora = datetime.now().strftime("%Y-%m-%d %H:%M")
                                        msg_final = f"Hola, vi que buscas '{sol[0]}'. {txt_msg}"
                                        run_query("INSERT INTO mensajes (remitente, destinatario, mensaje, fecha_hora) VALUES (?,?,?,?)",
                                                 (usuario[0], sol[4], msg_final, ahora))
                                        st.success("Enviado!")
        else:
            st.info("Nadie busca nada por ahora.")

    # 4. === NUEVO: SISTEMA DE MENSAJERÍA (CHAT) ===
    elif opcion == "💬 Mensajería":
        st.title("💬 Tu Buzón")
        
        # 1. Encontrar personas con las que he hablado (Enviados o Recibidos)
        sql_contactos = """
            SELECT DISTINCT u.email, u.nombre 
            FROM usuarios u
            JOIN mensajes m ON u.email = m.remitente OR u.email = m.destinatario
            WHERE (m.remitente = ? OR m.destinatario = ?) AND u.email != ?
        """
        contactos = run_query(sql_contactos, (usuario[0], usuario[0], usuario[0]), return_data=True)
        
        if contactos:
            # Crear lista de nombres para seleccionar
            nombres_contactos = {c[1]: c[0] for c in contactos} # Nombre -> Email
            seleccion = st.selectbox("Selecciona una conversación:", list(nombres_contactos.keys()))
            email_otro = nombres_contactos[seleccion]
            
            # 2. Cargar mensajes con esa persona
            st.divider()
            sql_chat = """
                SELECT remitente, mensaje, fecha_hora 
                FROM mensajes 
                WHERE (remitente = ? AND destinatario = ?) OR (remitente = ? AND destinatario = ?)
                ORDER BY id ASC
            """
            chat_historia = run_query(sql_chat, (usuario[0], email_otro, email_otro, usuario[0]), return_data=True)
            
            # 3. Mostrar Chat (Estilo WhatsApp)
            chat_container = st.container(height=400) # Caja con scroll
            with chat_container:
                for msg in chat_historia:
                    es_mio = (msg[0] == usuario[0])
                    # Usamos el componente st.chat_message de Streamlit
                    with st.chat_message("user" if es_mio else "assistant", avatar="👤" if es_mio else "🎓"):
                        st.write(msg[1])
                        st.caption(msg[2])
            
            # 4. Input para responder
            with st.form("chat_input", clear_on_submit=True):
                col_txt, col_btn = st.columns([4, 1])
                nuevo_txt = col_txt.text_input("Escribe tu respuesta...", key="input_msg")
                if col_btn.form_submit_button("Enviar ➤"):
                    if nuevo_txt:
                        ahora = datetime.now().strftime("%Y-%m-%d %H:%M")
                        run_query("INSERT INTO mensajes (remitente, destinatario, mensaje, fecha_hora) VALUES (?,?,?,?)",
                                 (usuario[0], email_otro, nuevo_txt, ahora))
                        st.rerun() # Recargar para ver el mensaje nuevo
        else:
            st.info("No tienes conversaciones iniciadas. Ve al Catálogo y contacta a alguien.")

    # 5. MI PERFIL
    elif opcion == "Mi Perfil":
        st.title("👤 Mi Perfil")
        with st.expander("📝 Editar datos", expanded=True):
            with st.form("edit_p"):
                na = st.text_input("Nombre", value=usuario[1])
                wa = st.text_input("WhatsApp", value=usuario[3])
                if st.form_submit_button("Guardar"):
                    run_query("UPDATE usuarios SET nombre=?, whatsapp=? WHERE email=?", (na, wa, usuario[0]))
                    st.session_state['usuario_actual'] = run_query("SELECT * FROM usuarios WHERE email=?", (usuario[0],), True)[0]
                    st.success("Listo!")
                    time.sleep(0.5)
                    st.rerun()
        
        st.divider()
        st.subheader("📦 Mis Ventas")
        mis_p = run_query("SELECT id, nombre, precio FROM productos WHERE email_dueño=?", (usuario[0],), True)
        if mis_p:
            d_p = {f"{p[1]} (${p[2]})": p for p in mis_p}
            s_p = st.selectbox("Editar producto:", list(d_p.keys()))
            with st.form("ed_pr"):
                if st.form_submit_button("🗑️ Borrar"):
                    run_query("DELETE FROM productos WHERE id=?", (d_p[s_p][0],))
                    st.rerun()
        else:
            st.caption("Nada publicado.")