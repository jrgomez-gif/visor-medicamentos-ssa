import streamlit as st
import pandas as pd
from rapidfuzz import process, fuzz
import time

# ==========================================
# 1. CONFIGURACIÓN DE PÁGINA Y TEMA
# ==========================================
st.set_page_config(page_title="Visor COFEPRIS", page_icon="🇲🇽", layout="wide")

# CSS Mejorado: Tema institucional y corrección del File Uploader
st.markdown("""
    <style>
    /* Color de fondo de la barra lateral (Verde Oscuro) */
    [data-testid="stSidebar"] { background-color: #13322B; }
    
    /* Textos básicos de la barra lateral a blanco */
    [data-testid="stSidebar"] .stMarkdown p, 
    [data-testid="stSidebar"] h1, 
    [data-testid="stSidebar"] h2, 
    [data-testid="stSidebar"] h3,
    [data-testid="stSidebar"] label { color: white !important; }
    
    /* --- ARREGLO DEL CAJÓN DE SUBIR ARCHIVOS --- */
    /* Fondo semitransparente para que resalte la zona de carga */
    [data-testid="stFileUploadDropzone"] {
        background-color: rgba(255, 255, 255, 0.1) !important; 
        border: 1px dashed rgba(255, 255, 255, 0.5) !important;
    }
    /* Forzar a blanco todo el texto interno del cajón (Drag and drop...) */
    [data-testid="stFileUploadDropzone"] * {
        color: white !important; 
    }
    /* Estilizar el botón interno de 'Browse files' */
    [data-testid="stFileUploadDropzone"] button {
        background-color: #B38E5D !important;
        color: white !important;
        border: none !important;
    }
    [data-testid="stFileUploadDropzone"] button:hover {
        background-color: #6F1827 !important;
    }
    /* ------------------------------------------- */

    /* Estilos del Gobierno para el título principal */
    h1 { color: #6F1827; border-bottom: 2px solid #B38E5D; padding-bottom: 10px; }
    
    /* Botones dorados principales */
    .stButton>button { background-color: #B38E5D; color: white; border: none; width: 100%; }
    .stButton>button:hover { background-color: #6F1827; color: white; }
    </style>
""", unsafe_allow_html=True)

# ==========================================
# 2. CARGA DE DATOS COFEPRIS (PARQUET)
# ==========================================
@st.cache_data
def cargar_parquet():
    try:
        df = pd.read_parquet("base_registros_sanitarios.parquet")
        # Rellenar valores nulos para evitar errores
        df['DenominacionGenerica'] = df['DenominacionGenerica'].fillna('')
        df['Presentacion'] = df['Presentacion'].fillna('')
        # Crear columna de búsqueda combinada
        df['Busqueda_COFEPRIS'] = df['DenominacionGenerica'].astype(str) + " " + df['Presentacion'].astype(str)
        return df
    except Exception as e:
        return None

df_cofepris = cargar_parquet()

# ==========================================
# 3. BARRA LATERAL (SIDEBAR) Y FIRMA
# ==========================================
with st.sidebar:
    # Intentar cargar el logo
    try:
        st.image("COFEPRIS.png", use_container_width=True)
    except:
        st.caption("Cofepris - Buscador")
    
    st.markdown("---")
    st.markdown("## ⚙️ Panel de Análisis (SSA)")
    
    # Cajón para subir archivo
    archivo_ssa = st.file_uploader("1. Suba el archivo CSV o Excel de la SSA", type=["csv", "xlsx"])
    
    umbral = st.slider("2. Umbral de similitud (%)", min_value=60, max_value=100, value=85, 
                       help="85% es recomendado para tolerar variaciones en la redacción de la SSA.")
    
    st.markdown("---")
    
    # Guía Rápida movida a la barra lateral
    with st.expander("📖 Guía de Uso"):
        st.markdown("""
        **🔍 Buscador General:** Ideal para consultas rápidas. Escriba la denominación, sustancia activa o registro sanitario para filtrar la base vigente.
        
        **⚙️ Cruce de Datos SSA:** 1. Suba el archivo de la SSA.
        2. Seleccione las columnas de *Clave* y *Descripción Completa*.
        3. Haga clic en *Ejecutar Análisis*. La IA cruzará los textos y generará un archivo con la clasificación de "Fuente Única/Múltiple".
        """)
    
    # Firma Oficial
    st.markdown("---")
    st.markdown("<div style='text-align: center; color: #B38E5D; font-size: 0.85em;'>Trámites Electrónicos COFEPRIS<br>Centro de Datos V1.0</div>", unsafe_allow_html=True)

# ==========================================
# 4. PANTALLA PRINCIPAL
# ==========================================
st.markdown("<h1>Visor Inteligente de Medicamentos</h1>", unsafe_allow_html=True)

# Validar que el Parquet exista
if df_cofepris is None:
    st.error("🚨 No se encontró el archivo 'base_registros_sanitarios.parquet'. Asegúrese de que esté cargado en el repositorio de GitHub.")
    st.stop()

# Creación de Pestañas
tab1, tab2 = st.tabs(["🔍 Buscador General", "⚙️ Cruce de Datos (SSA)"])

# ------------------------------------------
# PESTAÑA 1: BUSCADOR GENERAL
# ------------------------------------------
with tab1:
    st.markdown("### Base de Datos Activa")
    col1, col2 = st.columns(2)
    busqueda_libre = col1.text_input("Buscar por Denominación Distintiva, Genérica o Registro:")
    
    # Lista de estados únicos (ignorando nulos)
    estados = df_cofepris['Estado'].dropna().unique().tolist()
    filtro_estado = col2.selectbox("Filtrar por Estado:", ["Todos"] + estados)
    
    df_mostrar = df_cofepris.copy()
    
    # Aplicar filtro de estado
    if filtro_estado != "Todos":
        df_mostrar = df_mostrar[df_mostrar['Estado'] == filtro_estado]
        
    # Aplicar búsqueda libre
    if busqueda_libre:
        mask = df_mostrar.astype(str).apply(lambda x: x.str.contains(busqueda_libre, case=False, na=False)).any(axis=1)
        df_mostrar = df_mostrar[mask]
        
    st.write(f"Mostrando **{len(df_mostrar)}** registros:")
    st.dataframe(df_mostrar[['NumeroRegistro', 'DenominacionDistintiva', 'DenominacionGenerica', 'Presentacion', 'Estado', 'Titular']])

# ------------------------------------------
# PESTAÑA 2: CRUCE DE DATOS (SSA)
# ------------------------------------------
with tab2:
    if archivo_ssa:
        # Leer archivo según su extensión
        if archivo_ssa.name.endswith('.csv'):
            df_ssa = pd.read_csv(archivo_ssa, encoding='latin1', sep=None, engine='python') 
        else:
            df_ssa = pd.read_excel(archivo_ssa)
            
        st.success("✅ Archivo SSA cargado correctamente. Configure las columnas para el cruce:")
        
        col_c1, col_c2 = st.columns(2)
        columnas_ssa = df_ssa.columns.tolist()
        
        # Selectores para identificar las columnas de interés
        col_clave = col_c1.selectbox("¿Qué columna tiene la Clave Compendio?", columnas_ssa)
        col_descripcion = col_c2.selectbox("¿Qué columna tiene la Descripción Completa?", columnas_ssa)
        
        if st.button("Ejecutar Análisis de Fuentes de Abasto"):
            with st.spinner("Procesando descripciones largas con inteligencia matemática... esto puede tomar un par de minutos."):
                
                resultados_registros = []
                resultados_fuente = []
                puntajes_confianza = []
                
                for index, row in df_ssa.iterrows():
                    query = str(row[col_descripcion])
                    
                    # Fuzzy Matching: token_set_ratio ignora palabras extra y busca intersección de tokens
                    matches = process.extract(
                        query, 
                        df_cofepris['Busqueda_COFEPRIS'], 
                        scorer=fuzz.token_set_ratio, 
                        limit=None, 
                        score_cutoff=umbral
                    )
                    
                    if matches:
                        indices = [match[2] for match in matches]
                        mejor_puntaje = matches[0][1]
                        registros_encontrados = df_cofepris.loc[indices, 'NumeroRegistro'].unique()
                        
                        cantidad = len(registros_encontrados)
                        texto_registros = ", ".join(registros_encontrados)
                        
                        if cantidad == 1:
                            tipo_fuente = "Fuente Única"
                        elif cantidad > 1:
                            tipo_fuente = "Fuente Múltiple"
                    else:
                        texto_registros = "Sin registros"
                        tipo_fuente = "Sin Fuente"
                        mejor_puntaje = 0
                        
                    resultados_registros.append(texto_registros)
                    resultados_fuente.append(tipo_fuente)
                    puntajes_confianza.append(round(mejor_puntaje, 1))
                
                # Anexar resultados al DataFrame de la SSA
                df_ssa['Registros_Cofepris_Encontrados'] = resultados_registros
                df_ssa['Tipo_Fuente'] = resultados_fuente
                df_ssa['Similitud_Matematica_Maxima_%'] = puntajes_confianza
                
                st.success("¡Análisis Terminado con Éxito!")
                
                # Mostrar métricas resumen
                m1, m2, m3 = st.columns(3)
                m1.metric("Fuente Única ✅", resultados_fuente.count('Fuente Única'))
                m2.metric("Fuente Múltiple ⚠️", resultados_fuente.count('Fuente Múltiple'))
                m3.metric("Sin Fuente ❌", resultados_fuente.count('Sin Fuente'))
                
                # Mostrar vista previa
                st.dataframe(df_ssa)
                
                # Preparar descarga (usamos utf-8-sig para que Excel en Windows lea bien los acentos)
                csv_resultado = df_ssa.to_csv(index=False).encode('utf-8-sig')
                st.download_button(
                    label="⬇️ Descargar Resultados para Compras Consolidadas",
                    data=csv_resultado,
                    file_name="Fuentes_Abasto_Analizadas.csv",
                    mime="text/csv"
                )
    else:
        st.info("👈 Por favor, suba el archivo de la SSA en la barra lateral para comenzar.")
