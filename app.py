import streamlit as st
import pandas as pd
import random
import re
import os
from collections import defaultdict

# --- 1. CONFIGURACIÓN Y ESTILO ---
st.set_page_config(page_title="MyMenú", page_icon="🍴", layout="wide")

LOGO_FULL = "https://raw.githubusercontent.com/LuisaOGH/MyMenu/main/logo.png"
LOGO_RECORTADO = "https://raw.githubusercontent.com/LuisaOGH/MyMenu/main/logo_recortado.jpg"

def local_css():
    st.markdown(f"""
    <style>
    :root {{
        --morado: #4D243D;
        --bg-cream: #F7F3E9;
    }}
    .stApp {{ background-color: var(--bg-cream); }}
    
    /* Estilo para botones grandes y morados */
    div.stButton > button {{
        background-color: var(--morado) !important;
        color: white !important;
        font-size: 24px !important; /* Tamaño más grande */
        font-weight: bold !important;
        padding: 20px !important;
        border-radius: 15px !important;
        width: 100% !important;
        border: none !important;
    }}
    
    .logo-container {{ display: flex; justify-content: center; padding: 10px; }}
    .logo-img {{ width: 150px; border-radius: 50%; }}
    
    h1, h2, h3 {{ color: var(--morado) !important; text-align: center; }}
    </style>
    """, unsafe_allow_html=True)

local_css()

# --- 2. GESTIÓN DE ESTADOS ---
if 'paso' not in st.session_state: st.session_state['paso'] = 'inicio'
if 'menu' not in st.session_state: st.session_state['menu'] = None
if 'comensales' not in st.session_state: st.session_state['comensales'] = 2

# --- 3. MOTORES Y LÓGICA TÉCNICA ---

def escalar_texto(texto, n):
    if pd.isna(texto): return ""
    return re.sub(r'(\d+(?:\.\d+)?)', lambda m: str(round(float(m.group(1)) * n, 2)), str(texto))

def motor_O_orden(df, ultimo_id, num_dias=7):
    df.columns = [c.strip() for c in df.columns]
    df['n_id'] = df['ID'].str.extract(r'(\d+)').fillna(0).astype(int)
    # Filtramos las siguientes recetas después del ID introducido
    proximas = df[df['n_id'] > ultimo_id].sort_values('n_id')
    
    alms = proximas[proximas['ID'].str.contains('A', na=False)]
    cens = proximas[proximas['ID'].str.contains('C', na=False)]
    
    plan = []
    for i in range(min(num_dias, len(alms), len(cens))):
        alm, cen = alms.iloc[i], cens.iloc[i]
        plan.append({
            'Día': f'Día {i+1}', 
            'Almuerzo': f"({alm['ID']}) {alm['Nombre']}", 'Ing_A': alm['Ingredientes'], 'Desc_A': alm.get('Descripcion', 'Ver PDF'),
            'Cena': f"({cen['ID']}) {cen['Nombre']}", 'Ing_C': cen['Ingredientes'], 'Desc_C': cen.get('Descripcion', 'Ver PDF')
        })
    return pd.DataFrame(plan)

def generar_lista_compra(df_menu, comensales):
    # Lógica simplificada para agrupar ingredientes
    lista = defaultdict(float)
    for _, fila in df_menu.iterrows():
        for col in ['Ing_A', 'Ing_C']:
            items = str(fila[col]).split(',')
            for item in items:
                item = item.strip().capitalize()
                if item and item != 'Nan':
                    lista[item] += 1 # Aquí podrías mejorar la suma por unidades
    return lista

# --- 4. CARGA DE DATOS ---
@st.cache_data
def cargar_datos():
    file = "recetas_mymenu.csv"
    if not os.path.exists(file): return None
    for enc in ['utf-8-sig', 'latin1', 'cp1252', 'utf-8']:
        try: return pd.read_csv(file, encoding=enc, sep=None, engine='python')
        except: continue
    return None

df = cargar_datos()

# --- 5. PANTALLAS ---

# PANTALLA 1: INICIO
if st.session_state['paso'] == 'inicio':
    st.image(LOGO_FULL, use_container_width=True)
    st.write("<br>", unsafe_allow_html=True)
    if st.button("IR A SELECCIÓN"):
        st.session_state['paso'] = 'configurar'
        st.rerun()

# PANTALLA 2: CONFIGURACIÓN
elif st.session_state['paso'] == 'configurar':
    st.markdown(f'<div class="logo-container"><img src="{LOGO_RECORTADO}" class="logo-img"></div>', unsafe_allow_html=True)
    st.header("Configura tu Plan")
    
    col1, col2 = st.columns(2)
    with col1:
        modo = st.selectbox("Modo de selección", ["Orden (O)", "Saludable (A)"])
        comensales = st.slider("¿Cuántos sois?", 1, 6, st.session_state['comensales'])
    with col2:
        if modo == "Orden (O)":
            ultimo_id = st.number_input("Número del último ID cocinado:", min_value=0, step=1)
        else:
            st.info("El modo Saludable elegirá recetas variadas al azar.")

    st.write("<br>", unsafe_allow_html=True)
    if st.button("GENERAR MENÚ"):
        if df is not None:
            if modo == "Orden (O)":
                st.session_state['menu'] = motor_O_orden(df, ultimo_id)
            else:
                # Motor A (Aleatorio)
                st.session_state['menu'] = df.sample(7) # Simplificado para el ejemplo
            
            st.session_state['comensales'] = comensales
            st.session_state['paso'] = 'menu'
            st.rerun()

# PANTALLA 3: RESULTADO Y LISTA
elif st.session_state['paso'] == 'menu':
    st.markdown(f'<div class="logo-container"><img src="{LOGO_RECORTADO}" class="logo-img"></div>', unsafe_allow_html=True)
    
    if st.session_state['menu'] is not None:
        st.header("Tu Menú Semanal")
        n = st.session_state['comensales']
        
        # Mostrar Menú
        for i, row in st.session_state['menu'].iterrows():
            with st.expander(f"📅 {row['Día']}: {row['Almuerzo']} | {row['Cena']}"):
                c1, c2 = st.columns(2)
                with c1:
                    st.subheader("☀️ Almuerzo")
                    st.info(escalar_texto(row['Ing_A'], n))
                with c2:
                    st.subheader("🌙 Cena")
                    st.info(escalar_texto(row['Ing_C'], n))
        
        # Mostrar Lista de la Compra
        st.write("---")
        st.header("🛒 Lista de la Compra")
        lista = generar_lista_compra(st.session_state['menu'], n)
        for ing, cant in lista.items():
            st.write(f"☐ {ing}")

        if st.button("⬅️ VOLVER A SELECCIÓN"):
            st.session_state['paso'] = 'configurar'
            st.rerun()
