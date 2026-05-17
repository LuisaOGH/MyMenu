import streamlit as st
import pandas as pd
import random
import re
import os
from collections import defaultdict

# --- 1. CONFIGURACIÓN Y ESTILO ---
st.set_page_config(page_title="MyMenú", page_icon="🍴", layout="wide")

# URLs de activos en GitHub
LOGO_RECORTADO = "https://raw.githubusercontent.com/LuisaOGH/MyMenu/main/logo_recortado.jpg"
LOGO_FULL = "https://raw.githubusercontent.com/LuisaOGH/MyMenu/main/logo.png"
BTN_CONFIG = "https://raw.githubusercontent.com/LuisaOGH/MyMenu/main/boton_configurar.png"

def local_css():
    st.markdown(f"""
    <style>
    :root {{
        --bg-cream: #F7F3E9;
    }}
    .stApp {{ background-color: var(--bg-cream); }}
    
    /* Centrado de Logo */
    .logo-container {{
        display: flex;
        justify-content: center;
        padding: 10px;
    }}
    .logo-img {{ width: 150px; border-radius: 50%; }}

    /* Estilo para que la imagen parezca un botón */
    .img-button {{
        cursor: pointer;
        display: block;
        margin-left: auto;
        margin-right: auto;
        transition: transform 0.2s;
    }}
    .img-button:hover {{ transform: scale(1.05); }}
    
    /* Ocultar alertas de Streamlit */
    .element-container:has(.stAlert) {{ display: none; }}
    </style>
    """, unsafe_allow_html=True)

local_css()

# --- 2. FUNCIONES DE CARGA SEGURA ---
def cargar_csv_seguro(nombre_archivo):
    encodings = ['utf-8-sig', 'utf-8', 'latin1', 'cp1252']
    for enc in encodings:
        try:
            return pd.read_csv(nombre_archivo, encoding=enc, sep=None, engine='python')
        except:
            continue
    return None

df, df_maestro = None, None
if os.path.exists("recetas_mymenu.csv") and os.path.exists("maestro_ingredientes.csv"):
    df = cargar_csv_seguro("recetas_mymenu.csv")
    df_maestro = cargar_csv_seguro("maestro_ingredientes.csv")

# --- 3. LÓGICA DE INTERFAZ ---

# Siempre mostramos el logo pequeño arriba si ya estamos navegando
if 'menu' in st.session_state:
    st.markdown(f'<div class="logo-container"><img src="{LOGO_RECORTADO}" class="logo-img"></div>', unsafe_allow_html=True)

if df is not None:
    # Sidebar (Menú de selección)
    with st.sidebar:
        st.header("Configuración")
        modo = st.selectbox("¿Cómo planificamos?", ["Saludable (A)", "Inventario (I)", "Orden (O)"])
        comensales = st.slider("Comensales", 1, 6, 2)
        
        tengo = []
        if modo == "Inventario (I)":
            tengo = st.multiselect("¿Qué tienes en la cocina?", sorted(df_maestro.iloc[:,0].unique().tolist()))

        if st.button("🚀 GENERAR MI PLAN"):
            # Aquí irían tus motores A e I (asumiendo que están definidos arriba)
            # st.session_state['menu'] = motor_A_avanzado(df) ... 
            st.session_state['comensales'] = comensales
            st.rerun()

    # --- PANTALLA PRINCIPAL ---
    if 'menu' not in st.session_state or st.session_state['menu'] is None:
        # VISTA INICIAL: Logo grande + Botón para configurar
        st.image(LOGO_FULL, use_container_width=True)
        
        st.write("---")
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            st.markdown("### ¡Bienvenida! Comienza tu plan aquí:")
            # Usamos la imagen como un botón que abre el sidebar (instrucción visual)
            st.image(BTN_CONFIG, use_container_width=True)
            st.info("👈 Selecciona tus preferencias en el menú de la izquierda para generar tu menú personalizado.")
    else:
        # VISTA DEL MENÚ GENERADO
        st.header("Tu Plan Semanal")
        # ... (Aquí va el resto de tu código de renderizado de c1, c2, c3 que ya tienes)
else:
    st.error("Por favor, verifica que los archivos CSV estén en la carpeta raíz.")
