import streamlit as st
import pandas as pd
from rapidfuzz import process, fuzz
import re

# ==========================================
# 1. CONFIGURACIÓN DE PÁGINA Y TEMA
# ==========================================
st.set_page_config(page_title="Visor COFEPRIS", page_icon="🇲🇽", layout="wide")

st.markdown("""
    <style>
    [data-testid="stSidebar"] { background-color: #13322B; }
    [data-testid="stSidebar"] .stMarkdown p, 
    [data-testid="stSidebar"] h1, 
    [data-testid="stSidebar"] h2, 
    [data-testid="stSidebar"] h3,
    [data-testid="stSidebar"] label,
    [data-testid="stSidebar"] li { color: white !important; }
    
    [data-testid="stFileUploadDropzone"] {
        background-color: rgba(255, 255, 255, 0.1) !important; 
        border: 1px dashed rgba(255, 255, 255, 0.5) !important;
    }
    [data-testid="stFileUploadDropzone"] * { color: white !important; }
    [data-testid="stFileUploadDropzone"] button {
        background-color: #B38E5D !important;
        color: white !important;
        border: none !important;
    }
    [data-testid="stFileUploadDropzone"] button:hover { background-color: #6F1827 !important; }

    h1 { color: #6F1827; border-bottom: 2px solid #B38E5D; padding-bottom: 10px; }
    .stButton>button { background-color: #B38E5D; color: white; border: none; width: 100%; }
    .stButton>button:hover { background-color: #6F1827; color: white; }
    </style>
""", unsafe_allow_html=True)

# ==========================================
# 2. FUNCIONES Y CARGA DE DATOS
# ==========================================
def limpiar_texto_para_cruce(texto):
    """Limpia el texto de la SSA al vuelo para poder cruzarlo."""
    if pd.isna(texto): return ""
    t = str(texto).lower().replace('/', ' ').replace('-', ' ')
    t = re.sub(r'[^a-z0-9ñáéíóú\s]', ' ', t)
    stopwords = r'\b(caja|carton|cartón|envase|burbuja|frasco|ampula|ámpula|con|que|contiene|cada|de|en|el|la|los|las|un|una|para|instructivo|anexo|o|y)\b'
    t = re.sub(stopwords, ' ', t)
    return " ".join(t.split())

@st.cache_data
def cargar_parquet():
    try:
        # Ahora el Parquet ya viene limpio desde tu computadora
        df = pd.read_parquet("base_registros_sanitarios.parquet")
        return df, None
    except Exception as e:
        return None, str(e)

df_cofepris, error_carga = cargar_parquet()

# ==========================================
# 3. BARRA LATERAL (SIDEBAR)
# ==========================================
with st.sidebar:
    try:
        st.image("COFEPRIS.png", use_container_width=True)
    except:
        st.caption("Cofepris - Buscador")
    
    st.markdown("---")
    st.markdown("### 📖 Guía de Uso")
    st.markdown("""
    **🔍 Buscador:** Escriba la denominación, sustancia o use los filtros para explorar la base vigente.
    
    **⚙️ Cruce SSA:**
    1. Suba el archivo de la SSA.
    2. Seleccione las columnas de *Clave* y *Descripción*.
    3. Haga clic en *Ejecutar Análisis*.
    """)
    
    st.markdown("---")
    st.markdown("### ⚙️ Panel de Análisis (SSA)")
    archivo_ssa = st.file_uploader("Suba el archivo CSV o Excel", type=["csv", "xlsx"])
    umbral = st.slider("Umbral de similitud (%)", min_value=50, max_value=100, value=80)
    
    st.markdown("---")
    st.markdown("<div style='text-align: center; color: #B38E5D; font-size: 0.85em;'>Trámites Electrónicos COFEPRIS<br>Centro de Datos V1.0</div>", unsafe_allow_html=True)

# ==========================================
# 4. PANTALLA PRINCIPAL
# ==========================================
st.markdown("<h1>Visor Inteligente de Medicamentos</h1>", unsafe_allow_html=True)

if df_cofepris is None:
    st.error(f"🚨 Error al leer la base de datos: **{error_carga}**")
    st.stop()

tab1, tab2 = st.tabs(["🔍 Buscador General", "⚙️ Cruce de Datos (SSA)"])

# ------------------------------------------
# PESTAÑA 1: BUSCADOR GENERAL CON FILTROS
# ------------------------------------------
with tab1:
    st.markdown("### 🎛️ Panel de Búsqueda y Filtros")
    
    # Fila 1: Búsqueda libre
    busqueda_libre = st.text_input("🔍 Búsqueda global (Denominación, Genérica o No. Registro):")
    
    # Fila 2: Filtros desplegables en 4 columnas
    c1, c2, c3, c4 = st.columns(4)
    
    # Extraer valores únicos limpios para los filtros
    estados_validos = ["Todos", "VIGENTE", "CANCELADO", "REVOCADO"]
    formas_unicas = ["Todas"] + sorted(df_cofepris['FormaFarmaceutica'].dropna().unique().tolist())
    tipos_unicos = ["Todos"] + sorted(df_cofepris['TipoMedicamento'].dropna().unique().tolist())
    titulares_unicos = ["Todos"] + sorted(df_cofepris['Titular'].dropna().unique().tolist())
    
    filtro_estado = c1.selectbox("Estado:", estados_validos)
    filtro_forma = c2.selectbox("Forma Farmacéutica:", formas_unicas)
    filtro_tipo = c3.selectbox("Tipo de Medicamento:", tipos_unicos)
    filtro_titular = c4.selectbox("Titular del Registro:", titulares_unicos)
    
    # Aplicar lógica de filtrado
    df_mostrar = df_cofepris.copy()
    
    if filtro_estado != "Todos":
        df_mostrar = df_mostrar[df_mostrar['Estado'].astype(str).str.contains(filtro_estado, case=False, na=False)]
    if filtro_forma != "Todas":
        df_mostrar = df_mostrar[df_mostrar['FormaFarmaceutica'] == filtro_forma]
    if filtro_tipo != "Todos":
        df_mostrar = df_mostrar[df_mostrar['TipoMedicamento'] == filtro_tipo]
    if filtro_titular != "Todos":
        df_mostrar = df_mostrar[df_mostrar['Titular'] == filtro_titular]
        
    if busqueda_libre:
        mask = df_mostrar.astype(str).apply(lambda x: x.str.contains(busqueda_libre, case=False, na=False)).any(axis=1)
        df_mostrar = df_mostrar[mask]
        
    st.markdown(f"**Resultados encontrados:** {len(df_mostrar)} registros")
    
    # Ocultar columnas técnicas generadas en el backend
    columnas_ocultas = ['Texto_Limpio_Generica', 'Texto_Limpio_Forma', 'Texto_Limpio_Presentacion', 'Busqueda_COFEPRIS']
    st.dataframe(df_mostrar.drop(columns=columnas_ocultas, errors='ignore'))

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
            with st.spinner("Comparando catálogos con inteligencia matemática... esto puede tomar un par de minutos."):
                
                resultados_registros = []
                resultados_fuente = []
                puntajes_confianza = []
                
                for index, row in df_ssa.iterrows():
                    # Limpiamos el texto completo de la SSA al vuelo
                    query = limpiar_texto_para_cruce(str(row[col_descripcion]))
                    
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
