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
BTN_GENERAR = "https://raw.githubusercontent.com/LuisaOGH/MyMenu/main/boton_generarmenu.png"

def local_css():
    st.markdown(f"""
    <style>
    :root {{ --bg-cream: #F7F3E9; --primary: #D14E7B; }}
    .stApp {{ background-color: var(--bg-cream); }}
    .logo-container {{ display: flex; justify-content: center; padding: 10px; }}
    .logo-img {{ width: 120px; border-radius: 50%; }}
    .img-btn {{ cursor: pointer; transition: transform 0.2s; display: block; margin: auto; }}
    .img-btn:hover {{ transform: scale(1.05); }}
    /* Ocultar elementos nativos para diseño limpio */
    [data-testid="stSidebar"] {{ background-color: #EFE6D5; }}
    .element-container:has(.stAlert) {{ display: none; }}
    </style>
    """, unsafe_allow_html=True)

local_css()

# --- 2. GESTIÓN DE ESTADOS (NAVEGACIÓN) ---
if 'paso' not in st.session_state: st.session_state['paso'] = 'inicio'
if 'menu' not in st.session_state: st.session_state['menu'] = None

# --- 3. FUNCIONES TÉCNICAS Y MOTORES ---
def cargar_csv_seguro(nombre_archivo):
    for enc in ['utf-8-sig', 'utf-8', 'latin1']:
        try: return pd.read_csv(nombre_archivo, encoding=enc, sep=None, engine='python')
        except: continue
    return None

def escalar_texto(texto, n):
    if pd.isna(texto): return ""
    return re.sub(r'(\d+(?:\.\d+)?)', lambda m: str(round(float(m.group(1)) * n, 2)), texto)

# (Aquí irían tus funciones motor_A_avanzado y motor_I_avanzado que definimos antes)
# Asegúrate de mantenerlas en tu archivo final.

# --- 4. CARGA DE DATOS ---
df, df_maestro = None, None
if os.path.exists("recetas_mymenu.csv") and os.path.exists("maestro_ingredientes.csv"):
    df = cargar_csv_seguro("recetas_mymenu.csv")
    df_maestro = cargar_csv_seguro("maestro_ingredientes.csv")

# --- 5. LÓGICA DE PANTALLAS ---

# PANTALLA 1: BIENVENIDA
if st.session_state['paso'] == 'inicio':
    st.image(LOGO_FULL, use_container_width=True)
    st.write("<br><br>", unsafe_allow_html=True)
    if st.button("CONFIGURAR", key="btn_init_hidden", help="Haz clic en la imagen", use_container_width=True):
        st.session_state['paso'] = 'configurar'
        st.rerun()
    # Visualmente usamos tu botón:
    st.image(BTN_CONFIG, width=300)

# PANTALLA 2: CONFIGURACIÓN
elif st.session_state['paso'] == 'configurar':
    st.markdown(f'<div class="logo-container"><img src="{LOGO_RECORTADO}" class="logo-img"></div>', unsafe_allow_html=True)
    st.header("Configura tu Plan")
    
    col1, col2 = st.columns(2)
    with col1:
        modo = st.selectbox("Modo de selección", ["Saludable (A)", "Inventario (I)", "Orden (O)"])
        comensales = st.slider("¿Cuántas personas?", 1, 6, 2)
    with col2:
        tengo = []
        if modo == "Inventario (I)" and df_maestro is not None:
            tengo = st.multiselect("¿Qué tienes en casa?", sorted(df_maestro.iloc[:,0].unique().tolist()))
        else:
            st.info("El modo Saludable seleccionará las mejores recetas antiinflamatorias para ti.")

    st.write("---")
    
    # BOTÓN GENERAR (Tu imagen de GitHub)
    if st.button("GENERAR", key="btn_gen_hidden", use_container_width=True):
        # Aquí ejecutas el motor según el modo
        # st.session_state['menu'] = motor_A_avanzado(df) ...
        st.session_state['comensales'] = comensales
        st.session_state['paso'] = 'menu'
        st.rerun()
    st.image(BTN_GENERAR, width=300)

# PANTALLA 3: DESGLOSE DEL MENÚ
elif st.session_state['paso'] == 'menu':
    st.markdown(f'<div class="logo-container"><img src="{LOGO_RECORTADO}" class="logo-img"></div>', unsafe_allow_html=True)
    
    if st.session_state['menu'] is not None:
        st.header("Tu Menú Personalizado")
        n = st.session_state.get('comensales', 1)
        
        for i, row in st.session_state['menu'].iterrows():
            with st.expander(f"📅 {row['Día']} - {row['Almuerzo']} y {row['Cena']}"):
                c1, c2 = st.columns(2)
                with c1:
                    st.subheader("☀️ Almuerzo")
                    st.write(escalar_texto(row['Ing_A'], n))
                with c2:
                    st.subheader("🌙 Cena")
                    st.write(escalar_texto(row['Ing_C'], n))
        
        if st.button("⬅️ VOLVER A CONFIGURAR"):
            st.session_state['paso'] = 'configurar'
            st.rerun()
