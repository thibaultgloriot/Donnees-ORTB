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
def load_data(filepath, code_col, libelle_col):
    """Charge un fichier de données avec les colonnes standardisées"""
    try:
        df = pd.read_csv(filepath)
        df['date'] = pd.to_datetime(df['date'], format='%d/%m/%Y', errors='coerce')
        df[code_col] = df[code_col].astype(str)
        df = df.dropna(subset=['date'])
        if 'valeur' in df.columns:
            df['valeur'] = pd.to_numeric(df['valeur'], errors='coerce')
        return df
    except Exception as e:
        st.warning(f"Impossible de charger {filepath}: {e}")
        return None

@st.cache_data
def load_all_data():
    """Charge toutes les données (communes, EPCI, départements, régions)"""
    data = {}
    
    # Charger les communes
    data['communes'] = load_data('data/final_df_communes.csv', 'code_commune', 'libelle_commune')
    
    # Charger les EPCI
    data['epci'] = load_data('data/final_df_epci.csv', 'code_epci', 'libelle_epci')
    
    # Charger les départements
    data['departements'] = load_data('data/final_df_departement.csv', 'code_departement', 'libelle_departement')
    
    # Charger les régions
    data['regions'] = load_data('data/final_df_region.csv', 'code_region', 'libelle_region')
    
    return data

# Chargement du mapping
@st.cache_data
def load_mapping():
    try:
        mapping_df = pd.read_csv("data/columns_indicateurs.csv", sep=",")
        return mapping_df
    except:
        return None

# Charger les données
data = load_all_data()
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

# Appliquer les thématiques à toutes les données
for key in data:
    if data[key] is not None:
        data[key] = add_thematique_column(data[key], mapping_df)

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
    
    # Afficher les informations pour chaque échelle
    echelles = {
        'communes': 'Communes',
        'epci': 'EPCI',
        'departements': 'Départements',
        'regions': 'Régions'
    }
    
    for key, label in echelles.items():
        if data.get(key) is not None and not data[key].empty:
            st.caption(f"{label}: {data[key]['indicateur'].nunique()} indicateurs")

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
            module.show(data)
        elif selected_module == "cartes":
            module.show(data)
        elif selected_module == "donnees_brutes":
            module.show(data)
        elif selected_module == "a_propos":
            module.show()
        else:
            try:
                module.show(data)
            except:
                module.show()
                    
    except Exception as e:
        st.error(f"Erreur lors du chargement de la page: {e}")