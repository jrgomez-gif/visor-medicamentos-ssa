import re
import pandas as pd

_RE_CARACTERES = re.compile(r'[^a-z0-9ñáéíóú\s]')
_RE_STOPWORDS = re.compile(
    r'\b(caja|carton|cartón|envase|burbuja|frasco|ampula|ámpula|'
    r'con|que|contiene|cada|de|en|el|la|los|las|un|una|para|instructivo|anexo|o|y)\b'
)

CSS_TEMA = """
    <style>
    [data-testid="stSidebar"] { background-color: #13322B; }
    [data-testid="stSidebar"] .stMarkdown p,
    [data-testid="stSidebar"] h1, [data-testid="stSidebar"] h2, [data-testid="stSidebar"] h3,
    [data-testid="stSidebar"] label, [data-testid="stSidebar"] li { color: white !important; }
    h1 { color: #6F1827; border-bottom: 2px solid #B38E5D; padding-bottom: 10px; }
    .stMetric { background-color: #f8f9fa; padding: 10px; border-radius: 10px; border-left: 5px solid #B38E5D; }
    .stButton>button { background-color: #B38E5D; color: white; border: none; width: 100%; }
    .stButton>button:hover { background-color: #6F1827; color: white; }
    </style>
"""

def limpiar_texto_para_cruce(texto):
    if pd.isna(texto): return ""
    t = str(texto).lower().replace('/', ' ').replace('-', ' ')
    t = _RE_CARACTERES.sub(' ', t)
    t = _RE_STOPWORDS.sub(' ', t)
    return " ".join(t.split())
