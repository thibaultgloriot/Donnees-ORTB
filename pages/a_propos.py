import streamlit as st

def show():
    st.title("ℹ️ À propos et mentions légales")
    
    st.write("""
    ## Plateforme de visualisation des données de l'ORTB
    
    Cette application permet de visualiser et d'explorer les indicateurs territoriaux
    à différentes échelles géographiques (communes et EPCI)
    
    ### Échelles disponibles
    - 🏘️ **Communes** : Données à l'échelle communale
    - 🏙️ **EPCI** : Données à l'échelle des intercommunalités
    - 📍 **Départements** : Données à l'échelle départementale
    - 🌍 **Régions** : Données à l'échelle régionale.
    
    ### Fonctionnalités principales
    - 📍 Visualisation cartographique des indicateurs
    - 📊 Analyse statistique des données
    - 📥 Téléchargement des données brutes
    - 🎯 Filtrage par thématique et période
    
    ### Sources de données
    - **Données** : Sources renseignées pour chaque donnée sur la visualisation cartographique
    - **Géométries** : IGN - Admin Express
    
    ### Contact
    Pour toute question ou suggestion :
    - Email : ortb@i-carre.net
    - Tél : 06 59 61 63 54
    - Site Internet de l'ORTB : www.observatoire-transports-bretagne.fr
    
    ### Version
    Version 2.1 - Novembre 2026
    """)
    st.title(" Journal des mises à jour")
    st.write("""
    - v1.0 Début 2026 : Initialisation du projet 
    - v2.0 Aout 2026 : Améliorations diverses : ajout de fonctionalités, optimisation de l'ergonomie, ajout d'indicateurs
    - v2.1 novembre 2026 : intégration dans GéoBretagne""")
    
    
    st.title("⚖️ Mentions légales")

    st.subheader("1. Éditeur du site")
    st.write("""
    **Observatoire Régional des Transports de Bretagne (ORTB)**  
    Association Loi 1901, créée en janvier 1994  
    10 rue Maurice Fabre - CS 96515 - 35065 Rennes cedex  
    Numéro SIRET : 41289657300026
    
    Directeur de la publication : M.Patrick Lahaye  
    Contact : ortb@i-carre.net - Tél : 06 59 61 63 54
    """)

    st.subheader("2. Hébergement")
    st.write("""
    Ce site est hébergé par :  
    **GéoBretagne**  
    Adresse complète : https://geobretagne.fr 
    Contact : https://geobretagne.fr/partenariat/contact
    """)

    st.subheader("3. Propriété intellectuelle")
    st.write("""
    L'intégralité de ce site est protégé par le droit d'auteur. Toute reproduction, même partielle, est interdite sans l'autorisation expresse de l'ORTB.
    """)

    st.subheader("4. Données personnelles et cookies")
    st.write("""
    Pour plus d'informations sur la gestion de vos données personnelles et l'utilisation des cookies, nous vous invitons à consulter notre [Politique de confidentialité](lien-vers-votre-page-rgpd).
    """)
    st.divider()
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("📚 Documentation")
        st.write("""
        - [Fichier Grist du projet](https://grist.numerique.gouv.fr/o/docs/1yHHubK9LQYf/Donnees-Transport-ORTB?utm_id=share-doc)
        - [Guide d'utilisation]()
        - [Données publiées sur GéoBretagne]()
        """)
    
    with col2:
        st.subheader("🔧 Technologies")
        st.write("""
        - **Framework** : Streamlit
        - **Visualisation** : Plotly, Pandas
        - **Cartes** : GeoJSON, IGN data
        """)
