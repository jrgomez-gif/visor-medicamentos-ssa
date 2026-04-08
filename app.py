import streamlit as st
import pandas as pd
from rapidfuzz import process, fuzz
import time

# ==========================================
# 1. CONFIGURACIÓN DE PÁGINA Y TEMA
# ==========================================
st.set_page_config(page_title="Visor COFEPRIS", page_icon="🇲🇽", layout="wide")

# CSS Institucional y corrección del File Uploader
st.markdown("""
    <style>
    /* Color de fondo de la barra lateral (Verde Oscuro) */
    [data-testid="stSidebar"] { background-color: #13322B; }
    
    /* Textos básicos de la barra lateral a blanco */
    [data-testid="stSidebar"] .stMarkdown p, 
    [data-testid="stSidebar"] h1, 
    [data-testid="stSidebar"] h2, 
    [data-testid="stSidebar"] h3,
    [data-testid="stSidebar"] label,
    [data-testid="stSidebar"] li { color: white !important; }
    
    /* --- ARREGLO DEL CAJÓN DE SUBIR ARCHIVOS --- */
    [data-testid="stFileUploadDropzone"] {
        background-color: rgba(255, 255, 255, 0.1) !important; 
        border: 1px dashed rgba(255, 255, 255, 0.5) !important;
    }
    [data-testid="stFileUploadDropzone"] * {
        color: white !important; 
    }
    [data-testid="stFileUploadDropzone"] button {
        background-color: #B38E5D !important;
        color: white !important;
        border: none !important;
    }
    [data-testid="stFileUploadDropzone"] button:hover {
        background-color: #6F1827 !important;
    }

    /* Estilos del Gobierno para el título principal */
    h1 { color: #6F1827; border-bottom: 2px solid #B38E5D; padding-bottom: 10px; }
    
    /* Botones dorados principales */
    .stButton>button { background-color: #B38E5D; color: white; border: none; width: 100%; }
    .stButton>button:hover { background-color: #6F1827; color: white; }
    </style>
""", unsafe_allow_html=True)

# ==========================================
# 2. CARGA DE DATOS COFEPRIS (PARQUET) CON DEBUG
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
        return df, None
    except Exception as e:
        # Si falla, devolvemos el error exacto para saber qué pasa
        return None, str(e)

df_cofepris, error_carga = cargar_parquet()

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
    
    # Guía de Uso Directa (Arriba y visible)
    st.markdown("### 📖 Guía de Uso")
    st.markdown("""
    **🔍 Buscador:** Escriba la denominación, sustancia activa o registro para filtrar la base vigente.
    
    **⚙️ Cruce SSA:**
    1. Suba el archivo de la SSA.
    2. Seleccione las columnas de *Clave* y *Descripción*.
    3. Haga clic en *Ejecutar Análisis*.
    """)
    
    st.markdown("---")
    st.markdown("### ⚙️ Panel de Análisis (SSA)")
    
    # Cajón para subir archivo
    archivo_ssa = st.file_uploader("Suba el archivo CSV o Excel", type=["csv", "xlsx"])
    
    umbral = st.slider("Umbral de similitud (%)", min_value=60, max_value=100, value=85, 
                       help="85% es recomendado para tolerar variaciones en la redacción de la SSA.")
    
    # Firma Oficial
    st.markdown("---")
    st.markdown("<div style='text-align: center; color: #B38E5D; font-size: 0.85em;'>Trámites Electrónicos COFEPRIS<br>Centro de Datos V1.0</div>", unsafe_allow_html=True)

# ==========================================
# 4. PANTALLA PRINCIPAL
# ==========================================
st.markdown("<h1>Visor Inteligente de Medicamentos</h1>", unsafe_allow_html=True)

# Validar que el Parquet exista o mostrar el error real
if df_cofepris is None:
    st.error(f"🚨 Error al leer la base de datos. Detalle técnico: **{error_carga}**")
    st.info("💡 Tip: Si el error dice 'Missing optional dependency pyarrow', ve a tu panel de control de Streamlit Cloud (share.streamlit.io), haz clic en los 3 puntitos de tu aplicación y selecciona 'Reboot' para que instale las nuevas librerías de tu requirements.txt.")
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
    
    estados = df_cofepris['Estado'].dropna().unique().tolist()
    filtro_estado = col2.selectbox("Filtrar por Estado:", ["Todos"] + estados)
    
    df_mostrar = df_cofepris.copy()
    
    if filtro_estado != "Todos":
        df_mostrar = df_mostrar[df_mostrar['Estado'] == filtro_estado]
        
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
        if archivo_ssa.name.endswith('.csv'):
            df_ssa = pd.read_csv(archivo_ssa, encoding='latin1', sep=None, engine='python') 
        else:
            df_ssa = pd.read_excel(archivo_ssa)
            
        st.success("✅ Archivo SSA cargado. Configure las columnas para el cruce:")
        
        col_c1, col_c2 = st.columns(2)
        columnas_ssa = df_ssa.columns.tolist()
        
        col_clave = col_c1.selectbox("¿Qué columna tiene la Clave Compendio?", columnas_ssa)
        col_descripcion = col_c2.selectbox("¿Qué columna tiene la Descripción Completa?", columnas_ssa)
        
        if st.button("Ejecutar Análisis de Fuentes de Abasto"):
            with st.spinner("Procesando descripciones largas con inteligencia matemática... esto puede tomar un par de minutos."):
                
                resultados_registros = []
                resultados_fuente = []
                puntajes_confianza = []
                
                for index, row in df_ssa.iterrows():
                    query = str(row[col_descripcion])
                    
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
                
                df_ssa['Registros_Cofepris_Encontrados'] = resultados_registros
                df_ssa['Tipo_Fuente'] = resultados_fuente
                df_ssa['Similitud_Matematica_Maxima_%'] = puntajes_confianza
                
                st.success("¡Análisis Terminado con Éxito!")
                
                m1, m2, m3 = st.columns(3)
                m1.metric("Fuente Única ✅", resultados_fuente.count('Fuente Única'))
                m2.metric("Fuente Múltiple ⚠️", resultados_fuente.count('Fuente Múltiple'))
                m3.metric("Sin Fuente ❌", resultados_fuente.count('Sin Fuente'))
                
                st.dataframe(df_ssa)
                
                csv_resultado = df_ssa.to_csv(index=False).encode('utf-8-sig')
                st.download_button(
                    label="⬇️ Descargar Resultados",
                    data=csv_resultado,
                    file_name="Fuentes_Abasto_Analizadas.csv",
                    mime="text/csv"
                )
    else:
        st.info("👈 Por favor, suba el archivo de la SSA en la barra lateral para comenzar.")
