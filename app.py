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
        
        # Limpieza Visual
        if 'DenominacionGenerica' in df.columns:
            df['DenominacionGenerica'] = df['DenominacionGenerica'].apply(limpiar_vista_generica)
        if 'Presentacion' in df.columns:
            df['Presentacion'] = df['Presentacion'].astype(str).str.replace(r'\s+', ' ', regex=True).str.strip()
        
        # Renombrar y Formatear
        if 'VistaAdministracion' in df.columns:
            df = df.rename(columns={'VistaAdministracion': 'ViaAdministracion'})
        if 'FechaEmision' in df.columns:
            df['FechaEmision'] = pd.to_datetime(df['FechaEmision'], errors='coerce').dt.strftime('%d/%m/%Y')
            
        # Motor de Búsqueda Oculto (Mantenemos por seguridad si no se corre el jupyter, pero prioriza el del jupyter)
        generica = df['DenominacionGenerica'] if 'DenominacionGenerica' in df.columns else ""
        forma = df['FormaFarmaceutica'] if 'FormaFarmaceutica' in df.columns else ""
        presentacion = df['Presentacion'] if 'Presentacion' in df.columns else ""
        concentracion = df['FarmacoConcentracion'] if 'FarmacoConcentracion' in df.columns else ""
        
        df['Texto_Limpio_Generica'] = generica.apply(limpiar_texto_para_cruce)
        df['Texto_Limpio_Forma'] = forma.apply(limpiar_texto_para_cruce)
        df['Texto_Limpio_Presentacion'] = presentacion.apply(limpiar_texto_para_cruce)
        df['Texto_Limpio_Concentracion'] = concentracion.apply(limpiar_texto_para_cruce)
        
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
    **🔍 Buscador:** Use filtros para explorar la base vigente.
    
    **⚙️ Cruce SSA:**
    1. Suba el archivo de la SSA.
    2. Seleccione la columna de *Descripción* y ejecute el análisis.
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
# PESTAÑA 1: BUSCADOR GENERAL
# ------------------------------------------
with tab1:
    if 'reset' not in st.session_state:
        st.session_state.reset = False

    def reset_filters():
        st.session_state.busqueda = ""
        st.session_state.estado = "Todos"
        st.session_state.forma = "Todas"
        st.session_state.tipo = "Todos"
        st.session_state.titular = "Todos"

    st.markdown("### 🎛️ Panel de Búsqueda y Filtros")
    busqueda_libre = st.text_input("🔍 Búsqueda global:", key="busqueda")
    
    c1, c2, c3, c4 = st.columns(4)
    estados_validos = ["Todos", "VIGENTE", "CANCELADO", "REVOCADO"]
    formas_unicas = ["Todas"] + sorted(df_cofepris['FormaFarmaceutica'].dropna().unique().tolist())
    tipos_unicos = ["Todos"] + sorted(df_cofepris['TipoMedicamento'].dropna().unique().tolist())
    titulares_unicos = ["Todos"] + sorted(df_cofepris['Titular'].dropna().unique().tolist())
    
    filtro_estado = c1.selectbox("Estado:", estados_validos, key="estado")
    filtro_forma = c2.selectbox("Forma Farmacéutica:", formas_unicas, key="forma")
    filtro_tipo = c3.selectbox("Tipo de Medicamento:", tipos_unicos, key="tipo")
    filtro_titular = c4.selectbox("Titular del Registro:", titulares_unicos, key="titular")

    col_btn1, col_btn2, _ = st.columns([1, 1, 2])
    col_btn1.button("♻️ Limpiar Filtros", on_click=reset_filters)

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

    st.markdown(f"**Resultados encontrados:** {len(df_mostrar)}")
    
    columnas_excluidas = ['Texto_Limpio_Generica', 'Texto_Limpio_Forma', 'Texto_Limpio_Presentacion', 'Texto_Limpio_Concentracion', 'Busqueda_COFEPRIS', 'UUID', 'ClaveCompendio']
    df_final_vista = df_mostrar.drop(columns=columnas_excluidas, errors='ignore')
    
    st.dataframe(df_final_vista)

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
            with st.spinner("Analizando..."):
                res_reg, res_fue, res_score = [], [], []
                for index, row in df_ssa.iterrows():
                    query = limpiar_texto_para_cruce(str(row[col_descripcion]))
                    matches = process.extract(query, df_cofepris['Busqueda_COFEPRIS'], scorer=fuzz.token_set_ratio, limit=None, score_cutoff=umbral)
                    if matches:
                        idx = [m[2] for m in matches]
                        mejor_p = matches[0][1]
                        regs = df_cofepris.loc[idx, 'NumeroRegistro'].unique()
                        res_reg.append(", ".join(regs))
                        
                        # NUEVA REGLA RESPONSABLE PARA COMPRAS PÚBLICAS
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
                
                csv_out = df_ssa.to_csv(index=False).encode('utf-8-sig')
                st.download_button(label="⬇️ Descargar Resultados", data=csv_out, file_name="Fuentes_SSA_Analizadas.csv", mime="text/csv")
    else:
        st.info("👈 Suba el archivo de la SSA en la barra lateral.")
