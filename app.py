import streamlit as st
import pandas as pd
import re
import os
from collections import defaultdict

# --- 1. CONFIGURACIÓN ---
st.set_page_config(page_title="MyMenú", page_icon="🍴", layout="wide")

LOGO_FULL = "https://raw.githubusercontent.com/LuisaOGH/MyMenu/main/logo.png"
LOGO_RECORTADO = "https://raw.githubusercontent.com/LuisaOGH/MyMenu/main/logo_recortado.jpg"
BTN_CONFIG = "https://raw.githubusercontent.com/LuisaOGH/MyMenu/main/boton_configurar.png"
BTN_GENERAR = "https://raw.githubusercontent.com/LuisaOGH/MyMenu/main/boton_generarmenu.png"

def local_css():
    st.markdown(f"""
    <style>
    :root {{ --bg: #F7F3E9; --morado: #4D243D; }}
    .stApp {{ background-color: var(--bg); }}
    
    /* Botones de imagen de las pantallas 1 y 2 */
    .btn-imagen > div > button {{
        background-image: url('{BTN_CONFIG}');
        background-size: contain; background-repeat: no-repeat; background-position: center;
        background-color: transparent !important; border: none !important;
        height: 80px !important; width: 300px !important; color: transparent !important;
        margin: auto; display: block;
    }}
    .btn-generar > div > button {{
        background-image: url('{BTN_GENERAR}');
        background-size: contain; background-repeat: no-repeat; background-position: center;
        background-color: transparent !important; border: none !important;
        height: 80px !important; width: 300px !important; color: transparent !important;
        margin: auto; display: block;
    }}
    
    /* Botones del menú (Pantalla 3) - Morados y elegantes */
    .menu-btn > div > button {{
        background-color: var(--morado) !important;
        color: white !important;
        font-weight: bold !important;
        border-radius: 8px !important;
        border: none !important;
        margin-bottom: 10px;
    }}
    h1, h2, h3, h4 {{ color: var(--morado) !important; text-align: center; }}
    </style>
    """, unsafe_allow_html=True)

local_css()

# --- 2. ESTADOS Y DATOS ---
if 'paso' not in st.session_state: st.session_state['paso'] = 'inicio'
if 'menu' not in st.session_state: st.session_state['menu'] = None
if 'comensales' not in st.session_state: st.session_state['comensales'] = 2

@st.cache_data
def cargar_datos():
    try:
        # Usamos latin1 para evitar errores de caracteres especiales
        df_r = pd.read_csv("recetas_mymenu.csv", encoding='latin1', sep=None, engine='python')
        df_m = pd.read_csv("maestro_ingredientes.csv", encoding='latin1', sep=None, engine='python')
        df_r.columns = [c.strip() for c in df_r.columns]
        df_m.columns = [c.strip() for c in df_m.columns]
        return df_r, df_m
    except: return None, None

df_recetas, df_maestro = cargar_datos()

# --- 3. FUNCIONES TÉCNICAS ---

def escalar_valor(texto, n):
    if pd.isna(texto): return ""
    return re.sub(r'(\d+(?:\.\d+)?)', lambda m: str(round(float(m.group(1)) * n, 2)), str(texto))

def motor_seleccion(df, modo, n_dias=7, ultimo_id=0):
    df['ID_str'] = df['ID'].astype(str)
    alms = df[df['ID_str'].str.contains('A', case=False, na=False)]
    cens = df[df['ID_str'].str.contains('C', case=False, na=False)]
    
    if modo == "Orden (O)":
        df['n_num'] = df['ID_str'].str.extract(r'(\d+)').fillna(0).astype(int)
        alms = alms[alms['n_num'] > ultimo_id].sort_values('n_num')
        cens = cens[cens['n_num'] > ultimo_id].sort_values('n_num')

    cant = min(n_dias, len(alms), len(cens))
    if cant == 0: return None
    
    # Si es modo Saludable (A) hacemos sample, si es Orden (O) tomamos los primeros
    res_a = alms.sample(cant) if modo == "Saludable (A)" else alms.head(cant)
    res_c = cens.sample(cant) if modo == "Saludable (A)" else cens.head(cant)
    
    plan = []
    for i in range(cant):
        plan.append({
            'Día': i + 1,
            'Almuerzo': res_a.iloc[i].to_dict(),
            'Cena': res_c.iloc[i].to_dict()
        })
    return pd.DataFrame(plan)

# --- 4. LÓGICA DE NAVEGACIÓN ---

# PANTALLA 1: INICIO
if st.session_state['paso'] == 'inicio':
    st.image(LOGO_FULL, use_container_width=True)
    st.markdown('<div class="btn-imagen">', unsafe_allow_html=True)
    if st.button("CONFIGURAR"):
        st.session_state['paso'] = 'configurar'
        st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)

# PANTALLA 2: CONFIGURACIÓN
elif st.session_state['paso'] == 'configurar':
    st.markdown(f'<div style="text-align:center"><img src="{LOGO_RECORTADO}" width="120"></div>', unsafe_allow_html=True)
    st.header("Configura tu semana")
    
    col1, col2 = st.columns(2)
    with col1:
        modo = st.selectbox("Método de selección", ["Saludable (A)", "Orden (O)"])
        comensales = st.slider("¿Cuántos comensales?", 1, 6, st.session_state['comensales'])
    with col2:
        u_id = st.number_input("Último ID cocinado:", min_value=0) if modo == "Orden (O)" else 0

    st.markdown('<div class="btn-generar">', unsafe_allow_html=True)
    if st.button("GENERAR"):
        res = motor_seleccion(df_recetas, modo, ultimo_id=u_id)
        if res is not None:
            st.session_state['menu'] = res
            st.session_state['comensales'] = comensales
            st.session_state['paso'] = 'menu'
            st.rerun()
        else:
            st.error("No hay suficientes recetas.")
    st.markdown('</div>', unsafe_allow_html=True)

# PANTALLA 3: MENÚ (VISTA LIMPIA + DIÁLOGOS)
elif st.session_state['paso'] == 'menu':
    st.markdown(f'<div style="text-align:center"><img src="{LOGO_RECORTADO}" width="80"></div>', unsafe_allow_html=True)
    st.header("Tu Menú Semanal")
    n = st.session_state['comensales']

    for i, row in st.session_state['menu'].iterrows():
        st.markdown(f"#### Día {row['Día']}")
        col_a, col_c = st.columns(2)
        
        # Función para abrir el diálogo de detalle
        @st.dialog("Ficha Informativa")
        def mostrar_ficha(datos):
            st.image(LOGO_RECORTADO, width=60)
            st.subheader(datos['Nombre'])
            st.write(f"⏱️ **Preparación:** {datos.get('Tiempo', '25')} min | 🔥 **Calorías:** {datos.get('Calorias', 'N/A')}")
            st.divider()
            st.markdown("**🛒 Ingredientes:**")
            st.write(escalar_valor(datos['Ingredientes'], n))
            st.markdown("**👨‍🍳 Elaboración:**")
            st.write(datos.get('Descripcion', 'No hay descripción disponible.'))

        with col_a:
            st.markdown('<div class="menu-btn">', unsafe_allow_html=True)
            if st.button(f"☀️ {row['Almuerzo']['Nombre']}", key=f"a_{i}"):
                mostrar_ficha(row['Almuerzo'])
            st.markdown('</div>', unsafe_allow_html=True)
            
        with col_c:
            st.markdown('<div class="menu-btn">', unsafe_allow_html=True)
            if st.button(f"🌙 {row['Cena']['Nombre']}", key=f"c_{i}"):
                mostrar_ficha(row['Cena'])
            st.markdown('</div>', unsafe_allow_html=True)

    # --- LISTA DE LA COMPRA POR CATEGORÍAS ---
    st.divider()
    st.header("🛒 Lista de la Compra")
    
    compra_cat = defaultdict(list)
    # Mapeo de categorías desde el maestro
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

    if st.button("⬅️ VOLVER"):
        st.session_state['paso'] = 'configurar'
        st.rerun()
