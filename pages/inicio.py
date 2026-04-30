import streamlit as st
from datetime import date

FECHA_HOY = date.today().strftime("%-d de %B de %Y").replace(
    "January","enero").replace("February","febrero").replace("March","marzo").replace(
    "April","abril").replace("May","mayo").replace("June","junio").replace(
    "July","julio").replace("August","agosto").replace("September","septiembre").replace(
    "October","octubre").replace("November","noviembre").replace("December","diciembre")

with st.sidebar:
    st.markdown("### 📖 Guía de Uso")
    st.markdown("""
    **¿Qué es el Visor UIGD?**
    Plataforma de consulta de Registros Sanitarios COFEPRIS para SSA, BIRMEX y COFEPRIS.

    **💊 Medicamentos:** Busca y cruza registros sanitarios de medicamentos.

    **🏥 Dispositivos Médicos:** Consulta registros de dispositivos médicos.
    """)
    st.markdown("---")
    st.markdown(f"<div style='text-align:center;color:#B38E5D;font-size:0.85em;'>UIGD Versión 3.1<br>Datos actualizados: {FECHA_HOY}</div>", unsafe_allow_html=True)

st.markdown("<h1>Visor Inteligente COFEPRIS</h1>", unsafe_allow_html=True)
st.markdown(f"Plataforma de consulta de Registros Sanitarios · **UIGD Versión 3.1** · Datos actualizados: {FECHA_HOY}")
st.markdown("---")

st.markdown("## 🆕 Novedades de la versión 3.1")

tab_ssa, tab_birmex, tab_cofepris = st.tabs(["🏥 SSA", "🧪 BIRMEX", "🇲🇽 COFEPRIS"])

with tab_ssa:
    st.markdown("""
    **Principales mejoras para la Secretaría de Salud:**
    - Nueva sección de **Dispositivos Médicos** con catálogo oficial COFEPRIS
    - Cruce SSA de medicamentos mejorado: mayor velocidad y precisión de matching
    - Búsqueda múltiple por número de registro para verificación masiva de inventarios
    - Exportación a Excel de todos los resultados filtrados
    - Filtros avanzados por estado, forma farmacéutica, vía de administración y titular
    """)

with tab_birmex:
    st.markdown("""
    **Principales mejoras para BIRMEX:**
    - Acceso al catálogo completo y actualizado de registros sanitarios vigentes
    - Filtros por principio activo, forma farmacéutica y titular del registro
    - Identificación rápida de registros vigentes vs. otros estados
    - Herramienta de cruce inteligente para verificar estatus de productos en catálogo COFEPRIS
    - Descarga directa de resultados en formato Excel
    """)

with tab_cofepris:
    st.markdown("""
    **Principales mejoras para COFEPRIS:**
    - Base de datos migrada a formato Parquet: carga ~5x más rápida
    - Nuevo módulo de **Dispositivos Médicos** integrado a la plataforma
    - Buscador optimizado con algoritmos vectorizados (sin límite de resultados)
    - Interfaz unificada con navegación entre módulos de medicamentos y dispositivos
    - Arquitectura multipágina escalable para futuros módulos
    """)

st.markdown("---")

col1, col2 = st.columns(2)

with col1:
    st.markdown("### 💊 Medicamentos")
    st.markdown("""
    Explora el catálogo oficial de registros sanitarios de medicamentos COFEPRIS.

    - Búsqueda por nombre, sustancia activa o número de registro
    - Filtros por estado, forma farmacéutica, vía de administración y titular
    - Cruce inteligente con archivos SSA mediante similitud difusa
    - Exportación de resultados a Excel
    """)

with col2:
    st.markdown("### 🏥 Dispositivos Médicos")
    st.markdown("""
    Explora el catálogo oficial de registros sanitarios de dispositivos médicos COFEPRIS.

    - Búsqueda por denominación distintiva, genérica o número de registro
    - Filtros por clase (I/II/III), categoría, estado y titular
    - Exportación de resultados a Excel
    - *(Cruce inteligente próximamente)*
    """)

st.markdown("---")
st.caption(f"Trámites Electrónicos COFEPRIS · UIGD Versión 3.1 · Datos actualizados: {FECHA_HOY}")
