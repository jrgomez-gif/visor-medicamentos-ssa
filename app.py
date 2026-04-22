import streamlit as st
import pandas as pd
from rapidfuzz import process, fuzz
import re
import io
import glob

# ==========================================
# 1. CONFIGURACIÓN DE PÁGINA Y TEMA
# ==========================================
st.set_page_config(page_title="Visor Inteligente COFEPRIS", page_icon="🇲🇽", layout="wide")

st.markdown("""
    <style>
    [data-testid="stSidebar"] { background-color: #13322B; }
    [data-testid="stSidebar"] .stMarkdown p, 
    [data-testid="stSidebar"] h1, [data-testid="stSidebar"] h2, [data-testid="stSidebar"] h3,
    [data-testid="stSidebar"] label, [data-testid="stSidebar"] li { color: white !important; }
    
    h1 { color: #6F1827; border-bottom: 2px solid #B38E5D; padding-bottom: 10px; }
    .stMetric { background-color: #f8f9fa; padding: 10px; border-radius: 10px; border-left: 5px solid #B38E5D; }
    .stButton>button { background-color: #B38E5D; color: white; border: none; width: 100%; }
    .stButton>button:hover { background-color: #6F1827; color: white; }
    .detalle-card { background-color: #ffffff; padding: 20px; border-radius: 10px; border: 1px solid #dee2e6; box-shadow: 2px 2px 5px rgba(0,0,0,0.05); }
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

@st.cache_data
def cargar_datos_csv():
    try:
        # Modificado: Buscamos archivos .xlsx en lugar de .csv
        archivos_csv = glob.glob("*.xlsx")
        if not archivos_csv:
            return None, "No se encontró ningún archivo .xlsx en el repositorio. Por favor, sube tu archivo de Excel a GitHub."
            
        ruta = archivos_csv[0]
        
        # Modificado: Leemos el archivo usando pandas.read_excel
        df = pd.read_excel(ruta, dtype=str)
            
        if 'VistaAdministracion' in df.columns:
            df = df.rename(columns={'VistaAdministracion': 'ViaAdministracion'})
            
        col_gen = 'DenominacionGenerica' if 'DenominacionGenerica' in df.columns else df.columns[0]
        col_forma = 'FormaFarmaceutica' if 'FormaFarmaceutica' in df.columns else df.columns[0]
        
        df['Texto_Limpio_Generica'] = df[col_gen].apply(limpiar_texto_para_cruce)
        df['Texto_Limpio_Forma'] = df[col_forma].apply(limpiar_texto_para_cruce)
        df['Filtro_Paso1'] = df['Texto_Limpio_Generica'] + " " + df['Texto_Limpio_Forma']
        
        cols_search = [c for c in ['DenominacionGenerica', 'FormaFarmaceutica', 'Presentacion', 'FarmacoConcentracion'] if c in df.columns]
        
        if cols_search:
            df['Busqueda_COFEPRIS'] = df[cols_search].fillna('').astype(str).apply(lambda row: ' '.join(row), axis=1).apply(limpiar_texto_para_cruce)
        else:
            df['Busqueda_COFEPRIS'] = df['Filtro_Paso1']

        return df, None
    except Exception as e:
        return None, str(e)

df_cofepris, error_carga = cargar_datos_csv()

# ==========================================
# 3. GESTIÓN DE ESTADO (SESSION STATE)
# ==========================================
if 'resultado_ssa' not in st.session_state: st.session_state.resultado_ssa = None
if 'metricas_ssa' not in st.session_state: st.session_state.metricas_ssa = {}

def reset_filters():
    st.session_state.busqueda_libre = ""
    st.session_state.busqueda_mult = ""
    st.session_state.filtro_estado = []
    st.session_state.filtro_forma = []
    st.session_state.filtro_via = []
    st.session_state.filtro_titular = []

# ==========================================
# 4. BARRA LATERAL
# ==========================================
with st.sidebar:
    try: st.image("COFEPRIS.png", use_container_width=True)
    except: st.title("COFEPRIS")
    
    st.markdown("---")
    st.markdown("### 📖 Guía de Uso")
    st.markdown("""
    **🔍 Buscador:** Use filtros o búsqueda múltiple.
    **⚙️ Cruce SSA:** Suba un archivo externo para comparar contra la base de datos maestra de Excel cargada.
    """)
    st.markdown("---")
    
    st.markdown("### ⚙️ Configuración de Análisis")
    archivo_ssa = st.file_uploader("Suba archivo SSA (CSV/Excel)", type=["csv", "xlsx"])
    umbral = st.slider("Umbral de similitud (%)", 50, 100, 80)
    
    if st.button("🗑️ Borrar resultados de cruce"):
        st.session_state.resultado_ssa = None
        st.rerun()
        
    st.markdown("<br><div style='text-align: center; color: #B38E5D; font-size: 0.85em;'>Visor Inteligente v2.4</div>", unsafe_allow_html=True)

# ==========================================
# 5. CUERPO PRINCIPAL
# ==========================================
st.markdown("<h1>Visor Inteligente de Medicamentos</h1>", unsafe_allow_html=True)

if df_cofepris is None:
    st.error(f"🚨 Error al leer la base de datos (.xlsx): **{error_carga}**")
    st.stop()

tab1, tab2 = st.tabs(["🔍 Buscador y Detalles", "⚙️ Cruce SSA (Persistente)"])

with tab1:
    st.markdown("### 🎛️ Panel de Búsqueda y Filtros")
    col_search1, col_search2 = st.columns(2)
    busqueda_libre = col_search1.text_input("🔍 Búsqueda global:", key="busqueda_libre")
    busqueda_mult = col_search2.text_area("📋 Búsqueda Múltiple (registros separados por comas):", height=68, key="busqueda_mult")
    
    def get_opciones(columna):
        if columna in df_cofepris.columns:
            return sorted(df_cofepris[columna].dropna().unique().tolist())
        return []

    c1, c2, c3, c4 = st.columns(4)
    filtro_estado = c1.multiselect("Estado:", get_opciones('Estado'), key="filtro_estado")
    filtro_forma = c2.multiselect("Forma Farmacéutica:", get_opciones('FormaFarmaceutica'), key="filtro_forma")
    filtro_via = c3.multiselect("Vía de Administración:", get_opciones('ViaAdministracion'), key="filtro_via")
    filtro_titular = c4.multiselect("Titular del Registro:", get_opciones('Titular'), key="filtro_titular")

    st.button("♻️ Limpiar Filtros", on_click=reset_filters)

    df_mostrar = df_cofepris.copy()
    
    if busqueda_libre:
        mask = df_mostrar.astype(str).apply(lambda x: x.str.contains(busqueda_libre, case=False, na=False)).any(axis=1)
        df_mostrar = df_mostrar[mask]

    if filtro_estado: df_mostrar = df_mostrar[df_mostrar['Estado'].isin(filtro_estado)]
    if filtro_forma: df_mostrar = df_mostrar[df_mostrar['FormaFarmaceutica'].isin(filtro_forma)]
    if filtro_via: df_mostrar = df_mostrar[df_mostrar['ViaAdministracion'].isin(filtro_via)]
    if filtro_titular: df_mostrar = df_mostrar[df_mostrar['Titular'].isin(filtro_titular)]
        
    if busqueda_mult.strip():
        regs = [r.strip() for r in busqueda_mult.replace(',', '\n').split('\n') if r.strip()]
        if regs and 'NumeroRegistro' in df_mostrar.columns:
            patron_regex = '|'.join([re.escape(r) for r in regs])
            df_mostrar = df_mostrar[df_mostrar['NumeroRegistro'].astype(str).str.contains(patron_regex, case=False, na=False)]

    cols_ocultar = ['Texto_Limpio_Generica', 'Texto_Limpio_Forma', 'Filtro_Paso1', 'Busqueda_COFEPRIS']
    df_vista = df_mostrar.drop(columns=[c for c in cols_ocultar if c in df_mostrar.columns])
    
    st.markdown(f"**Registros cargados desde Excel:** {len(df_cofepris):,} | **Resultados filtrados:** {len(df_vista):,}")
    st.dataframe(df_vista, use_container_width=True, height=300)

    st.markdown("---")
    st.markdown("### 📄 Detalle Extendido de Registro")
    
    if not df_mostrar.empty and 'NumeroRegistro' in df_mostrar.columns:
        opciones_registro = df_mostrar['NumeroRegistro'].dropna().astype(str).tolist()
        seleccion = st.selectbox("Seleccione un Registro:", ["-- Seleccione --"] + opciones_registro)
        
        if seleccion != "-- Seleccione --":
            detalle = df_mostrar[df_mostrar['NumeroRegistro'].astype(str) == seleccion].iloc[0]
            st.markdown(f"""<div class="detalle-card">
                <h2 style="color: #6F1827;">{detalle.get('DenominacionDistintiva', 'GENÉRICO')}</h2>
                <p><b>Registro:</b> {detalle.get('NumeroRegistro', 'N/A')} | <b>Estado:</b> {detalle.get('Estado', 'N/A')}</p>
                <p><b>Titular:</b> {detalle.get('Titular', 'N/A')}</p>
                <p><b>Sustancia:</b> {detalle.get('DenominacionGenerica', 'N/A')}</p>
                <p><b>Forma:</b> {detalle.get('FormaFarmaceutica', 'N/A')} | <b>Vía:</b> {detalle.get('ViaAdministracion', 'N/A')}</p>
                <p><b>Presentación:</b> {detalle.get('Presentacion', 'N/A')}</p>
            </div>""", unsafe_allow_html=True)

with tab2:
    if archivo_ssa:
        df_ssa_temp = pd.read_csv(archivo_ssa, encoding='latin1', dtype=str) if archivo_ssa.name.endswith('.csv') else pd.read_excel(archivo_ssa, dtype=str)
        col_descripcion = st.selectbox("Columna de descripción:", df_ssa_temp.columns.tolist())
        
        if st.button("🚀 Iniciar Análisis"):
            with st.spinner("Analizando coincidencias..."):
                res_vigentes, res_otros, res_score = [], [], []
                col_registro = 'NumeroRegistro' if 'NumeroRegistro' in df_cofepris.columns else df_cofepris.columns[0]
                col_estado = 'Estado' if 'Estado' in df_cofepris.columns else df_cofepris.columns[0]

                for _, row in df_ssa_temp.iterrows():
                    q = limpiar_texto_para_cruce(str(row[col_descripcion]))
                    scores_paso1 = df_cofepris['Filtro_Paso1'].apply(lambda x: fuzz.token_set_ratio(q, x))
                    candidatos = df_cofepris[scores_paso1 >= 80].copy()
                    
                    if not candidatos.empty:
                        candidatos['Score_Final'] = candidatos['Busqueda_COFEPRIS'].apply(lambda x: fuzz.token_set_ratio(q, x))
                        matches_finales = candidatos[candidatos['Score_Final'] >= umbral]
                        
                        if not matches_finales.empty:
                            mask_vigente = matches_finales[col_estado].astype(str).str.upper().str.contains('VIGENTE', na=False)
                            res_vigentes.append(", ".join(matches_finales[mask_vigente][col_registro].unique()))
                            res_otros.append(", ".join(matches_finales[~mask_vigente][col_registro].unique()))
                            res_score.append(round(matches_finales['Score_Final'].max(), 1))
                            continue
                    res_vigentes.append("Sin Match"); res_otros.append("Sin Match"); res_score.append(0)

                df_ssa_temp['Registros_Vigentes'] = res_vigentes
                df_ssa_temp['Registros_Otros'] = res_otros
                df_ssa_temp['Similitud_%'] = res_score
                st.session_state.resultado_ssa = df_ssa_temp
                st.rerun()

    if st.session_state.resultado_ssa is not None:
        st.dataframe(st.session_state.resultado_ssa, use_container_width=True)
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            st.session_state.resultado_ssa.to_excel(writer, index=False)
        st.download_button("📥 Descargar Reporte", output.getvalue(), "Cruce_SSA.xlsx")
