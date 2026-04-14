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
def cargar_datos_parquet():
    # Asegúrate de poner el nombre exacto de tu archivo parquet exportado
    ruta = "_SELECT_P_ProductId_AS_UUID_REGISTRO_SANITARIO_P_PRODUCTNUMBER_A_202604140948.parquet"
    
    try:
        # DuckDB lee el archivo y lo pasamos a un DataFrame estándar
        df = duckdb.query(f"SELECT * FROM '{ruta}'").df()
        
        # Ajuste de nombre por si viene del formato anterior
        if 'VistaAdministracion' in df.columns:
            df = df.rename(columns={'VistaAdministracion': 'ViaAdministracion'})
            
        return df, None
    except Exception as e:
        return None, str(e)

# 🟢 Corrección: Ya no guardamos la "conexión", solo el DataFrame
df_cofepris, error_carga = cargar_datos_parquet()

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

if df_cofepris is None:
    st.error(f"🚨 Error al leer la base de datos: **{error_carga}**")
    st.stop()

tab1, tab2 = st.tabs(["🔍 Buscador y Detalles", "⚙️ Cruce SSA (Persistente)"])

# ------------------------------------------
# PESTAÑA 1: BUSCADOR Y DETALLE POR REGISTRO
# ------------------------------------------
with tab1:
    st.markdown("### 🎛️ Filtros de Búsqueda")
    st.info("💡 **Tip:** En la búsqueda múltiple, puedes ingresar varios registros separándolos por comas y presionar **Ctrl + Enter** para ejecutar la consulta.")
    
    c1, c2, c3 = st.columns([2, 2, 1])
    busqueda_libre = c1.text_input("🔍 Búsqueda rápida (Nombre o Sustancia):")
    busqueda_mult = c2.text_area("📋 Registros múltiples (Comas):", placeholder="001M2026, 002M2026", height=68)
    
    # 🟢 Corrección: DuckDB consulta directamente la variable df_cofepris
    if 'FormaFarmaceutica' in df_cofepris.columns:
        formas = duckdb.query("SELECT DISTINCT FormaFarmaceutica FROM df_cofepris WHERE FormaFarmaceutica IS NOT NULL ORDER BY 1").df()
        filtro_forma = c3.selectbox("Forma Farmacéutica:", ["Todas"] + formas['FormaFarmaceutica'].tolist())
    else:
        filtro_forma = "Todas"

    # Lógica de filtrado con DuckDB sobre el DataFrame
    query_sql = "SELECT * FROM df_cofepris WHERE 1=1"
    
    if busqueda_libre:
        # Busca en columnas si existen
        cols_b = []
        if 'DenominacionGenerica' in df_cofepris.columns: cols_b.append(f"DenominacionGenerica ILIKE '%{busqueda_libre}%'")
        if 'DenominacionDistintiva' in df_cofepris.columns: cols_b.append(f"DenominacionDistintiva ILIKE '%{busqueda_libre}%'")
        
        if cols_b:
            query_sql += f" AND ({' OR '.join(cols_b)})"

    if filtro_forma != "Todas":
        query_sql += f" AND FormaFarmaceutica = '{filtro_forma}'"
        
    if busqueda_mult:
        regs = [f"'{r.strip()}'" for r in busqueda_mult.split(',') if r.strip()]
        if regs and 'NumeroRegistro' in df_cofepris.columns: 
            query_sql += f" AND NumeroRegistro IN ({','.join(regs)})"

    # Ejecuta el filtro
    df_mostrar = duckdb.query(query_sql).df()

    # Ocultar columnas internas antes de mostrar en tabla
    cols_ocultar = ['Texto_Limpio_Generica', 'Busqueda_COFEPRIS']
    df_vista = df_mostrar.drop(columns=[c for c in cols_ocultar if c in df_mostrar.columns])
    
    st.dataframe(df_vista, use_container_width=True, height=300)

    # --- DETALLE DE REGISTRO ---
    st.markdown("---")
    st.markdown("### 📄 Detalle Extendido de Registro")
    
    if not df_mostrar.empty and 'NumeroRegistro' in df_mostrar.columns:
        opciones_registro = df_mostrar['NumeroRegistro'].dropna().astype(str).tolist()
        seleccion = st.selectbox("Seleccione un Registro Sanitario para ver su ficha técnica:", 
                               options=["-- Seleccione --"] + opciones_registro)
        
        if seleccion != "-- Seleccione --":
            detalle = df_mostrar[df_mostrar['NumeroRegistro'].astype(str) == seleccion].iloc[0]
            
            # Obtención segura de datos por si cambian los nombres de las columnas
            d_distintiva = detalle.get('DenominacionDistintiva', 'GENÉRICO')
            d_estado = detalle.get('Estado', 'VIGENTE')
            d_reg = detalle.get('NumeroRegistro', 'N/A')
            d_fecha = detalle.get('FechaEmision', 'N/A')
            d_titular = detalle.get('Titular', 'N/A')
            d_generica = detalle.get('DenominacionGenerica', 'N/A')
            d_forma = detalle.get('FormaFarmaceutica', 'N/A')
            d_via = detalle.get('ViaAdministracion', 'N/A')
            d_conc = detalle.get('FarmacoConcentracion', 'N/A')
            d_pres = detalle.get('Presentacion', 'N/A')
            
            if pd.isna(d_distintiva): d_distintiva = 'GENÉRICO'
            
            st.markdown(f"""<div class="detalle-card">
                <div style="display: flex; justify-content: space-between;">
                    <h2 style="color: #6F1827; margin:0;">{d_distintiva}</h2>
                    <span style="background: #B38E5D; color: white; padding: 5px 15px; border-radius: 20px;">{d_estado}</span>
                </div>
                <hr>
                <div style="display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 20px;">
                    <div><b>Registro:</b><br>{d_reg}</div>
                    <div><b>Vigencia:</b><br>{d_fecha}</div>
                    <div><b>Titular:</b><br>{d_titular}</div>
                    <div style="grid-column: span 3;"><b>Sustancia(s):</b><br>{d_generica}</div>
                    <div><b>Forma Farmacéutica:</b><br>{d_forma}</div>
                    <div><b>Vía Admón:</b><br>{d_via}</div>
                    <div><b>Concentración:</b><br>{d_conc}</div>
                </div>
                <br>
                <b>Presentación Autorizada:</b><br>{d_pres}
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
            
            with st.spinner("Analizando redes difusas..."):
                res_reg, res_fue, res_score = [], [], []
                
                # Validamos que tengamos la columna base de cruce en COFEPRIS
                col_busqueda = 'Busqueda_COFEPRIS' if 'Busqueda_COFEPRIS' in df_cofepris.columns else df_cofepris.columns[0]
                col_sustancia = 'Texto_Limpio_Generica' if 'Texto_Limpio_Generica' in df_cofepris.columns else df_cofepris.columns[0]
                col_registro = 'NumeroRegistro' if 'NumeroRegistro' in df_cofepris.columns else df_cofepris.columns[0]

                for _, row in df_ssa.iterrows():
                    q = limpiar_texto_para_cruce(str(row.iloc[0])) # Usando primera columna
                    
                    # Filtro rápido por sustancia (85%)
                    candidatos = df_cofepris[df_cofepris[col_sustancia].apply(lambda x: fuzz.token_set_ratio(q, x) >= 85)]
                    
                    if not candidatos.empty:
                        match = process.extractOne(q, candidatos[col_busqueda], scorer=fuzz.token_set_ratio)
                        if match and match[1] >= umbral:
                            res_reg.append(candidatos.loc[match[2], col_registro])
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
        
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            st.session_state.resultado_ssa.to_excel(writer, index=False)
        st.download_button("📥 Descargar Reporte de Cruce", output.getvalue(), "Cruce_SSA.xlsx")
    else:
        st.info("No hay análisis activo. Sube un archivo y presiona 'Iniciar' en la pestaña de Cruce SSA.")
