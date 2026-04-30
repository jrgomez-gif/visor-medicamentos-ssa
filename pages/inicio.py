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

st.markdown("## 🆕 Versión 3.1")
st.info("Actualmente se está trabajando en la sección de **Dispositivos Médicos**. Próximamente disponible.")

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
