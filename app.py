import streamlit as st
import pandas as pd
import random
import re
import os
from collections import defaultdict

# --- 1. CONFIGURACIÓN DE PÁGINA Y ESTILOS CSS ---
st.set_page_config(page_title="MyMenú", page_icon="🍴", layout="wide")

# URLs de tus archivos en GitHub (verifica que los nombres coincidan)
LOGO_RECORTADO = "https://raw.githubusercontent.com/LuisaOGH/MyMenu/main/logo_recortado.jpg"
LOGO_FULL = "https://raw.githubusercontent.com/LuisaOGH/MyMenu/main/logo.png"
BTN_CONFIG = "https://raw.githubusercontent.com/LuisaOGH/MyMenu/main/boton_configurar.png"
BTN_GENERAR = "https://raw.githubusercontent.com/LuisaOGH/MyMenu/main/boton_generarmenu.png"

def local_css():
    st.markdown(f"""
    <style>
    :root {{ --bg-cream: #F7F3E9; }}
    .stApp {{ background-color: var(--bg-cream); }}
    
    /* Contenedor para que el botón de Streamlit flote sobre la imagen */
    .btn-overlay-container {{
        position: relative;
        width: 350px;
        margin: auto;
        text-align: center;
    }}

    /* Hacemos el botón nativo de Streamlit invisible y gigante sobre la imagen */
    .btn-overlay-container div.stButton > button {{
        position: absolute;
        top: 0; left: 0;
        width: 100%; height: 100%;
        background-color: transparent !important;
        color: transparent !important;
        border: none !important;
        z-index: 999;
        cursor: pointer;
    }}

    .logo-container {{ display: flex; justify-content: center; padding: 20px; }}
    .logo-img {{ width: 140px; border-radius: 50%; }}
    </style>
    """, unsafe_allow_html=True)

local_css()

# --- 2. GESTIÓN DE ESTADOS Y NAVEGACIÓN ---
if 'paso' not in st.session_state: st.session_state['paso'] = 'inicio'
if 'menu' not in st.session_state: st.session_state['menu'] = None
if 'comensales' not in st.session_state: st.session_state['comensales'] = 2

# --- 3. FUNCIONES TÉCNICAS (MOTORES Y ESCALADO) ---

def escalar_texto(texto, n):
    if pd.isna(texto): return ""
    # Busca números y los multiplica por n (comensales)
    return re.sub(r'(\d+(?:\.\d+)?)', lambda m: str(round(float(m.group(1)) * n, 2)), str(texto))

def motor_A_avanzado(df):
    df.columns = [c.strip() for c in df.columns]
    # Selección aleatoria de 7 almuerzos (A) y 7 cenas (C)
    df_a = df[df['ID'].str.contains('A', na=False)].sample(7).reset_index(drop=True)
    df_c = df[df['ID'].str.contains('C', na=False)].sample(7).reset_index(drop=True)
    plan = []
    for i in range(7):
        plan.append({
            'Día': f'Día {i+1}', 
            'Almuerzo': df_a.loc[i, 'Nombre'], 'Ing_A': df_a.loc[i, 'Ingredientes'], 'Desc_A': df_a.loc[i].get('Descripcion', 'Ver PDF'),
            'Cena': df_c.loc[i, 'Nombre'], 'Ing_C': df_c.loc[i, 'Ingredientes'], 'Desc_C': df_c.loc[i].get('Descripcion', 'Ver PDF')
        })
    return pd.DataFrame(plan)

# --- 4. CARGA DE DATOS (BLINDADA CONTRA ERRORES UNICODE) ---
@st.cache_data
def cargar_datos():
    file = "recetas_mymenu.csv"
    if not os.path.exists(file): return None
    for enc in ['utf-8-sig', 'latin1', 'cp1252', 'utf-8']:
        try:
            return pd.read_csv(file, encoding=enc, sep=None, engine='python')
        except: continue
    return None

df = cargar_datos()

# --- 5. LÓGICA DE PANTALLAS ---

# PANTALLA 1: INICIO
if st.session_state['paso'] == 'inicio':
    # Logo principal
    st.image(LOGO_FULL, use_container_width=True)
    st.write("<br>", unsafe_allow_html=True)
    
    # MÉTODO DEFINITIVO: Usamos columnas para centrar y un botón con estilo
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        # Creamos el botón. Si se pulsa, cambia el estado.
        # El truco aquí es que Streamlit detecta el clic ANTES de cualquier CSS.
        if st.button("CONFIGURAR MI MENÚ", use_container_width=True):
            st.session_state['paso'] = 'configurar'
            st.rerun()
        
        # Debajo del botón, ponemos la imagen solo como referencia visual 
        # o podemos integrarla en el CSS del botón.
        st.image(BTN_CONFIG, use_container_width=True)

    st.markdown("""
        <style>
        /* Forzamos que el botón de arriba sea transparente y cubra la imagen */
        div.stButton > button {
            height: 150px; /* Ajusta según el alto de tu botón_configurar */
            margin-bottom: -150px; /* Tira la imagen hacia arriba para que coincidan */
            background-color: transparent !important;
            color: transparent !important;
            border: none !important;
            z-index: 1000;
        }
        </style>
    """, unsafe_allow_html=True)

# PANTALLA 2: CONFIGURACIÓN
elif st.session_state['paso'] == 'configurar':
    st.markdown(f'<div class="logo-container"><img src="{LOGO_RECORTADO}" class="logo-img"></div>', unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.subheader("Personaliza tu semana")
        modo = st.selectbox("Modo", ["Saludable (A)", "Inventario (I)"])
        comensales = st.slider("Personas", 1, 6, st.session_state['comensales'])
        
        st.write("<br>", unsafe_allow_html=True)
        
        st.markdown('<div class="btn-overlay-container">', unsafe_allow_html=True)
        st.image(BTN_GENERAR, width=350)
        if st.button(" ", key="generate_action"):
            if df is not None:
                st.session_state['menu'] = motor_A_avanzado(df)
                st.session_state['comensales'] = comensales
                st.session_state['paso'] = 'menu'
                st.rerun()
            else:
                st.error("Archivo de recetas no encontrado.")
        st.markdown('</div>', unsafe_allow_html=True)

# PANTALLA 3: DESGLOSE DE MENÚ
elif st.session_state['paso'] == 'menu':
    st.markdown(f'<div class="logo-container"><img src="{LOGO_RECORTADO}" class="logo-img"></div>', unsafe_allow_html=True)
    
    if st.session_state['menu'] is not None:
        st.header("Tu Plan Semanal")
        n = st.session_state['comensales']
        
        for i, row in st.session_state['menu'].iterrows():
            with st.expander(f"📅 {row['Día']}: {row['Almuerzo']} y {row['Cena']}"):
                c1, c2 = st.columns(2)
                with c1:
                    st.markdown("### ☀️ Almuerzo")
                    st.info(escalar_texto(row['Ing_A'], n))
                    st.write(row['Desc_A'])
                with c2:
                    st.markdown("### 🌙 Cena")
                    st.info(escalar_texto(row['Ing_C'], n))
                    st.write(row['Desc_C'])
        
        st.write("---")
        if st.button("⬅️ CAMBIAR CONFIGURACIÓN"):
            st.session_state['paso'] = 'configurar'
            st.rerun()
    else:
        st.session_state['paso'] = 'configurar'
        st.rerun()
