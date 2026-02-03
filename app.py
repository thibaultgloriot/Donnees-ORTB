import streamlit as st
import pandas as pd
import plotly.express as px
from PIL import Image
import importlib
import sys
import os

# Configuration de la page
st.set_page_config(
    page_title="Observatoire de la Planification Ecologique en Bretagne",
    page_icon="🗺️",
    layout="wide",
    initial_sidebar_state="expanded")

# Chargement du logo
logo = Image.open('assets/logo.png')

# Chargement des données
@st.cache_data
def load_data():
    df = pd.read_csv('data/final_df_communes.csv')
    # Conversion des dates en format datetime
    df['date'] = pd.to_datetime(df['date'], format='%d/%m/%Y', errors='coerce')
    # Suppression des lignes avec dates invalides si nécessaire
    df['code_commune'] = df['code_commune'].astype(str)
    df = df.dropna(subset=['date'])
    return df

@st.cache_data
def load_epci_data():
    # Charger les données EPCI (à adapter selon votre fichier)
    try:
        epci_df = pd.read_csv('data/final_df_epci.csv')
        epci_df.rename(columns={'nom':'libelle_epci'}, inplace=True)
        epci_df['date'] = pd.to_datetime(epci_df['date'], format='%d/%m/%Y', errors='coerce')
        epci_df['code_epci'] = epci_df['code_epci'].astype(str)
        return epci_df
    except FileNotFoundError:
        return None

# Charger les données
df = load_data()
epci_df = load_epci_data()

# Charger le mapping des indicateurs
try:
    mapping_df = pd.read_csv("data/columns_indicateurs.csv", sep=";")
except:
    # Créer un mapping par défaut si le fichier n'existe pas
    mapping_df = pd.DataFrame({
        'Indicateur': df['indicateur'].unique(),
        'Thématique': ['Non classé'] * len(df['indicateur'].unique()),
        'Nouveau_nom_indicateur': df['indicateur'].unique()
    })

def add_thematique_column(df):
    if df is None:
        return None
    
    # Créer un dictionnaire à partir des deux colonnes
    thematiques = dict(zip(mapping_df['Indicateur'], mapping_df['Thématique']))
    nouveau_nom = dict(zip(mapping_df['Indicateur'], mapping_df['Nouveau_nom_indicateur']))
    
    # Appliquer le mapping
    df['thematique'] = df['indicateur'].map(thematiques)
    # Remplacer les valeurs manquantes par l'original
    df['thematique'] = df['thematique'].fillna('Non classé')
    
    # Renommer les indicateurs
    df['indicateur'] = df['indicateur'].map(nouveau_nom)
    df['indicateur'] = df['indicateur'].fillna(df['indicateur'])
    
    return df

# Appliquer les thématiques
df = add_thematique_column(df)
if epci_df is not None:
    epci_df = add_thematique_column(epci_df)

# Définir les pages disponibles
# Vérifier d'abord quelles pages existent
available_pages = []
pages_to_check = [
    ("🏠 Accueil", "accueil"),
    ("🗺️ Cartes", "cartes"), 
    ("📊 Données brutes", "donnees_brutes"),
    ("ℹ️ À propos", "a_propos")
]

for page_name, page_file in pages_to_check:
    page_path = f"pages/{page_file}.py"
    if os.path.exists(page_path):
        available_pages.append((page_name, page_file))

# Si aucune page n'est trouvée, utiliser les pages par défaut
if not available_pages:
    available_pages = [
        ("🗺️ Cartes", "cartes"),
        ("📊 Données brutes", "donnees_brutes")
    ]

# Sidebar avec navigation
st.markdown("""<style>
    [data-testid="stSidebarNav"] {display: none;}</style>""", unsafe_allow_html=True)
with st.sidebar:
    st.image(logo, width=200)
    st.title("Navigation")
    
    # Créer la liste des pages disponibles
    page_options = [name for name, _ in available_pages]
    
    # Navigation
    selected_page_name = st.radio(
        "Sélectionnez une page",
        options=page_options,
        label_visibility="collapsed"
    )
    
    # Ajouter des informations utiles
    st.divider()
    st.subheader("📊 Informations")
    
    if df is not None and not df.empty:
        st.caption(f"Données mises à jour le: 15/12/2025")
        st.caption(f"Indicateurs communaux: {df['indicateur'].nunique()}")
    
    if epci_df is not None and not epci_df.empty:
        st.caption(f"Indicateurs EPCI: {epci_df['indicateur'].nunique()}")
    
    if 'thematique' in df.columns:
        st.caption(f"Thématiques: {df['thematique'].nunique()}")

# Trouver le module correspondant à la page sélectionnée
selected_module = None
for page_name, page_file in available_pages:
    if page_name == selected_page_name:
        selected_module = page_file
        break

# Charger et afficher la page sélectionnée
if selected_module:
    try:
        # Importer dynamiquement le module
        module = importlib.import_module(f"pages.{selected_module}")
        
        # Appeler la fonction show avec les bons paramètres
        if selected_module == "accueil":
            module.show(df, epci_df)
        elif selected_module == "cartes":
            module.show(df, epci_df)
        elif selected_module == "donnees_brutes":
            module.show(df, epci_df)
        elif selected_module == "a_propos":
            module.show()
        else:
            # Essayer d'appeler show avec les paramètres par défaut
            try:
                module.show(df, epci_df)
            except:
                try:
                    module.show(df)
                except:
                    module.show()
                    
    except Exception as e:
        st.error(f"Erreur lors du chargement de la page: {e}")
        st.info("Affichage de la page par défaut...")
        
        # Afficher une page par défaut
        if selected_module == "cartes":
            from pages import cartes
            cartes.show(df, epci_df)
        elif selected_module == "donnees_brutes":
            import pages.donnees_brutes
            pages.donnees_brutes.show(df,epci_df)
        else:
            st.title(f"Page: {selected_page_name}")
            st.write("Cette page est en cours de développement.")
else:
    st.error("Page non trouvée")


