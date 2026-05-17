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
    :root {{ 
        --morado: #4D243D; 
        --buganvilla: #E01E5A; 
        --albero: #DDBB66; 
        --berenjena: #3B0B2E; 
        --bg-cream: #F7F3E9; 
    }}
    .stApp {{ background-color: var(--bg-cream); }}
    
    /* Botones de acción (Morado) */
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

    /* Botones de Recetas (Buganvilla) */
    .btn-receta > div > button {{
        background-color: var(--buganvilla) !important;
        color: white !important;
        font-size: 15px !important;
        border-radius: 8px !important;
        border: none !important;
    }}
    
    /* Botones de Descarga (Albero y Berenjena) */
    .btn-descarga {{
        background-color: var(--albero) !important;
        color: var(--berenjena) !important;
        padding: 15px;
        border-radius: 12px;
        text-align: center;
        font-weight: bold;
        text-decoration: none;
        display: block;
        margin-bottom: 12px;
        border: 2px solid var(--berenjena);
        font-size: 18px;
    }}
    
    h1, h2, h3, h4 {{ color: var(--morado) !important; text-align: center; }}
    </style>
    """, unsafe_allow_html=True)

local_css()

# --- 2. GESTIÓN DE ESTADOS ---
if 'paso' not in st.session_state: st.session_state['paso'] = 'inicio'
if 'menu' not in st.session_state: st.session_state['menu'] = None
if 'comensales' not in st.session_state: st.session_state['comensales'] = 2

# --- 3. FUNCIONES TÉCNICAS Y MOTORES ---

def escalar_valor(texto, n):
    if pd.isna(texto): return ""
    return re.sub(r'(\d+(?:\.\d+)?)', lambda m: str(round(float(m.group(1)) * n, 2)), str(texto))

def es_repetido(nombre_nueva, nombre_anterior):
    if not nombre_anterior: return False
    palabras_clave = ['garbanzo', 'lenteja', 'arroz', 'pasta', 'pollo', 'merluza', 'ensalada', 'huevo']
    for p in palabras_clave:
        if p in nombre_nueva.lower() and p in nombre_anterior.lower():
            return True
    return False

def motor_seleccion(df, modo, n_dias=7, datos_extra=None, fijos=None):
    df_c = df.copy()
    df_c['ID_str'] = df_c['ID'].astype(str)
    
    # Priorizar recetas fijas si el usuario las eligió
    fijas_df = df_c[df_c['Nombre'].isin(fijos)] if fijos else pd.DataFrame()
    
    alms = df_c[df_c['ID_str'].str.contains('A', case=False, na=False)]
    cens = df_c[df_c['ID_str'].str.contains('C', case=False, na=False)]

    if modo == "Orden (O)":
        df_c['n_num'] = df_c['ID_str'].str.extract(r'(\d+)').fillna(0).astype(int)
        df_f = df_c[df_c['n_num'] > datos_extra].sort_values('n_num')
        alms, cens = df_f[df_f['ID_str'].str.contains('A')], df_f[df_f['ID_str'].str.contains('C')]
    elif modo == "Inventario (I)":
        def score(r): return sum(1 for i in datos_extra if i.lower() in str(r['Ingredientes']).lower())
        alms['pts'] = alms.apply(score, axis=1)
        cens['pts'] = cens.apply(score, axis=1)
        alms = alms[alms['pts'] > 0].sort_values('pts', ascending=False)
        cens = cens[cens['pts'] > 0].sort_values('pts', ascending=False)
    else:
        alms, cens = alms.sample(frac=1), cens.sample(frac=1)

    plan = []
    last_a, last_c = "", ""
    
    for i in range(n_dias):
        # Lógica Almuerzo
        pick_a = None
        for _, r in alms.iterrows():
            if r['Nombre'] not in [p['Almuerzo']['Nombre'] for p in plan] and not es_repetido(r['Nombre'], last_a):
                pick_a = r.to_dict(); break
        if not pick_a and not alms.empty: pick_a = alms.iloc[0].to_dict()

        # Lógica Cena
        pick_c = None
        for _, r in cens.iterrows():
            if r['Nombre'] not in [p['Cena']['Nombre'] for p in plan] and not es_repetido(r['Nombre'], last_c):
                pick_c = r.to_dict(); break
        if not pick_c and not cens.empty: pick_c = cens.iloc[0].to_dict()

        if pick_a and pick_c:
            plan.append({'Día': i+1, 'Almuerzo': pick_a, 'Cena': pick_c})
            last_a, last_c = pick_a['Nombre'], pick_c['Nombre']

    return pd.DataFrame(plan)

def get_download_link(df_menu, df_maestro, n, tipo="menu"):
    if tipo == "menu":
        html = "<h2>📅 Mi Planing Semanal</h2>"
        for _, r in df_menu.iterrows():
            html += f"<p><b>Día {r['Día']}:</b> {r['Almuerzo']['Nombre']} / {r['Cena']['Nombre']}</p>"
        label = "📥 DESCARGAR PLANING SEMANAL"
        fname = "menu.html"
    else:
        compra = defaultdict(list)
        mapeo = dict(zip(df_maestro.iloc[:,0].str.lower(), df_maestro.iloc[:,1].str.upper())) if df_maestro is not None else {}
        for _, f in df_menu.iterrows():
            for t in ['Almuerzo', 'Cena']:
                for ing in str(f[t]['Ingredientes']).split(','):
                    ing = ing.strip(); cat = "VARIOS"
                    for k, v in mapeo.items():
                        if k in ing.lower(): cat = v; break
                    compra[cat].append(escalar_valor(ing, n))
        html = "<h2>🛒 Lista de la Compra</h2>"
        for c in sorted(compra.keys()):
            html += f"<h3>{c}</h3><ul>"
            for item in sorted(set(compra[c])): html += f"<li>[ ] {item}</li>"
            html += "</ul>"
        label = "🛒 DESCARGAR LISTA DE LA COMPRA"
        fname = "lista_compra.html"
    
    b64 = base64.b64encode(html.encode()).decode()
    return f'<a href="data:text/html;base64,{b64}" download="{fname}" class="btn-descarga">{label}</a>'

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

# --- 5. LÓGICA DE PANTALLAS ---

if st.session_state['paso'] == 'inicio':
    st.image(LOGO_FULL, use_container_width=True)
    if st.button("CONFIGURAR MI MENÚ"):
        st.session_state['paso'] = 'configurar'; st.rerun()

elif st.session_state['paso'] == 'configurar':
    st.header("Configuración")
    col1, col2 = st.columns(2)
    with col1:
        modo = st.selectbox("Estrategia", ["Saludable (A)", "Inventario (I)", "Orden (O)"])
        comensales = st.slider("Personas", 1, 6, 2)
        nombres = sorted(df_recetas['Nombre'].unique().tolist()) if df_recetas is not None else []
        fijos = st.multiselect("Recetas que quieres sí o sí:", nombres)
    with col2:
        extra = 0
        if modo == "Orden (O)": extra = st.number_input("Último ID:", min_value=0)
        elif modo == "Inventario (I)":
            extra = st.multiselect("¿Qué tienes?", sorted(df_maestro.iloc[:,0].unique().tolist()) if df_maestro is not None else [])

    if st.button("GENERAR MI SEMANA"):
        res = motor_seleccion(df_recetas, modo, datos_extra=extra, fijos=fijos)
        if res is not None:
            st.session_state['menu'] = res
            st.session_state['comensales'] = comensales
            st.session_state['paso'] = 'menu'; st.rerun()

elif st.session_state['paso'] == 'menu':
    st.header("Tu Menú Semanal")
    n = st.session_state['comensales']
    
    for i, row in st.session_state['menu'].iterrows():
        st.write(f"#### Día {row['Día']}")
        ca, cc = st.columns(2)
        for col, datos, k in [(ca, row['Almuerzo'], 'a'), (cc, row['Cena'], 'c')]:
            with col:
                st.markdown('<div class="btn-receta">', unsafe_allow_html=True)
                if st.button(datos['Nombre'], key=f"{k}{i}"):
                    @st.dialog("Detalle")
                    def show(d=datos):
                        st.subheader(d['Nombre'])
                        st.write(f"⏱ {d.get('Tiempo','25')} min | 🔥 {d.get('Calorias','-')}")
                        st.divider()
                        st.markdown("**🛒 Ingredientes:**")
                        st.write(escalar_valor(d['Ingredientes'], n))
                        st.markdown("**👨‍🍳 Elaboración:**")
                        st.write(d.get('Descripcion',''))
                    show()
                st.markdown('</div>', unsafe_allow_html=True)

    st.divider()
    # Botones Albero y Berenjena
    st.markdown(get_download_link(st.session_state['menu'], df_maestro, n, "menu"), unsafe_allow_html=True)
    st.markdown(get_download_link(st.session_state['menu'], df_maestro, n, "compra"), unsafe_allow_html=True)
    
    if st.button("⬅ VOLVER"):
        st.session_state['paso'] = 'configurar'; st.rerun()
