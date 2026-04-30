import streamlit as st
from utils import CSS_TEMA

st.set_page_config(page_title="Visor Inteligente COFEPRIS", page_icon="🇲🇽", layout="wide")
st.markdown(CSS_TEMA, unsafe_allow_html=True)

with st.sidebar:
    try: st.image("COFEPRIS.png", use_container_width=True)
    except: st.title("COFEPRIS")
    st.markdown("---")
    st.markdown("<div style='color:white;'>Selecciona una herramienta en el menú de navegación.</div>", unsafe_allow_html=True)
    st.markdown("<br><div style='text-align:center;color:#B38E5D;font-size:0.85em;'>Visor Inteligente v2.5</div>", unsafe_allow_html=True)

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
    st.markdown("👈 Selecciona **1 Medicamentos** en el menú lateral.")

with col2:
    st.markdown("### 🏥 Dispositivos Médicos")
    st.markdown("""
    Explora el catálogo oficial de registros sanitarios de dispositivos médicos COFEPRIS.

    - Búsqueda por denominación distintiva, genérica o número de registro
    - Filtros por clase (I/II/III), categoría, estado y titular
    - Cruce inteligente con archivos de inventario mediante similitud difusa
    - Exportación de resultados a Excel
    """)
    st.markdown("👈 Selecciona **2 Dispositivos Medicos** en el menú lateral.")

st.markdown("---")
st.caption("Trámites Electrónicos COFEPRIS · Visor Inteligente v2.5")
