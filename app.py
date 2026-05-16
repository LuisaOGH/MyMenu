import streamlit as st
import pandas as pd
import random
import re
import os
from collections import defaultdict

# --- 1. ESTILO Y CONFIGURACIÓN ---
st.set_page_config(page_title="MyMenu App", page_icon="🍴", layout="wide")

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
    .stButton>button {{ background-color: var(--primary); color: white; border-radius: 20px; border: none; padding: 10px 25px; }}
    .stSidebar {{ background-color: #EFE6D5; }}
    h1, h2, h3 {{ color: var(--secondary) !important; }}
    thead tr th {{ background-color: var(--secondary) !important; color: white !important; }}
    </style>
    """, unsafe_allow_html=True)

local_css()

# --- 2. MOTORES DE SELECCIÓN ---

def motor_A(df):
    almuerzos = df[df['ID'].str.contains('A', na=False)].sample(7).reset_index(drop=True)
    cenas = df[df['ID'].str.contains('C', na=False)].sample(7).reset_index(drop=True)
    plan = []
    for i in range(7):
        plan.append({
            'Día': f'Día {i+1}',
            'Almuerzo': almuerzos.iloc[i]['Nombre'],
            'Cal_A': almuerzos.iloc[i]['Calorias'],
            'Ing_A': almuerzos.iloc[i]['Ingredientes'],
            'Cena': cenas.iloc[i]['Nombre'],
            'Cal_C': cenas.iloc[i]['Calorias'],
            'Ing_C': cenas.iloc[i]['Ingredientes']
        })
    return pd.DataFrame(plan)

def motor_I(df, disponibles, num_dias):
    def calcular_score(row):
        ing_base = str(row.get('Ingredientes_Base', '')).lower()
        return sum(1 for ing in disponibles if ing.lower() in ing_base)
    df_scored = df.copy()
    df_scored['Score'] = df_scored.apply(calcular_score, axis=1)
    opciones_a = df_scored[df_scored['ID'].str.contains('A', na=False)].sort_values('Score', ascending=False)
    opciones_c = df_scored[df_scored['ID'].str.contains('C', na=False)].sort_values('Score', ascending=False)
    plan = []
    for i in range(min(num_dias, len(opciones_a))):
        alm, cena = opciones_a.iloc[i], opciones_c.iloc[i]
        plan.append({'Día': f'Día {i+1}', 'Almuerzo': alm['Nombre'], 'Cal_A': alm['Calorias'], 'Ing_A': alm['Ingredientes'], 'Cena': cena['Nombre'], 'Cal_C': cena['Calorias'], 'Ing_C': cena['Ingredientes']})
    return pd.DataFrame(plan)

def motor_O(df, ultimo_id, num_dias):
    df_temp = df.copy()
    df_temp['n_id'] = df_temp['ID'].str.extract(r'(\d+)').fillna(0).astype(int)
    es_impar = ultimo_id % 2 != 0
    serie = df_temp[df_temp['n_id'] % 2 != (0 if es_impar else 1)].sort_values('n_id')
    proximas = serie[serie['n_id'] > ultimo_id]
    if len(proximas) < num_dias * 2: proximas = pd.concat([proximas, serie]).drop_duplicates('ID')
    alm = proximas[proximas['ID'].str.contains('A', na=False)]
    cen = proximas[proximas['ID'].str.contains('C', na=False)]
    plan = []
    for i in range(min(num_dias, len(alm))):
        plan.append({'Día': f'Día {i+1}', 'Almuerzo': f"({alm.iloc[i]['ID']}) {alm.iloc[i]['Nombre']}", 'Cal_A': alm.iloc[i]['Calorias'], 'Ing_A': alm.iloc[i]['Ingredientes'], 'Cena': f"({cen.iloc[i]['ID']}) {cen.iloc[i]['Nombre']}", 'Cal_C': cen.iloc[i]['Calorias'], 'Ing_C': cen.iloc[i]['Ingredientes']})
    return pd.DataFrame(plan)

def generar_lista_compra_universal(df_menu, df_maestro, num_comensales=1, ingredientes_en_casa=None):
    # Lógica simplificada para evitar errores de mapeo
    inventario = defaultdict(lambda: defaultdict(lambda: defaultdict(float)))
    mapeo = dict(zip(df_maestro.iloc[:,0].str.lower(), df_maestro.iloc[:,1])) # Asume col 1: Ingrediente, col 2: Categoria
    
    for _, fila in df_menu.iterrows():
        for col in ['Ing_A', 'Ing_C']:
            items = str(fila[col]).split(',')
            for item in items:
                item = item.strip().lower()
                if not item or item == 'nan': continue
                match = re.search(r'\(?([\d\.]+)\s*([a-zA-Záéíóú]+)\)?\s+(.*)', item)
                if match:
                    cant, uni, nom = float(match.group(1))*num_comensales, match.group(2), match.group(3).capitalize()
                    inventario["GENERAL"][nom][uni] += cant
                else:
                    inventario["VARIOS"][item.capitalize()]['unidad'] = 1
    return inventario

# --- 3. CARGA DE DATOS ---
st.sidebar.title("MyMenu Config")
df, df_maestro = None, None
file_r, file_m = "recetas_mymenu.csv", "maestro_ingredientes.csv"

if os.path.exists(file_r) and os.path.exists(file_m):
    try:
        df = pd.read_csv(file_r, encoding='latin1', sep=None, engine='python')
        df_maestro = pd.read_csv(file_m, encoding='latin1', sep=None, engine='python')
        
        # Limpiar nombres de columnas y datos de la columna ID
        df.columns = [c.strip() for c in df.columns]
        if 'ID' in df.columns:
            df['ID'] = df['ID'].astype(str).str.strip().str.upper()
        st.sidebar.success("✅ Recetas cargadas de GitHub")
    except Exception as e:
        st.sidebar.error(f"Error al leer: {e}")
else:
    st.sidebar.warning("📂 Sube los archivos manualmente:")
    u1 = st.sidebar.file_uploader("Recetas", type="csv")
    u2 = st.sidebar.file_uploader("Maestro", type="csv")
    if u1 and u2:
        df, df_maestro = pd.read_csv(u1, encoding='latin1'), pd.read_csv(u2, encoding='latin1')
        df.columns = [c.strip() for c in df.columns]
        df['ID'] = df['ID'].astype(str).str.strip().str.upper()

# --- 4. INTERFAZ ---
if df is not None and df_maestro is not None:
    modo = st.sidebar.selectbox("Modo de Selección", ["Saludable (A)", "Inventario (I)", "Orden (O)"])
    comensales = st.sidebar.slider("Comensales", 1, 6, 2)
    
    if st.sidebar.button("Generar Menú"):
        if modo == "Saludable (A)": st.session_state['menu'] = motor_A(df)
        elif modo == "Inventario (I)": st.session_state['menu'] = motor_I(df, [], 3)
        elif modo == "Orden (O)": st.session_state['menu'] = motor_O(df, 0, 7)

    if 'menu' in st.session_state:
        st.header("🗓️ Tu Menú MyMenu")
        st.table(st.session_state['menu'][['Día', 'Almuerzo', 'Cena']])
        if st.button("🛒 Generar Lista"):
            lista = generar_lista_compra_universal(st.session_state['menu'], df_maestro, comensales)
            for cat, ings in lista.items():
                with st.expander(f"📍 {cat}"):
                    for ing, unis in ings.items():
                        for u, c in unis.items(): st.write(f"☐ {c} {u} de {ing}")
