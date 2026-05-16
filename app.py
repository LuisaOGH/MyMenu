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
    [data-testid="stImage"] img {{ width: 100%; height: auto; border-radius: 0px; }}

    /* Botón Generar (Rosa) */
    .stButton>button {{ 
        background-color: var(--primary); 
        color: white; border-radius: 20px; border: none; 
        padding: 10px 25px; width: 100%; font-weight: bold;
    }}
    
    /* Botón Lista de la Compra (Morado) */
    div.stButton > button[key="btn_lista"] {{
        background-color: var(--secondary) !important;
        color: white !important;
    }}
    
    .stSidebar {{ background-color: #EFE6D5; }}
    h1, h2, h3 {{ color: var(--secondary) !important; text-align: center; }}
    
    /* Limpieza visual: Ocultar alertas de éxito */
    .element-container:has(.stAlert) {{ display: none; }}
    </style>
    """, unsafe_allow_html=True)

local_css()

# Inicialización de estados
if 'menu' not in st.session_state: st.session_state['menu'] = None
if 'en_casa' not in st.session_state: st.session_state['en_casa'] = []

# --- 2. MOTORES DE COLAB (INTEGRADOS) ---

def motor_A_avanzado(df):
    df.columns = [c.replace('í', 'i').replace(' ', '_').strip() for c in df.columns]
    memoria = {'prot': [], 'huevos': 0, 'leg': 0, 'ids': []}
    plan = []
    df_a = df[df['ID'].str.contains('A', na=False)].copy()
    df_c = df[df['ID'].str.contains('C', na=False)].copy()

    for dia in range(1, 8):
        opc_a = df_a[~df_a['ID'].isin(memoria['ids'])]
        if memoria['leg'] >= 3:
            opc_a = opc_a[~opc_a['Subcategorias_App'].str.contains('Legumbres', na=False)]
        almuerzo = opc_a.sample(1).iloc[0] if not opc_a.empty else df_a.sample(1).iloc[0]
        memoria['ids'].append(almuerzo['ID'])
        memoria['leg'] += 1 if 'Legumbres' in str(almuerzo['Subcategorias_App']) else 0
        
        opc_c = df_c[~df_c['ID'].isin(memoria['ids'])]
        if memoria['huevos'] >= 4:
            col_b = 'Ingredientes_Base' if 'Ingredientes_Base' in df.columns else 'Ingredientes'
            opc_c = opc_c[~opc_c[col_b].str.contains('Huevo', na=False)]
        cena = opc_c.sample(1).iloc[0] if not opc_c.empty else df_c.sample(1).iloc[0]
        memoria['ids'].append(cena['ID'])
        memoria['huevos'] += 1 if 'Huevo' in str(cena.get('Ingredientes_Base', '')) else 0

        plan.append({
            'Día': f'Día {dia}', 'Almuerzo': almuerzo['Nombre'], 'Ing_A': almuerzo['Ingredientes'],
            'Desc_A': almuerzo.get('Descripcion', 'Sin descripción'),
            'Cena': cena['Nombre'], 'Ing_C': cena['Ingredientes'],
            'Desc_C': cena.get('Descripcion', 'Sin descripción')
        })
    return pd.DataFrame(plan)

def motor_I_avanzado(df, ingredientes_disponibles, num_dias=3):
    df.columns = [c.replace('í', 'i').replace(' ', '_').strip() for c in df.columns]
    disponibles = [x.lower().strip() for x in ingredientes_disponibles]
    def calcular_score(row):
        return sum(1 for ing in disponibles if ing in str(row.get('Ingredientes_Base', '')).lower())
    df_scored = df.copy()
    df_scored['Score'] = df_scored.apply(calcular_score, axis=1)
    opc_a = df_scored[df_scored['ID'].str.contains('A', na=False)].sort_values('Score', ascending=False)
    opc_c = df_scored[df_scored['ID'].str.contains('C', na=False)].sort_values('Score', ascending=False)
    plan = []
    ids_usados = []
    for i in range(num_dias):
        alm = opc_a[~opc_a['ID'].isin(ids_usados)].iloc[0]
        ids_usados.append(alm['ID'])
        cen = opc_c[~opc_c['ID'].isin(ids_usados)].iloc[0]
        ids_usados.append(cen['ID'])
        plan.append({
            'Día': f'Día {i+1}', 'Almuerzo': alm['Nombre'], 'Ing_A': alm['Ingredientes'], 'Desc_A': alm.get('Descripcion', 'Sin descripción'),
            'Cena': cen['Nombre'], 'Ing_C': cen['Ingredientes'], 'Desc_C': cen.get('Descripcion', 'Sin descripción')
        })
    return pd.DataFrame(plan)

def motor_O_avanzado(df, ultimo_id_num, num_dias=7):
    df_temp = df.copy()
    df_temp.columns = [c.replace('í', 'i').replace(' ', '_').strip() for c in df_temp.columns]
    df_temp['n_id'] = df_temp['ID'].str.extract(r'(\d+)').fillna(0).astype(int)
    es_impar = ultimo_id_num % 2 != 0
    serie = df_temp[df_temp['n_id'] % 2 != (0 if es_impar else 1)].sort_values('n_id')
    opc = serie[serie['n_id'] > ultimo_id_num]
    alms = opc[opc['ID'].str.contains('A')]
    cens = opc[opc['ID'].str.contains('C')]
    plan = []
    for i in range(min(num_dias, len(alms), len(cens))):
        alm, cen = alms.iloc[i], cens.iloc[i]
        plan.append({
            'Día': f'Día {i+1}', 'Almuerzo': f"({alm['ID']}) {alm['Nombre']}", 'Ing_A': alm['Ingredientes'], 'Desc_A': alm.get('Descripcion', 'Sin descripción'),
            'Cena': f"({cen['ID']}) {cen['Nombre']}", 'Ing_C': cen['Ingredientes'], 'Desc_C': cen.get('Descripcion', 'Sin descripción')
        })
    return pd.DataFrame(plan)

# --- 3. LISTA DE LA COMPRA ---
def generar_lista_compra_universal_avanzada(df_menu, df_maestro, num_comensales=1, en_casa=None):
    df_maestro.columns = [c.strip() for c in df_maestro.columns]
    mapeo = dict(zip(df_maestro.iloc[:,0].str.lower(), df_maestro.iloc[:,1]))
    casa = [x.lower().strip() for x in en_casa] if en_casa else []
    inventario = defaultdict(lambda: defaultdict(lambda: defaultdict(float)))
    
    for _, fila in df_menu.iterrows():
        for col in ['Ing_A', 'Ing_C']:
            items = str(fila[col]).split(',')
            for item in items:
                item = item.strip().lower()
                if item == 'nan' or not item: continue
                match = re.search(r'\(?([\d\.]+)\s*([a-zA-Záéíóú]+)\)?\s+(.*)', item)
                if match:
                    cant, uni, nom = float(match.group(1))*num_comensales, match.group(2), match.group(3).strip().capitalize()
                    if any(c in nom.lower() for c in casa): continue
                    pasillo = mapeo.get(nom.lower(), "DESPENSA / OTROS").upper()
                    inventario[pasillo][nom][uni] += cant
                else:
                    nom_v = item.capitalize()
                    if not any(c in nom_v.lower() for c in casa): inventario["ESPECIAS / VARIOS"][nom_v]['sin_unidad'] = 1
    return inventario

# --- 4. CARGA Y LOGO ---
st.image(LOGO_URL, use_container_width=True)
st.sidebar.title("MyMenú Selección")

df, df_maestro = None, None
if os.path.exists("recetas_mymenu.csv") and os.path.exists("maestro_ingredientes.csv"):
    try:
        df = pd.read_csv("recetas_mymenu.csv", encoding='latin1', sep=None, engine='python')
        df_maestro = pd.read_csv("maestro_ingredientes.csv", encoding='latin1', sep=None, engine='python')
    except: pass

# --- 5. INTERFAZ ---
if df is not None and df_maestro is not None:
    modo = st.sidebar.selectbox("Modo", ["Saludable (A)", "Inventario (I)", "Orden (O)"])
    comensales = st.sidebar.slider("Comensales", 1, 6, 2)
    
    if st.sidebar.button("🚀 GENERAR"):
        if modo == "Saludable (A)": st.session_state['menu'] = motor_A_avanzado(df)
        elif modo == "Inventario (I)":
            ing_opc = sorted(df_maestro.iloc[:,0].unique().tolist())
            tengo = st.sidebar.multiselect("¿Qué tienes?", ing_opc)
            if tengo: st.session_state['menu'] = motor_I_avanzado(df, tengo, 3)
        elif modo == "Orden (O)": st.session_state['menu'] = motor_O_avanzado(df, 0, 7)

    if st.session_state['menu'] is not None:
        st.header("MyMenú")
        for i, row in st.session_state['menu'].iterrows():
            c1, c2, c3 = st.columns([1, 2, 2])
            c1.write(f"**{row['Día']}**")
            if c2.button(row['Almuerzo'], key=f"a{i}"):
                @st.dialog(row['Almuerzo'])
                def m_a():
                    st.image(LOGO_URL, width=150)
                    st.subheader("Ingredientes")
                    st.write(row['Ing_A'])
                    st.subheader("Descripción")
                    st.write(row['Desc_A'])
                m_a()
            if c3.button(row['Cena'], key=f"c{i}"):
                @st.dialog(row['Cena'])
                def m_c():
                    st.image(LOGO_URL, width=150)
                    st.subheader("Ingredientes")
                    st.write(row['Ing_C'])
                    st.subheader("Descripción")
                    st.write(row['Desc_C'])
                m_c()
        
        if st.button("🛒 GENERAR LISTA DE LA COMPRA", key="btn_lista"):
            lista = generar_lista_compra_universal_avanzada(st.session_state['menu'], df_maestro, comensales)
            for cat, ings in sorted(lista.items()):
                with st.expander(f"📍 {cat}"):
                    for ing, unis in ings.items():
                        for u, c in unis.items():
                            st.write(f"☐ {int(c) if c.is_integer() else c} {u} de {ing}" if u != 'sin_unidad' else f"☐ {ing}")
