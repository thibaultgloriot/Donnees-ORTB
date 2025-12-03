import streamlit as st
import pandas as pd
import numpy as np

def show(df_communes, df_epci):
    st.title("📁 Données Brutes")
    
    # Vérifier qu'au moins un DataFrame est fourni
    if df_communes is None and df_epci is None:
        st.error("Aucune donnée fournie. Veuillez fournir au moins un DataFrame (communes ou EPCI).")
        return
    
    # Combiner les DataFrames si les deux sont fournis
    if df_communes is not None and df_epci is not None:
        # Ajouter une colonne pour identifier la source
        df_communes = df_communes.copy()
        df_epci = df_epci.copy()
        
        if 'maille' not in df_communes.columns:
            df_communes['maille'] = 'Commune'
        if 'maille' not in df_epci.columns:
            df_epci['maille'] = 'EPCI'
        
        # Combiner les DataFrames
        df = pd.concat([df_communes, df_epci], ignore_index=True)
        
        # Vérifier les colonnes nécessaires
        required_columns = ['date', 'indicateur', 'thematique']
        for col in required_columns:
            if col not in df.columns:
                st.error(f"Colonne manquante dans les données combinées : {col}")
                return
                
    elif df_communes is not None:
        df = df_communes.copy()
        if 'maille' not in df.columns:
            df['maille'] = 'Commune'
            
        # Vérifier les colonnes nécessaires
        required_columns = ['date', 'indicateur', 'thematique']
        for col in required_columns:
            if col not in df.columns:
                st.error(f"Colonne manquante dans les données communes : {col}")
                return
                
    else:  # seulement df_epci
        df = df_epci.copy()
        if 'maille' not in df.columns:
            df['maille'] = 'EPCI'
            
        # Vérifier les colonnes nécessaires
        required_columns = ['date', 'indicateur', 'thematique']
        for col in required_columns:
            if col not in df.columns:
                st.error(f"Colonne manquante dans les données EPCI : {col}")
                return
    
    # Sidebar pour les filtres
    with st.sidebar:
        st.header("🔍 Filtres")
        
        # Message d'instruction
        st.markdown("---")
        st.info("ℹ️ Veuillez sélectionner vos filtres ci-dessous")
        st.markdown("---")
        
        # Déterminer les options disponibles pour la maille
        maille_options = []
        if df_communes is not None:
            maille_options.append('Commune')
        if df_epci is not None:
            maille_options.append('EPCI')
        
        if not maille_options:
            st.error("Aucune donnée disponible pour les mailles")
            return
        
        # Sélection de la maille avec une clé unique
        maille = st.selectbox(
            "Maille territoriale",
            options=maille_options,
            index=0,
            key="selectbox_maille_territoriale"  # Clé unique pour éviter l'erreur
        )
        
        # Initialiser les variables de sélection
        codes_selection = []
        
        # Filtre par commune (avec nom)
        if maille == 'Commune' and df_communes is not None:
            # Créer un DataFrame temporaire pour les communes
            df_temp = df_communes.copy() if df_communes is not None else df[df['maille'] == 'Commune'].copy()
            
            # Vérifier si on a le nom des communes
            if 'libelle_commune' in df_temp.columns:
                # Créer un mapping code_commune -> libelle_commune
                communes_data = df_temp[['code_commune', 'libelle_commune']].dropna().drop_duplicates()
                if not communes_data.empty:
                    communes_dict = dict(zip(communes_data['libelle_commune'], communes_data['code_commune']))
                    communes_names = sorted(communes_data['libelle_commune'].unique().tolist())
                    
                    col1, col2 = st.columns([3, 1])
                    with col1:
                        communes_selection = st.multiselect(
                            "Sélectionner les communes",
                            options=communes_names,
                            default=[],
                            key="multiselect_communes_names"  # Clé unique
                        )
                    with col2:
                        if st.button("Tout", key="button_all_communes"):
                            if 'communes_selection' not in st.session_state:
                                st.session_state['communes_selection'] = communes_names
                            else:
                                st.session_state['communes_selection'] = communes_names
                            st.rerun()
                    
                    # Vérifier si une sélection est en session
                    if 'communes_selection' in st.session_state and st.session_state['communes_selection']:
                        communes_selection = st.session_state['communes_selection']
                    
                    # Convertir les noms sélectionnés en codes
                    codes_selection = [communes_dict[name] for name in communes_selection] if communes_selection else []
                    
                else:
                    st.info("Aucune donnée de commune disponible")
            
            elif 'code_commune' in df_temp.columns:
                # Fallback sur les codes si pas de libellé
                codes = sorted(df_temp['code_commune'].dropna().unique().astype(str).tolist())
                if codes:
                    col1, col2 = st.columns([3, 1])
                    with col1:
                        codes_selection = st.multiselect(
                            "Sélectionner les communes (codes)",
                            options=codes,
                            default=[],
                            key="multiselect_communes_codes"  # Clé unique
                        )
                    with col2:
                        if st.button("Tout", key="button_all_communes_codes"):
                            if 'communes_codes_selection' not in st.session_state:
                                st.session_state['communes_codes_selection'] = codes
                            else:
                                st.session_state['communes_codes_selection'] = codes
                            st.rerun()
                    
                    # Vérifier si une sélection est en session
                    if 'communes_codes_selection' in st.session_state and st.session_state['communes_codes_selection']:
                        codes_selection = st.session_state['communes_codes_selection']
                        
                else:
                    st.info("Aucun code de commune disponible")
        
        # Filtre par EPCI
        elif maille == 'EPCI' and df_epci is not None:
            # Créer un DataFrame temporaire pour les EPCI
            df_temp = df_epci.copy() if df_epci is not None else df[df['maille'] == 'EPCI'].copy()
            
            # Essayer d'abord avec le libellé si disponible
            if 'libelle_epci' in df_temp.columns:
                epci_data = df_temp[['code_epci', 'libelle_epci']].dropna().drop_duplicates()
                if not epci_data.empty:
                    epci_dict = dict(zip(epci_data['libelle_epci'], epci_data['code_epci']))
                    epci_names = sorted(epci_data['libelle_epci'].unique().tolist())
                    
                    col1, col2 = st.columns([3, 1])
                    with col1:
                        epci_selection = st.multiselect(
                            "Sélectionner les EPCI",
                            options=epci_names,
                            default=[],
                            key="multiselect_epci_names"  # Clé unique
                        )
                    with col2:
                        if st.button("Tout", key="button_all_epci"):
                            if 'epci_selection' not in st.session_state:
                                st.session_state['epci_selection'] = epci_names
                            else:
                                st.session_state['epci_selection'] = epci_names
                            st.rerun()
                    
                    # Vérifier si une sélection est en session
                    if 'epci_selection' in st.session_state and st.session_state['epci_selection']:
                        epci_selection = st.session_state['epci_selection']
                    
                    codes_selection = [epci_dict[name] for name in epci_selection] if epci_selection else []
                    
                else:
                    st.info("Aucune donnée d'EPCI disponible")
            
            else:
                # Fallback sur les codes
                codes = sorted(df_temp['code_epci'].dropna().unique().astype(str).tolist())
                if codes:
                    col1, col2 = st.columns([3, 1])
                    with col1:
                        codes_selection = st.multiselect(
                            "Sélectionner les EPCI (codes)",
                            options=codes,
                            default=[],
                            key="multiselect_epci_codes"  # Clé unique
                        )
                    with col2:
                        if st.button("Tout", key="button_all_epci_codes"):
                            if 'epci_codes_selection' not in st.session_state:
                                st.session_state['epci_codes_selection'] = codes
                            else:
                                st.session_state['epci_codes_selection'] = codes
                            st.rerun()
                    
                    # Vérifier si une sélection est en session
                    if 'epci_codes_selection' in st.session_state and st.session_state['epci_codes_selection']:
                        codes_selection = st.session_state['epci_codes_selection']
                        
                else:
                    st.info("Aucun code d'EPCI disponible")
        
        # Filtre par thématique
        thematiques_selection = []
        if 'thematique' in df.columns:
            thematiques = sorted(df['thematique'].dropna().unique().tolist())
            if thematiques:
                col1, col2 = st.columns([3, 1])
                with col1:
                    thematiques_selection = st.multiselect(
                        "Sélectionner les thématiques",
                        options=thematiques,
                        default=[],
                        key="multiselect_thematiques"  # Clé unique
                    )
                with col2:
                    if st.button("Tout", key="button_all_thematiques"):
                        if 'thematiques_selection' not in st.session_state:
                            st.session_state['thematiques_selection'] = thematiques
                        else:
                            st.session_state['thematiques_selection'] = thematiques
                        st.rerun()
                
                # Vérifier si une sélection est en session
                if 'thematiques_selection' in st.session_state and st.session_state['thematiques_selection']:
                    thematiques_selection = st.session_state['thematiques_selection']
            else:
                st.info("Aucune thématique disponible")
        
        # Filtre par indicateur
        indicateurs_selection = []
        if 'indicateur' in df.columns:
            indicateurs = sorted(df['indicateur'].dropna().unique().tolist())
            if indicateurs:
                col1, col2 = st.columns([3, 1])
                with col1:
                    indicateurs_selection = st.multiselect(
                        "Sélectionner les indicateurs",
                        options=indicateurs,
                        default=[],
                        key="multiselect_indicateurs"  # Clé unique
                    )
                with col2:
                    if st.button("Tout", key="button_all_indicateurs"):
                        if 'indicateurs_selection' not in st.session_state:
                            st.session_state['indicateurs_selection'] = indicateurs
                        else:
                            st.session_state['indicateurs_selection'] = indicateurs
                        st.rerun()
                
                # Vérifier si une sélection est en session
                if 'indicateurs_selection' in st.session_state and st.session_state['indicateurs_selection']:
                    indicateurs_selection = st.session_state['indicateurs_selection']
            else:
                st.info("Aucun indicateur disponible")
        
        # Filtre par date
        dates_selection = []
        if 'date' in df.columns:
            dates = sorted(df['date'].dropna().unique())
            if len(dates) > 0:
                dates_str = [d.strftime('%Y-%m-%d') if hasattr(d, 'strftime') else str(d) for d in dates]
                col1, col2 = st.columns([3, 1])
                with col1:
                    dates_selection = st.multiselect(
                        "Sélectionner les dates",
                        options=dates_str,
                        default=[],
                        key="multiselect_dates"  # Clé unique
                    )
                with col2:
                    if st.button("Tout", key="button_all_dates"):
                        if 'dates_selection' not in st.session_state:
                            st.session_state['dates_selection'] = dates_str
                        else:
                            st.session_state['dates_selection'] = dates_str
                        st.rerun()
                
                # Vérifier si une sélection est en session
                if 'dates_selection' in st.session_state and st.session_state['dates_selection']:
                    dates_selection = st.session_state['dates_selection']
            else:
                st.info("Aucune date disponible")
        
        st.markdown("---")
        
        # Bouton pour tout remplir (sauf territoires)
        if st.button("🧹 Tout remplir (sauf territoires)", type="primary", use_container_width=True, key="button_fill_all"):
            # Réinitialiser les sélections de territoires
            if 'communes_selection' in st.session_state:
                del st.session_state['communes_selection']
            if 'communes_codes_selection' in st.session_state:
                del st.session_state['communes_codes_selection']
            if 'epci_selection' in st.session_state:
                del st.session_state['epci_selection']
            if 'epci_codes_selection' in st.session_state:
                del st.session_state['epci_codes_selection']
            
            # Remplir les autres filtres
            if 'thematique' in df.columns:
                thematiques = sorted(df['thematique'].dropna().unique().tolist())
                st.session_state['thematiques_selection'] = thematiques
            
            if 'indicateur' in df.columns:
                indicateurs = sorted(df['indicateur'].dropna().unique().tolist())
                st.session_state['indicateurs_selection'] = indicateurs
            
            if 'date' in df.columns:
                dates = sorted(df['date'].dropna().unique())
                dates_str = [d.strftime('%Y-%m-%d') if hasattr(d, 'strftime') else str(d) for d in dates]
                st.session_state['dates_selection'] = dates_str
            
            st.rerun()
        
        # Bouton pour tout vider
        if st.button("🗑️ Tout vider", use_container_width=True, key="button_clear_all"):
            # Supprimer toutes les clés de session liées aux sélections
            keys_to_delete = []
            for key in st.session_state.keys():
                if key.endswith('_selection') or key.startswith('all_'):
                    keys_to_delete.append(key)
            
            for key in keys_to_delete:
                del st.session_state[key]
            
            st.rerun()
    
    # Message principal avant les données
    main_container = st.container()
    
    # Vérifier si des filtres sont sélectionnés
    any_filter_selected = (
        codes_selection or
        thematiques_selection or
        indicateurs_selection or
        dates_selection
    )
    
    # Afficher les données ou le message d'instruction
    with main_container:
        if not any_filter_selected:
            st.markdown("---")
            st.markdown("### 📋 Instructions")
            st.info("""
            **Veuillez sélectionner les filtres à gauche de l'écran :**
            
            1. **Choisissez une maille territoriale** (Commune ou EPCI)
            2. **Sélectionnez les territoires** concernés
            3. **Filtrez par thématique**, indicateur ou date selon vos besoins
            4. Utilisez les boutons **"Tout"** pour sélectionner toutes les options d'un filtre
            5. Cliquez sur **"Tout remplir (sauf territoires)"** pour sélectionner toutes les thématiques, indicateurs et dates
            
            Les données s'afficheront automatiquement une fois les filtres sélectionnés.
            """)
            st.markdown("---")
            return
        
        # Application des filtres
        filtered_df = df.copy()
        
        # Filtrer par maille
        filtered_df = filtered_df[filtered_df['maille'] == maille]
        
        # Filtre par code territorial
        if codes_selection:
            if maille == 'Commune' and 'code_commune' in filtered_df.columns:
                filtered_df = filtered_df[filtered_df['code_commune'].astype(str).isin(codes_selection)]
            elif maille == 'EPCI' and 'code_epci' in filtered_df.columns:
                filtered_df = filtered_df[filtered_df['code_epci'].astype(str).isin(codes_selection)]
        
        # Filtre par thématique
        if thematiques_selection:
            filtered_df = filtered_df[filtered_df['thematique'].isin(thematiques_selection)]
        
        # Filtre par indicateur
        if indicateurs_selection:
            filtered_df = filtered_df[filtered_df['indicateur'].isin(indicateurs_selection)]
        
        # Filtre par date
        if dates_selection:
            filtered_df = filtered_df[filtered_df['date'].astype(str).isin(dates_selection)]
        
        # Affichage des statistiques
        st.markdown(f"**📊 {len(filtered_df)} lignes filtrées**")
        
        if len(filtered_df) == 0:
            st.warning("Aucune donnée ne correspond aux filtres sélectionnés.")
            return
        
        # Réorganiser les colonnes pour une meilleure lisibilité
        display_df = filtered_df.copy()
        
        # Définir l'ordre des colonnes préféré
        preferred_order = []
        
        # Ajouter les colonnes territoriales en fonction de la maille
        if maille == 'Commune':
            if 'libelle_commune' in display_df.columns:
                preferred_order.append('libelle_commune')
            if 'code_commune' in display_df.columns:
                preferred_order.append('code_commune')
        else:  # EPCI
            if 'libelle_epci' in display_df.columns:
                preferred_order.append('libelle_epci')
            if 'code_epci' in display_df.columns:
                preferred_order.append('code_epci')
        
        # Ajouter la maille
        preferred_order.append('maille')
        
        # Ajouter les autres colonnes importantes
        important_cols = ['date', 'thematique', 'indicateur', 'valeur', 'unite']
        for col in important_cols:
            if col in display_df.columns and col not in preferred_order:
                preferred_order.append(col)
        
        # Ajouter les colonnes restantes
        remaining_cols = [col for col in display_df.columns if col not in preferred_order]
        final_order = preferred_order + remaining_cols
        
        # Réorganiser le DataFrame
        display_df = display_df[final_order]
        
        # Affichage des données
        st.dataframe(
            display_df,
            use_container_width=True,
            height=400
        )
        
        # Téléchargement
        csv = filtered_df.to_csv(index=False, encoding='utf-8-sig')
        st.download_button(
            label="📥 Télécharger les données filtrées (CSV)",
            data=csv,
            file_name=f"donnees_{maille.lower()}_filtrees.csv",
            mime="text/csv",
            use_container_width=True
        )
        
        # Affichage des métriques
        st.markdown("---")
        st.markdown("### 📈 Statistiques des données filtrées")
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Nombre de lignes", len(filtered_df))
        with col2:
            st.metric("Nombre d'indicateurs", filtered_df['indicateur'].nunique())
        with col3:
            st.metric("Nombre de thématiques", filtered_df['thematique'].nunique())
        with col4:
            if 'date' in filtered_df.columns and len(filtered_df) > 0:
                dates_min = filtered_df['date'].min()
                dates_max = filtered_df['date'].max()
                min_str = dates_min.strftime('%Y-%m-%d') if hasattr(dates_min, 'strftime') else str(dates_min)
                max_str = dates_max.strftime('%Y-%m-%d') if hasattr(dates_max, 'strftime') else str(dates_max)
                st.metric("Période couverte", f"{min_str} à {max_str}")
            else:
                st.metric("Période couverte", "N/A")
