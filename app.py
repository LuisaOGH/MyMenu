import streamlit as st
import pandas as pd
import random
import re
import os
from collections import defaultdict

# --- 1. CONFIGURACIÓN Y ESTILO ---
st.set_page_config(page_title="MyMenú", page_icon="🍴", layout="wide")

# URLs de activos
LOGO_RECORTADO = "https://raw.githubusercontent.com/LuisaOGH/MyMenu/main/logo_recortado.jpg"
LOGO_FULL = "https://raw.githubusercontent.com/LuisaOGH/MyMenu/main/logo.png"

def local_css():
    st.markdown(f"""
    <style>
    :root {{
        --primary: #D14E7B;
        --secondary: #4D243D;
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

    /* Botones Modernos */
    .stButton>button {{
        border-radius: 25px;
        font-weight: bold;
        transition: 0.3s;
    }}
    
    /* Ocultar mensajes de éxito de Streamlit para limpieza */
    .element-container:has(.stAlert) {{ display: none; }}
    </style>
    """, unsafe_allow_html=True)

local_css()

# --- 2. MOTORES DE SELECCIÓN CORREGIDOS ---

def motor_A_avanzado(df):
    df.columns = [c.strip() for c in df.columns]
    df_a = df[df['ID'].str.contains('A', na=False)]
    df_c = df[df['ID'].str.contains('C', na=False)]
    
    plan = []
    # Seleccionamos 7 días al azar sin repetir
    alms = df_a.sample(7).reset_index()
    cens = df_c.sample(7).reset_index()
    
    for i in range(7):
        plan.append({
            'Día': f'Día {i+1}', 
            'Almuerzo': alms.loc[i, 'Nombre'], 'Ing_A': alms.loc[i, 'Ingredientes'], 'Desc_A': alms.loc[i].get('Descripcion', 'Ver PDF'),
            'Cena': cens.loc[i, 'Nombre'], 'Ing_C': cens.loc[i, 'Ingredientes'], 'Desc_C': cens.loc[i].get('Descripcion', 'Ver PDF')
        })
    return pd.DataFrame(plan)

def motor_I_avanzado(df, disponibles):
    """Motor I Corregido: Ahora mezcla aleatoriedad con los mejores matches"""
    df.columns = [c.strip() for c in df.columns]
    disp_l = [x.lower().strip() for x in disponibles]
    
    def calcular_score(row):
        # Puntuamos según cuántos ingredientes del stock coinciden
        return sum(1 for ing in disp_l if ing in str(row.get('Ingredientes', '')).lower())
    
    df['Score'] = df.apply(calcular_score, axis=1)
    
    # Filtramos las mejores (Score > 0 si hay stock, o simplemente las mejores disponibles)
    opc_a = df[df['ID'].str.contains('A', na=False)].nlargest(10, 'Score')
    opc_c = df[df['ID'].str.contains('C', na=False)].nlargest(10, 'Score')
    
    # De las 10 mejores, elegimos 3 al azar para que el menú cambie
    alms = opc_a.sample(min(3, len(opc_a))).reset_index()
    cens = opc_c.sample(min(3, len(opc_c))).reset_index()
    
    plan = []
    for i in range(len(alms)):
        plan.append({
            'Día': f'Día {i+1}', 
            'Almuerzo': alms.loc[i, 'Nombre'], 'Ing_A': alms.loc[i, 'Ingredientes'], 'Desc_A': alms.loc[i].get('Descripcion', 'Ver PDF'),
            'Cena': cens.loc[i, 'Nombre'], 'Ing_C': cens.loc[i, 'Ingredientes'], 'Desc_C': cens.loc[i].get('Descripcion', 'Ver PDF')
        })
    return pd.DataFrame(plan)

# --- 3. LÓGICA TÉCNICA: ESCALADO DE CANTIDADES ---
def escalar_texto(texto, n):
    if pd.isna(texto): return ""
    def mult(match):
        return str(round(float(match.group(1)) * n, 2))
    return re.sub(r'(\d+(?:\.\d+)?)', mult, texto)

# --- 4. CARGA Y LOGO ---
df, df_maestro = None, None

def cargar_csv_seguro(nombre_archivo):
    # Lista de codificaciones a probar en orden de probabilidad
    encodings = ['utf-8-sig', 'utf-8', 'latin1', 'cp1252']
    for enc in encodings:
        try:
            return pd.read_csv(nombre_archivo, encoding=enc, sep=None, engine='python')
        except (UnicodeDecodeError, Exception):
            continue
    return None

if os.path.exists("recetas_mymenu.csv") and os.path.exists("maestro_ingredientes.csv"):
    df = cargar_csv_seguro("recetas_mymenu.csv")
    df_maestro = cargar_csv_seguro("maestro_ingredientes.csv")

# Mostrar Logo Recortado centrado (Siempre arriba)
st.markdown(f'<div class="logo-container"><img src="{LOGO_RECORTADO}" class="logo-img"></div>', unsafe_allow_html=True)

# --- 5. RENDERIZADO DEL MENÚ ---
    if 'menu' in st.session_state and st.session_state['menu'] is not None:
        n = st.session_state.get('comensales', 1)
        for i, row in st.session_state['menu'].iterrows():
            with st.container():
                c1, c2, c3 = st.columns([1, 2, 2])
                c1.subheader(row['Día'])
                
                # Botones de platos
                if c2.button(f"🥗 {row['Almuerzo']}", key=f"a{i}"):
                    @st.dialog(row['Almuerzo'])
                    def modal_a():
                        st.write(f"**Cantidades para {n} personas:**")
                        st.info(escalar_texto(row['Ing_A'], n))
                        st.write("**Preparación:**", row['Desc_A'])
                    modal_a()

                if c3.button(f"🌙 {row['Cena']}", key=f"c{i}"):
                    @st.dialog(row['Cena'])
                    def modal_c():
                        st.write(f"**Cantidades para {n} personas:**")
                        st.info(escalar_texto(row['Ing_C'], n))
                        st.write("**Preparación:**", row['Desc_C'])
                    modal_c()
    else:
        # Si no hay menú, mostramos el logo con eslogan grande para dar la bienvenida
        st.image(LOGO_FULL, use_container_width=True)
