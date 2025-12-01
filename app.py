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
    
    div.stButton > button:contains("Eliminar"), 
    div.stButton > button:contains("Dejar de seguir"),
    div.stButton > button:contains("Borrar") {
        background-color: #ff4b4b !important;
        color: white !important;
    }
    
    div.stButton > button:contains("Pausar"),
    div.stButton > button:contains("Reactivar") {
        background-color: #f0ad4e !important; 
        color: white !important;
    }

    .stChatMessage {
        border-radius: 10px;
        padding: 10px;
    }
    
    /* Estilo para la notificación roja */
    .notify-badge {
        background-color: #ff4b4b;
        color: white;
        padding: 2px 8px;
        border-radius: 10px;
        font-size: 0.8em;
        font-weight: bold;
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
    
    c.execute('''CREATE TABLE IF NOT EXISTS usuarios (
                    email TEXT PRIMARY KEY,
                    nombre TEXT,
                    password TEXT,
                    whatsapp TEXT,
                    carrera TEXT,
                    pregunta TEXT,
                    respuesta TEXT)''')
    
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
    
    c.execute('''CREATE TABLE IF NOT EXISTS solicitudes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    titulo TEXT,
                    presupuesto INTEGER,
                    descripcion TEXT,
                    email_solicitante TEXT,
                    fecha TEXT,
                    FOREIGN KEY(email_solicitante) REFERENCES usuarios(email))''')
    
    # --- TABLA MENSAJES ACTUALIZADA (Columna 'leido') ---
    c.execute('''CREATE TABLE IF NOT EXISTS mensajes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    remitente TEXT,
                    destinatario TEXT,
                    mensaje TEXT,
                    fecha_hora TEXT,
                    leido INTEGER DEFAULT 0,
                    FOREIGN KEY(remitente) REFERENCES usuarios(email),
                    FOREIGN KEY(destinatario) REFERENCES usuarios(email))''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS resenas (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    calificador TEXT,
                    calificado TEXT,
                    estrellas INTEGER,
                    comentario TEXT,
                    fecha TEXT,
                    FOREIGN KEY(calificador) REFERENCES usuarios(email),
                    FOREIGN KEY(calificado) REFERENCES usuarios(email))''')

    c.execute('''CREATE TABLE IF NOT EXISTS seguidores (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    seguidor TEXT,
                    seguido TEXT,
                    FOREIGN KEY(seguidor) REFERENCES usuarios(email),
                    FOREIGN KEY(seguido) REFERENCES usuarios(email))''')
    
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
#           LÓGICA DE NEGOCIO
# ==========================================
if 'usuario_actual' not in st.session_state:
    st.session_state['usuario_actual'] = None

def login_user(email, password):
    hashed_pswd = make_hashes(password)
    result = run_query("SELECT * FROM usuarios WHERE email = ? AND password = ?", (email, hashed_pswd), return_data=True)
    return result

def register_user(email, nombre, password, whatsapp, carrera, pregunta, respuesta):
    try:
        hashed_pswd = make_hashes(password)
        hashed_resp = make_hashes(respuesta.lower().strip())
        run_query("INSERT INTO usuarios (email, nombre, password, whatsapp, carrera, pregunta, respuesta) VALUES (?,?,?,?,?,?,?)", 
                 (email, nombre, hashed_pswd, whatsapp, carrera, pregunta, hashed_resp))
        return True
    except:
        return False

def get_reputacion(email_usuario):
    res = run_query("SELECT AVG(estrellas), COUNT(*) FROM resenas WHERE calificado = ?", (email_usuario,), return_data=True)
    if res and res[0][0]:
        promedio = round(res[0][0], 1)
        total = res[0][1]
        estrellas_str = "⭐" * int(promedio)
        return f"{promedio} {estrellas_str} ({total})"
    return "🆕 Nuevo"

def check_follow(seguidor, seguido):
    res = run_query("SELECT * FROM seguidores WHERE seguidor=? AND seguido=?", (seguidor, seguido), return_data=True)
    return True if res else False

def get_followers_count(email):
    res = run_query("SELECT COUNT(*) FROM seguidores WHERE seguido=?", (email,), return_data=True)
    return res[0][0]

def get_following_count(email):
    res = run_query("SELECT COUNT(*) FROM seguidores WHERE seguidor=?", (email,), return_data=True)
    return res[0][0]

LISTA_CARRERAS = ["Ing. Civil Minas", "Ing. Civil Industrial", "Enfermería", "Derecho", "Geología", "Otras"]
LISTA_PREGUNTAS = ["Nombre de tu primera mascota", "Ciudad donde naciste", "Nombre de tu madre", "Tu comida favorita", "Nombre de tu colegio"]

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
    
    menu_login = st.sidebar.selectbox("Bienvenido", ["Iniciar Sesión", "Registrarse", "Recuperar Contraseña"])
    
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
        st.markdown("---")
        st.write("🔐 **Seguridad**")
        new_preg = st.selectbox("Elige una pregunta de seguridad", LISTA_PREGUNTAS)
        new_resp = st.text_input("Tu respuesta")
        
        if st.button("Crear Cuenta"):
            if "@udalba.cl" in new_email and new_resp:
                exito = register_user(new_email, new_name, new_pass, new_wsp, new_carrera, new_preg, new_resp)
                if exito:
                    st.success("¡Cuenta creada! Ahora inicia sesión.")
                else:
                    st.error("Ese correo ya está registrado.")
            else:
                st.warning("Revisa el correo y la pregunta de seguridad.")

    elif menu_login == "Recuperar Contraseña":
        st.subheader("🔐 Recuperación de Acceso")
        rec_email = st.text_input("Ingresa tu correo registrado")
        if rec_email:
            datos_user = run_query("SELECT pregunta, respuesta FROM usuarios WHERE email = ?", (rec_email,), return_data=True)
            if datos_user:
                st.info(f"Pregunta: **{datos_user[0][0]}**")
                rec_respuesta = st.text_input("Tu respuesta", type="password")
                new_pass_1 = st.text_input("Nueva Contraseña", type="password")
                new_pass_2 = st.text_input("Repetir Contraseña", type="password")
                if st.button("Restablecer"):
                    hash_input = make_hashes(rec_respuesta.lower().strip())
                    if hash_input == datos_user[0][1]:
                        if new_pass_1 == new_pass_2 and len(new_pass_1) > 0:
                            new_pass_hash = make_hashes(new_pass_1)
                            run_query("UPDATE usuarios SET password = ? WHERE email = ?", (new_pass_hash, rec_email))
                            st.success("✅ Contraseña actualizada.")
                        else:
                            st.error("Las contraseñas no coinciden.")
                    else:
                        st.error("❌ Respuesta incorrecta.")
            else:
                st.warning("Correo no encontrado.")

# --- ESCENARIO B: USUARIO LOGUEADO ---
else:
    usuario = st.session_state['usuario_actual']
    
    try:
        st.sidebar.image("logo.png", use_container_width=True)
    except:
        pass
        
    st.sidebar.write(f"Hola, **{usuario[1]}**")
    
    # === SISTEMA DE NOTIFICACIONES INTELIGENTE ===
    # Contamos solo los mensajes donde destinatario soy YO y leido = 0
    msg_nuevos = run_query("SELECT COUNT(*) FROM mensajes WHERE destinatario = ? AND leido = 0", (usuario[0],), return_data=True)[0][0]
    
    if msg_nuevos > 0:
        st.sidebar.error(f"🔔 Tienes {msg_nuevos} mensaje(s) nuevo(s)")
    else:
        st.sidebar.success("📭 Sin mensajes nuevos")

    if st.sidebar.button("Cerrar Sesión"):
        st.session_state['usuario_actual'] = None
        st.rerun()
    st.sidebar.divider()
    
    opcion = st.sidebar.radio("Navegación", ["Catálogo", "Publicar Aviso", "Muro de Solicitudes", "💬 Mensajería", "Mi Perfil"])

    if opcion == "Catálogo":
        st.title("🛒 Catálogo General")
        sql = """SELECT p.id, p.nombre, p.descripcion, p.precio, p.foto, u.nombre, p.email_dueño, p.fecha 
                 FROM productos p 
                 JOIN usuarios u ON p.email_dueño = u.email 
                 WHERE p.estado='Disponible' ORDER BY p.id DESC"""
        items = run_query(sql, return_data=True)
        
        if items:
            for item in items:
                with st.container(border=True):
                    c1, c2 = st.columns([1, 2])
                    with c1:
                        if item[4]:
                            st.image(item[4], use_container_width=True)
                        else:
                            st.text("📷 Sin foto")
                    with c2:
                        st.subheader(item[1])
                        c_rep, c_follow = st.columns([2,1])
                        reputacion = get_reputacion(item[6])
                        c_rep.caption(f"Vendedor: {item[5]} | {reputacion}")
                        
                        if item[6] != usuario[0]:
                            ya_sigue = check_follow(usuario[0], item[6])
                            if ya_sigue:
                                if c_follow.button("Dejar de seguir", key=f"unfol_{item[0]}"):
                                    run_query("DELETE FROM seguidores WHERE seguidor=? AND seguido=?", (usuario[0], item[6]))
                                    st.rerun()
                            else:
                                if c_follow.button("Seguir ➕", key=f"fol_{item[0]}"):
                                    run_query("INSERT INTO seguidores (seguidor, seguido) VALUES (?,?)", (usuario[0], item[6]))
                                    st.success(f"Siguiendo a {item[5]}")
                                    time.sleep(0.5)
                                    st.rerun()

                        st.write(f"_{item[2]}_")
                        st.caption(f"📅 {item[7]}")
                        st.metric("Precio", f"${item[3]}")
                        
                        col_chat, col_rate = st.columns(2)
                        
                        if item[6] != usuario[0]:
                            with col_chat:
                                with st.popover(f"📩 Chat"):
                                    with st.form(f"msg_form_{item[0]}"):
                                        txt_msg = st.text_area("Mensaje:")
                                        if st.form_submit_button("Enviar"):
                                            ahora = datetime.now().strftime("%Y-%m-%d %H:%M")
                                            msg_final = f"Hola, me interesa '{item[1]}'. {txt_msg}"
                                            # Enviamos con leido=0 (default)
                                            run_query("INSERT INTO mensajes (remitente, destinatario, mensaje, fecha_hora) VALUES (?,?,?,?)",
                                                     (usuario[0], item[6], msg_final, ahora))
                                            st.success("Enviado!")
                            
                            with col_rate:
                                with st.popover(f"⭐ Calificar"):
                                    ya_califico = run_query("SELECT id FROM resenas WHERE calificador=? AND calificado=?", 
                                                           (usuario[0], item[6]), return_data=True)
                                    if ya_califico:
                                        st.warning(f"Ya has calificado a {item[5]}.")
                                    else:
                                        st.write(f"Calificar a **{item[5]}**")
                                        with st.form(f"rate_form_{item[0]}"):
                                            stars = st.slider("Estrellas", 1, 5, 5)
                                            comment = st.text_input("Comentario")
                                            if st.form_submit_button("Enviar Reseña"):
                                                fecha_hoy = datetime.now().strftime("%d-%m-%Y")
                                                run_query("INSERT INTO resenas (calificador, calificado, estrellas, comentario, fecha) VALUES (?,?,?,?,?)",
                                                         (usuario[0], item[6], stars, comment, fecha_hoy))
                                                st.success("Gracias!")
                                                time.sleep(1)
                                                st.rerun()
        else:
            st.info("No hay productos disponibles.")

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
        sql_sol = """SELECT s.titulo, s.presupuesto, s.descripcion, u.nombre, s.email_solicitante, s.fecha, s.id 
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
                        c_user, c_fol = st.columns([2,1])
                        c_user.caption(f"📅 {sol[5]} | {sol[3]}")
                        if sol[4] != usuario[0]:
                            ya_sigue = check_follow(usuario[0], sol[4])
                            if ya_sigue:
                                if c_fol.button("Dejar de seguir", key=f"unfol_s_{sol[6]}"):
                                    run_query("DELETE FROM seguidores WHERE seguidor=? AND seguido=?", (usuario[0], sol[4]))
                                    st.rerun()
                            else:
                                if c_fol.button("Seguir ➕", key=f"fol_s_{sol[6]}"):
                                    run_query("INSERT INTO seguidores (seguidor, seguido) VALUES (?,?)", (usuario[0], sol[4]))
                                    st.rerun()
                    with c2:
                        st.metric("Ofrece", f"${sol[1]}")
                        if sol[4] != usuario[0]:
                            with st.popover(f"📩 Responder"):
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

    elif opcion == "💬 Mensajería":
        st.title("💬 Tu Buzón")
        sql_contactos = """
            SELECT DISTINCT u.email, u.nombre 
            FROM usuarios u
            JOIN mensajes m ON u.email = m.remitente OR u.email = m.destinatario
            WHERE (m.remitente = ? OR m.destinatario = ?) AND u.email != ?
        """
        contactos = run_query(sql_contactos, (usuario[0], usuario[0], usuario[0]), return_data=True)
        if contactos:
            nombres_contactos = {c[1]: c[0] for c in contactos} 
            seleccion = st.selectbox("Selecciona una conversación:", list(nombres_contactos.keys()))
            email_otro = nombres_contactos[seleccion]
            
            # --- MARCAR COMO LEÍDOS AL ENTRAR AL CHAT ---
            # Si hay mensajes de ESA persona para MÍ que están en 0, los paso a 1
            run_query("UPDATE mensajes SET leido = 1 WHERE remitente = ? AND destinatario = ? AND leido = 0", (email_otro, usuario[0]))
            
            st.divider()
            sql_chat = """
                SELECT remitente, mensaje, fecha_hora 
                FROM mensajes 
                WHERE (remitente = ? AND destinatario = ?) OR (remitente = ? AND destinatario = ?)
                ORDER BY id ASC
            """
            chat_historia = run_query(sql_chat, (usuario[0], email_otro, email_otro, usuario[0]), return_data=True)
            chat_container = st.container(height=400)
            with chat_container:
                for msg in chat_historia:
                    es_mio = (msg[0] == usuario[0])
                    with st.chat_message("user" if es_mio else "assistant", avatar="👤" if es_mio else "🎓"):
                        st.write(msg[1])
                        st.caption(msg[2])
            with st.form("chat_input", clear_on_submit=True):
                col_txt, col_btn = st.columns([4, 1])
                nuevo_txt = col_txt.text_input("Escribe tu respuesta...", key="input_msg")
                if col_btn.form_submit_button("Enviar ➤"):
                    if nuevo_txt:
                        ahora = datetime.now().strftime("%Y-%m-%d %H:%M")
                        run_query("INSERT INTO mensajes (remitente, destinatario, mensaje, fecha_hora, leido) VALUES (?,?,?,?,?)",
                                 (usuario[0], email_otro, nuevo_txt, ahora, 0))
                        st.rerun()
        else:
            st.info("No tienes conversaciones iniciadas.")

    elif opcion == "Mi Perfil":
        st.title("👤 Mi Perfil")
        
        c_stats_1, c_stats_2, c_stats_3 = st.columns(3)
        mi_rep = get_reputacion(usuario[0])
        seguidores = get_followers_count(usuario[0])
        seguidos = get_following_count(usuario[0])
        
        c_stats_1.metric("⭐ Reputación", mi_rep.split()[0])
        c_stats_2.metric("👥 Seguidores", seguidores)
        c_stats_3.metric("👀 Seguidos", seguidos)
        
        st.divider()
        
        tab_social_1, tab_social_2 = st.tabs(["👥 Mis Seguidores", "👀 A quién sigo"])
        
        with tab_social_1:
            lista_seguidores = run_query("SELECT u.nombre, u.email, u.carrera FROM usuarios u JOIN seguidores s ON u.email = s.seguidor WHERE s.seguido = ?", (usuario[0],), return_data=True)
            if lista_seguidores:
                for seg in lista_seguidores:
                    st.write(f"👤 **{seg[0]}** ({seg[2]})")
            else:
                st.caption("Aún no tienes seguidores.")
                
        with tab_social_2:
            lista_seguidos = run_query("SELECT u.nombre, u.email, u.carrera, u.whatsapp FROM usuarios u JOIN seguidores s ON u.email = s.seguido WHERE s.seguidor = ?", (usuario[0],), return_data=True)
            if lista_seguidos:
                dic_seguidos = {f"{u[0]} ({u[2]})": u for u in lista_seguidos}
                seleccionado_nombre = st.selectbox("Ver perfil de:", list(dic_seguidos.keys()))
                
                if seleccionado_nombre:
                    user_data = dic_seguidos[seleccionado_nombre]
                    email_view = user_data[1]
                    with st.container(border=True):
                        st.markdown(f"## Perfil de {user_data[0]}")
                        st.write(f"🎓 **Carrera:** {user_data[2]}")
                        st.write(f"⭐ **Reputación:** {get_reputacion(email_view)}")
                        
                        if st.button("🚫 Dejar de seguir a este usuario", key="unfol_profile"):
                            run_query("DELETE FROM seguidores WHERE seguidor=? AND seguido=?", (usuario[0], email_view))
                            st.success(f"Dejaste de seguir a {user_data[0]}")
                            time.sleep(1)
                            st.rerun()

                        st.markdown("#### 📦 Sus Productos")
                        prods_view = run_query("SELECT nombre, precio FROM productos WHERE email_dueño=? AND estado='Disponible'", (email_view,), True)
                        if prods_view:
                            for p in prods_view:
                                st.write(f"- {p[0]} (${p[1]})")
                        else:
                            st.caption("No tiene productos activos.")
                        st.markdown("#### 🙋‍♂️ Sus Solicitudes")
                        sols_view = run_query("SELECT titulo FROM solicitudes WHERE email_solicitante=?", (email_view,), True)
                        if sols_view:
                            for s in sols_view:
                                st.write(f"- Busca: {s[0]}")
                        else:
                            st.caption("No busca nada por ahora.")
            else:
                st.caption("No sigues a nadie todavía.")

        st.divider()
        with st.expander("🛠️ Gestionar mis datos personales", expanded=False):
            with st.form("edit_p"):
                na = st.text_input("Nombre", value=usuario[1])
                wa = st.text_input("WhatsApp", value=usuario[3])
                idx_carrera = 0
                if usuario[4] in LISTA_CARRERAS:
                    idx_carrera = LISTA_CARRERAS.index(usuario[4])
                nc = st.selectbox("Carrera", LISTA_CARRERAS, index=idx_carrera)
                if st.form_submit_button("Guardar Datos"):
                    run_query("UPDATE usuarios SET nombre=?, whatsapp=?, carrera=? WHERE email=?", (na, wa, nc, usuario[0]))
                    st.session_state['usuario_actual'] = run_query("SELECT * FROM usuarios WHERE email=?", (usuario[0],), True)[0]
                    st.success("Listo!")
                    time.sleep(0.5)
                    st.rerun()
            
        st.markdown("---")
        st.subheader("📦 Gestionar Productos")
        mis_p = run_query("SELECT id, nombre, descripcion, precio, estado FROM productos WHERE email_dueño=?", (usuario[0],), True)
        
        if mis_p:
            d_p = {f"{p[1]} (${p[3]}) - {p[4]}": p for p in mis_p}
            s_p = st.selectbox("Seleccionar producto:", list(d_p.keys()))
            dat = d_p[s_p]
            
            with st.form(f"edit_prod_{dat[0]}"):
                st.caption(f"Editando: {dat[1]}")
                new_nom = st.text_input("Nombre", value=dat[1])
                new_desc = st.text_area("Descripción", value=dat[2])
                new_pre = st.number_input("Precio", value=dat[3], step=500)
                
                if st.form_submit_button("💾 Guardar Cambios"):
                    run_query("UPDATE productos SET nombre=?, descripcion=?, precio=? WHERE id=?", 
                             (new_nom, new_desc, new_pre, dat[0]))
                    st.success("Producto actualizado")
                    time.sleep(1)
                    st.rerun()
            
            col_estado, col_borrar = st.columns([2,1])
            with col_estado:
                if dat[4] == "Disponible":
                    if st.button("⏸️ Pausar", key="pausar"):
                        run_query("UPDATE productos SET estado='Ocupado' WHERE id=?", (dat[0],))
                        st.rerun()
                else:
                    if st.button("▶️ Reactivar", key="reactivar"):
                        run_query("UPDATE productos SET estado='Disponible' WHERE id=?", (dat[0],))
                        st.rerun()
            with col_borrar:
                if st.button("🗑️ Borrar", key="del_prod"):
                    run_query("DELETE FROM productos WHERE id=?", (dat[0],))
                    st.rerun()
        else:
            st.caption("Nada publicado.")
            
        st.markdown("---")
        st.subheader("🙋‍♂️ Gestionar Solicitudes")
        mis_sols = run_query("SELECT id, titulo, descripcion, presupuesto FROM solicitudes WHERE email_solicitante = ?", (usuario[0],), return_data=True)
        
        if mis_sols:
            dict_sols = {f"{s[1]} (${s[3]})": s for s in mis_sols}
            sel_sol = st.selectbox("Editar solicitud:", list(dict_sols.keys()))
            dat_sol = dict_sols[sel_sol]
            
            with st.form(f"edit_sol_{dat_sol[0]}"):
                st.caption(f"Editando: {dat_sol[1]}")
                n_tit = st.text_input("Título", value=dat_sol[1])
                n_det = st.text_area("Detalles", value=dat_sol[2])
                n_pres = st.number_input("Presupuesto", value=dat_sol[3], step=500)
                
                if st.form_submit_button("💾 Guardar Cambios"):
                    run_query("UPDATE solicitudes SET titulo=?, descripcion=?, presupuesto=? WHERE id=?", 
                             (n_tit, n_det, n_pres, dat_sol[0]))
                    st.success("Solicitud actualizada")
                    time.sleep(1)
                    st.rerun()
            
            if st.button("🗑️ Borrar Solicitud", key="del_sol"):
                run_query("DELETE FROM solicitudes WHERE id=?", (dat_sol[0],))
                st.rerun()
        else:
            st.caption("Nada solicitado.")