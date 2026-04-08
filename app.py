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
        # Leer el archivo dependiendo de su formato
        if archivo_ssa.name.endswith('.csv'):
            df_ssa = pd.read_csv(archivo_ssa, encoding='latin1') # latin1 o utf-8 dependiendo de como lo guarde SSA
        else:
            df_ssa = pd.read_excel(archivo_ssa)
            
        st.success("Archivo SSA cargado correctamente. Seleccione las columnas para el cruce:")
        
        # Selectores dinámicos de columnas
        col_c1, col_c2, col_c3 = st.columns(3)
        columnas_ssa = df_ssa.columns.tolist()
        
        col_clave = col_c1.selectbox("Columna: Clave Compendio", columnas_ssa)
        col_activo = col_c2.selectbox("Columna: Principio Activo", columnas_ssa)
        col_pres = col_c3.selectbox("Columna: Presentación", columnas_ssa)
        
        if st.button("Ejecutar Análisis de Fuentes de Abasto"):
            with st.spinner("Comparando bases de datos con inteligencia matemática... esto puede tomar un par de minutos."):
                
                # Preparamos la búsqueda combinada de la SSA
                df_ssa['Busqueda_SSA'] = df_ssa[col_activo].astype(str) + " " + df_ssa[col_pres].astype(str)
                
                resultados_registros = []
                resultados_fuente = []
                
                # Función principal de Fuzzy Matching
                for index, row in df_ssa.iterrows():
                    query = row['Busqueda_SSA']
                    
                    # Extraer coincidencias que superen el umbral usando token_set_ratio (ignora el orden de las palabras)
                    matches = process.extract(
                        query, 
                        df_cofepris['Busqueda_COFEPRIS'], 
                        scorer=fuzz.token_set_ratio, 
                        limit=None, 
                        score_cutoff=umbral
                    )
                    
                    if matches:
                        # matches devuelve una lista de tuplas (texto_coincidente, score, indice_en_df)
                        indices = [match[2] for match in matches]
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
                        
                    resultados_registros.append(texto_registros)
                    resultados_fuente.append(tipo_fuente)
                
                # Agregamos las nuevas columnas al Excel de la SSA
                df_ssa['Registros_Cofepris_Encontrados'] = resultados_registros
                df_ssa['Tipo_Fuente'] = resultados_fuente
                
                # Limpiamos columnas temporales
                df_ssa = df_ssa.drop(columns=['Busqueda_SSA'])
                
                st.success("¡Análisis Terminado!")
                
                # Mostramos métricas
                f_unica = resultados_fuente.count('Fuente Única')
                f_mult = resultados_fuente.count('Fuente Múltiple')
                s_fuente = resultados_fuente.count('Sin Fuente')
                
                m1, m2, m3 = st.columns(3)
                m1.metric("Fuente Única", f_unica)
                m2.metric("Fuente Múltiple", f_mult)
                m3.metric("Sin Fuente", s_fuente)
                
                st.dataframe(df_ssa)
                
                # Botón de descarga
                csv_resultado = df_ssa.to_csv(index=False).encode('latin1', errors='replace')
                st.download_button(
                    label="⬇️ Descargar Resultados en CSV",
                    data=csv_resultado,
                    file_name="Analisis_Fuentes_Abasto.csv",
                    mime="text/csv"
                )
    else:
        st.info("👈 Por favor, suba el archivo de la SSA en la barra lateral para comenzar.")