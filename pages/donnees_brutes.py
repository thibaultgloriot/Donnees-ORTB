import streamlit as st
import pandas as pd
import numpy as np

def show(df_communes, df_epci):
    st.title("📁 Données Brutes")
    
    # Vérifier qu'au moins un DataFrame est fourni
    if df_communes is None and df_epci is None:
        st.error("Aucune donnée fournie. Veuillez fournir au moins un DataFrame (communes ou EPCI).")
        return
    
    # Préparer les DataFrames
    if df_communes is not None and df_epci is not None:
        # Préparer les deux DataFrames séparément
        df_communes_prepared = df_communes.copy()
        df_epci_prepared = df_epci.copy()
        
        # Ajouter colonne maille
        if 'maille' not in df_communes_prepared.columns:
            df_communes_prepared['maille'] = 'Commune'
        if 'maille' not in df_epci_prepared.columns:
            df_epci_prepared['maille'] = 'EPCI'
            
        # Utiliser le DataFrame correspondant à la maille sélectionnée
        df_dict = {
            'Commune': df_communes_prepared,
            'EPCI': df_epci_prepared
        }
        
    elif df_communes is not None:
        df_communes_prepared = df_communes.copy()
        if 'maille' not in df_communes_prepared.columns:
            df_communes_prepared['maille'] = 'Commune'
        df_dict = {'Commune': df_communes_prepared}
        
    else:  # seulement df_epci
        df_epci_prepared = df_epci.copy()
        if 'maille' not in df_epci_prepared.columns:
            df_epci_prepared['maille'] = 'EPCI'
        df_dict = {'EPCI': df_epci_prepared}
    
    # Sidebar pour les filtres
    with st.sidebar:
        st.header("🔍 Filtres")
        
        st.markdown("---")
        st.info("ℹ️ Veuillez sélectionner vos filtres ci-dessous")
        st.markdown("---")
        
        # Options de maille disponibles
        maille_options = list(df_dict.keys())
        
        # Sélection de la maille avec clé statique
        maille = st.selectbox(
            "Maille territoriale",
            options=maille_options,
            index=0,
            key="maille_territoriale_select"
        )
        
        # Récupérer le DataFrame pour cette maille
        current_df = df_dict[maille]
        
        # Initialiser les sélections
        codes_selection = []
        thematiques_selection = []
        indicateurs_selection = []
        dates_selection = []
        
        # Filtrer par territoire selon la maille
        if maille == 'Commune':
            # Utiliser libelle_commune si disponible
            if 'libelle_commune' in current_df.columns:
                communes = sorted(current_df['libelle_commune'].dropna().unique().tolist())
                if communes:
                    selected_communes = st.multiselect(
                        "Sélectionner les communes",
                        options=communes,
                        default=[],
                        key="communes_select"
                    )
                    
                    # Bouton Tout pour communes
                    col_btn1, col_btn2 = st.columns(2)
                    with col_btn1:
                        if st.button("Tout", key="btn_all_communes"):
                            selected_communes = communes
                    with col_btn2:
                        if st.button("Aucun", key="btn_no_communes"):
                            selected_communes = []
                    
                    # Convertir noms en codes si besoin
                    if selected_communes and 'code_commune' in current_df.columns:
                        # Créer un mapping temporaire
                        temp_df = current_df[['code_commune', 'libelle_commune']].drop_duplicates()
                        mapping = dict(zip(temp_df['libelle_commune'], temp_df['code_commune']))
                        codes_selection = [mapping.get(name) for name in selected_communes if name in mapping]
                else:
                    st.info("Aucune commune disponible")
            elif 'code_commune' in current_df.columns:
                codes = sorted(current_df['code_commune'].dropna().unique().astype(str).tolist())
                if codes:
                    codes_selection = st.multiselect(
                        "Sélectionner les communes (codes)",
                        options=codes,
                        default=[],
                        key="communes_codes_select"
                    )
                    
                    col_btn1, col_btn2 = st.columns(2)
                    with col_btn1:
                        if st.button("Tout", key="btn_all_communes_codes"):
                            codes_selection = codes
                    with col_btn2:
                        if st.button("Aucun", key="btn_no_communes_codes"):
                            codes_selection = []
                else:
                    st.info("Aucun code de commune disponible")
                    
        elif maille == 'EPCI':
            # Utiliser libelle_epci si disponible
            if 'libelle_epci' in current_df.columns:
                epcis = sorted(current_df['libelle_epci'].dropna().unique().tolist())
                if epcis:
                    selected_epcis = st.multiselect(
                        "Sélectionner les EPCI",
                        options=epcis,
                        default=[],
                        key="epci_select"
                    )
                    
                    col_btn1, col_btn2 = st.columns(2)
                    with col_btn1:
                        if st.button("Tout", key="btn_all_epci"):
                            selected_epcis = epcis
                    with col_btn2:
                        if st.button("Aucun", key="btn_no_epci"):
                            selected_epcis = []
                    
                    # Convertir noms en codes si besoin
                    if selected_epcis and 'code_epci' in current_df.columns:
                        temp_df = current_df[['code_epci', 'libelle_epci']].drop_duplicates()
                        mapping = dict(zip(temp_df['libelle_epci'], temp_df['code_epci']))
                        codes_selection = [mapping.get(name) for name in selected_epcis if name in mapping]
                else:
                    st.info("Aucun EPCI disponible")
            elif 'code_epci' in current_df.columns:
                codes = sorted(current_df['code_epci'].dropna().unique().astype(str).tolist())
                if codes:
                    codes_selection = st.multiselect(
                        "Sélectionner les EPCI (codes)",
                        options=codes,
                        default=[],
                        key="epci_codes_select"
                    )
                    
                    col_btn1, col_btn2 = st.columns(2)
                    with col_btn1:
                        if st.button("Tout", key="btn_all_epci_codes"):
                            codes_selection = codes
                    with col_btn2:
                        if st.button("Aucun", key="btn_no_epci_codes"):
                            codes_selection = []
                else:
                    st.info("Aucun code d'EPCI disponible")
        
        # Filtrer par thématique
        if 'thematique' in current_df.columns:
            thematiques = sorted(current_df['thematique'].dropna().unique().tolist())
            if thematiques:
                thematiques_selection = st.multiselect(
                    "Sélectionner les thématiques",
                    options=thematiques,
                    default=[],
                    key="thematiques_select"
                )
                
                col_btn1, col_btn2 = st.columns(2)
                with col_btn1:
                    if st.button("Tout", key="btn_all_thematiques"):
                        thematiques_selection = thematiques
                with col_btn2:
                    if st.button("Aucun", key="btn_no_thematiques"):
                        thematiques_selection = []
            else:
                st.info("Aucune thématique disponible")
        
        # Filtrer par indicateur
        if 'indicateur' in current_df.columns:
            indicateurs = sorted(current_df['indicateur'].dropna().unique().tolist())
            if indicateurs:
                indicateurs_selection = st.multiselect(
                    "Sélectionner les indicateurs",
                    options=indicateurs,
                    default=[],
                    key="indicateurs_select"
                )
                
                col_btn1, col_btn2 = st.columns(2)
                with col_btn1:
                    if st.button("Tout", key="btn_all_indicateurs"):
                        indicateurs_selection = indicateurs
                with col_btn2:
                    if st.button("Aucun", key="btn_no_indicateurs"):
                        indicateurs_selection = []
            else:
                st.info("Aucun indicateur disponible")
        
        # Filtrer par date
        if 'date' in current_df.columns:
            dates = sorted(current_df['date'].dropna().unique())
            if len(dates) > 0:
                dates_str = [d.strftime('%Y-%m-%d') if hasattr(d, 'strftime') else str(d) for d in dates]
                dates_selection = st.multiselect(
                    "Sélectionner les dates",
                    options=dates_str,
                    default=[],
                    key="dates_select"
                )
                
                col_btn1, col_btn2 = st.columns(2)
                with col_btn1:
                    if st.button("Tout", key="btn_all_dates"):
                        dates_selection = dates_str
                with col_btn2:
                    if st.button("Aucun", key="btn_no_dates"):
                        dates_selection = []
            else:
                st.info("Aucune date disponible")
        
        st.markdown("---")
        
        # Boutons d'action
        col1, col2 = st.columns(2)
        with col1:
            if st.button("🧹 Tout remplir", type="primary", use_container_width=True, key="btn_fill_all"):
                # Le rerun sera géré par les boutons individuels
                st.info("Utilisez les boutons 'Tout' de chaque section")
        with col2:
            if st.button("🗑️ Réinitialiser", use_container_width=True, key="btn_reset"):
                # Réinitialiser les sélections
                st.session_state.clear()
                st.rerun()
    
    # Zone principale
    main_container = st.container()
    
    # Vérifier si des filtres sont sélectionnés
    has_filters = (
        (codes_selection and len(codes_selection) > 0) or
        (thematiques_selection and len(thematiques_selection) > 0) or
        (indicateurs_selection and len(indicateurs_selection) > 0) or
        (dates_selection and len(dates_selection) > 0)
    )
    
    with main_container:
        if not has_filters:
            st.markdown("---")
            st.markdown("### 📋 Instructions")
            st.info("""
            **Veuillez sélectionner les filtres à gauche de l'écran :**
            
            1. **Choisissez une maille territoriale** (Commune ou EPCI)
            2. **Sélectionnez les territoires** concernés
            3. **Filtrez par thématique**, indicateur ou date selon vos besoins
            4. Utilisez les boutons **"Tout"** pour sélectionner toutes les options d'un filtre
            5. Utilisez les boutons **"Aucun"** pour effacer la sélection
            
            Les données s'afficheront automatiquement une fois les filtres sélectionnés.
            """)
            st.markdown("---")
            return
        
        # Appliquer les filtres
        filtered_df = current_df.copy()
        
        # Filtrer par territoire
        if codes_selection and len(codes_selection) > 0:
            if maille == 'Commune' and 'code_commune' in filtered_df.columns:
                filtered_df = filtered_df[filtered_df['code_commune'].astype(str).isin([str(c) for c in codes_selection])]
            elif maille == 'EPCI' and 'code_epci' in filtered_df.columns:
                filtered_df = filtered_df[filtered_df['code_epci'].astype(str).isin([str(c) for c in codes_selection])]
        
        # Filtrer par thématique
        if thematiques_selection and len(thematiques_selection) > 0:
            filtered_df = filtered_df[filtered_df['thematique'].isin(thematiques_selection)]
        
        # Filtrer par indicateur
        if indicateurs_selection and len(indicateurs_selection) > 0:
            filtered_df = filtered_df[filtered_df['indicateur'].isin(indicateurs_selection)]
        
        # Filtrer par date
        if dates_selection and len(dates_selection) > 0:
            filtered_df = filtered_df[filtered_df['date'].astype(str).isin(dates_selection)]
        
        # Afficher les résultats
        if len(filtered_df) == 0:
            st.warning("Aucune donnée ne correspond aux filtres sélectionnés.")
            return
        
        st.markdown(f"**📊 {len(filtered_df)} lignes filtrées**")
        
        # Préparer l'affichage
        display_df = filtered_df.copy()
        
        # Réorganiser les colonnes
        col_order = []
        
        # Colonnes territoriales selon la maille
        if maille == 'Commune':
            if 'libelle_commune' in display_df.columns:
                col_order.append('libelle_commune')
            if 'code_commune' in display_df.columns:
                col_order.append('code_commune')
        else:
            if 'libelle_epci' in display_df.columns:
                col_order.append('libelle_epci')
            if 'code_epci' in display_df.columns:
                col_order.append('code_epci')
        
        # Colonnes principales
        main_cols = ['maille', 'date', 'thematique', 'indicateur', 'valeur', 'unite']
        for col in main_cols:
            if col in display_df.columns and col not in col_order:
                col_order.append(col)
        
        # Autres colonnes
        other_cols = [c for c in display_df.columns if c not in col_order]
        final_order = col_order + other_cols
        
        # Afficher le DataFrame
        st.dataframe(
            display_df[final_order],
            use_container_width=True,
            height=400
        )
        
        # Téléchargement
        csv = filtered_df.to_csv(index=False, encoding='utf-8-sig')
        st.download_button(
            label="📥 Télécharger les données (CSV)",
            data=csv,
            file_name=f"donnees_{maille.lower()}_filtrees.csv",
            mime="text/csv",
            use_container_width=True
        )
        
        # Métriques
        st.markdown("---")
        st.markdown("### 📈 Statistiques")
        
        cols = st.columns(4)
        with cols[0]:
            st.metric("Lignes", len(filtered_df))
        with cols[1]:
            st.metric("Indicateurs", filtered_df['indicateur'].nunique())
        with cols[2]:
            st.metric("Thématiques", filtered_df['thematique'].nunique())
        with cols[3]:
            if 'date' in filtered_df.columns and len(filtered_df) > 0:
                date_min = filtered_df['date'].min()
                date_max = filtered_df['date'].max()
                min_str = date_min.strftime('%d/%m/%Y') if hasattr(date_min, 'strftime') else str(date_min)
                max_str = date_max.strftime('%d/%m/%Y') if hasattr(date_max, 'strftime') else str(date_max)
                st.metric("Période", f"{min_str} à {max_str}")
