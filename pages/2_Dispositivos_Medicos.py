import streamlit as st
import pandas as pd
from rapidfuzz import process, fuzz
import re
import io
import glob
from utils import limpiar_texto_para_cruce, CSS_TEMA

st.set_page_config(page_title="Dispositivos Médicos - COFEPRIS", page_icon="🏥", layout="wide")
st.markdown(CSS_TEMA, unsafe_allow_html=True)

_COLS_OCULTAR = {'ID', 'Texto_Busqueda_Rapida', 'Texto_Limpio_Generica', 'Texto_Limpio_Distintiva', 'Filtro_Paso1', 'Busqueda_Disp'}

@st.cache_data
def cargar_dispositivos():
    archivos_pq = glob.glob("dispositivos*.parquet")
    archivos_xl = glob.glob("dispositivos*.xlsx") + glob.glob("dispositivos*.xls")

    if not archivos_pq and not archivos_xl:
        return None, (
            "No se encontró ningún archivo de dispositivos médicos. "
            "Sube **dispositivos.parquet** (recomendado) o **dispositivos.xlsx** al repositorio."
        )
    try:
        if archivos_pq:
            df = pd.read_parquet(archivos_pq[0]).astype(str)
        else:
            df = pd.read_excel(archivos_xl[0], dtype=str)
    except Exception as e:
        return None, f"Error al leer el archivo: {e}"

    df = df.fillna('').replace('NULL', '').replace('nan', '')

    col_gen = 'DENOMINACION_GENERICA' if 'DENOMINACION_GENERICA' in df.columns else df.columns[0]
    col_dist = 'DENOMINACION_DISTINTIVA' if 'DENOMINACION_DISTINTIVA' in df.columns else df.columns[0]

    df['Texto_Busqueda_Rapida'] = df.astype(str).agg(' '.join, axis=1).str.lower()
    df['Texto_Limpio_Generica'] = df[col_gen].apply(limpiar_texto_para_cruce)
    df['Texto_Limpio_Distintiva'] = df[col_dist].apply(limpiar_texto_para_cruce)
    df['Filtro_Paso1'] = df['Texto_Limpio_Generica'] + ' ' + df['Texto_Limpio_Distintiva']
    cols_search = [c for c in ['DENOMINACION_GENERICA', 'DENOMINACION_DISTINTIVA', 'CATEGORIA', 'CLASE'] if c in df.columns]
    df['Busqueda_Disp'] = df[cols_search].agg(' '.join, axis=1).apply(limpiar_texto_para_cruce) if cols_search else df['Filtro_Paso1']

    return df, None

df_disp, error_carga = cargar_dispositivos()

if 'resultado_disp' not in st.session_state: st.session_state.resultado_disp = None
if 'metricas_disp' not in st.session_state: st.session_state.metricas_disp = {}

def reset_filters_disp():
    for k in ['busqueda_libre_disp', 'busqueda_mult_disp']:
        if k in st.session_state: st.session_state[k] = ""
    for k in ['filtro_clase_disp', 'filtro_cat_disp', 'filtro_estado_disp', 'filtro_titular_disp']:
        if k in st.session_state: st.session_state[k] = []

with st.sidebar:
    try: st.image("COFEPRIS.png", use_container_width=True)
    except: st.title("COFEPRIS")
    st.markdown("---")
    st.markdown("### 📖 Guía de Uso")
    st.markdown("""
    **🔍 Buscador:** Filtra por clase, categoría, estado o titular.

    **⚙️ Cruce:** Compara tu inventario contra el catálogo oficial.
    """)
    st.markdown("---")
    st.markdown("### ⚙️ Configuración de Cruce")
    archivo_inv = st.file_uploader("Archivo inventario (CSV/Excel)", type=["csv", "xlsx"])
    umbral = st.slider("Umbral de similitud (%)", 50, 100, 80)
    if st.button("🗑️ Borrar resultados"):
        st.session_state.resultado_disp = None
        st.rerun()
    if df_disp is not None and glob.glob("dispositivos*.xlsx"):
        st.markdown("---")
        st.info("💡 Convierte tu Excel a Parquet para una carga más rápida.")
    st.markdown("<br><div style='text-align:center;color:#B38E5D;font-size:0.85em;'>Visor Inteligente v2.5</div>", unsafe_allow_html=True)

st.markdown("<h1>🏥 Dispositivos Médicos COFEPRIS</h1>", unsafe_allow_html=True)

if df_disp is None:
    st.error(f"🚨 {error_carga}")
    st.stop()

@st.cache_data
def get_opciones_disp(col):
    if col not in df_disp.columns: return []
    return sorted(df_disp[col].replace('', pd.NA).dropna().unique().tolist())

tab1, tab2 = st.tabs(["🔍 Buscador Interactivo", "⚙️ Cruce Inventario (Persistente)"])

with tab1:
    st.markdown("### 🎛️ Panel de Búsqueda y Filtros")
    col_s1, col_s2 = st.columns(2)
    busqueda_libre = col_s1.text_input("🔍 Búsqueda global:", key="busqueda_libre_disp")
    busqueda_mult = col_s2.text_area("📋 Búsqueda múltiple de registros (separe con comas):", placeholder="Ej: 1697E2011 SSA, 0902R2008 SSA", height=68, key="busqueda_mult_disp")

    c1, c2, c3, c4 = st.columns(4)
    filtro_clase = c1.multiselect("Clase:", get_opciones_disp('CLASE'), key="filtro_clase_disp")
    filtro_cat = c2.multiselect("Categoría:", get_opciones_disp('CATEGORIA'), key="filtro_cat_disp")
    filtro_estado = c3.multiselect("Estado:", get_opciones_disp('ESTADO'), key="filtro_estado_disp")
    filtro_titular = c4.multiselect("Titular:", get_opciones_disp('TITULAR'), key="filtro_titular_disp")

    col_btn, _ = st.columns([1, 4])
    col_btn.button("♻️ Limpiar Filtros", on_click=reset_filters_disp, use_container_width=True)

    df_mostrar = df_disp
    if busqueda_libre:
        df_mostrar = df_mostrar[df_mostrar['Texto_Busqueda_Rapida'].str.contains(busqueda_libre.lower(), na=False, regex=False)]
    if filtro_clase:
        df_mostrar = df_mostrar[df_mostrar['CLASE'].isin(filtro_clase)]
    if filtro_cat:
        df_mostrar = df_mostrar[df_mostrar['CATEGORIA'].isin(filtro_cat)]
    if filtro_estado:
        df_mostrar = df_mostrar[df_mostrar['ESTADO'].isin(filtro_estado)]
    if filtro_titular:
        df_mostrar = df_mostrar[df_mostrar['TITULAR'].isin(filtro_titular)]
    if busqueda_mult.strip():
        regs = [r.strip() for r in busqueda_mult.replace(',', '\n').split('\n') if r.strip()]
        if regs and 'NUMERO_REGISTRO' in df_mostrar.columns:
            patron = '|'.join([re.escape(r) for r in regs])
            df_mostrar = df_mostrar[df_mostrar['NUMERO_REGISTRO'].str.contains(patron, case=False, na=False)]

    df_vista = df_mostrar.drop(columns=[c for c in _COLS_OCULTAR if c in df_mostrar.columns])

    st.markdown(f"**Total de resultados:** {len(df_vista):,}")
    if not df_vista.empty:
        out = io.BytesIO()
        with pd.ExcelWriter(out, engine='openpyxl') as w:
            df_vista.to_excel(w, index=False, sheet_name='Dispositivos_Medicos')
        st.download_button("📥 Descargar Tabla (Excel)", out.getvalue(), "COFEPRIS_Dispositivos.xlsx",
                           mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

    MAX_FILAS = 1000
    if len(df_vista) > MAX_FILAS:
        st.warning(f"Mostrando {MAX_FILAS:,} de {len(df_vista):,} resultados. Usa filtros para acotar.")
    st.dataframe(df_vista.head(MAX_FILAS), use_container_width=True, height=400)

with tab2:
    if archivo_inv:
        df_inv = pd.read_csv(archivo_inv, encoding='latin1', dtype=str) if archivo_inv.name.endswith('.csv') else pd.read_excel(archivo_inv, dtype=str)
        st.markdown("### 🎯 Configuración del Cruce")
        col_desc = st.selectbox("Columna con la descripción del dispositivo:", df_inv.columns.tolist())

        if st.button("🚀 Iniciar Análisis de Similitud"):
            with st.spinner("Analizando coincidencias..."):
                col_reg = 'NUMERO_REGISTRO' if 'NUMERO_REGISTRO' in df_disp.columns else df_disp.columns[0]
                col_est = 'ESTADO' if 'ESTADO' in df_disp.columns else df_disp.columns[0]
                lista_paso1 = df_disp['Filtro_Paso1'].tolist()
                lista_busq = df_disp['Busqueda_Disp'].tolist()
                res_v, res_o, res_s = [], [], []

                for _, row in df_inv.iterrows():
                    q = limpiar_texto_para_cruce(str(row[col_desc]))
                    sc1 = process.cdist([q], lista_paso1, scorer=fuzz.token_set_ratio, workers=-1)[0]
                    cands = df_disp[sc1 >= 80].copy()
                    if not cands.empty:
                        cands['Score_Final'] = process.cdist([q], [lista_busq[i] for i in cands.index], scorer=fuzz.token_set_ratio, workers=-1)[0]
                        matches = cands[cands['Score_Final'] >= umbral]
                        if not matches.empty:
                            mask_v = matches[col_est].str.upper().str.contains('VIGENTE', na=False)
                            rv = ", ".join(matches[mask_v][col_reg].dropna().astype(str).unique())
                            ro = ", ".join(matches[~mask_v][col_reg].dropna().astype(str).unique())
                            res_v.append(rv or "Sin Vigentes")
                            res_o.append(ro or "Sin Otros")
                            res_s.append(round(matches['Score_Final'].max(), 1))
                            continue
                    res_v.append("Sin Match"); res_o.append("Sin Match"); res_s.append(0)

                df_inv['Registros_Vigentes'] = res_v
                df_inv['Registros_Otros'] = res_o
                df_inv['Similitud_%'] = res_s
                st.session_state.resultado_disp = df_inv
                st.session_state.metricas_disp = {
                    "Total": len(df_inv),
                    "Encontrados": len(df_inv[df_inv['Similitud_%'] > 0])
                }

    if st.session_state.resultado_disp is not None:
        st.markdown("### 📊 Resultado del Último Análisis")
        m = st.session_state.metricas_disp
        c1, c2 = st.columns(2)
        c1.metric("Total Analizados", m["Total"])
        c2.metric("Matches Encontrados", m["Encontrados"])
        st.dataframe(st.session_state.resultado_disp, use_container_width=True)
        out = io.BytesIO()
        with pd.ExcelWriter(out, engine='openpyxl') as w:
            st.session_state.resultado_disp.to_excel(w, index=False)
        st.download_button("📥 Descargar Reporte", out.getvalue(), "Cruce_Dispositivos.xlsx")
    else:
        st.info("No hay análisis activo. Sube un archivo de inventario y presiona 'Iniciar'.")
