import streamlit as st
import pandas as pd

def show(df, epci_df):
    st.title("🏠 Tableau de bord - Observatoire Régional de la Planification Ecologique")
    
    # KPI globaux
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Nombre d'indicateurs à l'échelle commune", df['indicateur'].nunique())
    with col2:
        st.metric("Nombre d'indicateurs à l'échelle EPCI", epci_df['indicateur'].nunique())
    
    with col3:
        st.metric("Nombre de communes", df['code_commune'].nunique())
    
    with col4:
        if epci_df is not None:
            st.metric("Nombre d'EPCI", 61)
        else:
            st.metric("Période couverte", f"{df['date'].min().year}-{df['date'].max().year}")
    
    # Liste des indicateurs disponibles
    st.subheader("📋 Indicateurs disponibles par thématique")
    
    # Récupérer toutes les thématiques uniques des deux sources
    all_thematiques = set()
    
    # Ajouter les thématiques des communes
    if 'thematique' in df.columns:
        # Filtrer les valeurs non nulles
        themes_communes = [t for t in df['thematique'].dropna().unique() if str(t).strip() != '']
        all_thematiques.update(themes_communes)
    
    # Ajouter les thématiques des EPCI
    if 'thematique' in epci_df.columns:
        # Filtrer les valeurs non nulles
        themes_epci = [t for t in epci_df['thematique'].dropna().unique() if str(t).strip() != '']
        all_thematiques.update(themes_epci)
    
    # Afficher par thématique si disponible
    if all_thematiques:
        for thematique in sorted(all_thematiques):
            with st.expander(f"{thematique}"):
                # Collecter tous les indicateurs uniques pour cette thématique
                indicateurs = set()
                
                # Indicateurs des communes
                if 'thematique' in df.columns:
                    mask = (df['thematique'].notna()) & (df['thematique'] == thematique)
                    if mask.any():
                        indicateurs.update(df[mask]['indicateur'].dropna().unique())
                
                # Indicateurs des EPCI
                if 'thematique' in epci_df.columns:
                    mask = (epci_df['thematique'].notna()) & (epci_df['thematique'] == thematique)
                    if mask.any():
                        indicateurs.update(epci_df[mask]['indicateur'].dropna().unique())
                
                # Afficher tous les indicateurs
                for ind in sorted(indicateurs):
                    st.write(f"• {ind}")
    else:
        # Fallback si pas de colonne thématique
        st.write("**Tous les indicateurs :**")
        
        # Indicateurs des communes
        if 'indicateur' in df.columns:
            for ind in sorted(df['indicateur'].dropna().unique()):
                st.write(f"• {ind}")
        
        # Indicateurs des EPCI  
        if 'indicateur' in epci_df.columns:
            for ind in sorted(epci_df['indicateur'].dropna().unique()):
                st.write(f"• {ind}")
