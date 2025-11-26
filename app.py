import streamlit as st
import sqlite3
import pandas as pd
import time
import hashlib

# --- 1. CONFIGURACIÓN ---
st.set_page_config(page_title="Arriendos UDALBA", page_icon="🎓", layout="centered")

# ==========================================
#           CONFIGURACIÓN ESTÉTICA
# ==========================================

# 1. Ocultar elementos de Streamlit y personalizar botones
st.markdown("""
<style>
    /* Ocultar el menú de hamburguesa y el pie de página de Streamlit */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    
    /* Personalizar el botón principal (Azul Institucional UDALBA) */
    div.stButton > button:first-child {
        background-color: #002e6e; 
        color: white;
        border-radius: 8px;
        border: none;
        font-weight: bold;
    }
    div.stButton > button:first-child:hover {
        background-color: #001a40; /* Un azul más oscuro al pasar el mouse */
        color: white;
    }
    
    /* Personalizar los inputs de texto */
    .stTextInput > div > div > input {
        border-radius: 8px;
    }
</style>
""", unsafe_allow_html=True)

# 2. Poner el Logo Oficial en la barra lateral
st.sidebar.image("logoudalba.png", use_container_width=True)
st.sidebar.markdown("---") # Una línea divisora elegante

# --- 2. GESTIÓN DE BASE DE DATOS ---
def make_hashes(password):
    return hashlib.sha256(str.encode(password)).hexdigest()

def check_hashes(password, hashed_text):
    if make_hashes(password) == hashed_text:
        return hashed_text
    return False

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
    
    # Tabla PRODUCTOS (Ahora vinculada al email del usuario)
    c.execute('''CREATE TABLE IF NOT EXISTS productos (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    nombre TEXT,
                    descripcion TEXT,
                    precio INTEGER,
                    estado TEXT,
                    email_dueño TEXT,
                    foto BLOB,
                    FOREIGN KEY(email_dueño) REFERENCES usuarios(email))''')
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

# --- 3. GESTIÓN DE SESIÓN ---
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
        return False # Probablemente el email ya existe

# ==========================================
#              INTERFAZ GRÁFICA
# ==========================================

# --- ESCENARIO A: NO ESTÁ LOGUEADO ---
if st.session_state['usuario_actual'] is None:
    st.title("🎓 Acceso UDALBA")
    
    menu_login = st.sidebar.selectbox("Selecciona opción", ["Iniciar Sesión", "Registrarse"])
    
    if menu_login == "Iniciar Sesión":
        st.subheader("Ingresa a tu cuenta")
        email = st.text_input("Correo Institucional")
        password = st.text_input("Contraseña", type='password')
        
        if st.button("Entrar"):
            user = login_user(email, password)
            if user:
                # user es una lista de tuplas: [(email, nombre, pass, wsp, carrera)]
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
                    st.success("¡Cuenta creada! Ahora ve a 'Iniciar Sesión'")
                else:
                    st.error("Ese correo ya está registrado.")
            else:
                st.warning("Debes usar un correo institucional.")

# --- ESCENARIO B: USUARIO LOGUEADO (DENTRO DE LA APP) ---
else:
    # Datos del usuario activo
    usuario = st.session_state['usuario_actual'] 
    # usuario = (0:email, 1:nombre, 2:pass, 3:wsp, 4:carrera)

    # Sidebar con datos del usuario
    st.sidebar.image("https://img.icons8.com/bubbles/100/user.png")
    st.sidebar.write(f"Hola, **{usuario[1]}**")
    st.sidebar.caption(f"{usuario[4]}")
    
    if st.sidebar.button("Cerrar Sesión"):
        st.session_state['usuario_actual'] = None
        st.rerun()
    
    st.sidebar.divider()
    opcion = st.sidebar.radio("Navegación", ["Catálogo", "Publicar Aviso", "Mi Perfil"])

    # 1. PANTALLA CATÁLOGO (MARKETPLACE)
    if opcion == "Catálogo":
        st.title("🛒 Catálogo General")
        st.caption("Mira lo que ofrecen tus compañeros")
        
        # Traemos productos + datos del dueño (JOIN)
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
                        if item[3]: # Si tiene foto
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
                        st.link_button("Contactar por WhatsApp 💬", link)
        else:
            st.info("No hay productos disponibles.")

    # 2. PANTALLA PUBLICAR
    elif opcion == "Publicar Aviso":
        st.title("📢 Publicar Artículo")
        
        with st.form("form_prod"):
            nombre = st.text_input("¿Qué arriendas?")
            desc = st.text_area("Descripción")
            precio = st.number_input("Precio diario", min_value=0, step=500)
            foto = st.file_uploader("Foto del producto", type=['jpg','png'])
            
            if st.form_submit_button("Publicar"):
                foto_blob = foto.getvalue() if foto else None
                # Guardamos usando el email del usuario logueado (usuario[0])
                run_query("INSERT INTO productos (nombre, descripcion, precio, estado, email_dueño, foto) VALUES (?,?,?,?,?,?)",
                         (nombre, desc, precio, "Disponible", usuario[0], foto_blob))
                st.success("¡Publicado!")
                time.sleep(1)
                st.rerun()

    # 3. PANTALLA MI PERFIL
    elif opcion == "Mi Perfil":
        st.title("👤 Mi Perfil")
        
        col_A, col_B = st.columns(2)
        col_A.markdown(f"**Nombre:** {usuario[1]}")
        col_A.markdown(f"**Email:** {usuario[0]}")
        col_B.markdown(f"**WhatsApp:** {usuario[3]}")
        col_B.markdown(f"**Carrera:** {usuario[4]}")
        
        st.divider()
        st.subheader("📦 Mis Publicaciones")
        
        # Buscar SOLO mis productos
        mis_items = run_query("SELECT id, nombre, precio, estado FROM productos WHERE email_dueño = ?", (usuario[0],), return_data=True)
        
        if mis_items:
            df = pd.DataFrame(mis_items, columns=["ID", "Producto", "Precio", "Estado"])
            st.dataframe(df, hide_index=True, use_container_width=True)
            
            id_borrar = st.number_input("ID para eliminar", min_value=0)
            if st.button("Eliminar mi publicación"):
                # Verificar que el producto sea mío antes de borrar
                check = run_query("SELECT * FROM productos WHERE id=? AND email_dueño=?", (id_borrar, usuario[0]), return_data=True)
                if check:
                    run_query("DELETE FROM productos WHERE id=?", (id_borrar,))
                    st.success("Eliminado.")
                    st.rerun()
                else:
                    st.error("Ese producto no es tuyo o no existe.")
        else:
            st.info("Aún no has publicado nada.")