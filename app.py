import streamlit as st
import pandas as pd
import re
import os
from collections import defaultdict

# --- 1. CONFIGURACIÓN ---
st.set_page_config(page_title="MyMenú", page_icon="🍴", layout="wide")

# URLs de tus imágenes
LOGO_FULL = "https://raw.githubusercontent.com/LuisaOGH/MyMenu/main/logo.png"
LOGO_RECORTADO = "https://raw.githubusercontent.com/LuisaOGH/MyMenu/main/logo_recortado.jpg"
BTN_CONFIG = "https://raw.githubusercontent.com/LuisaOGH/MyMenu/main/boton_configurar.png"
BTN_GENERAR = "https://raw.githubusercontent.com/LuisaOGH/MyMenu/main/boton_generarmenu.png"

# --- 2. CSS DEFINITIVO PARA BOTONES CON IMAGEN ---
st.markdown(f"""
<style>
    :root {{ --bg: #F7F3E9; }}
    .stApp {{ background-color: var(--bg); }}
    
    /* ESTILO PARA EL BOTÓN QUE ES UNA IMAGEN */
    .btn-imagen > div > button {{
        background-image: url('{BTN_CONFIG}');
        background-size: contain;
        background-repeat: no-repeat;
        background-position: center;
        background-color: transparent !important;
        border: none !important;
        height: 80px !important;
        width: 300px !important;
        color: transparent !important; /* Esconde el texto del botón */
        margin: auto;
        display: block;
    }}
    
    .btn-generar > div > button {{
        background-image: url('{BTN_GENERAR}');
        background-size: contain;
        background-repeat: no-repeat;
        background-position: center;
        background-color: transparent !important;
        border: none !important;
        height: 80px !important;
        width: 300px !important;
        color: transparent !important;
        margin: auto;
        display: block;
    }}
</style>
""", unsafe_allow_html=True)

# --- 3. GESTIÓN DE ESTADOS ---
if 'paso' not in st.session_state: st.session_state['paso'] = 'inicio'
if 'menu' not in st.session_state: st.session_state['menu'] = None

# --- 4. CARGA DE DATOS (BLINDADA) ---
@st.cache_data
def cargar_datos():
    try:
        # Probamos latin1 por si hay acentos problemáticos
        df_r = pd.read_csv("recetas_mymenu.csv", encoding='latin1', sep=None, engine='python')
        df_m = pd.read_csv("maestro_ingredientes.csv", encoding='latin1', sep=None, engine='python')
        df_r.columns = [c.strip() for c in df_r.columns]
        return df_r, df_m
    except:
        return None, None

df_recetas, df_maestro = cargar_datos()

# --- 5. NAVEGACIÓN ---

# PANTALLA 1: INICIO
if st.session_state['paso'] == 'inicio':
    st.image(LOGO_FULL, use_container_width=True)
    st.write("<br>", unsafe_allow_html=True)
    
    # Envolvemos el botón en un div con la clase CSS que creamos arriba
    st.markdown('<div class="btn-imagen">', unsafe_allow_html=True)
    if st.button("CONFIGURAR"): # El texto no se verá por el CSS
        st.session_state['paso'] = 'configurar'
        st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)

# PANTALLA 2: CONFIGURACIÓN
elif st.session_state['paso'] == 'configurar':
    st.image(LOGO_RECORTADO, width=150)
    st.header("Configura tu Menú")
    
    col1, col2 = st.columns(2)
    with col1:
        modo = st.selectbox("Método", ["Saludable (A)", "Orden (O)"])
        comensales = st.slider("Comensales", 1, 6, 2)
    
    st.write("<br>", unsafe_allow_html=True)
    
    st.markdown('<div class="btn-generar">', unsafe_allow_html=True)
    if st.button("GENERAR"):
        # Lógica de generación simplificada para probar
        if df_recetas is not None:
            # Aquí iría tu motor_A o motor_O
            st.session_state['menu'] = df_recetas.sample(5) # Ejemplo rápido
            st.session_state['paso'] = 'menu'
            st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)

# PANTALLA 3: MENÚ
elif st.session_state['paso'] == 'menu':
    st.image(LOGO_RECORTADO, width=100)
    st.title("Tu Menú")
    
    if st.session_state['menu'] is not None:
        st.dataframe(st.session_state['menu'][['Nombre', 'Ingredientes']])
    
    if st.button("VOLVER AL INICIO"):
        st.session_state['paso'] = 'inicio'
        st.rerun()
