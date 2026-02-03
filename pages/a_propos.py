

import streamlit as st

def show():
    st.title("ℹ️ À propos")
    
    st.write("""
    ## Observatoire de la Planification Ecologique en Bretagne
    
    Cet outil permet de visualiser et d'explorer les indicateurs territoriaux de la planification écologique
    à différentes échelles géographiques (communes et EPCI).
    
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
    - Email : thibault.gloriot@developpement-durable.gouv.fr ou cpros.coprev.dreal-bretagne@developpement-durable.gouv.fr
    - Tél : 06 59 61 63 54
    
    ### Version
    Version 1.0 - Décembre 2025
    """)
    
    st.divider()
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("📚 Documentation")
        st.write("""
        - [Fichier Grist du projet](https://grist.numerique.gouv.fr/o/docs/56VbbinHJQEo/IndicateursPlanificationEcologique?utm_id=share-doc)
        - [Guide d'utilisation]()
        - [Données publiées sur GéoBretagne]()
        """)
    
    with col2:
        st.subheader("🔧 Technologies")
        st.write("""
        - **Framework** : Streamlit
        - **Visualisation** : Plotly, Pandas
        - **Cartes** : GeoJSON, IGN data
        - **Hébergement** : Streamlit Cloud

        """)



