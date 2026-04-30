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
    </style>
""", unsafe_allow_html=True)

# ==========================================
# 2. FUNCIONES DE LIMPIEZA Y CARGA
# ==========================================
_RE_CARACTERES = re.compile(r'[^a-z0-9ñáéíóú\s]')
_RE_STOPWORDS = re.compile(
    r'\b(caja|carton|cartón|envase|burbuja|frasco|ampula|ámpula|'
    r'con|que|contiene|cada|de|en|el|la|los|las|un|una|para|instructivo|anexo|o|y)\b'
)

def limpiar_texto_para_cruce(texto):
    if pd.isna(texto): return ""
    t = str(texto).lower().replace('/', ' ').replace('-', ' ')
    t = _RE_CARACTERES.sub(' ', t)
    t = _RE_STOPWORDS.sub(' ', t)
    return " ".join(t.split())

@st.cache_data
def cargar_datos_csv():
    try:
        # Modificado para leer formato Parquet
        archivos_csv = glob.glob("*.parquet")
        if not archivos_csv:
            return None, "No se encontró ningún archivo .parquet en el repositorio. Por favor, sube tu base de datos convertida."
            
        ruta = archivos_csv[0]
        
        try:
            # Leemos parquet y forzamos todo a string para evitar errores de tipo en las búsquedas
            df = pd.read_parquet(ruta).astype(str)
        except Exception as e:
            return None, f"Error al leer el archivo Parquet: {str(e)}"
            
        df['Texto_Busqueda_Rapida'] = df.fillna('').astype(str).agg(' '.join, axis=1).str.lower()
            
        col_gen = 'Denominacion Generica' if 'Denominacion Generica' in df.columns else df.columns[0]
        col_forma = 'Forma Farmaceutica' if 'Forma Farmaceutica' in df.columns else df.columns[0]
        
        df['Texto_Limpio_Generica'] = df[col_gen].apply(limpiar_texto_para_cruce)
        df['Texto_Limpio_Forma'] = df[col_forma].apply(limpiar_texto_para_cruce)
        
        df['Filtro_Paso1'] = df['Texto_Limpio_Generica'] + " " + df['Texto_Limpio_Forma']
        
        cols_search = [c for c in ['Denominacion Generica', 'Forma Farmaceutica', 'Presentación', 'Farmaco Concentración'] if c in df.columns]
        
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
    **¿Qué es este Visor Inteligente?**
    Es una herramienta analítica avanzada diseñada para explorar la base de datos de Registros Sanitarios de COFEPRIS.
    
    **🔍 Buscador:** Use filtros múltiples o la búsqueda por registros específicos.
    
    **⚙️ Cruce SSA:** Suba un archivo para encontrar coincidencias probables basadas en el principio activo y la forma farmacéutica.
    """)
    st.markdown("---")
    
    st.markdown("### ⚙️ Configuración de Análisis")
    archivo_ssa = st.file_uploader("Suba archivo SSA (CSV/Excel)", type=["csv", "xlsx"])
    umbral = st.slider("Umbral de similitud (%)", 50, 100, 80)
    
    if st.button("🗑️ Borrar resultados de cruce"):
        st.session_state.resultado_ssa = None
        st.rerun()
        
    st.markdown("<br><div style='text-align: center; color: #B38E5D; font-size: 0.85em;'>Trámites Electrónicos COFEPRIS<br>Visor Inteligente v2.5</div>", unsafe_allow_html=True)

# ==========================================
# 5. CUERPO PRINCIPAL
# ==========================================
st.markdown("<h1>Visor Inteligente de Medicamentos</h1>", unsafe_allow_html=True)

if df_cofepris is None:
    st.error(f"🚨 Error al leer la base de datos: **{error_carga}**")
    st.stop()

tab1, tab2 = st.tabs(["🔍 Buscador Interactivo", "⚙️ Cruce SSA (Persistente)"])

# ------------------------------------------
# PESTAÑA 1: BUSCADOR
# ------------------------------------------
with tab1:
    st.markdown("### 🎛️ Panel de Búsqueda y Filtros")
    
    col_search1, col_search2 = st.columns(2)
    busqueda_libre = col_search1.text_input("🔍 Búsqueda global (Nombre, Sustancia, etc.):", key="busqueda_libre")
    busqueda_mult = col_search2.text_area("📋 Búsqueda Múltiple de Registros (separe con comas):", placeholder="Ej: 363M2018 SSA, 004M2020 SSA", height=68, key="busqueda_mult")
    
    @st.cache_data
    def get_opciones(columna):
        if columna in df_cofepris.columns:
            return sorted(df_cofepris[columna].dropna().unique().tolist())
        return []

    c1, c2, c3, c4 = st.columns(4)
    filtro_estado = c1.multiselect("Estado:", get_opciones('Estado'), key="filtro_estado")
    filtro_forma = c2.multiselect("Forma Farmacéutica:", get_opciones('Forma Farmaceutica'), key="filtro_forma")
    filtro_via = c3.multiselect("Vía de Administración:", get_opciones('Vista Administración'), key="filtro_via")
    filtro_titular = c4.multiselect("Titular del Registro:", get_opciones('Titular'), key="filtro_titular")

    # Restaurado el diseño del botón a su tamaño pequeño original
    col_btn1, _ = st.columns([1, 4])
    col_btn1.button("♻️ Limpiar Filtros", on_click=reset_filters, use_container_width=True)

    df_mostrar = df_cofepris

    if busqueda_libre:
        df_mostrar = df_mostrar[df_mostrar['Texto_Busqueda_Rapida'].str.contains(busqueda_libre.lower(), na=False, regex=False)]

    if len(filtro_estado) > 0:
        df_mostrar = df_mostrar[df_mostrar['Estado'].isin(filtro_estado)]
        
    if len(filtro_forma) > 0:
        df_mostrar = df_mostrar[df_mostrar['Forma Farmaceutica'].isin(filtro_forma)]
        
    if len(filtro_via) > 0:
        df_mostrar = df_mostrar[df_mostrar['Vista Administración'].isin(filtro_via)]
        
    if len(filtro_titular) > 0:
        df_mostrar = df_mostrar[df_mostrar['Titular'].isin(filtro_titular)]
        
    if busqueda_mult.strip():
        regs = [r.strip() for r in busqueda_mult.replace(',', '\n').split('\n') if r.strip()]
        if regs and 'Número de Registro' in df_mostrar.columns:
            patron_regex = '|'.join([re.escape(r) for r in regs])
            df_mostrar = df_mostrar[df_mostrar['Número de Registro'].astype(str).str.contains(patron_regex, case=False, na=False)]

    cols_ocultar = ['Texto_Limpio_Generica', 'Texto_Limpio_Forma', 'Filtro_Paso1', 'Busqueda_COFEPRIS', 'Texto_Busqueda_Rapida']
    df_vista = df_mostrar.drop(columns=[c for c in cols_ocultar if c in df_mostrar.columns])
    
    st.markdown(f"**Total de resultados:** {len(df_vista):,}")
    
    if not df_vista.empty:
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df_vista.to_excel(writer, index=False, sheet_name='Registros_Sanitarios')
        
        st.download_button(
            label="📥 Descargar Tabla (Excel)",
            data=output.getvalue(),
            file_name="Cofepris_Registros_Filtrados.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
        
    MAX_FILAS = 1000
    if len(df_vista) > MAX_FILAS:
        st.warning(f"Mostrando {MAX_FILAS:,} de {len(df_vista):,} resultados. Usa filtros para acotar la búsqueda.")
    st.dataframe(df_vista.head(MAX_FILAS), use_container_width=True, height=400)

# ------------------------------------------
# PESTAÑA 2: CRUCE SSA (PERSISTENTE)
# ------------------------------------------
with tab2:
    if archivo_ssa:
        df_ssa_temp = pd.read_csv(archivo_ssa, encoding='latin1', dtype=str) if archivo_ssa.name.endswith('.csv') else pd.read_excel(archivo_ssa, dtype=str)
        
        st.markdown("### 🎯 Configuración del Cruce")
        col_descripcion = st.selectbox("¿Qué columna de tu archivo contiene la descripción del medicamento a cruzar?", df_ssa_temp.columns.tolist())
        
        if st.button("🚀 Iniciar Análisis de Similitud"):
            with st.spinner("Analizando coincidencias..."):
                res_vigentes, res_otros, res_score = [], [], []
                
                col_registro = 'Número de Registro' if 'Número de Registro' in df_cofepris.columns else df_cofepris.columns[0]
                col_estado = 'Estado' if 'Estado' in df_cofepris.columns else df_cofepris.columns[0]

                lista_filtro_paso1 = df_cofepris['Filtro_Paso1'].tolist()
                lista_busqueda_cofepris = df_cofepris['Busqueda_COFEPRIS'].tolist()

                for _, row in df_ssa_temp.iterrows():
                    q_original = str(row[col_descripcion])
                    q = limpiar_texto_para_cruce(q_original)

                    scores_paso1 = process.cdist([q], lista_filtro_paso1, scorer=fuzz.token_set_ratio, workers=-1)[0]
                    mask_paso1 = scores_paso1 >= 80
                    candidatos = df_cofepris[mask_paso1].copy()

                    if not candidatos.empty:
                        lista_candidatos = [lista_busqueda_cofepris[i] for i in candidatos.index]
                        scores_finales = process.cdist([q], lista_candidatos, scorer=fuzz.token_set_ratio, workers=-1)[0]
                        candidatos['Score_Final'] = scores_finales
                        matches_finales = candidatos[candidatos['Score_Final'] >= umbral]
                        
                        if not matches_finales.empty:
                            max_score = matches_finales['Score_Final'].max()
                            
                            mask_vigente = matches_finales[col_estado].astype(str).str.upper().str.contains('VIGENTE', na=False)
                            df_vigentes = matches_finales[mask_vigente]
                            df_otros = matches_finales[~mask_vigente]
                            
                            regs_vigentes = ", ".join(df_vigentes[col_registro].dropna().astype(str).unique())
                            regs_otros = ", ".join(df_otros[col_registro].dropna().astype(str).unique())
                            
                            res_vigentes.append(regs_vigentes if regs_vigentes else "Sin Vigentes")
                            res_otros.append(regs_otros if regs_otros else "Sin Otros")
                            res_score.append(round(max_score, 1))
                            continue
                    
                    res_vigentes.append("Sin Match")
                    res_otros.append("Sin Match")
                    res_score.append(0)

                df_ssa_temp['Registros_Vigentes'] = res_vigentes
                df_ssa_temp['Registros_Otros'] = res_otros
                df_ssa_temp['Similitud_%'] = res_score
                
                st.session_state.resultado_ssa = df_ssa_temp
                st.session_state.metricas_ssa = {
                    "Total": len(df_ssa_temp),
                    "Encontrados": len(df_ssa_temp[df_ssa_temp['Similitud_%'] > 0])
                }

    if st.session_state.resultado_ssa is not None:
        st.markdown("### 📊 Resultado del Último Análisis")
        m = st.session_state.metricas_ssa
        col1, col2 = st.columns(2)
        col1.metric("Total Analizados", m["Total"])
        col2.metric("Múltiples Matches Encontrados", m["Encontrados"])
        
        st.dataframe(st.session_state.resultado_ssa, use_container_width=True)
        
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            st.session_state.resultado_ssa.to_excel(writer, index=False)
        st.download_button("📥 Descargar Reporte de Cruce", output.getvalue(), "Cruce_SSA_Multiples.xlsx")
    else:
        st.info("No hay análisis activo. Sube un archivo, selecciona la columna de descripción y presiona 'Iniciar'.")
