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
    :root {{ --morado: #4D243D; --bg-cream: #F7F3E9; }}
    .stApp {{ background-color: var(--bg-cream); }}
    div.stButton > button {{
        background-color: var(--morado) !important;
        color: white !important;
        font-size: 20px !important;
        font-weight: bold !important;
        padding: 15px !important;
        border-radius: 12px !important;
        width: 100% !important;
    }}
    .recipe-btn {{ margin-bottom: 10px; }}
    h1, h2, h3 {{ color: var(--morado) !important; text-align: center; }}
    </style>
    """, unsafe_allow_html=True)

local_css()

# --- 2. GESTIÓN DE ESTADOS ---
if 'paso' not in st.session_state: st.session_state['paso'] = 'inicio'
if 'menu' not in st.session_state: st.session_state['menu'] = None
if 'comensales' not in st.session_state: st.session_state['comensales'] = 2

# --- 3. MOTORES DE SELECCIÓN ---

def escalar_cantidades(texto, n):
    if pd.isna(texto): return ""
    # Multiplica números por n personas
    return re.sub(r'(\d+(?:\.\d+)?)', lambda m: str(round(float(m.group(1)) * n, 2)), str(texto))

def motor_A_saludable(df):
    df.columns = [c.strip() for c in df.columns]
    df_a = df[df['ID'].str.contains('A', na=False)].sample(min(7, len(df))).reset_index(drop=True)
    df_c = df[df['ID'].str.contains('C', na=False)].sample(min(7, len(df))).reset_index(drop=True)
    plan = []
    for i in range(min(len(df_a), len(df_c))):
        plan.append({
            'Día': f'Día {i+1}', 
            'Almuerzo': df_a.iloc[i], 'Cena': df_c.iloc[i]
        })
    return pd.DataFrame(plan)

def motor_I_ingredientes(df, disponibles):
    df.columns = [c.strip() for c in df.columns]
    disp_l = [x.lower().strip() for x in disponibles]
    def score(row):
        return sum(1 for ing in disp_l if ing in str(row.get('Ingredientes', '')).lower())
    df['Score'] = df.apply(score, axis=1)
    df_a = df[df['ID'].str.contains('A', na=False)].nlargest(10, 'Score').sample(3).reset_index(drop=True)
    df_c = df[df['ID'].str.contains('C', na=False)].nlargest(10, 'Score').sample(3).reset_index(drop=True)
    plan = []
    for i in range(min(len(df_a), len(df_c))):
        plan.append({'Día': f'Día {i+1}', 'Almuerzo': df_a.iloc[i], 'Cena': df_c.iloc[i]})
    return pd.DataFrame(plan)

def generar_lista_compra(df_menu, df_maestro, n):
    # Diccionario: Categoria -> Producto -> Cantidad y Unidad
    compra = defaultdict(lambda: defaultdict(lambda: {"cant": 0.0, "uni": ""}))
    mapeo = dict(zip(df_maestro.iloc[:,0].str.lower(), df_maestro.iloc[:,1]))
    
    for _, fila in df_menu.iterrows():
        for comida in [fila['Almuerzo'], fila['Cena']]:
            ings = str(comida['Ingredientes']).split(',')
            for item in ings:
                match = re.search(r'([\d\.]+)\s*([a-zA-Záéíóú]+)\s+(.*)', item.strip())
                if match:
                    cant, uni, nom = float(match.group(1))*n, match.group(2), match.group(3).strip().lower()
                    cat = mapeo.get(nom, "VARIOS").upper()
                    compra[cat][nom]["cant"] += cant
                    compra[cat][nom]["uni"] = uni
                else:
                    nom = item.strip().lower()
                    cat = mapeo.get(nom, "VARIOS").upper()
                    compra[cat][nom]["cant"] = 0 # Solo nombre
    return compra

# --- 4. CARGA DE DATOS ---
@st.cache_data
def cargar_datos():
    try:
        df_r = pd.read_csv("recetas_mymenu.csv", encoding='utf-8-sig', sep=None, engine='python')
        df_m = pd.read_csv("maestro_ingredientes.csv", encoding='utf-8-sig', sep=None, engine='python')
        return df_r, df_m
    except: return None, None

df_recetas, df_maestro = cargar_datos()

# --- 5. PANTALLAS ---

if st.session_state['paso'] == 'inicio':
    st.image(LOGO_FULL, use_container_width=True)
    if st.button("IR A SELECCIÓN"):
        st.session_state['paso'] = 'configurar'
        st.rerun()

elif st.session_state['paso'] == 'configurar':
    st.image(LOGO_RECORTADO, width=150)
    col1, col2 = st.columns(2)
    with col1:
        modo = st.selectbox("Modo", ["Saludable (A)", "Inventario (I)", "Orden (O)"])
        comensales = st.slider("Personas", 1, 6, st.session_state['comensales'])
    with col2:
        if modo == "Inventario (I)":
            tengo = st.multiselect("¿Qué tienes?", sorted(df_maestro.iloc[:,0].unique().tolist()))
        elif modo == "Orden (O)":
            ultimo_id = st.number_input("Último ID cocinado:", min_value=0)

    if st.button("GENERAR MENÚ"):
        if modo == "Saludable (A)": st.session_state['menu'] = motor_A_saludable(df_recetas)
        elif modo == "Inventario (I)": st.session_state['menu'] = motor_I_ingredientes(df_recetas, tengo)
        st.session_state['comensales'] = comensales
        st.session_state['paso'] = 'menu'
        st.rerun()

elif st.session_state['paso'] == 'menu':
    st.image(LOGO_RECORTADO, width=100)
    n = st.session_state['comensales']
    
    # Mostrar Menú como botones
    for i, row in st.session_state['menu'].iterrows():
        st.write(f"### {row['Día']}")
        c1, c2 = st.columns(2)
        
        for col, receta, llave in [(c1, row['Almuerzo'], 'A'), (c2, row['Cena'], 'C')]:
            if col.button(f"{'☀️' if llave=='A' else '🌙'} {receta['Nombre']}", key=f"{llave}{i}"):
                @st.dialog(receta['Nombre'])
                def detalle():
                    st.image(LOGO_RECORTADO, width=100)
                    st.markdown(f"**🕒 Tiempo:** {receta.get('Tiempo', '20 min')} | **🔥 Calorías:** {receta.get('Calorias', 'N/A')}")
                    st.subheader("🛒 Ingredientes")
                    st.write(escalar_cantidades(receta['Ingredientes'], n))
                    st.subheader("👨‍🍳 Preparación")
                    st.write(receta.get('Descripcion', 'Consulta el PDF para el detalle.'))
                detalle()

    # Lista de la Compra
    st.write("---")
    st.header("🛒 Lista de la Compra")
    compra_agrupada = generar_lista_compra(st.session_state['menu'], df_maestro, n)
    
    for cat, prods in compra_agrupada.items():
        with st.expander(f"📍 {cat}"):
            for p, d in prods.items():
                cant_str = f"{d['cant']} {d['uni']}" if d['cant'] > 0 else ""
                st.write(f"☐ {cant_str} {p.capitalize()}")

    if st.button("⬅️ RECONFIGURAR"):
        st.session_state['paso'] = 'configurar'
        st.rerun()
