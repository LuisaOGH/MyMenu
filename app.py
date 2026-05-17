import streamlit as st
import pandas as pd
import re
import os
import random
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
        --buganvilla: #E01E5A; 
        --bg-cream: #F7F3E9; 
    }}
    .stApp {{ background-color: var(--bg-cream); }}
    
    /* Botones de acción (Morado) */
    div.stButton > button {{
        background-color: var(--morado) !important;
        color: white !important;
        font-size: 22px !important;
        font-weight: bold !important;
        padding: 15px !important;
        border-radius: 15px !important;
        width: 100% !important;
        border: none !important;
    }}

    /* Botones de Recetas (Buganvilla) */
    .btn-receta > div > button {{
        background-color: var(--buganvilla) !important;
        color: white !important;
        font-size: 16px !important;
        padding: 12px !important;
        border-radius: 10px !important;
    }}
    
    /* Contenedor para centrar el logo */
    .logo-container {{
        display: flex;
        justify-content: center;
        margin-bottom: 10px;
    }}
    
    h1, h2, h3, h4 {{ color: var(--morado) !important; text-align: center; }}
    </style>
    """, unsafe_allow_html=True)

local_css()

# --- 2. GESTIÓN DE ESTADOS ---
if 'paso' not in st.session_state: st.session_state['paso'] = 'inicio'
if 'menu' not in st.session_state: st.session_state['menu'] = None
if 'comensales' not in st.session_state: st.session_state['comensales'] = 2

# --- 3. MOTORES Y FUNCIONES ---

def escalar_valor(texto, n):
    if pd.isna(texto): return ""
    return re.sub(r'(\d+(?:\.\d+)?)', lambda m: str(round(float(m.group(1)) * n, 2)), str(texto))

def normalizar_resultado(df_a, df_c, n_dias):
    cant = min(n_dias, len(df_a), len(df_c))
    if cant == 0: return None
    plan = []
    for i in range(cant):
        plan.append({
            'Día': i + 1,
            'Almuerzo': df_a.iloc[i].to_dict(),
            'Cena': df_c.iloc[i].to_dict()
        })
    return pd.DataFrame(plan)

def motor_logica(df, modo, n_dias=7, datos_extra=None):
    df_copy = df.copy()
    df_copy['ID_str'] = df_copy['ID'].astype(str)
    
    if modo == "Orden (O)":
        df_copy['n_num'] = df_copy['ID_str'].str.extract(r'(\d+)').fillna(0).astype(int)
        df_filtrado = df_copy[df_copy['n_num'] > datos_extra].sort_values('n_num')
        alms = df_filtrado[df_filtrado['ID_str'].str.contains('A', case=False, na=False)]
        cens = df_filtrado[df_filtrado['ID_str'].str.contains('C', case=False, na=False)]
    
    elif modo == "Inventario (I)":
        def calcular_puntos(row):
            count = 0
            ing_receta = str(row['Ingredientes']).lower()
            for ing in datos_extra:
                if ing.lower() in ing_receta: count += 1
            return count
        df_copy['puntos'] = df_copy.apply(calcular_puntos, axis=1)
        df_filtrado = df_copy[df_copy['puntos'] > 0].sort_values('puntos', ascending=False)
        alms = df_filtrado[df_filtrado['ID_str'].str.contains('A', case=False, na=False)]
        cens = df_filtrado[df_filtrado['ID_str'].str.contains('C', case=False, na=False)]

    else: # Saludable (A)
        alms = df_copy[df_copy['ID_str'].str.contains('A', case=False, na=False)].sample(frac=1)
        cens = df_copy[df_copy['ID_str'].str.contains('C', case=False, na=False)].sample(frac=1)

    return normalizar_resultado(alms, cens, n_dias)

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

# PANTALLA 1: INICIO
if st.session_state['paso'] == 'inicio':
    st.image(LOGO_FULL, use_container_width=True)
    st.write("<br>", unsafe_allow_html=True)
    if st.button("CONFIGURAR MI MENÚ"):
        st.session_state['paso'] = 'configurar'
        st.rerun()

# PANTALLA 2: SELECCIÓN
elif st.session_state['paso'] == 'configurar':
    # Logo corregido con st.image
    col_l, col_r, col_ex = st.columns([1, 2, 1])
    with col_r: st.image(LOGO_RECORTADO, width=120)
    
    st.header("Configura tu semana")
    
    col1, col2 = st.columns(2)
    with col1:
        modo = st.selectbox("Método de selección", ["Saludable (A)", "Inventario (I)", "Orden (O)"])
        comensales = st.slider("¿Cuántos comensales?", 1, 6, st.session_state['comensales'])
    with col2:
        extra = 0
        if modo == "Orden (O)":
            extra = st.number_input("Último ID cocinado:", min_value=0, step=1)
        elif modo == "Inventario (I)":
            extra = st.multiselect("¿Qué ingredientes tienes?", sorted(df_maestro.iloc[:,0].unique().tolist()) if df_maestro is not None else [])

    if st.button("GENERAR MENÚ"):
        res = motor_logica(df_recetas, modo, datos_extra=extra)
        if res is not None:
            st.session_state['menu'] = res
            st.session_state['comensales'] = comensales
            st.session_state['paso'] = 'menu'
            st.rerun()
        else:
            st.error("No se encontraron recetas suficientes.")

# PANTALLA 3: MENÚ
elif st.session_state['paso'] == 'menu':
    # Logo corregido con st.image
    col_l, col_r, col_ex = st.columns([1, 2, 1])
    with col_r: st.image(LOGO_RECORTADO, width=120)
    
    st.header("Tu Menú Semanal")
    n = st.session_state['comensales']

    for i, row in st.session_state['menu'].iterrows():
        st.markdown(f"#### Día {row['Día']}")
        col_a, col_c = st.columns(2)
        
        @st.dialog("Detalle de la Receta")
        def mostrar_ficha(datos):
            # Logo corregido dentro del diálogo
            st.image(LOGO_RECORTADO, width=80)
            st.subheader(datos['Nombre'])
            st.write(f"⏱️ **Tiempo:** {datos.get('Tiempo', '25')} min | 🔥 **Calorías:** {datos.get('Calorias', 'N/A')}")
            st.divider()
            st.markdown("**🛒 Ingredientes:**")
            st.write(escalar_valor(datos['Ingredientes'], n))
            st.markdown("**👨‍🍳 Elaboración:**")
            st.write(datos.get('Descripcion', 'Consulta el PDF.'))

        with col_a:
            st.markdown('<div class="btn-receta">', unsafe_allow_html=True)
            if st.button(f"☀️ {row['Almuerzo']['Nombre']}", key=f"a_{i}"):
                mostrar_ficha(row['Almuerzo'])
            st.markdown('</div>', unsafe_allow_html=True)
            
        with col_c:
            st.markdown('<div class="btn-receta">', unsafe_allow_html=True)
            if st.button(f"🌙 {row['Cena']['Nombre']}", key=f"c_{i}"):
                mostrar_ficha(row['Cena'])
            st.markdown('</div>', unsafe_allow_html=True)

    # LISTA DE LA COMPRA
    st.divider()
    st.header("🛒 Lista de la Compra")
    compra_cat = defaultdict(list)
    mapeo = dict(zip(df_maestro.iloc[:,0].str.lower(), df_maestro.iloc[:,1].str.upper())) if df_maestro is not None else {}

    for _, fila in st.session_state['menu'].iterrows():
        for t in ['Almuerzo', 'Cena']:
            ingreds = str(fila[t]['Ingredientes']).split(',')
            for ing in ingreds:
                ing = ing.strip()
                cat = "VARIOS"
                for nombre_maestro, categoria in mapeo.items():
                    if nombre_maestro in ing.lower():
                        cat = categoria
                        break
                compra_cat[cat].append(escalar_valor(ing, n))

    for cat in sorted(compra_cat.keys()):
        with st.expander(f"📍 {cat}"):
            for item in sorted(set(compra_cat[cat])):
                st.write(f"☐ {item.capitalize()}")

    st.write("<br>", unsafe_allow_html=True)
    if st.button("⬅️ VOLVER A SELECCIÓN"):
        st.session_state['paso'] = 'configurar'
        st.rerun()
