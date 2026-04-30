import streamlit as st
import pandas as pd
import re
import io
import glob
from datetime import date

FECHA_HOY = date.today().strftime("%-d de %B de %Y").replace(
    "January","enero").replace("February","febrero").replace("March","marzo").replace(
    "April","abril").replace("May","mayo").replace("June","junio").replace(
    "July","julio").replace("August","agosto").replace("September","septiembre").replace(
    "October","octubre").replace("November","noviembre").replace("December","diciembre")

_COLS_OCULTAR = {'ID', 'Texto_Busqueda_Rapida'}

# ── Autenticación ──────────────────────────────────────────────────────────────
if 'disp_autenticado' not in st.session_state:
    st.session_state.disp_autenticado = False

if not st.session_state.disp_autenticado:
    st.markdown("<h1>🏥 Dispositivos Médicos COFEPRIS</h1>", unsafe_allow_html=True)
    st.info("Esta sección es de acceso restringido. Ingresa tus credenciales para continuar.")
    with st.form("login_disp"):
        usuario = st.text_input("Usuario")
        contrasena = st.text_input("Contraseña", type="password")
        if st.form_submit_button("Iniciar sesión"):
            if usuario == "ocf" and contrasena == "ocf":
                st.session_state.disp_autenticado = True
                st.rerun()
            else:
                st.error("Usuario o contraseña incorrectos.")
    st.stop()
# ──────────────────────────────────────────────────────────────────────────────

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
    df['Texto_Busqueda_Rapida'] = df.astype(str).agg(' '.join, axis=1).str.lower()
    return df, None

df_disp, error_carga = cargar_dispositivos()

def reset_filters_disp():
    for k in ['busqueda_libre_disp', 'busqueda_mult_disp']:
        if k in st.session_state: st.session_state[k] = ""
    for k in ['filtro_clase_disp', 'filtro_cat_disp', 'filtro_estado_disp', 'filtro_titular_disp']:
        if k in st.session_state: st.session_state[k] = []

with st.sidebar:
    st.markdown("### 📖 Guía de Uso")
    st.markdown("""
    **🔍 Buscador:** Filtra por clase, categoría, estado o titular del registro.

    **📋 Búsqueda múltiple:** Ingresa varios números de registro separados por comas.

    **📥 Descargar:** Exporta los resultados filtrados a Excel.
    """)
    st.markdown("---")
    if df_disp is not None and glob.glob("dispositivos*.xlsx"):
        st.info("💡 Convierte tu Excel a Parquet para una carga más rápida.")
        st.markdown("---")
    st.markdown(f"<div style='text-align:center;color:#B38E5D;font-size:0.85em;'>UIGD Versión 3.1<br>Datos actualizados: {FECHA_HOY}</div>", unsafe_allow_html=True)

st.markdown("<h1>🏥 Dispositivos Médicos COFEPRIS</h1>", unsafe_allow_html=True)
st.warning("⚠️ **En construcción** — la información se encuentra bajo proceso de validación.")

if df_disp is None:
    st.error(f"🚨 {error_carga}")
    st.stop()

@st.cache_data
def get_opciones_disp(col):
    if col not in df_disp.columns: return []
    return sorted(df_disp[col].replace('', pd.NA).dropna().unique().tolist())

st.markdown("### 🎛️ Panel de Búsqueda y Filtros")
col_s1, col_s2 = st.columns(2)
busqueda_libre = col_s1.text_input("🔍 Búsqueda global:", key="busqueda_libre_disp")
busqueda_mult = col_s2.text_area("📋 Búsqueda múltiple de registros (separe con comas):", placeholder="Ej: 1697E2011 SSA, 0902R2008 SSA", height=68, key="busqueda_mult_disp")

c1, c2, c3, c4 = st.columns(4)
filtro_clase    = c1.multiselect("Clase:",    get_opciones_disp('CLASE'),    key="filtro_clase_disp")
filtro_cat      = c2.multiselect("Categoría:", get_opciones_disp('CATEGORIA'), key="filtro_cat_disp")
filtro_estado   = c3.multiselect("Estado:",   get_opciones_disp('ESTADO'),   key="filtro_estado_disp")
filtro_titular  = c4.multiselect("Titular:",  get_opciones_disp('TITULAR'),  key="filtro_titular_disp")

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
