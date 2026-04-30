import re
import pandas as pd

_RE_CARACTERES = re.compile(r'[^a-z0-9ñáéíóú\s]')
_RE_STOPWORDS = re.compile(
    r'\b(caja|carton|cartón|envase|burbuja|frasco|ampula|ámpula|'
    r'con|que|contiene|cada|de|en|el|la|los|las|un|una|para|instructivo|anexo|o|y)\b'
)

CSS_TEMA = """
    <style>
    /* Fondo sidebar */
    [data-testid="stSidebar"] { background-color: #13322B; }

    /* Todo el texto del sidebar en blanco */
    [data-testid="stSidebar"] p,
    [data-testid="stSidebar"] span,
    [data-testid="stSidebar"] label,
    [data-testid="stSidebar"] li,
    [data-testid="stSidebar"] h1,
    [data-testid="stSidebar"] h2,
    [data-testid="stSidebar"] h3,
    [data-testid="stSidebar"] small,
    [data-testid="stSidebar"] div { color: white !important; }

    /* Menú de navegación (st.navigation) */
    [data-testid="stSidebarNavLink"]          { color: white !important; }
    [data-testid="stSidebarNavLink"] p        { color: white !important; }
    [data-testid="stSidebarNavLink"] span     { color: white !important; }
    [data-testid="stSidebarNavLink"]:hover    { background-color: rgba(255,255,255,0.12) !important; }
    [data-testid="stSidebarNavLink"][aria-selected="true"] {
        background-color: rgba(179,142,93,0.35) !important;
        border-left: 3px solid #B38E5D !important;
    }

    /* Títulos principales */
    h1 { color: #6F1827; border-bottom: 2px solid #B38E5D; padding-bottom: 10px; }

    /* Métricas */
    .stMetric { background-color: #f8f9fa; padding: 10px; border-radius: 10px; border-left: 5px solid #B38E5D; }

    /* Botones */
    .stButton>button                { background-color: #B38E5D; color: white; border: none; width: 100%; }
    .stButton>button:hover          { background-color: #6F1827; color: white; }
    </style>
"""

def limpiar_texto_para_cruce(texto):
    if pd.isna(texto): return ""
    t = str(texto).lower().replace('/', ' ').replace('-', ' ')
    t = _RE_CARACTERES.sub(' ', t)
    t = _RE_STOPWORDS.sub(' ', t)
    return " ".join(t.split())
