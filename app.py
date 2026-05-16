import streamlit as st
import pandas as pd
import random
import re
import os
from collections import defaultdict

# --- 1. CONFIGURACIÓN E INYECCIÓN DE ESTILO (BRANDING) ---
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

# --- 2. EL "CEREBRO" (FUNCIONES LÓGICAS) ---

def unificar_categorias(pasillo):
    pasillo = str(pasillo).upper().strip()
    if pasillo in ["DESPENSA", "OTROS", "OTROS / DESPENSA"]:
        return "DESPENSA / OTROS"
    return pasillo

def generar_lista_compra_universal(df_menu, df_maestro, num_comensales=1, ingredientes_en_casa=None):
    mapeo_pasillos = dict(zip(df_maestro['Ingrediente_Base'].str.lower(), df_maestro['Categoria']))
    en_casa = [x.lower().strip() for x in ingredientes_en_casa] if ingredientes_en_casa else []
    inventario = defaultdict(lambda: defaultdict(lambda: defaultdict(float)))
    
    for _, fila in df_menu.iterrows():
        for col in ['Ing_A', 'Ing_C']:
            items = str(fila[col]).split(',')
            for item in items:
                item = item.strip().lower()
                if item == 'nan' or not item: continue
                match = re.search(r'\(?([\d\.]+)\s*([a-zA-Záéíóú]+)\)?\s+(.*)', item)
                if match:
                    cantidad = float(match.group(1)) * num_comensales
                    unidad = match.group(2)
                    nombre_completo = match.group(3).strip().capitalize()
                    if any(casa in nombre_completo.lower() for casa in en_casa): continue
                    
                    pasillo = "DESPENSA / OTROS"
                    for ing_base, cat_maestra in mapeo_pasillos.items():
                        if ing_base in nombre_completo.lower():
                            pasillo = unificar_categorias(cat_maestra)
                            break
                    inventario[pasillo][nombre_completo][unidad] += cantidad
                else:
                    nombre_v = item.capitalize()
                    if not any(casa in nombre_v.lower() for casa in en_casa):
                        inventario["ESPECIAS / VARIOS"][nombre_v]['sin_unidad'] = 1
    return inventario

# --- 3. MOTORES DE SELECCIÓN ---

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
        ing_base = str(row['Ingredientes_Base']).lower()
        return sum(1 for ing in disponibles if ing.lower() in ing_base)
    df_scored = df.copy()
    df_scored['Score'] = df_scored.apply(calcular_score, axis=1)
    opciones_a = df_scored[df_scored['ID'].str.contains('A')].sort_values('Score', ascending=False)
    opciones_c = df_scored[df_scored['ID'].str.contains('C')].sort_values('Score', ascending=False)
    plan = []
    for i in range(min(num_dias, len(opciones_a))):
        alm = opciones_a.iloc[i]
        cena = opciones_c.iloc[i]
        plan.append({'Día': f'Día {i+1}', 'Almuerzo': alm['Nombre'], 'Cal_A': alm['Calorias'], 'Ing_A': alm['Ingredientes'], 'Cena': cena['Nombre'], 'Cal_C': cena['Calorias'], 'Ing_C': cena['Ingredientes']})
    return pd.DataFrame(plan)

def motor_O(df, ultimo_id, num_dias):
    df_temp = df.copy()
    df_temp['n_id'] = df_temp['ID'].str.extract(r'(\d+)').astype(int)
    es_impar = ultimo_id % 2 != 0
    serie = df_temp[df_temp['n_id'] % 2 != (0 if es_impar else 1)].sort_values('n_id')
    proximas = serie[serie['n_id'] > ultimo_id]
    if len(proximas) < num_dias * 2:
        proximas = pd.concat([proximas, serie]).drop_duplicates('ID')
    almuerzos = proximas[proximas['ID'].str.contains('A')]
    cenas = proximas[proximas['ID'].str.contains('C')]
    plan = []
    for i in range(min(num_dias, len(almuerzos))):
        alm = almuerzos.iloc[i]
        cena = cenas.iloc[i]
        plan.append({'Día': f'Día {i+1}', 'Almuerzo': f"({alm['ID']}) {alm['Nombre']}", 'Cal_A': alm['Calorias'], 'Ing_A': alm['Ingredientes'], 'Cena': f"({cena['ID']}) {cena['Nombre']}", 'Cal_C': cena['Calorias'], 'Ing_C': cena['Ingredientes']})
    return pd.DataFrame(plan)

# --- 4. CARGA DE DATOS (AUTO O MANUAL) ---

st.sidebar.title("MyMenu Config")

df = None
df_maestro = None

# Intentar cargar archivos automáticamente desde el repositorio
if os.path.exists("recetas_mymenu.csv") and os.path.exists("maestro_ingredientes.csv"):
    df = pd.read_csv("recetas_mymenu.csv")
    df_maestro = pd.read_csv("maestro_ingredientes.csv")
    st.sidebar.success("✅ Recetas cargadas de GitHub")
else:
    st.sidebar.warning("📂 Sube los CSV manualmente:")
    uploaded_recetas = st.sidebar.file_uploader("Subir Recetas (CSV)", type="csv")
    uploaded_maestro = st.sidebar.file_uploader("Subir Maestro Ingredientes (CSV)", type="csv")
    if uploaded_recetas and uploaded_maestro:
        df = pd.read_csv(uploaded_recetas)
        df_maestro = pd.read_csv(uploaded_maestro)

# --- 5. INTERFAZ DE USUARIO ---

if df is not None and df_maestro is not None:
    modo = st.sidebar.selectbox("Modo de Selección", ["Saludable (A)", "Inventario (I)", "Orden (O)"])
    comensales = st.sidebar.slider("Comensales", 1, 6, 2)
    
    if modo == "Saludable (A)":
        if st.sidebar.button("Generar Menú Semanal"):
            st.session_state['menu'] = motor_A(df)
            st.session_state['modo_usado'] = "A"

    elif modo == "Inventario (I)":
        ing_opciones = sorted(df_maestro['Ingrediente_Base'].unique().tolist())
        tengo = st.sidebar.multiselect("¿Qué tienes en casa?", ing_opciones)
        dias = st.sidebar.slider("¿Cuántos días?", 1, 7, 3)
        if st.sidebar.button("Optimizar Inventario"):
            st.session_state['menu'] = motor_I(df, tengo, dias)
            st.session_state['modo_usado'] = "I"
            st.session_state['en_casa'] = tengo

    elif modo == "Orden (O)":
        ultimo = st.sidebar.number_input("Último ID realizado", min_value=0, value=0)
        dias = st.sidebar.slider("¿Cuántos días?", 1, 7, 7)
        if st.sidebar.button("Seguir Serie"):
            st.session_state['menu'] = motor_O(df, ultimo, dias)
            st.session_state['modo_usado'] = "O"

    if 'menu' in st.session_state:
        st.header(f"🗓️ Tu Menú MyMenu")
        st.table(st.session_state['menu'][['Día', 'Almuerzo', 'Cal_A', 'Cena', 'Cal_C']])
        
        if st.button("🛒 Generar Lista de la Compra"):
            casa = st.session_state.get('en_casa', [])
            lista = generar_lista_compra_universal(st.session_state['menu'], df_maestro, comensales, casa)
            
            st.header("🛒 Lista de la Compra")
            for cat, ingredientes in sorted(lista.items()):
                with st.expander(f"📍 {cat}"):
                    for ing, unis in ingredientes.items():
                        for u, c in unis.items():
                            cant_f = int(c) if c.is_integer() else round(c, 2)
                            st.write(f"☐ {cant_f} {u} de {ing}")
else:
    st.info("👋 Por favor, asegúrate de tener 'recetas_mymenu.csv' y 'maestro_ingredientes.csv' en GitHub.")
