import streamlit as st
import pandas as pd
import random
import re
import os
from collections import defaultdict

# --- 1. CONFIGURACIÓN Y ESTILO (BRANDING) ---
st.set_page_config(page_title="MyMenu App", page_icon="🍴", layout="wide")

# Dirección del logo en GitHub (directa a imagen raw)
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
    .stButton>button {{ 
        background-color: var(--primary); 
        color: white; 
        border-radius: 20px; 
        border: none; 
        padding: 10px 25px;
        font-weight: bold;
    }}
    .stSidebar {{ background-color: #EFE6D5; }}
    h1, h2, h3 {{ color: var(--secondary) !important; text-align: center; }}
    thead tr th {{ background-color: var(--secondary) !important; color: white !important; }}
    /* Ajuste para que la tabla se vea bien en móvil */
    .stTable {{ font-size: 14px; }}
    </style>
    """, unsafe_allow_html=True)

local_css()

# Inicialización del estado de sesión para que el menú persista en móvil
if 'menu' not in st.session_state:
    st.session_state['menu'] = None
if 'modo_usado' not in st.session_state:
    st.session_state['modo_usado'] = None
if 'en_casa' not in st.session_state:
    st.session_state['en_casa'] = []

# --- 2. MOTORES DE SELECCIÓN AVANZADOS (INTEGRADOS DE COLAB) ---

# Modo A - Aleatorio Saludable (con filtros de nutrición)
def motor_A_avanzado(df):
    # Limpieza de nombres de columnas para que coincidan con la lógica (Calorias sin tilde)
    df.columns = [c.replace('í', 'i').strip() for c in df.columns]

    memoria = {
        'proteinas_usadas': [],
        'conteo_huevos': 0,
        'conteo_legumbres': 0,
        'ids_usados': []
    }

    plan_semanal = []
    df_a = df[df['ID'].str.contains('A', na=False)].copy()
    df_c = df[df['ID'].str.contains('C', na=False)].copy()

    for dia in range(1, 8):
        # --- SELECCIÓN ALMUERZO ---
        opciones_a = df_a[~df_a['ID'].isin(memoria['ids_usados'])].copy()

        # Filtros de Salud
        if memoria['conteo_legumbres'] >= 3:
            opciones_a = opciones_a[~opciones_a['Subcategorias_App'].str.contains('Legumbres', na=False)]
        elif dia >= 6 and memoria['conteo_legumbres'] < 2:
            solo_leg = opciones_a[opciones_a['Subcategorias_App'].str.contains('Legumbres', na=False)]
            if not solo_leg.empty: opciones_a = solo_leg

        for prot in set(memoria['proteinas_usadas']):
            if memoria['proteinas_usadas'].count(prot) >= 2:
                opciones_a = opciones_a[~opciones_a['Subcategorias_App'].str.contains(prot, na=False)]

        if opciones_a.empty: opciones_a = df_a # Reset si se acaban

        almuerzo = opciones_a.sample(1).iloc[0]
        memoria['ids_usados'].append(almuerzo['ID'])
        memoria['conteo_legumbres'] += 1 if 'Legumbres' in str(almuerzo['Subcategorias_App']) else 0
        memoria['proteinas_usadas'].append(almuerzo['Subcategorias_App'])

        # --- SELECCIÓN CENA ---
        opciones_c = df_c[~df_c['ID'].isin(memoria['ids_usados'])].copy()

        if memoria['conteo_huevos'] >= 4:
            opciones_c = opciones_c[~opciones_c['Ingredientes_Base'].str.contains('Huevo', na=False)]

        if 'Hortalizas' in str(almuerzo['Subcategorias_App']):
            hoja_verde = opciones_c[opciones_c['Subcategorias_App'].str.contains('Hoja Verde', na=False)]
            if not hoja_verde.empty: opciones_c = hoja_verde

        if almuerzo['Calorias'] > 400:
            opciones_c = opciones_c[opciones_c['Calorias'] < 250]

        if opciones_c.empty:
            opciones_c = df_c[~df_c['ID'].isin(memoria['ids_usados'])]

        if opciones_c.empty: opciones_c = df_c # Reset si se acaban

        cena = opciones_c.sample(1).iloc[0]
        memoria['ids_usados'].append(cena['ID'])
        memoria['conteo_huevos'] += 1 if 'Huevo' in str(cena['Ingredientes_Base']) else 0

        plan_semanal.append({
            'Día': f'Día {dia}',
            'Almuerzo': almuerzo['Nombre'],
            'Cal_A': almuerzo['Calorias'],
            'Ing_A': almuerzo['Ingredientes'],
            'Cena': cena['Nombre'],
            'Cal_C': cena['Calorias'],
            'Ing_C': cena['Ingredientes']
        })

    return pd.DataFrame(plan_semanal)

# Modo I - Selección por Inventario (prioriza aprovechamiento)
def motor_I_avanzado(df, ingredientes_disponibles, num_dias=3):
    df.columns = [c.replace('í', 'i').strip() for c in df.columns]
    disponibles = [x.lower().strip() for x in ingredientes_disponibles]
    
    def calcular_score(row):
        ing_base_receta = str(row['Ingredientes_Base']).lower()
        return sum(1 for ing in disponibles if ing in ing_base_receta)

    df_scored = df.copy()
    df_scored['Score'] = df_scored.apply(calcular_score, axis=1)
    
    opciones_a = df_scored[df_scored['ID'].str.contains('A', na=False)].sort_values('Score', ascending=False)
    opciones_c = df_scored[df_scored['ID'].str.contains('C', na=False)].sort_values('Score', ascending=False)

    plan_semanal = []
    ids_usados = []

    for i in range(num_dias):
        # Selección Almuerzo
        opc_a_disp = opciones_a[~opciones_a['ID'].isin(ids_usados)]
        if opc_a_disp.empty: break
        alm = opc_a_disp.iloc[0]
        ids_usados.append(alm['ID'])
        
        # Selección Cena
        opc_c_disp = opciones_c[~opciones_c['ID'].isin(ids_usados)]
        if opc_c_disp.empty: break
        cena = opc_c_disp.iloc[0]
        ids_usados.append(cena['ID'])
        
        plan_semanal.append({
            'Día': f'Día {i+1}',
            'Almuerzo': alm['Nombre'],
            'Cal_A': alm['Calorias'],
            'Ing_A': alm['Ingredientes'],
            'Cena': cena['Nombre'],
            'Cal_C': cena['Calorias'],
            'Ing_C': cena['Ingredientes']
        })

    return pd.DataFrame(plan_semanal)

# Modo O - Selección por Orden numérico
def motor_O_avanzado(df, ultimo_id_num, num_dias=7):
    df_temp = df.copy()
    df_temp.columns = [c.replace('í', 'i').strip() for c in df_temp.columns]
    
    df_temp['n_id'] = df_temp['ID'].str.extract(r'(\d+)').fillna(0).astype(int)
    es_impar = ultimo_id_num % 2 != 0
    
    if es_impar:
        serie = df_temp[df_temp['n_id'] % 2 != 0].sort_values('n_id')
    else:
        serie = df_temp[df_temp['n_id'] % 2 == 0].sort_values('n_id')
    
    opciones = serie[serie['n_id'] > ultimo_id_num]
    
    almuerzos = opciones[opciones['ID'].str.contains('A')]
    cenas = opciones[opciones['ID'].str.contains('C')]
    
    # Bucle de retorno si se acaba
    if len(almuerzos) < num_dias:
        almuerzos = pd.concat([almuerzos, serie[serie['ID'].str.contains('A')]]).drop_duplicates(subset=['ID'])
    if len(cenas) < num_dias:
        cenas = pd.concat([cenas, serie[serie['ID'].str.contains('C')]]).drop_duplicates(subset=['ID'])

    plan_semanal = []
    for i in range(num_dias):
        if i < len(almuerzos) and i < len(cenas):
            alm = almuerzos.iloc[i]
            cena = cenas.iloc[i]
            plan_semanal.append({
                'Día': f'Día {i+1}',
                'Almuerzo': f"({alm['ID']}) {alm['Nombre']}",
                'Cal_A': alm['Calorias'],
                'Ing_A': alm['Ingredientes'],
                'Cena': f"({cena['ID']}) {cena['Nombre']}",
                'Cal_C': cena['Calorias'],
                'Ing_C': cena['Ingredientes']
            })
    return pd.DataFrame(plan_semanal)

# --- 3. LÓGICA DE LISTA DE LA COMPRA UNIVERSAL ---

def generar_lista_compra_universal_avanzada(df_menu, df_maestro, num_comensales=1, ingredientes_en_casa=None):
    # Limpieza de maestro para mapeo
    df_maestro.columns = [c.strip() for c in df_maestro.columns]
    
    mapeo_pasillos = dict(zip(df_maestro.iloc[:,0].str.lower(), df_maestro.iloc[:,1])) # Asume col 1: Ingrediente, col 2: Categoria
    en_casa = [x.lower().strip() for x in ingredientes_en_casa] if ingredientes_en_casa else []
    inventario = defaultdict(lambda: defaultdict(lambda: defaultdict(float)))
    
    for _, fila in df_menu.iterrows():
        cols_ingredientes = [c for c in df_menu.columns if c.startswith('Ing_')]
        
        for col in cols_ingredientes:
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
                            pasillo = str(cat_maestra).upper().strip()
                            break
                    
                    if pasillo in ["DESPENSA", "OTROS", "OTROS / DESPENSA", "DESPENSA / OTROS"]:
                        pasillo = "DESPENSA / OTROS"
                    
                    inventario[pasillo][nombre_completo][unidad] += cantidad
                else:
                    nombre_v = item.capitalize()
                    if not any(casa in nombre_v.lower() for casa in en_casa):
                        inventario["ESPECIAS / VARIOS"][nombre_v]['sin_unidad'] = 1
    return inventario

# --- 4. CARGA DE DATOS ---
# Logo centrado
st.image(LOGO_URL, width=200, output_format="PNG")

st.sidebar.title("MyMenu Config")
df, df_maestro = None, None
file_r, file_m = "recetas_mymenu.csv", "maestro_ingredientes.csv"

if os.path.exists(file_r) and os.path.exists(file_m):
    try:
        # Carga todoterreno con detección de separador y encoding latin1
        df = pd.read_csv(file_r, encoding='latin1', sep=None, engine='python')
        df_maestro = pd.read_csv(file_m, encoding='latin1', sep=None, engine='python')
        
        # Limpieza inicial de columnas y datos clave
        df.columns = [c.strip() for c in df.columns]
        df_maestro.columns = [c.strip() for c in df_maestro.columns]
        if 'ID' in df.columns:
            df['ID'] = df['ID'].astype(str).str.strip().str.upper()
            
        st.sidebar.success("✅ Datos de GitHub cargados")
    except Exception as e:
        st.sidebar.error(f"Error al leer archivos: {e}")
else:
    st.sidebar.warning("📂 Esperando archivos en GitHub...")

# --- 5. INTERFAZ DE USUARIO ---
if df is not None and df_maestro is not None:
    modo = st.sidebar.selectbox("Modo de Selección", ["Saludable (A)", "Inventario (I)", "Orden (O)"])
    comensales = st.sidebar.slider("Comensales", 1, 6, 2)
    
    # Lógica específica por modo en la barra lateral
    if modo == "Saludable (A)":
        if st.sidebar.button("Generar Menú Semanal"):
            with st.spinner('Planificando tu semana saludable...'):
                st.session_state['menu'] = motor_A_avanzado(df)
                st.session_state['modo_usado'] = "A"
                st.session_state['en_casa'] = [] # Reset

    elif modo == "Inventario (I)":
        # Aseguramos que la columna Ingrediente_Base existe en maestro
        if 'Ingrediente_Base' in df_maestro.columns:
            ing_opciones = sorted(df_maestro['Ingrediente_Base'].unique().tolist())
            tengo = st.sidebar.multiselect("¿Qué tienes en casa?", ing_opciones)
            dias_i = st.sidebar.slider("¿Cuántos días?", 1, 7, 3)
            if st.sidebar.button("Optimizar Inventario"):
                if tengo:
                    with st.spinner('Aprovechando tus existencias...'):
                        st.session_state['menu'] = motor_I_avanzado(df, tengo, dias_i)
                        st.session_state['modo_usado'] = "I"
                        st.session_state['en_casa'] = tengo
                else:
                    st.sidebar.warning("Selecciona al menos un ingrediente.")
        else:
            st.sidebar.error("El maestro no tiene columna 'Ingrediente_Base'")

    elif modo == "Orden (O)":
        ultimo = st.sidebar.number_input("Último ID realizado (número)", min_value=0, value=0)
        dias_o = st.sidebar.slider("¿Cuántos días?", 1, 7, 7)
        if st.sidebar.button("Seguir Serie"):
            with st.spinner('Siguiendo la serie numérica...'):
                st.session_state['menu'] = motor_O_avanzado(df, ultimo, dias_o)
                st.session_state['modo_usado'] = "O"
                st.session_state['en_casa'] = [] # Reset

    # --- SALIDA VISUAL DEL MENÚ ---
    if st.session_state['menu'] is not None:
        st.header("🗓️ Tu Menú MyMenu")
        
        # Mostramos la tabla principal
        st.table(st.session_state['menu'][['Día', 'Almuerzo', 'Cena']])
        
        # Botón para la lista de la compra (fuera de st.sidebar para que persista)
        if st.button("🛒 GENERAR LISTA DE LA COMPRA"):
            casa = st.session_state.get('en_casa', [])
            with st.spinner('Unificando ingredientes...'):
                lista = generar_lista_compra_universal_avanzada(st.session_state['menu'], df_maestro, comensales, casa)
            
            st.header(f"🛒 Lista de la Compra ({comensales} comensales)")
            # Si usamos inventario, avisamos
            if casa:
                st.info(f"Nota: Se han restado {len(casa)} ingredientes que ya tienes.")

            for cat, ingredientes in sorted(lista.items()):
                with st.expander(f"📍 {cat}"):
                    for ing, unis in ingredientes.items():
                        if 'sin_unidad' in unis:
                            st.write(f"☐ {ing}")
                        else:
                            for u, c in unis.items():
                                c_formateada = int(c) if c.is_integer() else round(c, 2)
                                st.write(f"☐ {c_formateada} {u} de {ing}")
else:
    st.info("👋 MyMenu está listo. Asegúrate de tener los CSV en GitHub para empezar automáticamente.")
