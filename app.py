import streamlit as st
from utils import CSS_TEMA

st.set_page_config(page_title="Visor Inteligente COFEPRIS", page_icon="🇲🇽", layout="wide")
st.markdown(CSS_TEMA, unsafe_allow_html=True)

with st.sidebar:
    try: st.image("COFEPRIS.png", use_container_width=True)
    except: st.title("COFEPRIS")
    st.markdown("---")

pg = st.navigation([
    st.Page("pages/inicio.py",                title="Inicio",               icon="🏠", default=True),
    st.Page("pages/1_Medicamentos.py",         title="Medicamentos",         icon="💊"),
    st.Page("pages/2_Dispositivos_Medicos.py", title="Dispositivos Médicos", icon="🏥"),
])
pg.run()
