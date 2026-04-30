import streamlit as st
import pandas as pd
from rapidfuzz import process, fuzz
import re
import io
import glob
from utils import limpiar_texto_para_cruce, CSS_TEMA

st.set_page_config(page_title="Medicamentos - COFEPRIS", page_icon="💊", layout="wide")
st.markdown(CSS_TEMA, unsafe_allow_html=True)

_COLS_OCULTAR = ['Texto_Limpio_Generica', 'Texto_Limpio_Forma', 'Filtro_Paso1', 'Busqueda_COFEPRIS', 'Texto_Busqueda_Rapida']

@st.cache_data
def cargar_medicamentos():
    archivos = glob.glob("medicamentos.parquet") or glob.glob("*.parquet")
    if not archivos:
        return None, "No se encontró medicamentos.parquet en el repositorio."
    try:
        df = pd.read_parquet(archivos[0]).astype(str)
    except Exception as e:
        return None, f"Error al leer el archivo Parquet: {e}"

    df['Texto_Busqueda_Rapida'] = df.fillna('').agg(' '.join, axis=1).str.lower()
    col_gen = 'Denominacion Generica' if 'Denominacion Generica' in df.columns else df.columns[0]
    col_forma = 'Forma Farmaceutica' if 'Forma Farmaceutica' in df.columns else df.columns[0]
    df['Texto_Limpio_Generica'] = df[col_gen].apply(limpiar_texto_para_cruce)
    df['Texto_Limpio_Forma'] = df[col_forma].apply(limpiar_texto_para_cruce)
    df['Filtro_Paso1'] = df['Texto_Limpio_Generica'] + ' ' + df['Texto_Limpio_Forma']
    cols_search = [c for c in ['Denominacion Generica', 'Forma Farmaceutica', 'Presentación', 'Farmaco Concentración'] if c in df.columns]
    df['Busqueda_COFEPRIS'] = df[cols_search].fillna('').agg(' '.join, axis=1).apply(limpiar_texto_para_cruce) if cols_search else df['Filtro_Paso1']
    return df, None

df_cofepris, error_carga = cargar_medicamentos()

if 'resultado_med' not in st.session_state: st.session_state.resultado_med = None
if 'metricas_med' not in st.session_state: st.session_state.metricas_med = {}

def reset_filters_med():
    for k in ['busqueda_libre_med', 'busqueda_mult_med']:
        if k in st.session_state: st.session_state[k] = ""
    for k in ['filtro_estado_med', 'filtro_forma_med', 'filtro_via_med', 'filtro_titular_med']:
        if k in st.session_state: st.session_state[k] = []

with st.sidebar:
    try: st.image("COFEPRIS.png", use_container_width=True)
    except: st.title("COFEPRIS")
    st.markdown("---")
    st.markdown("### 📖 Guía de Uso")
    st.markdown("""
    **🔍 Buscador:** Usa filtros múltiples o búsqueda por registros específicos.

    **⚙️ Cruce SSA:** Sube un archivo para encontrar coincidencias en el catálogo.
    """)
    st.markdown("---")
    st.markdown("### ⚙️ Configuración de Cruce")
    archivo_ssa = st.file_uploader("Archivo SSA (CSV/Excel)", type=["csv", "xlsx"])
    umbral = st.slider("Umbral de similitud (%)", 50, 100, 80)
    if st.button("🗑️ Borrar resultados"):
        st.session_state.resultado_med = None
        st.rerun()
    st.markdown("<br><div style='text-align:center;color:#B38E5D;font-size:0.85em;'>Visor Inteligente v2.5</div>", unsafe_allow_html=True)

st.markdown("<h1>💊 Medicamentos COFEPRIS</h1>", unsafe_allow_html=True)

if df_cofepris is None:
    st.error(f"🚨 {error_carga}")
    st.stop()

@st.cache_data
def get_opciones_med(col):
    return sorted(df_cofepris[col].dropna().unique().tolist()) if col in df_cofepris.columns else []

tab1, tab2 = st.tabs(["🔍 Buscador Interactivo", "⚙️ Cruce SSA (Persistente)"])

with tab1:
    st.markdown("### 🎛️ Panel de Búsqueda y Filtros")
    col_s1, col_s2 = st.columns(2)
    busqueda_libre = col_s1.text_input("🔍 Búsqueda global (Nombre, Sustancia, etc.):", key="busqueda_libre_med")
    busqueda_mult = col_s2.text_area("📋 Búsqueda múltiple de registros (separe con comas):", placeholder="Ej: 363M2018 SSA, 004M2020 SSA", height=68, key="busqueda_mult_med")

    c1, c2, c3, c4 = st.columns(4)
    filtro_estado = c1.multiselect("Estado:", get_opciones_med('Estado'), key="filtro_estado_med")
    filtro_forma = c2.multiselect("Forma Farmacéutica:", get_opciones_med('Forma Farmaceutica'), key="filtro_forma_med")
    filtro_via = c3.multiselect("Vía de Administración:", get_opciones_med('Vista Administración'), key="filtro_via_med")
    filtro_titular = c4.multiselect("Titular:", get_opciones_med('Titular'), key="filtro_titular_med")

    col_btn, _ = st.columns([1, 4])
    col_btn.button("♻️ Limpiar Filtros", on_click=reset_filters_med, use_container_width=True)

    df_mostrar = df_cofepris
    if busqueda_libre:
        df_mostrar = df_mostrar[df_mostrar['Texto_Busqueda_Rapida'].str.contains(busqueda_libre.lower(), na=False, regex=False)]
    if filtro_estado:
        df_mostrar = df_mostrar[df_mostrar['Estado'].isin(filtro_estado)]
    if filtro_forma:
        df_mostrar = df_mostrar[df_mostrar['Forma Farmaceutica'].isin(filtro_forma)]
    if filtro_via:
        df_mostrar = df_mostrar[df_mostrar['Vista Administración'].isin(filtro_via)]
    if filtro_titular:
        df_mostrar = df_mostrar[df_mostrar['Titular'].isin(filtro_titular)]
    if busqueda_mult.strip():
        regs = [r.strip() for r in busqueda_mult.replace(',', '\n').split('\n') if r.strip()]
        if regs and 'Número de Registro' in df_mostrar.columns:
            patron = '|'.join([re.escape(r) for r in regs])
            df_mostrar = df_mostrar[df_mostrar['Número de Registro'].astype(str).str.contains(patron, case=False, na=False)]

    df_vista = df_mostrar.drop(columns=[c for c in _COLS_OCULTAR if c in df_mostrar.columns])

    st.markdown(f"**Total de resultados:** {len(df_vista):,}")
    if not df_vista.empty:
        out = io.BytesIO()
        with pd.ExcelWriter(out, engine='openpyxl') as w:
            df_vista.to_excel(w, index=False, sheet_name='Registros_Sanitarios')
        st.download_button("📥 Descargar Tabla (Excel)", out.getvalue(), "Cofepris_Medicamentos.xlsx",
                           mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

    MAX_FILAS = 1000
    if len(df_vista) > MAX_FILAS:
        st.warning(f"Mostrando {MAX_FILAS:,} de {len(df_vista):,} resultados. Usa filtros para acotar.")
    st.dataframe(df_vista.head(MAX_FILAS), use_container_width=True, height=400)

with tab2:
    if archivo_ssa:
        df_ssa = pd.read_csv(archivo_ssa, encoding='latin1', dtype=str) if archivo_ssa.name.endswith('.csv') else pd.read_excel(archivo_ssa, dtype=str)
        st.markdown("### 🎯 Configuración del Cruce")
        col_desc = st.selectbox("Columna con la descripción del medicamento:", df_ssa.columns.tolist())

        if st.button("🚀 Iniciar Análisis de Similitud"):
            with st.spinner("Analizando coincidencias..."):
                col_reg = 'Número de Registro' if 'Número de Registro' in df_cofepris.columns else df_cofepris.columns[0]
                col_est = 'Estado' if 'Estado' in df_cofepris.columns else df_cofepris.columns[0]
                lista_paso1 = df_cofepris['Filtro_Paso1'].tolist()
                lista_busq = df_cofepris['Busqueda_COFEPRIS'].tolist()
                res_v, res_o, res_s = [], [], []

                for _, row in df_ssa.iterrows():
                    q = limpiar_texto_para_cruce(str(row[col_desc]))
                    sc1 = process.cdist([q], lista_paso1, scorer=fuzz.token_set_ratio, workers=-1)[0]
                    cands = df_cofepris[sc1 >= 80].copy()
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

                df_ssa['Registros_Vigentes'] = res_v
                df_ssa['Registros_Otros'] = res_o
                df_ssa['Similitud_%'] = res_s
                st.session_state.resultado_med = df_ssa
                st.session_state.metricas_med = {
                    "Total": len(df_ssa),
                    "Encontrados": len(df_ssa[df_ssa['Similitud_%'] > 0])
                }

    if st.session_state.resultado_med is not None:
        st.markdown("### 📊 Resultado del Último Análisis")
        m = st.session_state.metricas_med
        c1, c2 = st.columns(2)
        c1.metric("Total Analizados", m["Total"])
        c2.metric("Matches Encontrados", m["Encontrados"])
        st.dataframe(st.session_state.resultado_med, use_container_width=True)
        out = io.BytesIO()
        with pd.ExcelWriter(out, engine='openpyxl') as w:
            st.session_state.resultado_med.to_excel(w, index=False)
        st.download_button("📥 Descargar Reporte", out.getvalue(), "Cruce_Medicamentos.xlsx")
    else:
        st.info("No hay análisis activo. Sube un archivo y presiona 'Iniciar'.")
