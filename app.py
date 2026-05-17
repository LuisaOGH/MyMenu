import streamlit as st
import pandas as pd
import re
import os
from collections import defaultdict

# --- 1. CONFIGURACIÓN ---
st.set_page_config(page_title="MyMenú", page_icon="🍴", layout="wide")

# URLs de tus imágenes (asegúrate de que los nombres coincidan en GitHub)
LOGO_FULL = "https://raw.githubusercontent.com/LuisaOGH/MyMenu/main/logo.png"
LOGO_RECORTADO = "https://raw.githubusercontent.com/LuisaOGH/MyMenu/main/logo_recortado.jpg"
BTN_CONFIG = "https://raw.githubusercontent.com/LuisaOGH/MyMenu/main/boton_configurar.png"
BTN_GENERAR = "https://raw.githubusercontent.com/LuisaOGH/MyMenu/main/boton_generarmenu.png"

def local_css():
    st.markdown(f"""
    <style>
    :root {{ --bg: #F7F3E9; --morado: #4D243D; }}
    .stApp {{ background-color: var(--bg); }}
    /* Contenedor para botones de imagen */
    .img-btn-container {{ position: relative; width: 300px; margin: auto; }}
    .img-btn-container div.stButton > button {{
        position: absolute; top: 0; left: 0; width: 100%; height: 50px;
        background: transparent !important; color: transparent !important;
        border: none !important; z-index: 10; cursor: pointer;
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

@st.cache_data
def cargar_datos():
    try:
        # Usamos latin1 para evitar el error de la imagen
        df_r = pd.read_csv("recetas_mymenu.csv", encoding='latin1', sep=None, engine='python')
        df_m = pd.read_csv("maestro_ingredientes.csv", encoding='latin1', sep=None, engine='python')
        df_r.columns = [c.strip() for c in df_r.columns]
        df_m.columns = [c.strip() for c in df_m.columns]
        return df_r, df_m
    except:
        return None, None

def escalar_cantidades(texto, n):
    if pd.isna(texto): return ""
    return re.sub(r'(\d+(?:\.\d+)?)', lambda m: str(round(float(m.group(1)) * n, 2)), str(texto))

def normalizar_df(df_parcial, num_dias):
    alms = df_parcial[df_parcial['ID'].astype(str).str.contains('A', case=False, na=False)]
    cens = df_parcial[df_parcial['ID'].astype(str).str.contains('C', case=False, na=False)]
    if alms.empty or cens.empty: return None
    
    cant = min(num_dias, len(alms), len(cens))
    df_a = alms.sample(cant).reset_index(drop=True)
    df_c = cens.sample(cant).reset_index(drop=True)
    
    plan = []
    for i in range(cant):
        plan.append({
            'Día': f'Día {i+1}',
            'Almuerzo': df_a.iloc[i].to_dict(),
            'Cena': df_c.iloc[i].to_dict()
        })
    return pd.DataFrame(plan)

df_recetas, df_maestro = cargar_datos()

# --- 4. LÓGICA DE PANTALLAS ---

# PANTALLA 1: INICIO
if st.session_state['paso'] == 'inicio':
    st.image(LOGO_FULL, use_container_width=True)
    st.markdown('<div class="img-btn-container">', unsafe_allow_html=True)
    st.image(BTN_CONFIG)
    if st.button(" ", key="go_config"):
        st.session_state['paso'] = 'configurar'
        st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)

# PANTALLA 2: CONFIGURACIÓN
elif st.session_state['paso'] == 'configurar':
    st.image(LOGO_RECORTADO, width=120)
    st.header("Configuración")
    
    col1, col2 = st.columns(2)
    with col1:
        modo = st.selectbox("Método", ["Saludable (A)", "Inventario (I)", "Orden (O)"])
        comensales = st.slider("Personas", 1, 6, st.session_state['comensales'])
    with col2:
        if modo == "Inventario (I)":
            tengo = st.multiselect("¿Qué tienes?", sorted(df_maestro.iloc[:,0].unique().tolist()) if df_maestro is not None else [])
        elif modo == "Orden (O)":
            ultimo_id = st.number_input("Último ID cocinado:", min_value=0)

    st.markdown('<div class="img-btn-container">', unsafe_allow_html=True)
    st.image(BTN_GENERAR)
    if st.button(" ", key="go_menu"):
        res = None
        if df_recetas is not None:
            if modo == "Saludable (A)":
                res = normalizar_df(df_recetas, 7)
            elif modo == "Orden (O)":
                df_recetas['n_id'] = df_recetas['ID'].astype(str).str.extract(r'(\d+)').fillna(0).astype(int)
                proximas = df_recetas[df_recetas['n_id'] > ultimo_id]
                res = normalizar_df(proximas, 7)
            
            if res is not None:
                st.session_state['menu'] = res
                st.session_state['comensales'] = comensales
                st.session_state['paso'] = 'menu'
                st.rerun()
            else:
                st.error("No hay suficientes recetas para este criterio.")
    st.markdown('</div>', unsafe_allow_html=True)

# PANTALLA 3: MENÚ
elif st.session_state['paso'] == 'menu':
    st.image(LOGO_RECORTADO, width=80)
    n = st.session_state['comensales']
    
    for i, row in st.session_state['menu'].iterrows():
        st.write(f"### {row['Día']}")
        c1, c2 = st.columns(2)
        for col, receta, llave in [(c1, row['Almuerzo'], 'A'), (c2, row['Cena'], 'C')]:
            if col.button(f"{receta['Nombre']}", key=f"{llave}{i}"):
                @st.dialog(receta['Nombre'])
                def show(r=receta):
                    st.write(f"🕒 {r.get('Tiempo', '20 min')} | 🔥 {r.get('Calorias', 'N/A')} kcal")
                    st.subheader("🛒 Ingredientes")
                    st.write(escalar_cantidades(r.get('Ingredientes',''), n))
                    st.subheader("👨‍🍳 Preparación")
                    st.write(r.get('Descripcion', 'Consulta el PDF.'))
                show()

    # LISTA DE LA COMPRA
    st.divider()
    st.header("🛒 Lista de la Compra")
    with st.expander("Ver lista por categorías"):
        # Lógica simplificada de categorías
        for tipo in ['FRUTA/VERDURA', 'CARNICERÍA', 'DESPENSA']:
            st.markdown(f"**{tipo}**")
            st.write("☐ Ejemplo de ingrediente escalado")

    if st.button("⬅️ VOLVER"):
        st.session_state['paso'] = 'configurar'
        st.rerun()
