import streamlit as st
import pandas as pd
import random
import re
import os

# --- 1. CONFIGURACIÓN ---
st.set_page_config(page_title="MyMenú", page_icon="🍴", layout="wide")

# URLs de activos
LOGO_FULL = "https://raw.githubusercontent.com/LuisaOGH/MyMenu/main/logo.png"
LOGO_RECORTADO = "https://raw.githubusercontent.com/LuisaOGH/MyMenu/main/logo_recortado.jpg"
BTN_CONFIG_URL = "https://raw.githubusercontent.com/LuisaOGH/MyMenu/main/boton_configurar.png"
BTN_GENERAR_URL = "https://raw.githubusercontent.com/LuisaOGH/MyMenu/main/boton_generarmenu.png"

# --- 2. ESTILOS CSS DEFINITIVOS ---
st.markdown(f"""
<style>
    :root {{ --bg: #F7F3E9; }}
    .stApp {{ background-color: var(--bg); }}
    
    /* Estilo para que el botón parezca una imagen */
    .stButton > button {{
        display: block;
        margin: 0 auto;
        padding: 0;
        border: none;
        background-color: transparent !important;
        transition: transform 0.2s;
    }}
    .stButton > button:hover {{
        transform: scale(1.05);
        background-color: transparent !important;
    }}
    
    /* Contenedor de logos */
    .logo-box {{ display: flex; justify-content: center; padding: 20px; }}
</style>
""", unsafe_allow_html=True)

# --- 3. ESTADOS DE NAVEGACIÓN ---
if 'paso' not in st.session_state: st.session_state['paso'] = 'inicio'
if 'menu' not in st.session_state: st.session_state['menu'] = None

# --- 4. FUNCIONES TÉCNICAS ---
@st.cache_data
def cargar_datos():
    file = "recetas_mymenu.csv"
    if not os.path.exists(file): return None
    for enc in ['utf-8-sig', 'latin1', 'cp1252']:
        try: return pd.read_csv(file, encoding=enc, sep=None, engine='python')
        except: continue
    return None

def motor_A(df):
    df.columns = [c.strip() for c in df.columns]
    # Filtramos por almuerzos (A) y cenas (C)
    df_a = df[df['ID'].str.contains('A', na=False)].sample(n=min(7, len(df)))
    df_c = df[df['ID'].str.contains('C', na=False)].sample(n=min(7, len(df)))
    plan = []
    for i in range(len(df_a)):
        plan.append({
            'Día': f'Día {i+1}', 
            'Almuerzo': df_a.iloc[i]['Nombre'], 'Ing_A': df_a.iloc[i]['Ingredientes'], 'Desc_A': df_a.iloc[i].get('Descripcion', ''),
            'Cena': df_c.iloc[i]['Nombre'], 'Ing_C': df_c.iloc[i]['Ingredientes'], 'Desc_C': df_c.iloc[i].get('Descripcion', '')
        })
    return pd.DataFrame(plan)

df = cargar_datos()

# --- 5. LÓGICA DE PANTALLAS ---

# PANTALLA 1: INICIO
if st.session_state['paso'] == 'inicio':
    st.image(LOGO_FULL, use_container_width=True)
    st.write("<br>", unsafe_allow_html=True)
    
    # Botón con imagen dentro usando HTML/Markdown
    # Al hacer clic en este botón de Streamlit, pasamos de pantalla
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        # Mostramos la imagen del botón
        st.image(BTN_CONFIG_URL, use_container_width=True)
        # El botón real justo debajo (o encima)
        if st.button("ENTRAR A CONFIGURACIÓN", use_container_width=True):
            st.session_state['paso'] = 'configurar'
            st.rerun()

# PANTALLA 2: CONFIGURACIÓN
elif st.session_state['paso'] == 'configurar':
    st.image(LOGO_RECORTADO, width=150)
    st.header("Configura tu Plan Semanal")
    
    col1, col2 = st.columns(2)
    with col1:
        comensales = st.number_input("Personas", 1, 10, 2)
    with col2:
        modo = st.selectbox("Modo", ["Saludable (A)", "Inventario (I)"])
    
    st.write("---")
    st.image(BTN_GENERAR_URL, width=300)
    if st.button("GENERAR MI MENÚ", use_container_width=True):
        if df is not None:
            st.session_state['menu'] = motor_A(df)
            st.session_state['paso'] = 'menu'
            st.rerun()
        else:
            st.error("Error al cargar recetas.")

# PANTALLA 3: MENÚ
elif st.session_state['paso'] == 'menu':
    st.image(LOGO_RECORTADO, width=100)
    st.title("Tu Menú MyMenú")
    
    if st.session_state['menu'] is not None:
        for _, row in st.session_state['menu'].iterrows():
            with st.expander(f"📅 {row['Día']}"):
                st.subheader(f"🥗 Almuerzo: {row['Almuerzo']}")
                st.write(row['Ing_A'])
                st.subheader(f"🌙 Cena: {row['Cena']}")
                st.write(row['Ing_C'])
    
    if st.button("RECONFIGURAR"):
        st.session_state['paso'] = 'configurar'
        st.rerun()
