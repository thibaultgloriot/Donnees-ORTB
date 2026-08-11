import streamlit as st
import pandas as pd

def show(data):
    st.title("🏠 Plateforme de visualisation des données de l'ORTB")
    
    # KPI globaux
    echelles = {
        'communes': 'Communes',
        'epci': 'EPCI',
        'departements': 'Départements',
        'regions': 'Régions'
    }
    
    # Créer une ligne de métriques pour chaque échelle
    cols = st.columns(4)
    
    for i, (key, label) in enumerate(echelles.items()):
        if data.get(key) is not None and not data[key].empty:
            with cols[i]:
                st.metric(
                    f"Indicateurs ({label})",
                    data[key]['indicateur'].nunique()
                )
    
    # Charger les données des groupes
    try:
        groups_df = pd.read_csv("data/denomination_groupes.csv", sep=",")
        group_names = dict(zip(groups_df['Groupe'].astype(str), groups_df['nom_groupe']))
    except:
        group_names = {}
    
    # Charger le mapping des indicateurs
    try:
        mapping_df = pd.read_csv("data/columns_indicateurs.csv", sep=",")
        if 'Nouveau_nom_indicateur' in mapping_df.columns:
            indicator_col = 'Nouveau_nom_indicateur'
        else:
            indicator_col = 'Indicateur'
        
        # Créer un mapping indicateur -> groupe
        indicator_to_group = {}
        if 'Groupe' in mapping_df.columns:
            for _, row in mapping_df.iterrows():
                if pd.notna(row['Groupe']) and row['Groupe'] != 0:
                    groupe_str = str(row['Groupe'])
                    indicator_to_group[row[indicator_col]] = {
                        'groupe': groupe_str,
                        'nom_groupe': group_names.get(groupe_str, f"Groupe {groupe_str}")
                    }
        
        # Récupérer les thématiques
        thematiques_dict = {}
        if 'Thématique' in mapping_df.columns:
            for _, row in mapping_df.iterrows():
                if pd.notna(row['Thématique']) and row['Thématique'] != '':
                    themes = [t.strip() for t in str(row['Thématique']).split(';') if t.strip()]
                    if themes:
                        thematiques_dict[row[indicator_col]] = themes
        
    except:
        indicator_to_group = {}
        thematiques_dict = {}
    
    # Liste des indicateurs disponibles par thématique
    st.subheader("📋 Indicateurs disponibles par thématique")
    
    # Récupérer toutes les thématiques uniques
    all_thematiques = set()
    
    # Parcourir toutes les données pour récupérer les thématiques
    for df_temp in data.values():
        if df_temp is not None and 'indicateur' in df_temp.columns:
            for indicateur in df_temp['indicateur'].unique():
                if indicateur in thematiques_dict:
                    all_thematiques.update(thematiques_dict[indicateur])
    
    if all_thematiques:
        for thematique in sorted(all_thematiques):
            with st.expander(f"{thematique}"):
                # Utiliser un ensemble pour éviter les doublons
                indicateurs_vus = set()
                groupes_comptes = {}
                
                # Parcourir toutes les données
                for df_temp in data.values():
                    if df_temp is not None and 'indicateur' in df_temp.columns:
                        for indicateur in df_temp['indicateur'].unique():
                            # Vérifier si l'indicateur a déjà été traité
                            if indicateur in indicateurs_vus:
                                continue
                            
                            # Vérifier si l'indicateur appartient à cette thématique
                            if indicateur in thematiques_dict and thematique in thematiques_dict[indicateur]:
                                indicateurs_vus.add(indicateur)
                                
                                # Vérifier si l'indicateur est dans un groupe
                                if indicateur in indicator_to_group:
                                    nom_groupe = indicator_to_group[indicateur]['nom_groupe']
                                    
                                    if nom_groupe not in groupes_comptes:
                                        groupes_comptes[nom_groupe] = {
                                            'compte': 1,
                                            'type': 'groupe'
                                        }
                                    else:
                                        groupes_comptes[nom_groupe]['compte'] += 1
                                else:
                                    groupes_comptes[indicateur] = {
                                        'compte': 1,
                                        'type': 'individuel'
                                    }
                
                # Afficher les indicateurs groupés
                for nom, info in sorted(groupes_comptes.items()):
                    if info['type'] == 'groupe':
                        if info['compte'] == 1:
                            st.write(f"• 📊 {nom} (1 indicateur)")
                        else:
                            st.write(f"• 📊 {nom} ({info['compte']} indicateurs)")
                    else:
                        st.write(f"• 📈 {nom}")
    else:
        st.write("Aucune thématique définie dans le fichier columns_indicateurs.csv")