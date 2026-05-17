import streamlit as st
import pandas as pd
import random
import re
import os
from collections import defaultdict

# --- 1. CONFIGURACIÓN ---
st.set_page_config(page_title="MyMenú", page_icon="🍴", layout="wide")

# URLs de activos
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
        height: 60px !important;
        border: none !important;
    }}
    h1, h2, h3 {{ color: var(--morado) !important; text-align: center; }}
    </style>
    """, unsafe_allow_html=True)

local_css()

# --- 2. GESTIÓN DE ESTADOS ---
if 'paso' not in st.session_state: st.session_state['paso'] = 'inicio'
if 'menu' not in st.session_state: st.session_state['menu'] = None
if 'comensales' not in st.session_state: st.session_state['comensales'] = 2

# --- 3. FUNCIONES TÉCNICAS ---

def escalar_cantidades(texto, n):
    if pd.isna(texto): return "Ingredientes no disponibles"
    return re.sub(r'(\d+(?:\.\d+)?)', lambda m: str(round(float(m.group(1)) * n, 2)), str(texto))

def normalizar_df(df_parcial, num_dias):
    """Convierte cualquier selección de recetas en la estructura Día/Almuerzo/Cena"""
    # Separar almuerzos y cenas
    alms_raw = df_parcial[df_parcial['ID'].str.contains('A', na=False, case=False)]
    cens_raw = df_parcial[df_parcial['ID'].str.contains('C', na=False, case=False)]
    
    if len(alms_raw) < 1 or len(cens_raw) < 1:
        return None # No hay suficientes recetas

    num_final = min(num_dias, len(alms_raw), len(cens_raw))
    df_a = alms_raw.sample(num_final).reset_index(drop=True)
    df_c = cens_raw.sample(num_final).reset_index(drop=True)
    
    plan = []
    for i in range(num_final):
        plan.append({
            'Día': f'Día {i+1}',
            'Almuerzo': df_a.iloc[i].to_dict(),
            'Cena': df_c.iloc[i].to_dict()
        })
    return pd.DataFrame(plan)

# --- 4. CARGA DE DATOS ---
@st.cache_data
def cargar_datos():
    try:
        df_r = pd.read_csv("recetas_mymenu.csv", encoding='utf-8-sig', sep=None, engine='python')
        df_m = pd.read_csv("maestro_ingredientes.csv", encoding='utf-8-sig', sep=None, engine='python')
        df_r.columns = [c.strip() for c in df_r.columns]
        df_m.columns = [c.strip() for c in df_m.columns]
        return df_r, df_m
    except Exception as e:
        st.error(f"Error al cargar archivos CSV: {e}")
        return None, None

df_recetas, df_maestro = cargar_datos()

# --- 5. LÓGICA DE PANTALLAS ---

if st.session_state['paso'] == 'inicio':
    st.image(LOGO_FULL, use_container_width=True)
    if st.button("IR A SELECCIÓN"):
        st.session_state['paso'] = 'configurar'
        st.rerun()

elif st.session_state['paso'] == 'configurar':
    st.markdown(f'<div style="text-align:center"><img src="{LOGO_RECORTADO}" width="120"></div>', unsafe_allow_html=True)
    st.header("Configuración")
    
    col1, col2 = st.columns(2)
    with col1:
        modo = st.selectbox("Método", ["Saludable (A)", "Inventario (I)", "Orden (O)"])
        comensales = st.slider("Comensales", 1, 6, st.session_state['comensales'])
    with col2:
        if modo == "Inventario (I)":
            tengo = st.multiselect("Ingredientes que tienes:", sorted(df_maestro.iloc[:,0].unique().tolist()) if df_maestro is not None else [])
        elif modo == "Orden (O)":
            ultimo_id = st.number_input("Último ID cocinado:", min_value=0, value=0)

    if st.button("GENERAR MENÚ"):
        resultado = None
        if modo == "Saludable (A)":
            resultado = normalizar_df(df_recetas, 7)
        elif modo == "Orden (O)":
            df_recetas['n_id'] = df_recetas['ID'].str.extract(r'(\d+)').fillna(0).astype(int)
            proximas = df_recetas[df_recetas['n_id'] > ultimo_id]
            resultado = normalizar_df(proximas, 7)
        elif modo == "Inventario (I)":
            if not tengo:
                st.warning("Selecciona al menos un ingrediente.")
            else:
                def score(row): return sum(1 for ing in tengo if ing.lower() in str(row.get('Ingredientes','')).lower())
                df_recetas['Score'] = df_recetas.apply(score, axis=1)
                mejores = df_recetas[df_recetas['Score'] > 0]
                resultado = normalizar_df(mejores, 3) if not mejores.empty else None

        if resultado is not None:
            st.session_state['menu'] = resultado
            st.session_state['comensales'] = comensales
            st.session_state['paso'] = 'menu'
            st.rerun()
        else:
            st.error("No se encontraron suficientes recetas con esos criterios. Prueba otra opción.")

elif st.session_state['paso'] == 'menu':
    st.markdown(f'<div style="text-align:center"><img src="{LOGO_RECORTADO}" width="80"></div>', unsafe_allow_html=True)
    n = st.session_state['comensales']
    
    # Render del Menú
    for i, row in st.session_state['menu'].iterrows():
        st.write(f"#### {row['Día']}")
        c1, c2 = st.columns(2)
        for col, receta, llave in [(c1, row['Almuerzo'], 'A'), (c2, row['Cena'], 'C')]:
            if col.button(f"{receta['Nombre']}", key=f"{llave}{i}"):
                @st.dialog(receta['Nombre'])
                def mostrar_detalle(r=receta):
                    st.write(f"🕒 {r.get('Tiempo', '20 min')} | 🔥 {r.get('Calorias', 'N/A')} kcal")
                    st.subheader("🛒 Ingredientes")
                    st.write(escalar_cantidades(r.get('Ingredientes',''), n))
                    st.subheader("👨‍🍳 Preparación")
                    st.write(r.get('Descripcion', 'Consulta el PDF detallado.'))
                mostrar_detalle()

    # Lista de la Compra Simplificada
    st.write("---")
    st.header("🛒 Lista de la Compra")
    with st.expander("Ver lista completa"):
        lista_final = defaultdict(float)
        for _, fila in st.session_state['menu'].iterrows():
            for t in ['Almuerzo', 'Cena']:
                ing_str = str(fila[t].get('Ingredientes', ''))
                for item in ing_str.split(','):
                    if item.strip(): lista_final[item.strip().capitalize()] += 1
        
        for ing in sorted(lista_final.keys()):
            st.write(f"☐ {ing}")

    if st.button("⬅️ RECONFIGURAR"):
        st.session_state['paso'] = 'configurar'
        st.rerun()
