import streamlit as st
import pandas as pd
import duckdb
from rapidfuzz import process, fuzz
import re
import io

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
# 2. FUNCIONES DE LIMPIEZA Y MOTOR DUCKDB
# ==========================================
def limpiar_texto_para_cruce(texto):
    if pd.isna(texto): return ""
    t = str(texto).lower().replace('/', ' ').replace('-', ' ')
    t = re.sub(r'[^a-z0-9ñáéíóú\s]', ' ', t)
    stopwords = r'\b(caja|carton|cartón|envase|burbuja|frasco|ampula|ámpula|con|que|contiene|cada|de|en|el|la|los|las|un|una|para|instructivo|anexo|o|y)\b'
    t = re.sub(stopwords, ' ', t)
    return " ".join(t.split())

@st.cache_data
def cargar_datos_duckdb():
    ruta = "base_registros_sanitarios.parquet"
    try:
        # Usamos DuckDB para pre-procesar y cargar en memoria
        con = duckdb.connect(database=':memory:')
        con.execute(f"CREATE TABLE medicamentos AS SELECT * FROM read_parquet('{ruta}')")
        
        # Ajustes de nombres de columnas si existen
        cols = con.execute("PRAGMA table_info('medicamentos')").fetchall()
        col_names = [c[1] for c in cols]
        
        if 'VistaAdministracion' in col_names:
            con.execute("ALTER TABLE medicamentos RENAME VistaAdministracion TO ViaAdministracion")
        
        df = con.execute("SELECT * FROM medicamentos").df()
        
        # Pre-procesamiento de textos para redes difusas
        df['Texto_Limpio_Generica'] = df['DenominacionGenerica'].apply(limpiar_texto_para_cruce)
        df['Busqueda_COFEPRIS'] = (df['Texto_Limpio_Generica'] + " " + 
                                  df['FormaFarmaceutica'].fillna('') + " " + 
                                  df['Presentacion'].fillna('')).str.lower()
        
        return df, con
    except Exception as e:
        return None, str(e)

df_cofepris, con_duck = cargar_datos_duckdb()

# ==========================================
# 3. GESTIÓN DE ESTADO (SESSION STATE)
# ==========================================
if 'resultado_ssa' not in st.session_state:
    st.session_state.resultado_ssa = None
if 'metricas_ssa' not in st.session_state:
    st.session_state.metricas_ssa = {}

# ==========================================
# 4. BARRA LATERAL
# ==========================================
with st.sidebar:
    try: st.image("COFEPRIS.png", use_container_width=True)
    except: st.title("COFEPRIS")
    
    st.markdown("### ⚙️ Configuración de Análisis")
    archivo_ssa = st.file_uploader("Suba archivo SSA (CSV/Excel)", type=["csv", "xlsx"])
    umbral = st.slider("Umbral de similitud (%)", 50, 100, 80)
    
    if st.button("🗑️ Borrar resultados de cruce"):
        st.session_state.resultado_ssa = None
        st.rerun()

# ==========================================
# 5. CUERPO PRINCIPAL
# ==========================================
st.markdown("<h1>Visor Inteligente de Medicamentos</h1>", unsafe_allow_html=True)

tab1, tab2 = st.tabs(["🔍 Buscador y Detalles", "⚙️ Cruce SSA (Persistente)"])

# ------------------------------------------
# PESTAÑA 1: BUSCADOR Y DETALLE POR REGISTRO
# ------------------------------------------
with tab1:
    st.markdown("### 🎛️ Filtros de Búsqueda")
    
    c1, c2, c3 = st.columns([2, 2, 1])
    busqueda_libre = c1.text_input("🔍 Búsqueda rápida (Nombre o Sustancia):")
    busqueda_mult = c2.text_area("📋 Registros múltiples (Comas):", placeholder="001M2026, 002M2026", height=68)
    
    # DuckDB para filtros rápidos
    formas = con_duck.execute("SELECT DISTINCT FormaFarmaceutica FROM medicamentos ORDER BY 1").df()
    filtro_forma = c3.selectbox("Forma Farmacéutica:", ["Todas"] + formas['FormaFarmaceutica'].tolist())

    # Lógica de filtrado con DuckDB
    query_sql = "SELECT * FROM medicamentos WHERE 1=1"
    if busqueda_libre:
        query_sql += f" AND (DenominacionGenerica ILIKE '%{busqueda_libre}%' OR DenominacionDistintiva ILIKE '%{busqueda_libre}%')"
    if filtro_forma != "Todas":
        query_sql += f" AND FormaFarmaceutica = '{filtro_forma}'"
    if busqueda_mult:
        regs = [f"'{r.strip()}'" for r in busqueda_mult.split(',') if r.strip()]
        if regs: query_sql += f" AND NumeroRegistro IN ({','.join(regs)})"

    df_mostrar = con_duck.execute(query_sql).df()

    st.dataframe(df_mostrar, use_container_width=True, height=300)

    # --- SECCIÓN NUEVA: DETALLE DE REGISTRO ---
    st.markdown("---")
    st.markdown("### 📄 Detalle Extendido de Registro")
    
    if not df_mostrar.empty:
        opciones_registro = df_mostrar['NumeroRegistro'].tolist()
        seleccion = st.selectbox("Seleccione un Registro Sanitario para ver su ficha técnica:", 
                               options=["-- Seleccione --"] + opciones_registro)
        
        if seleccion != "-- Seleccione --":
            detalle = df_mostrar[df_mostrar['NumeroRegistro'] == seleccion].iloc[0]
            
            st.markdown(f"""<div class="detalle-card">
                <div style="display: flex; justify-content: space-between;">
                    <h2 style="color: #6F1827; margin:0;">{detalle['DenominacionDistintiva'] if pd.notna(detalle['DenominacionDistintiva']) else 'GENÉRICO'}</h2>
                    <span style="background: #B38E5D; color: white; padding: 5px 15px; border-radius: 20px;">{detalle['Estado']}</span>
                </div>
                <hr>
                <div style="display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 20px;">
                    <div><b>Registro:</b><br>{detalle['NumeroRegistro']}</div>
                    <div><b>Vigencia:</b><br>{detalle['FechaEmision'] if 'FechaEmision' in detalle else 'N/A'}</div>
                    <div><b>Titular:</b><br>{detalle['Titular']}</div>
                    <div style="grid-column: span 3;"><b>Sustancia(s):</b><br>{detalle['DenominacionGenerica']}</div>
                    <div><b>Forma Farmacéutica:</b><br>{detalle['FormaFarmaceutica']}</div>
                    <div><b>Vía Admón:</b><br>{detalle['ViaAdministracion']}</div>
                    <div><b>Concentración:</b><br>{detalle['FarmacoConcentracion']}</div>
                </div>
                <br>
                <b>Presentación Autorizada:</b><br>{detalle['Presentacion']}
            </div>""", unsafe_allow_html=True)
    else:
        st.info("No hay registros que coincidan con los filtros para mostrar detalles.")

# ------------------------------------------
# PESTAÑA 2: CRUCE SSA (PERSISTENTE)
# ------------------------------------------
with tab2:
    if archivo_ssa:
        # Si el usuario hace clic, procesamos y guardamos en Session State
        if st.button("🚀 Iniciar Análisis de Similitud"):
            df_ssa = pd.read_csv(archivo_ssa, encoding='latin1') if archivo_ssa.name.endswith('.csv') else pd.read_excel(archivo_ssa)
            
            # (Aquí va tu lógica de RapidFuzz simplificada para el ejemplo)
            with st.spinner("Analizando redes difusas..."):
                res_reg, res_fue, res_score = [], [], []
                
                # Usamos los datos cargados en df_cofepris para el cruce
                for _, row in df_ssa.iterrows():
                    q = limpiar_texto_para_cruce(str(row.iloc[0])) # Usando primera col como ejemplo
                    
                    # Filtro rápido por sustancia (85%)
                    candidatos = df_cofepris[df_cofepris['Texto_Limpio_Generica'].apply(lambda x: fuzz.token_set_ratio(q, x) >= 85)]
                    
                    if not candidatos.empty:
                        match = process.extractOne(q, candidatos['Busqueda_COFEPRIS'], scorer=fuzz.token_set_ratio)
                        if match and match[1] >= umbral:
                            res_reg.append(candidatos.loc[match[2], 'NumeroRegistro'])
                            res_fue.append("Fuente Localizada")
                            res_score.append(match[1])
                            continue
                    
                    res_reg.append("Sin Match")
                    res_fue.append("N/A")
                    res_score.append(0)

                df_ssa['Match_Registro'] = res_reg
                df_ssa['Similitud_%'] = res_score
                
                # PERSISTENCIA: Guardamos en Session State
                st.session_state.resultado_ssa = df_ssa
                st.session_state.metricas_ssa = {
                    "Total": len(df_ssa),
                    "Encontrados": len(df_ssa[df_ssa['Similitud_%'] > 0])
                }

    # MOSTRAR RESULTADOS SI EXISTEN (Incluso si cambias de pestaña)
    if st.session_state.resultado_ssa is not None:
        st.markdown("### 📊 Resultado del Último Análisis")
        m = st.session_state.metricas_ssa
        col1, col2 = st.columns(2)
        col1.metric("Total Analizados", m["Total"])
        col2.metric("Matches Encontrados", m["Encontrados"])
        
        st.dataframe(st.session_state.resultado_ssa, use_container_width=True)
        
        # Botón de descarga
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            st.session_state.resultado_ssa.to_excel(writer, index=False)
        st.download_button("📥 Descargar Reporte de Cruce", output.getvalue(), "Cruce_SSA.xlsx")
    else:
        st.info("No hay análisis activo. Sube un archivo y presiona 'Iniciar' en la pestaña de Cruce SSA.")
