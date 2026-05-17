import streamlit as st
import pandas as pd
import re
import os
import random
from collections import defaultdict
import base64

# --- 1. CONFIGURACIÓN Y ESTILO ---
st.set_page_config(page_title="MyMenú", page_icon="🍴", layout="wide")

LOGO_FULL = "https://raw.githubusercontent.com/LuisaOGH/MyMenu/main/logo.png"

def local_css():
    st.markdown(f"""
    <style>
    :root {{ --morado: #4D243D; --buganvilla: #E01E5A; --bg-cream: #F7F3E9; }}
    .stApp {{ background-color: var(--bg-cream); }}
    div.stButton > button {{
        background-color: var(--morado) !important;
        color: white !important;
        font-size: 20px !important;
        font-weight: bold !important;
        padding: 12px !important;
        border-radius: 12px !important;
        width: 100% !important;
        border: none !important;
    }}
    .btn-receta > div > button {{
        background-color: var(--buganvilla) !important;
        color: white !important;
        font-size: 15px !important;
        border-radius: 8px !important;
        border: none !important;
    }}
    h1, h2, h3, h4 {{ color: var(--morado) !important; text-align: center; }}
    </style>
    """, unsafe_allow_html=True)

local_css()

# --- 2. GESTIÓN DE ESTADOS ---
if 'paso' not in st.session_state: st.session_state['paso'] = 'inicio'
if 'menu' not in st.session_state: st.session_state['menu'] = None
if 'comensales' not in st.session_state: st.session_state['comensales'] = 2

# --- 3. MOTORES Y FUNCIONES TÉCNICAS ---

def escalar_valor(texto, n):
    if pd.isna(texto): return ""
    return re.sub(r'(\d+(?:\.\d+)?)', lambda m: str(round(float(m.group(1)) * n, 2)), str(texto))

def es_repetido(nombre_nueva, nombre_anterior):
    """Detecta si el ingrediente principal (primera palabra del nombre) se repite"""
    if not nombre_anterior: return False
    # Comparamos la primera palabra (ej: "Ensalada de garbanzos" -> "Ensalada")
    # O mejor, buscamos palabras clave como 'Garbanzos', 'Arroz', 'Pasta'
    palabras_clave = ['garbanzos', 'lentejas', 'arroz', 'pasta', 'pollo', 'merluza', 'ensalada']
    for p in palabras_clave:
        if p in nombre_nueva.lower() and p in nombre_anterior.lower():
            return True
    return False

def motor_logica_avanzado(df, modo, n_dias=7, datos_extra=None, recetas_fijas=None):
    df_copy = df.copy()
    df_copy['ID_str'] = df_copy['ID'].astype(str)
    
    # 1. Separar Almuerzos y Cenas
    alms = df_copy[df_copy['ID_str'].str.contains('A', case=False, na=False)]
    cens = df_copy[df_copy['ID_str'].str.contains('C', case=False, na=False)]

    # 2. Filtrar por el modo seleccionado
    if modo == "Orden (O)":
        df_copy['n_num'] = df_copy['ID_str'].str.extract(r'(\d+)').fillna(0).astype(int)
        df_filtrado = df_copy[df_copy['n_num'] > datos_extra].sort_values('n_num')
        alms = df_filtrado[df_filtrado['ID_str'].str.contains('A', case=False, na=False)]
        cens = df_filtrado[df_filtrado['ID_str'].str.contains('C', case=False, na=False)]
    elif modo == "Inventario (I)":
        def score(row): return sum(1 for ing in datos_extra if ing.lower() in str(row['Ingredientes']).lower())
        alms['puntos'] = alms.apply(score, axis=1)
        cens['puntos'] = cens.apply(score, axis=1)
        alms = alms[alms['puntos'] > 0].sort_values('puntos', ascending=False)
        cens = cens[cens['puntos'] > 0].sort_values('puntos', ascending=False)
    else: # Saludable
        alms = alms.sample(frac=1)
        cens = cens.sample(frac=1)

    # 3. Construir el menú con filtro anti-repetición
    plan = []
    last_alm = ""
    last_cen = ""
    
    # Usar recetas fijas si existen
    fijas_list = df_copy[df_copy['Nombre'].isin(recetas_fijas)] if recetas_fijas else pd.DataFrame()

    for i in range(n_dias):
        # Intentar sacar almuerzo (que no repita ingrediente)
        cand_alms = alms[~alms['Nombre'].isin([p['Almuerzo']['Nombre'] for p in plan])]
        pick_a = None
        for _, c in cand_alms.iterrows():
            if not es_repetido(c['Nombre'], last_alm):
                pick_a = c.to_dict()
                break
        if not pick_a and not cand_alms.empty: pick_a = cand_alms.iloc[0].to_dict()

        # Intentar sacar cena
        cand_cens = cens[~cens['Nombre'].isin([p['Cena']['Nombre'] for p in plan])]
        pick_c = None
        for _, c in cand_cens.iterrows():
            if not es_repetido(c['Nombre'], last_cen):
                pick_c = c.to_dict()
                break
        if not pick_c and not cand_cens.empty: pick_c = cand_cens.iloc[0].to_dict()

        if pick_a and pick_c:
            plan.append({'Día': i+1, 'Almuerzo': pick_a, 'Cena': pick_c})
            last_alm = pick_a['Nombre']
            last_cen = pick_c['Nombre']

    return pd.DataFrame(plan)

def crear_descarga(df_menu):
    html = "<h2>Mi Menú Semanal</h2>"
    for _, r in df_menu.iterrows():
        html += f"<p><b>Día {r['Día']}:</b> {r['Almuerzo']['Nombre']} / {r['Cena']['Nombre']}</p>"
    b64 = base64.b64encode(html.encode()).decode()
    return f'<a href="data:text/html;base64,{b64}" download="menu.html" style="color:white;text-decoration:none;">📥 DESCARGAR MENÚ</a>'

# --- 4. CARGA DE DATOS ---
@st.cache_data
def cargar_datos():
    try:
        df_r = pd.read_csv("recetas_mymenu.csv", encoding='latin1', sep=None, engine='python')
        df_m = pd.read_csv("maestro_ingredientes.csv", encoding='latin1', sep=None, engine='python')
        df_r.columns = [c.strip() for c in df_r.columns]
        df_m.columns = [c.strip() for c in df_m.columns]
        return df_r, df_m
    except: return None, None

df_recetas, df_maestro = cargar_datos()

# --- 5. PANTALLAS ---

if st.session_state['paso'] == 'inicio':
    st.image(LOGO_FULL, use_container_width=True)
    if st.button("CONFIGURAR MI MENÚ"):
        st.session_state['paso'] = 'configurar'; st.rerun()

elif st.session_state['paso'] == 'configurar':
    st.header("Personaliza tu Menú")
    col1, col2 = st.columns(2)
    with col1:
        modo = st.selectbox("Estrategia", ["Saludable (A)", "Inventario (I)", "Orden (O)"])
        comensales = st.slider("Comensales", 1, 6, 2)
        # NUEVO: Buscador por nombre
        nombres_disponibles = sorted(df_recetas['Nombre'].unique().tolist()) if df_recetas is not None else []
        fijas = st.multiselect("Fijar recetas específicas:", nombres_disponibles)
    with col2:
        extra = 0
        if modo == "Orden (O)": extra = st.number_input("Último ID:", min_value=0)
        elif modo == "Inventario (I)":
            extra = st.multiselect("Tengo en la despensa:", sorted(df_maestro.iloc[:,0].unique().tolist()) if df_maestro is not None else [])

    if st.button("GENERAR"):
        res = motor_logica_avanzado(df_recetas, modo, datos_extra=extra, recetas_fijas=fijas)
        if res is not None:
            st.session_state['menu'] = res
            st.session_state['comensales'] = comensales
            st.session_state['paso'] = 'menu'
            st.rerun()

elif st.session_state['paso'] == 'menu':
    st.header("Tu Menú Semanal")
    n = st.session_state['comensales']
    
    for i, row in st.session_state['menu'].iterrows():
        st.write(f"#### Día {row['Día']}")
        c_a, c_c = st.columns(2)
        for col, datos, key in [(c_a, row['Almuerzo'], 'a'), (c_c, row['Cena'], 'c')]:
            with col:
                st.markdown('<div class="btn-receta">', unsafe_allow_html=True)
                if st.button(datos['Nombre'], key=f"{key}{i}"):
                    @st.dialog("Detalle")
                    def show(d=datos):
                        st.subheader(d['Nombre'])
                        st.write(f"⏱ {d.get('Tiempo','25')} min | 🔥 {d.get('Calorias','-')}")
                        st.markdown("**Ingredientes:**")
                        st.write(escalar_valor(d['Ingredientes'], n))
                        st.markdown("**Elaboración:**")
                        st.write(d.get('Descripcion',''))
                    show()
                st.markdown('</div>', unsafe_allow_html=True)

    st.divider()
    # Botón de descarga
    st.markdown(f'<div style="background-color:#4D243D;padding:15px;border-radius:10px;text-align:center;">{crear_descarga(st.session_state["menu"])}</div>', unsafe_allow_html=True)
    
    if st.button("⬅ VOLVER"):
        st.session_state['paso'] = 'configurar'; st.rerun()
