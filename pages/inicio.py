import streamlit as st

st.markdown("<h1>Visor Inteligente COFEPRIS</h1>", unsafe_allow_html=True)
st.markdown("Plataforma de consulta de Registros Sanitarios de la Comisión Federal para la Protección contra Riesgos Sanitarios.")
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
    - Cruce inteligente con archivos de inventario mediante similitud difusa
    - Exportación de resultados a Excel
    """)

st.markdown("---")
st.caption("Trámites Electrónicos COFEPRIS · Visor Inteligente v2.5")
