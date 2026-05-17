import streamlit as st
import pandas as pd
import random
import re
import os
from collections import defaultdict

# --- 1. CONFIGURACIÓN Y ESTILO ---
st.set_page_config(page_title="MyMenú", page_icon="🍴", layout="wide")

LOGO_RECORTADO = "https://raw.githubusercontent.com/LuisaOGH/MyMenu/main/logo_recortado.jpg"
LOGO_FULL = "https://raw.githubusercontent.com/LuisaOGH/MyMenu/main/logo.png"
BTN_CONFIG = "https://raw.githubusercontent.com/LuisaOGH/MyMenu/main/boton_configurar.png"
BTN_GENERAR = "https://raw.githubusercontent.com/LuisaOGH/MyMenu/main/boton_generarmenu.png"

def local_css():
    st.markdown(f"""
    <style>
    :root {{ --bg-cream: #F7F3E9; }}
    .stApp {{ background-color: var(--bg-cream); }}
    
    /* Superposición de botón invisible sobre imagen */
    .overlay-container {{
        position: relative;
        text-align: center;
        margin: auto;
    }}
    
    /* Hacer el botón de Streamlit invisible pero clicable sobre la imagen */
    div.stButton > button {{
        position: absolute;
        top: 0; left: 0;
        width: 100%; height: 100%;
        background: transparent !important;
        color: transparent !important;
        border: none !important;
        z-index: 10;
        cursor: pointer;
    }}
    
    .logo-container {{ display: flex; justify-content: center; padding: 20px; }}
    .logo-img {{ width: 140px; border-radius: 50%; }}
    </style>
    """, unsafe_allow_html=True)

local_css()

# --- 2. GESTIÓN DE ESTADOS ---
if 'paso' not in st.session_state: st.session_state['paso'] = 'inicio'
if 'menu' not in st.session_state: st.session_state['menu'] = None
if 'comensales' not in st.session_state: st.session_state['comensales'] = 2

# --- 3. MOTORES (Copia aquí tus funciones motor_A y motor_I corregidas) ---
def motor_A_avanzado(df):
    df.columns = [c.strip() for c in df.columns]
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

def escalar_texto(texto, n):
    if pd.isna(texto): return ""
    return re.sub(r'(\d+(?:\.\d+)?)', lambda m: str(round(float(m.group(1)) * n, 2)), str(texto))

# --- 4. CARGA DE DATOS ---
@st.cache_data
def cargar_datos():
    if os.path.exists("recetas_mymenu.csv"):
        return pd.read_csv("recetas_mymenu.csv", encoding='utf-8-sig', sep=None, engine='python')
    return None

df = cargar_datos()

# --- 5. LÓGICA DE PANTALLAS ---

# PANTALLA 1: INICIO
if st.session_state['paso'] == 'inicio':
    st.image(LOGO_FULL, use_container_width=True)
    st.write("<br>", unsafe_allow_html=True)
    
    # Contenedor con botón invisible sobre la imagen
    with st.container():
        st.markdown('<div class="overlay-container">', unsafe_allow_html=True)
        st.image(BTN_CONFIG, width=350)
        if st.button("config", key="click_config"):
            st.session_state['paso'] = 'configurar'
            st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)

# PANTALLA 2: CONFIGURACIÓN
elif st.session_state['paso'] == 'configurar':
    st.markdown(f'<div class="logo-container"><img src="{LOGO_RECORTADO}" class="logo-img"></div>', unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.subheader("Configura tu Plan")
        modo = st.selectbox("Modo", ["Saludable (A)", "Inventario (I)"])
        comensales = st.slider("Personas", 1, 6, st.session_state['comensales'])
        
        st.write("<br>", unsafe_allow_html=True)
        # Botón Generar con imagen
        st.markdown('<div class="overlay-container">', unsafe_allow_html=True)
        st.image(BTN_GENERAR, width=350)
        if st.button("generar", key="click_gen"):
            if df is not None:
                st.session_state['menu'] = motor_A_avanzado(df) # Ejemplo con Motor A
                st.session_state['comensales'] = comensales
                st.session_state['paso'] = 'menu'
                st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)

# PANTALLA 3: MENÚ (SOLUCIÓN PANTALLA EN BLANCO)
elif st.session_state['paso'] == 'menu':
    st.markdown(f'<div class="logo-container"><img src="{LOGO_RECORTADO}" class="logo-img"></div>', unsafe_allow_html=True)
    
    if st.session_state['menu'] is not None:
        st.header("Tu Menú Semanal")
        n = st.session_state['comensales']
        
        # Usamos columnas para que no salga una lista infinita hacia abajo
        for i, row in st.session_state['menu'].iterrows():
            with st.expander(f"📅 {row['Día']}: {row['Almuerzo']} | {row['Cena']}"):
                c1, c2 = st.columns(2)
                with c1:
                    st.markdown("### ☀️ Almuerzo")
                    st.info(escalar_texto(row['Ing_A'], n))
                    st.write(row['Desc_A'])
                with c2:
                    st.markdown("### 🌙 Cena")
                    st.info(escalar_texto(row['Ing_C'], n))
                    st.write(row['Desc_C'])
        
        if st.button("⬅️ MODIFICAR CONFIGURACIÓN"):
            st.session_state['paso'] = 'configurar'
            st.rerun()
    else:
        # Si por error llega aquí sin menú, lo devolvemos
        st.session_state['paso'] = 'configurar'
        st.rerun()
