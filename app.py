import streamlit as st
import pandas as pd
import random
import re
import os
from collections import defaultdict

# --- 1. CONFIGURACIÓN ---
st.set_page_config(page_title="MyMenú", page_icon="🍴", layout="wide")

LOGO_FULL = "https://raw.githubusercontent.com/LuisaOGH/MyMenu/main/logo.png"
LOGO_RECORTADO = "https://raw.githubusercontent.com/LuisaOGH/MyMenu/main/logo_recortado.jpg"

def local_css():
    st.markdown(f"""
    <style>
    :root {{ --morado: #4D243D; --bg: #F7F3E9; }}
    .stApp {{ background-color: var(--bg); }}
    div.stButton > button {{
        background-color: var(--morado) !important;
        color: white !important;
        font-size: 18px !important;
        font-weight: bold !important;
        border-radius: 10px !important;
        width: 100% !important;
        border: none !important;
    }}
    h1, h2, h3 {{ color: var(--morado) !important; text-align: center; }}
    </style>
    """, unsafe_allow_html=True)

local_css()

# --- 2. ESTADOS ---
if 'paso' not in st.session_state: st.session_state['paso'] = 'inicio'
if 'menu' not in st.session_state: st.session_state['menu'] = None
if 'comensales' not in st.session_state: st.session_state['comensales'] = 2

# --- 3. MOTORES CORREGIDOS ---

def escalar_cantidades(texto, n):
    if pd.isna(texto): return ""
    return re.sub(r'(\d+(?:\.\d+)?)', lambda m: str(round(float(m.group(1)) * n, 2)), str(texto))

def normalizar_df(df_parcial, num_dias):
    """Asegura que el menú tenga siempre las mismas columnas"""
    df_a = df_parcial[df_parcial['ID'].str.contains('A', na=False)].sample(num_dias).reset_index(drop=True)
    df_c = df_parcial[df_parcial['ID'].str.contains('C', na=False)].sample(num_dias).reset_index(drop=True)
    
    plan = []
    for i in range(num_dias):
        plan.append({
            'Día': f'Día {i+1}',
            'Almuerzo': df_a.iloc[i].to_dict(),
            'Cena': df_c.iloc[i].to_dict()
        })
    return pd.DataFrame(plan)

def motor_O_orden(df, ultimo_id):
    df['n_id'] = df['ID'].str.extract(r'(\d+)').fillna(0).astype(int)
    proximas = df[df['n_id'] > ultimo_id]
    return normalizar_df(proximas, 7)

def motor_A_saludable(df):
    return normalizar_df(df, 7)

def motor_I_ingredientes(df, disponibles):
    disp_l = [x.lower().strip() for x in disponibles]
    def score(row):
        return sum(1 for ing in disp_l if ing in str(row.get('Ingredientes', '')).lower())
    df['Score'] = df.apply(score, axis=1)
    # Seleccionamos las mejores opciones pero con un toque de azar
    mejores = df.nlargest(15, 'Score')
    return normalizar_df(mejores, 3)

def generar_lista_compra(df_menu, df_maestro, n):
    compra = defaultdict(lambda: defaultdict(lambda: {"cant": 0.0, "uni": ""}))
    mapeo = dict(zip(df_maestro.iloc[:,0].str.lower(), df_maestro.iloc[:,1]))
    
    for _, fila in df_menu.iterrows():
        for tipo in ['Almuerzo', 'Cena']:
            receta = fila[tipo]
            ings = str(receta.get('Ingredientes', '')).split(',')
            for item in ings:
                # Buscamos: (cantidad) (unidad) (nombre)
                match = re.search(r'([\d\.]+)\s*([a-zA-Záéíóú]+)\s+(.*)', item.strip())
                if match:
                    cant = float(match.group(1)) * n
                    uni = match.group(2)
                    nom = match.group(3).strip().lower()
                    cat = mapeo.get(nom, "VARIOS").upper()
                    compra[cat][nom]["cant"] += cant
                    compra[cat][nom]["uni"] = uni
                else:
                    nom = item.strip().lower()
                    cat = mapeo.get(nom, "VARIOS").upper()
                    if nom: compra[cat][nom]["cant"] = 0
    return compra

# --- 4. CARGA ---
@st.cache_data
def cargar_datos():
    try:
        df_r = pd.read_csv("recetas_mymenu.csv", encoding='utf-8-sig', sep=None, engine='python')
        df_m = pd.read_csv("maestro_ingredientes.csv", encoding='utf-8-sig', sep=None, engine='python')
        df_r.columns = [c.strip() for c in df_r.columns]
        df_m.columns = [c.strip() for c in df_m.columns]
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
    st.markdown(f'<div style="text-align:center"><img src="{LOGO_RECORTADO}" width="150"></div>', unsafe_allow_html=True)
    col1, col2 = st.columns(2)
    with col1:
        modo = st.selectbox("Modo", ["Saludable (A)", "Inventario (I)", "Orden (O)"])
        comensales = st.slider("Personas", 1, 6, st.session_state['comensales'])
    with col2:
        if modo == "Inventario (I)":
            tengo = st.multiselect("¿Qué tienes?", sorted(df_maestro.iloc[:,0].unique().tolist()))
        elif modo == "Orden (O)":
            ultimo_id = st.number_input("Último ID:", min_value=0)

    if st.button("GENERAR MENÚ"):
        if modo == "Saludable (A)": st.session_state['menu'] = motor_A_saludable(df_recetas)
        elif modo == "Inventario (I)": st.session_state['menu'] = motor_I_ingredientes(df_recetas, tengo)
        elif modo == "Orden (O)": st.session_state['menu'] = motor_O_orden(df_recetas, ultimo_id)
        st.session_state['comensales'] = comensales
        st.session_state['paso'] = 'menu'
        st.rerun()

elif st.session_state['paso'] == 'menu':
    st.markdown(f'<div style="text-align:center"><img src="{LOGO_RECORTADO}" width="100"></div>', unsafe_allow_html=True)
    n = st.session_state['comensales']
    
    for i, row in st.session_state['menu'].iterrows():
        st.write(f"### {row['Día']}")
        c1, c2 = st.columns(2)
        for col, receta, llave in [(c1, row['Almuerzo'], 'A'), (c2, row['Cena'], 'C')]:
            if col.button(f"{receta['Nombre']}", key=f"{llave}{i}"):
                @st.dialog(receta['Nombre'])
                def detalle(r=receta):
                    st.markdown(f"🕒 **Tiempo:** {r.get('Tiempo', '20 min')} | 🔥 **Calorías:** {r.get('Calorias', 'N/A')}")
                    st.subheader("🛒 Ingredientes")
                    st.write(escalar_cantidades(r['Ingredientes'], n))
                    st.subheader("👨‍🍳 Preparación")
                    st.write(r.get('Descripcion', 'Ver detalle en PDF.'))
                detalle()

    st.write("---")
    st.header("🛒 Lista de la Compra")
    compra = generar_lista_compra(st.session_state['menu'], df_maestro, n)
    for cat, prods in compra.items():
        with st.expander(f"📍 {cat}"):
            for p, d in prods.items():
                txt = f"{d['cant']} {d['uni']} {p.capitalize()}" if d['cant'] > 0 else p.capitalize()
                st.write(f"☐ {txt}")

    if st.button("⬅️ RECONFIGURAR"):
        st.session_state['paso'] = 'configurar'
        st.rerun()
