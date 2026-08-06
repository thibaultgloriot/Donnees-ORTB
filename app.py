import streamlit as st
import pandas as pd
from PIL import Image
import importlib
import os

# Configuration de la page
st.set_page_config(
    page_title="Plateforme de visualisation des données de l'ORTB",
    page_icon="🗺️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Chargement du logo
logo = Image.open('assets/logo.jpg')

# Chargement des données
@st.cache_data
def load_data():
    df = pd.read_csv('data/final_df_communes.csv')
    df['date'] = pd.to_datetime(df['date'], format='%d/%m/%Y', errors='coerce')
    df['code_commune'] = df['code_commune'].astype(str)
    df = df.dropna(subset=['date'])
    if 'valeur' in df.columns:
        df['valeur'] = pd.to_numeric(df['valeur'], errors='coerce')
    return df

@st.cache_data
def load_epci_data():
    try:
        epci_df = pd.read_csv('data/final_df_epci.csv')
        epci_df.rename(columns={'nom':'libelle_epci'}, inplace=True)
        epci_df['date'] = pd.to_datetime(epci_df['date'], format='%d/%m/%Y', errors='coerce')
        epci_df['code_epci'] = epci_df['code_epci'].astype(str)
        if 'valeur' in epci_df.columns:
            epci_df['valeur'] = pd.to_numeric(epci_df['valeur'], errors='coerce')
        return epci_df
    except FileNotFoundError:
        return None

# Chargement du mapping
@st.cache_data
def load_mapping():
    try:
        mapping_df = pd.read_csv("data/columns_indicateurs.csv", sep=",")
        return mapping_df
    except:
        return None

# Charger les données
df = load_data()
epci_df = load_epci_data()
mapping_df = load_mapping()

# Ajouter les thématiques
def add_thematique_column(df, mapping_df):
    if df is None or df.empty:
        return None
    
    # Créer un dictionnaire des thématiques (avec gestion des multiples)
    thematiques_dict = {}
    if mapping_df is not None and 'Thématique' in mapping_df.columns:
        if 'Nouveau_nom_indicateur' in mapping_df.columns:
            indicator_col = 'Nouveau_nom_indicateur'
        else:
            indicator_col = 'Indicateur'
        
        for _, row in mapping_df.iterrows():
            if pd.notna(row['Thématique']) and row['Thématique'] != '':
                themes = [t.strip() for t in str(row['Thématique']).split(';')]
                thematiques_dict[row[indicator_col]] = themes
    
    # Appliquer les thématiques
    df['thematique'] = df['indicateur'].map(
        lambda x: thematiques_dict.get(x, ['Non classé'])[0]
    )
    df['thematique'] = df['thematique'].fillna('Non classé')
    
    # Renommer les indicateurs
    if mapping_df is not None and 'Nouveau_nom_indicateur' in mapping_df.columns:
        nouveau_nom = dict(zip(mapping_df['Indicateur'], mapping_df['Nouveau_nom_indicateur']))
        df['indicateur'] = df['indicateur'].map(nouveau_nom)
        df['indicateur'] = df['indicateur'].fillna(df['indicateur'])
    
    return df

# Appliquer les thématiques
df = add_thematique_column(df, mapping_df)
if epci_df is not None:
    epci_df = add_thematique_column(epci_df, mapping_df)

# Navigation
available_pages = []
pages_to_check = [
    ("🏠 Accueil", "accueil"),
    ("🗺️ Cartes", "cartes"),
    ("📊 Données brutes", "donnees_brutes"),
    ("ℹ️ À propos", "a_propos")
]

for page_name, page_file in pages_to_check:
    if os.path.exists(f"pages/{page_file}.py"):
        available_pages.append((page_name, page_file))

# Sidebar
st.markdown("""<style>[data-testid="stSidebarNav"] {display: none;}</style>""", unsafe_allow_html=True)

with st.sidebar:
    st.image(logo, width=200)
    st.title("Navigation")
    
    page_options = [name for name, _ in available_pages]
    selected_page_name = st.radio(
        "Sélectionnez une page",
        options=page_options,
        label_visibility="collapsed"
    )
    
    st.divider()
    st.subheader("📊 Informations")
    
    if df is not None and not df.empty:
        st.caption(f"Données mises à jour le: 06/08/2026")
        st.caption(f"Indicateurs communaux: {df['indicateur'].nunique()}")
    
    if epci_df is not None and not epci_df.empty:
        st.caption(f"Indicateurs EPCI: {epci_df['indicateur'].nunique()}")

# Charger la page sélectionnée
selected_module = None
for page_name, page_file in available_pages:
    if page_name == selected_page_name:
        selected_module = page_file
        break

if selected_module:
    try:
        module = importlib.import_module(f"pages.{selected_module}")
        
        if selected_module == "accueil":
            module.show(df, epci_df)
        elif selected_module == "cartes":
            module.show(df, epci_df)
        elif selected_module == "donnees_brutes":
            module.show(df, epci_df)
        elif selected_module == "a_propos":
            module.show()
        else:
            try:
                module.show(df, epci_df)
            except:
                try:
                    module.show(df)
                except:
                    module.show()
                    
    except Exception as e:
        st.error(f"Erreur lors du chargement de la page: {e}")