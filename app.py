import streamlit as st
import pandas as pd
from rapidfuzz import process, fuzz
import time

# ==========================================
# CONFIGURACIÓN DE PÁGINA Y TEMA
# ==========================================
st.set_page_config(page_title="Visor COFEPRIS", page_icon="🇲🇽", layout="wide")

st.markdown("""
    <style>
    [data-testid="stSidebar"] { background-color: #13322B; color: white; }
    [data-testid="stSidebar"] * { color: white !important; }
    h1 { color: #6F1827; border-bottom: 2px solid #B38E5D; padding-bottom: 10px; }
    .stButton>button { background-color: #B38E5D; color: white; border: none; width: 100%; }
    .stButton>button:hover { background-color: #6F1827; color: white; }
    </style>
""", unsafe_allow_html=True)

# ==========================================
# CARGA DE DATOS COFEPRIS (PARQUET)
# ==========================================
@st.cache_data
def cargar_parquet():
    try:
        # Carga el archivo Parquet real que generaste
        df = pd.read_parquet("base_registros_sanitarios.parquet")
        # Rellenar nulos para evitar errores en la búsqueda
        df['DenominacionGenerica'] = df['DenominacionGenerica'].fillna('')
        df['Presentacion'] = df['Presentacion'].fillna('')
        # Columna combinada para el Fuzzy Matching
        df['Busqueda_COFEPRIS'] = df['DenominacionGenerica'].astype(str) + " " + df['Presentacion'].astype(str)
        return df
    except Exception as e:
        return None

df_cofepris = cargar_parquet()

# ==========================================
# BARRA LATERAL (SIDEBAR)
# ==========================================
with st.sidebar:
    try:
        st.image("COFEPRIS.png", use_container_width=True)
    except:
        st.caption("Cofepris - Buscador")
    
    st.markdown("---")
    st.markdown("## Análisis para SSA")
    archivo_ssa = st.file_uploader("1. Suba el archivo CSV/Excel de la SSA", type=["csv", "xlsx"])
    
    umbral = st.slider("2. Umbral de similitud (%)", min_value=60, max_value=100, value=85, help="85% es recomendado para tolerar errores de dedo.")

# ==========================================
# PANTALLA PRINCIPAL (PESTAÑAS)
# ==========================================
st.markdown("<h1>Visor Inteligente de Medicamentos</h1>", unsafe_allow_html=True)

if df_cofepris is None:
    st.error("🚨 No se encontró el archivo 'base_registros_sanitarios.parquet'. Asegúrate de subirlo a GitHub o a la carpeta local.")
    st.stop()

# Creamos dos pestañas: Una para buscar libremente y otra para el cruce de SSA
tab1, tab2 = st.tabs(["🔍 Buscador General", "⚙️ Cruce de Datos (SSA)"])

# ------------------------------------------
# PESTAÑA 1: BUSCADOR GENERAL
# ------------------------------------------
with tab1:
    st.markdown("### Base de Datos Activa")
    col1, col2 = st.columns(2)
    busqueda_libre = col1.text_input("Buscar por Denominación Distintiva, Genérica o Registro:")
    filtro_estado = col2.selectbox("Filtrar por Estado:", ["Todos"] + df_cofepris['Estado'].dropna().unique().tolist())
    
    df_mostrar = df_cofepris.copy()
    
    if filtro_estado != "Todos":
        df_mostrar = df_mostrar[df_mostrar['Estado'] == filtro_estado]
        
    if busqueda_libre:
        # Búsqueda simple en todo el texto del dataframe para esa fila
        mask = df_mostrar.astype(str).apply(lambda x: x.str.contains(busqueda_libre, case=False, na=False)).any(axis=1)
        df_mostrar = df_mostrar[mask]
        
    st.write(f"Mostrando {len(df_mostrar)} registros:")
    # Mostramos columnas clave para no saturar la vista
    st.dataframe(df_mostrar[['NumeroRegistro', 'DenominacionDistintiva', 'DenominacionGenerica', 'Presentacion', 'Estado', 'Titular']])

# ------------------------------------------
# PESTAÑA 2: CRUCE DE DATOS (SSA)
# ------------------------------------------
with tab2:
    if archivo_ssa:
        if archivo_ssa.name.endswith('.csv'):
            # Usamos separador de tabulaciones '\t' o comas ',' según venga el archivo
            df_ssa = pd.read_csv(archivo_ssa, encoding='latin1', sep=None, engine='python') 
        else:
            df_ssa = pd.read_excel(archivo_ssa)
            
        st.success("Archivo SSA cargado correctamente. Configure el cruce:")
        
        # Como vimos en los datos reales, todo viene en una sola descripción
        col_c1, col_c2 = st.columns(2)
        columnas_ssa = df_ssa.columns.tolist()
        
        col_clave = col_c1.selectbox("¿Qué columna tiene la Clave?", columnas_ssa)
        col_descripcion = col_c2.selectbox("¿Qué columna tiene la Descripción Completa?", columnas_ssa)
        
        if st.button("Ejecutar Análisis de Fuentes de Abasto"):
            with st.spinner("Procesando descripciones largas con inteligencia matemática..."):
                
                resultados_registros = []
                resultados_fuente = []
                puntajes_confianza = []
                
                for index, row in df_ssa.iterrows():
                    # Tomamos la celda completa de la SSA (ej. "VARENICLINA. TABLETA. Cada tableta...")
                    query = str(row[col_descripcion])
                    
                    # token_set_ratio buscará la intersección de palabras clave ignorando el ruido
                    matches = process.extract(
                        query, 
                        df_cofepris['Busqueda_COFEPRIS'], 
                        scorer=fuzz.token_set_ratio, 
                        limit=None, 
                        score_cutoff=umbral
                    )
                    
                    if matches:
                        indices = [match[2] for match in matches]
                        mejor_puntaje = matches[0][1] # El puntaje de la mejor coincidencia
                        registros_encontrados = df_cofepris.loc[indices, 'NumeroRegistro'].unique()
                        
                        cantidad = len(registros_encontrados)
                        texto_registros = ", ".join(registros_encontrados)
                        
                        if cantidad == 1:
                            tipo_fuente = "Fuente Única"
                        else:
                            tipo_fuente = "Fuente Múltiple"
                    else:
                        texto_registros = "Sin registros"
                        tipo_fuente = "Sin Fuente"
                        mejor_puntaje = 0
                        
                    resultados_registros.append(texto_registros)
                    resultados_fuente.append(tipo_fuente)
                    puntajes_confianza.append(round(mejor_puntaje, 1))
                
                # Agregamos las nuevas variables al Excel de la SSA
                df_ssa['Registros_Cofepris_Encontrados'] = resultados_registros
                df_ssa['Tipo_Fuente'] = resultados_fuente
                df_ssa['Similitud_Matematica_Maxima_%'] = puntajes_confianza
                
                st.success("¡Análisis Terminado!")
                
                # Métricas visuales
                m1, m2, m3 = st.columns(3)
                m1.metric("Fuente Única ✅", resultados_fuente.count('Fuente Única'))
                m2.metric("Fuente Múltiple ⚠️", resultados_fuente.count('Fuente Múltiple'))
                m3.metric("Sin Fuente ❌", resultados_fuente.count('Sin Fuente'))
                
                st.dataframe(df_ssa)
                
                # Botón de descarga
                csv_resultado = df_ssa.to_csv(index=False).encode('latin1', errors='replace')
                st.download_button(
                    label="⬇️ Descargar Resultados para Compras Consolidadas",
                    data=csv_resultado,
                    file_name="Fuentes_Abasto_Analizadas.csv",
                    mime="text/csv"
                )
    else:
        st.info("👈 Por favor, suba el archivo de la SSA en la barra lateral para comenzar.")
