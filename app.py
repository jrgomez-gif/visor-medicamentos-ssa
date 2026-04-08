import streamlit as st
import pandas as pd
from rapidfuzz import process, fuzz
import re
import io

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
# 2. FUNCIONES DE LIMPIEZA Y CARGA
# ==========================================
def limpiar_texto_para_cruce(texto):
    if pd.isna(texto): return ""
    t = str(texto).lower().replace('/', ' ').replace('-', ' ')
    t = re.sub(r'[^a-z0-9ñáéíóú\s]', ' ', t)
    stopwords = r'\b(caja|carton|cartón|envase|burbuja|frasco|ampula|ámpula|con|que|contiene|cada|de|en|el|la|los|las|un|una|para|instructivo|anexo|o|y)\b'
    t = re.sub(stopwords, ' ', t)
    return " ".join(t.split())

def limpiar_vista_generica(texto):
    if pd.isna(texto): return ""
    partes = [p.strip() for p in str(texto).split('/') if p.strip()]
    return " / ".join(partes)

@st.cache_data
def cargar_parquet():
    try:
        df = pd.read_parquet("base_registros_sanitarios.parquet")
        
        if 'DenominacionGenerica' in df.columns:
            df['DenominacionGenerica'] = df['DenominacionGenerica'].apply(limpiar_vista_generica)
        if 'Presentacion' in df.columns:
            df['Presentacion'] = df['Presentacion'].astype(str).str.replace(r'\s+', ' ', regex=True).str.strip()
        
        if 'VistaAdministracion' in df.columns:
            df = df.rename(columns={'VistaAdministracion': 'ViaAdministracion'})
        if 'FechaEmision' in df.columns:
            df['FechaEmision'] = pd.to_datetime(df['FechaEmision'], errors='coerce').dt.strftime('%d/%m/%Y')
            
        if 'Texto_Limpio_Generica' not in df.columns:
            df['Texto_Limpio_Generica'] = df['DenominacionGenerica'].apply(limpiar_texto_para_cruce)
            df['Texto_Limpio_Forma'] = df['FormaFarmaceutica'].apply(limpiar_texto_para_cruce)
            df['Texto_Limpio_Presentacion'] = df['Presentacion'].apply(limpiar_texto_para_cruce)
            df['Texto_Limpio_Concentracion'] = df['FarmacoConcentracion'].apply(limpiar_texto_para_cruce)
            df['Busqueda_COFEPRIS'] = df['Texto_Limpio_Generica'] + " " + df['Texto_Limpio_Forma'] + " " + df['Texto_Limpio_Presentacion'] + " " + df['Texto_Limpio_Concentracion']
            
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
    **🔍 Buscador:** Use filtros o la búsqueda múltiple por registros (separados por comas) para explorar la base vigente.
    
    **⚙️ Cruce SSA:**
    1. Suba el archivo de la SSA.
    2. Seleccione la columna de *Descripción* y ejecute el análisis en dos pasos.
    """)
    
    st.markdown("---")
    st.markdown("### ⚙️ Panel de Análisis (SSA)")
    archivo_ssa = st.file_uploader("Suba el archivo CSV o Excel", type=["csv", "xlsx"])
    umbral = st.slider("Umbral de similitud global (%)", min_value=50, max_value=100, value=80,
                       help="Nivel de coincidencia requerido después de verificar que es el mismo principio activo.")
    
    st.markdown("---")
    st.markdown("<div style='text-align: center; color: #B38E5D; font-size: 0.85em;'>Trámites Electrónicos COFEPRIS<br>Centro de Datos V1.1</div>", unsafe_allow_html=True)

# ==========================================
# 4. PANTALLA PRINCIPAL
# ==========================================
st.markdown("<h1>Visor Inteligente de Medicamentos</h1>", unsafe_allow_html=True)

if df_cofepris is None:
    st.error(f"🚨 Error al leer la base de datos: **{error_carga}**")
    st.stop()

tab1, tab2 = st.tabs(["🔍 Buscador General", "⚙️ Cruce de Datos (SSA)"])

# ------------------------------------------
# PESTAÑA 1: BUSCADOR GENERAL
# ------------------------------------------
with tab1:
    # Inicialización de variables de estado para el botón Limpiar
    if 'busqueda' not in st.session_state: st.session_state.busqueda = ""
    if 'busqueda_mult' not in st.session_state: st.session_state.busqueda_mult = ""
    if 'estado' not in st.session_state: st.session_state.estado = "Todos"
    if 'forma' not in st.session_state: st.session_state.forma = "Todas"
    if 'via' not in st.session_state: st.session_state.via = "Todas"
    if 'titular' not in st.session_state: st.session_state.titular = "Todos"

    def reset_filters():
        st.session_state.busqueda = ""
        st.session_state.busqueda_mult = ""
        st.session_state.estado = "Todos"
        st.session_state.forma = "Todas"
        st.session_state.via = "Todas"
        st.session_state.titular = "Todos"

    st.markdown("### 🎛️ Panel de Búsqueda y Filtros")
    
    # Búsqueda Simple y Múltiple
    col_search1, col_search2 = st.columns(2)
    busqueda_libre = col_search1.text_input("🔍 Búsqueda global (Nombre, Sustancia, etc.):", key="busqueda")
    busqueda_multiple = col_search2.text_area("📋 Búsqueda Múltiple de Registros (separe con comas):", 
                                              placeholder="Ej: 003H95 SSA, 032H95 SSA, 339M2006 SSA", 
                                              key="busqueda_mult", height=68)
    
    # Filtros Desplegables
    c1, c2, c3, c4 = st.columns(4)
    estados_validos = ["Todos", "VIGENTE", "CANCELADO", "REVOCADO"]
    formas_unicas = ["Todas"] + sorted(df_cofepris['FormaFarmaceutica'].dropna().unique().tolist())
    vias_unicas = ["Todas"] + sorted(df_cofepris['ViaAdministracion'].dropna().unique().tolist())
    titulares_unicos = ["Todos"] + sorted(df_cofepris['Titular'].dropna().unique().tolist())
    
    filtro_estado = c1.selectbox("Estado:", estados_validos, key="estado")
    filtro_forma = c2.selectbox("Forma Farmacéutica:", formas_unicas, key="forma")
    filtro_via = c3.selectbox("Vía de Administración:", vias_unicas, key="via")
    filtro_titular = c4.selectbox("Titular del Registro:", titulares_unicos, key="titular")

    # Botones de Acción
    col_btn1, col_btn2, _ = st.columns([1, 1, 2])
    col_btn1.button("♻️ Limpiar Filtros", on_click=reset_filters)

    # --- APLICACIÓN DE LÓGICA DE FILTROS ---
    df_mostrar = df_cofepris.copy()
    
    # 1. Filtros desplegables
    if filtro_estado != "Todos":
        df_mostrar = df_mostrar[df_mostrar['Estado'].astype(str).str.contains(filtro_estado, case=False, na=False)]
    if filtro_forma != "Todas":
        df_mostrar = df_mostrar[df_mostrar['FormaFarmaceutica'] == filtro_forma]
    if filtro_via != "Todas":
        df_mostrar = df_mostrar[df_mostrar['ViaAdministracion'] == filtro_via]
    if filtro_titular != "Todos":
        df_mostrar = df_mostrar[df_mostrar['Titular'] == filtro_titular]
        
    # 2. Búsqueda Global (Palabra Clave)
    if busqueda_libre:
        mask = df_mostrar.astype(str).apply(lambda x: x.str.contains(busqueda_libre, case=False, na=False)).any(axis=1)
        df_mostrar = df_mostrar[mask]
        
    # 3. Búsqueda Múltiple de Registros
    if busqueda_multiple.strip():
        # Separar por comas y limpiar espacios en blanco
        lista_registros = [r.strip() for r in busqueda_multiple.split(',') if r.strip()]
        if lista_registros:
            # Creamos un patrón de búsqueda que acepte cualquiera de los registros de la lista
            patron_regex = '|'.join([re.escape(r) for r in lista_registros])
            df_mostrar = df_mostrar[df_mostrar['NumeroRegistro'].astype(str).str.contains(patron_regex, case=False, na=False)]

    # --- MOSTRAR RESULTADOS ---
    st.markdown(f"**Resultados encontrados:** {len(df_mostrar)}")
    
    columnas_excluidas = ['Texto_Limpio_Generica', 'Texto_Limpio_Forma', 'Texto_Limpio_Presentacion', 'Texto_Limpio_Concentracion', 'Busqueda_COFEPRIS', 'UUID', 'ClaveCompendio']
    df_final_vista = df_mostrar.drop(columns=columnas_excluidas, errors='ignore')
    
    st.dataframe(df_final_vista)

    # --- DESCARGA EXCEL ---
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df_final_vista.to_excel(writer, index=False, sheet_name='Registros_Sanitarios')
    processed_data = output.getvalue()

    col_btn2.download_button(
        label="📥 Descargar Excel (Visible)",
        data=processed_data,
        file_name="Cofepris_Registros_Vigentes.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

# ------------------------------------------
# PESTAÑA 2: CRUCE DE DATOS (SSA)
# ------------------------------------------
with tab2:
    if archivo_ssa:
        if archivo_ssa.name.endswith('.csv'):
            df_ssa = pd.read_csv(archivo_ssa, encoding='latin1', sep=None, engine='python') 
        else:
            df_ssa = pd.read_excel(archivo_ssa)
            
        st.success("✅ Archivo SSA cargado.")
        columnas_ssa = df_ssa.columns.tolist()
        col_descripcion = st.selectbox("¿Qué columna contiene la Descripción Completa del medicamento?", columnas_ssa)
        
        if st.button("Ejecutar Análisis de Fuentes"):
            with st.spinner("Ejecutando cruce en dos pasos... esto puede tomar un par de minutos."):
                
                res_reg, res_fue, res_score = [], [], []
                
                for index, row in df_ssa.iterrows():
                    query = limpiar_texto_para_cruce(str(row[col_descripcion]))
                    
                    # PASO 1: CANDADO DE SUSTANCIA ACTIVA
                    scores_generica = df_cofepris['Texto_Limpio_Generica'].apply(
                        lambda x: fuzz.token_set_ratio(query, x) if pd.notna(x) else 0
                    )
                    
                    df_candidatos = df_cofepris[scores_generica >= 85]
                    
                    if df_candidatos.empty:
                        res_reg.append("Sin registros")
                        res_fue.append("Sin Fuente")
                        res_score.append(0)
                        continue
                        
                    # PASO 2: SIMILITUD GLOBAL
                    matches = process.extract(
                        query, 
                        df_candidatos['Busqueda_COFEPRIS'], 
                        scorer=fuzz.token_set_ratio, 
                        limit=None, 
                        score_cutoff=umbral
                    )
                    
                    if matches:
                        idx = [m[2] for m in matches]
                        mejor_p = matches[0][1]
                        regs = df_cofepris.loc[idx, 'NumeroRegistro'].unique()
                        res_reg.append(", ".join(regs))
                        
                        res_fue.append("Probable Fuente Única" if len(regs) == 1 else "Fuente Múltiple")
                    else:
                        res_reg.append("Sin registros")
                        res_fue.append("Sin Fuente")
                        mejor_p = 0
                        
                    res_score.append(round(mejor_p, 1))
                
                df_ssa['Registros_Cofepris'] = res_reg
                df_ssa['Tipo_Fuente'] = res_fue
                df_ssa['Similitud_%'] = res_score
                
                st.success("¡Terminado!")
                m1, m2, m3 = st.columns(3)
                m1.metric("Probable Fuente Única ✅", res_fue.count('Probable Fuente Única'))
                m2.metric("Fuente Múltiple ⚠️", res_fue.count('Fuente Múltiple'))
                m3.metric("Sin Fuente ❌", res_fue.count('Sin Fuente'))
                st.dataframe(df_ssa)
                
                output_ssa = io.BytesIO()
                with pd.ExcelWriter(output_ssa, engine='openpyxl') as writer:
                    df_ssa.to_excel(writer, index=False, sheet_name='Analisis_Fuentes')
                excel_ssa = output_ssa.getvalue()
                
                st.download_button(
                    label="⬇️ Descargar Resultados en Excel",
                    data=excel_ssa,
                    file_name="Analisis_Mercado_SSA.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )
    else:
        st.info("👈 Suba el archivo de la SSA en la barra lateral.")
