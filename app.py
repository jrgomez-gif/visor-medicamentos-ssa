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
def cargar_datos_parquet():
    try:
        archivos_parquet = glob.glob("*.parquet")
        if not archivos_parquet:
            return None, "No se encontró ningún archivo .parquet en el repositorio."
            
        ruta = archivos_parquet[0]
        # Leemos directo con Pandas (ultra rápido para 15k registros)
        df = pd.read_parquet(ruta)
        
        if 'VistaAdministracion' in df.columns:
            df = df.rename(columns={'VistaAdministracion': 'ViaAdministracion'})
            
        return df, None
    except Exception as e:
        return None, str(e)

df_cofepris, error_carga = cargar_datos_parquet()

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
    Es una herramienta analítica avanzada diseñada para explorar la base de datos de Registros Sanitarios de COFEPRIS. Integra un motor de búsqueda ultra-rápido y un sistema de análisis de redes difusas (Fuzzy Matching) para cruzar bases de datos externas de forma automatizada.
    
    **🔍 Buscador:** Use filtros múltiples o la búsqueda por registros específicos (separados por comas) para aislar información.
    
    **⚙️ Cruce SSA:**
    1. Suba el archivo (CSV/Excel) de la Secretaría de Salud u otra institución.
    2. Ejecute el análisis para encontrar coincidencias probables basadas en el principio activo y la forma farmacéutica.
    """)
    st.markdown("---")
    
    st.markdown("### ⚙️ Configuración de Análisis")
    archivo_ssa = st.file_uploader("Suba archivo SSA (CSV/Excel)", type=["csv", "xlsx"])
    umbral = st.slider("Umbral de similitud (%)", 50, 100, 80)
    
    if st.button("🗑️ Borrar resultados de cruce"):
        st.session_state.resultado_ssa = None
        st.rerun()
        
    st.markdown("<br><div style='text-align: center; color: #B38E5D; font-size: 0.85em;'>Trámites Electrónicos COFEPRIS<br>Visor Inteligente v2.2</div>", unsafe_allow_html=True)

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
    st.markdown("### 🎛️ Panel de Búsqueda y Filtros")
    st.info("💡 **Tip de Búsqueda:** Ingresa varios registros separados por comas y presiona **Ctrl + Enter** para ejecutar.")
    
    col_search1, col_search2 = st.columns(2)
    busqueda_libre = col_search1.text_input("🔍 Búsqueda global (Nombre, Sustancia, etc.):", key="busqueda_libre")
    busqueda_mult = col_search2.text_area("📋 Búsqueda Múltiple de Registros (separe con comas):", placeholder="001M2026, 002M2026", height=68, key="busqueda_mult")
    
    def get_opciones(columna):
        if columna in df_cofepris.columns:
            return sorted(df_cofepris[columna].dropna().unique().tolist())
        return []

    c1, c2, c3, c4 = st.columns(4)
    filtro_estado = c1.multiselect("Estado:", get_opciones('Estado'), key="filtro_estado")
    filtro_forma = c2.multiselect("Forma Farmacéutica:", get_opciones('FormaFarmaceutica'), key="filtro_forma")
    filtro_via = c3.multiselect("Vía de Administración:", get_opciones('ViaAdministracion'), key="filtro_via")
    filtro_titular = c4.multiselect("Titular del Registro:", get_opciones('Titular'), key="filtro_titular")

    col_btn1, _ = st.columns([1, 4])
    col_btn1.button("♻️ Limpiar Filtros", on_click=reset_filters, use_container_width=True)

    # Lógica de filtrado nativa de Pandas (¡Vuelve a ser instantánea!)
    df_mostrar = df_cofepris.copy()
    
    if busqueda_libre:
        mask = df_mostrar.astype(str).apply(lambda x: x.str.contains(busqueda_libre, case=False, na=False)).any(axis=1)
        df_mostrar = df_mostrar[mask]

    if filtro_estado:
        df_mostrar = df_mostrar[df_mostrar['Estado'].isin(filtro_estado)]
        
    if filtro_forma:
        df_mostrar = df_mostrar[df_mostrar['FormaFarmaceutica'].isin(filtro_forma)]
        
    if filtro_via:
        df_mostrar = df_mostrar[df_mostrar['ViaAdministracion'].isin(filtro_via)]
        
    if filtro_titular:
        df_mostrar = df_mostrar[df_mostrar['Titular'].isin(filtro_titular)]
        
    if busqueda_mult.strip():
        regs = [r.strip() for r in busqueda_mult.replace(',', '\n').split('\n') if r.strip()]
        if regs and 'NumeroRegistro' in df_mostrar.columns:
            # Usamos regex para atrapar variaciones si es necesario, o exact match
            patron_regex = '|'.join([re.escape(r) for r in regs])
            df_mostrar = df_mostrar[df_mostrar['NumeroRegistro'].astype(str).str.contains(patron_regex, case=False, na=False)]

    # Ocultar columnas internas
    cols_ocultar = ['Texto_Limpio_Generica', 'Busqueda_COFEPRIS', 'UUID', 'ClaveCompendio']
    df_vista = df_mostrar.drop(columns=[c for c in cols_ocultar if c in df_mostrar.columns])
    
    st.markdown(f"**Resultados encontrados:** {len(df_vista):,}")
    
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
        
    st.dataframe(df_vista, use_container_width=True, height=300)

    # --- DETALLE DE REGISTRO ---
    st.markdown("---")
    st.markdown("### 📄 Detalle Extendido de Registro")
    
    if not df_mostrar.empty and 'NumeroRegistro' in df_mostrar.columns:
        opciones_registro = df_mostrar['NumeroRegistro'].dropna().astype(str).tolist()
        seleccion = st.selectbox("Seleccione un Registro Sanitario para ver su ficha técnica completa:", 
                               options=["-- Seleccione --"] + opciones_registro)
        
        if seleccion != "-- Seleccione --":
            detalle = df_mostrar[df_mostrar['NumeroRegistro'].astype(str) == seleccion].iloc[0]
            
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
        if st.button("🚀 Iniciar Análisis de Similitud"):
            df_ssa = pd.read_csv(archivo_ssa, encoding='latin1') if archivo_ssa.name.endswith('.csv') else pd.read_excel(archivo_ssa)
            
            with st.spinner("Analizando redes difusas..."):
                res_reg, res_fue, res_score = [], [], []
                
                col_busqueda = 'Busqueda_COFEPRIS' if 'Busqueda_COFEPRIS' in df_cofepris.columns else df_cofepris.columns[0]
                col_sustancia = 'Texto_Limpio_Generica' if 'Texto_Limpio_Generica' in df_cofepris.columns else df_cofepris.columns[0]
                col_registro = 'NumeroRegistro' if 'NumeroRegistro' in df_cofepris.columns else df_cofepris.columns[0]

                for _, row in df_ssa.iterrows():
                    q = limpiar_texto_para_cruce(str(row.iloc[0]))
                    
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
                
                st.session_state.resultado_ssa = df_ssa
                st.session_state.metricas_ssa = {
                    "Total": len(df_ssa),
                    "Encontrados": len(df_ssa[df_ssa['Similitud_%'] > 0])
                }

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
