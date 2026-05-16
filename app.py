import streamlit as st
import pandas as pd
import random
import re
import os
from collections import defaultdict

# --- 1. CONFIGURACIÓN Y ESTILO ---
st.set_page_config(page_title="MyMenú", page_icon="🍴", layout="wide")

LOGO_URL = "https://raw.githubusercontent.com/LuisaOGH/MyMenu/main/logo.png"

def local_css():
    st.markdown(f"""
    <style>
    :root {{
        --primary: #D14E7B;
        --secondary: #7E4F8C;
        --bg-cream: #F7F3E9;
        --text: #4D243D;
    }}
    .stApp {{ background-color: var(--bg-cream); color: var(--text); }}
    
    /* Logo ancho total móvil */
    [data-testid="stImage"] img {{
        width: 100%;
        height: auto;
        border-radius: 0px;
    }}

    .stButton>button {{ 
        background-color: var(--primary); 
        color: white; 
        border-radius: 20px; 
        border: none; 
        padding: 10px 25px;
        width: 100%;
        font-weight: bold;
    }}
    
    .stSidebar {{ background-color: #EFE6D5; }}
    h1, h2, h3 {{ color: var(--secondary) !important; text-align: center; }}
    
    /* Estilo de tabla táctil */
    .stTable {{ font-size: 16px !important; }}
    
    /* Esconder mensajes de éxito de carga para limpieza visual */
    .element-container:has(.stAlert) {{ display: none; }}
    </style>
    """, unsafe_allow_html=True)

local_css()

# Inicialización de estados
if 'menu' not in st.session_state: st.session_state['menu'] = None
if 'en_casa' not in st.session_state: st.session_state['en_casa'] = []

# --- 2. MOTORES DE SELECCIÓN ---

def motor_A_avanzado(df):
    # Normalización de columnas para evitar KeyErrors
    df.columns = [c.replace('í', 'i').replace(' ', '_').strip() for c in df.columns]
    
    memoria = {'prot': [], 'huevos': 0, 'leg': 0, 'ids': []}
    plan = []
    df_a = df[df['ID'].str.contains('A', na=False)].copy()
    df_c = df[df['ID'].str.contains('C', na=False)].copy()

    for dia in range(1, 8):
        # Almuerzo
        opc_a = df_a[~df_a['ID'].isin(memoria['ids'])]
        if memoria['leg'] >= 3:
            opc_a = opc_a[~opc_a['Subcategorias_App'].str.contains('Legumbres', na=False)]
        
        almuerzo = opc_a.sample(1).iloc[0] if not opc_a.empty else df_a.sample(1).iloc[0]
        memoria['ids'].append(almuerzo['ID'])
        memoria['leg'] += 1 if 'Legumbres' in str(almuerzo['Subcategorias_App']) else 0
        
        # Cena
        opc_c = df_c[~df_c['ID'].isin(memoria['ids'])]
        if memoria['huevos'] >= 4:
            # Usamos get para evitar error si la columna no existe exactamente
            col_base = 'Ingredientes_Base' if 'Ingredientes_Base' in df.columns else 'Ingredientes'
            opc_c = opc_c[~opc_c[col_base].str.contains('Huevo', na=False)]
        
        cena = opc_c.sample(1).iloc[0] if not opc_c.empty else df_c.sample(1).iloc[0]
        memoria['ids'].append(cena['ID'])
        memoria['huevos'] += 1 if 'Huevo' in str(cena.get('Ingredientes_Base', '')) else 0

        plan.append({
            'Día': f'Día {dia}',
            'Almuerzo': almuerzo['Nombre'],
            'Detalle_A': almuerzo['Ingredientes'],
            'Cena': cena['Nombre'],
            'Detalle_C': cena['Ingredientes']
        })
    return pd.DataFrame(plan)

# --- 3. CARGA DE DATOS ---
st.image(LOGO_URL, use_container_width=True)

df, df_maestro = None, None
file_r, file_m = "recetas_mymenu.csv", "maestro_ingredientes.csv"

if os.path.exists(file_r) and os.path.exists(file_m):
    try:
        df = pd.read_csv(file_r, encoding='latin1', sep=None, engine='python')
        df_maestro = pd.read_csv(file_m, encoding='latin1', sep=None, engine='python')
        df.columns = [c.strip() for c in df.columns]
        df['ID'] = df['ID'].astype(str).str.strip().str.upper()
    except:
        pass

# --- 4. INTERFAZ ---
st.sidebar.title("MyMenú Selección")

if df is not None:
    modo = st.sidebar.selectbox("Modo", ["Saludable (A)", "Inventario (I)", "Orden (O)"])
    comensales = st.sidebar.slider("Comensales", 1, 6, 2)
    
    if st.sidebar.button("🚀 GENERAR"):
        if modo == "Saludable (A)":
            st.session_state['menu'] = motor_A_avanzado(df)
    
    if st.session_state['menu'] is not None:
        st.header("MyMenú")
        
        # Tabla Interactiva con Botones para Ventana Emergente
        for i, row in st.session_state['menu'].iterrows():
            col_d, col_a, col_c = st.columns([1, 2, 2])
            col_d.write(f"**{row['Día']}**")
            
            if col_a.button(row['Almuerzo'], key=f"a_{i}"):
                @st.dialog("Receta de Almuerzo")
                def modal_a():
                    st.image(LOGO_URL, width=150)
                    st.subheader(row['Almuerzo'])
                    st.write("**Ingredientes e Instrucciones:**")
                    st.write(row['Detalle_A'])
                modal_a()
                
            if col_c.button(row['Cena'], key=f"c_{i}"):
                @st.dialog("Receta de Cena")
                def modal_c():
                    st.image(LOGO_URL, width=150)
                    st.subheader(row['Cena'])
                    st.write("**Ingredientes e Instrucciones:**")
                    st.write(row['Detalle_C'])
                modal_c()
        
        st.write("---")
        if st.button("🛒 GENERAR LISTA DE COMPRA"):
            st.success("Lista unificada (Próximamente exportable)")
