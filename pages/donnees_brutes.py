import streamlit as st
import pandas as pd
import numpy as np

# Configuration des échelles
ECHELLES_CONFIG = {
    'communes': {
        'label': 'Commune',
        'code_col': 'code_commune',
        'libelle_col': 'libelle_commune'
    },
    'epci': {
        'label': 'EPCI',
        'code_col': 'code_epci',
        'libelle_col': 'libelle_epci'
    },
    'departements': {
        'label': 'Département',
        'code_col': 'code_departement',
        'libelle_col': 'libelle_departement'
    },
    'regions': {
        'label': 'Région',
        'code_col': 'code_region',
        'libelle_col': 'libelle_region'
    }
}

def show(data):
    st.title("📁 Données Brutes")
    
    # Vérifier qu'au moins un DataFrame est fourni
    available_echelles = {}
    for key, config in ECHELLES_CONFIG.items():
        if data.get(key) is not None and not data[key].empty:
            available_echelles[key] = config
    
    if not available_echelles:
        st.error("Aucune donnée disponible")
        return
    
    # Sidebar pour les filtres
    with st.sidebar:
        st.header("🔍 Filtres")
        
        st.markdown("---")
        st.info("ℹ️ Veuillez sélectionner vos filtres ci-dessous")
        st.markdown("---")
        
        # Sélection de la maille
        echelle_options = list(available_echelles.keys())
        echelle_labels = [config['label'] for config in available_echelles.values()]
        
        selected_echelle_label = st.selectbox(
            "Maille territoriale",
            options=echelle_labels,
            index=0,
            key="maille_territoriale_select"
        )
        
        # Trouver la clé correspondante
        echelle = None
        for key, config in available_echelles.items():
            if config['label'] == selected_echelle_label:
                echelle = key
                break
        
        config = ECHELLES_CONFIG[echelle]
        current_df = data[echelle].copy()
        code_col = config['code_col']
        libelle_col = config['libelle_col']
        
        # Initialiser les sélections
        codes_selection = []
        thematiques_selection = []
        indicateurs_selection = []
        dates_selection = []
        
        # Filtrer par territoire
        if libelle_col in current_df.columns:
            territoires = sorted(current_df[libelle_col].dropna().unique().tolist())
            if territoires:
                selected_territoires = st.multiselect(
                    f"Sélectionner les {config['label'].lower()}s",
                    options=territoires,
                    default=[],
                    key="territoires_select"
                )
                
                col_btn1, col_btn2 = st.columns(2)
                with col_btn1:
                    if st.button("Tout", key="btn_all_territoires"):
                        selected_territoires = territoires
                with col_btn2:
                    if st.button("Aucun", key="btn_no_territoires"):
                        selected_territoires = []
                
                if selected_territoires and code_col in current_df.columns:
                    temp_df = current_df[[code_col, libelle_col]].drop_duplicates()
                    mapping = dict(zip(temp_df[libelle_col], temp_df[code_col]))
                    codes_selection = [mapping.get(name) for name in selected_territoires if name in mapping]
            else:
                st.info(f"Aucun {config['label'].lower()} disponible")
        
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
        
        col1, col2 = st.columns(2)
        with col1:
            if st.button("🧹 Tout remplir", type="primary", use_container_width=True, key="btn_fill_all"):
                st.info("Utilisez les boutons 'Tout' de chaque section")
        with col2:
            if st.button("🗑️ Réinitialiser", use_container_width=True, key="btn_reset"):
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
            st.info(f"""
            **Veuillez sélectionner les filtres à gauche de l'écran :**
            
            1. **Choisissez une maille territoriale** ({', '.join(echelle_labels)})
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
            filtered_df = filtered_df[filtered_df[code_col].astype(str).isin([str(c) for c in codes_selection])]
        
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
        
        # Colonnes territoriales
        if libelle_col in display_df.columns:
            col_order.append(libelle_col)
        if code_col in display_df.columns:
            col_order.append(code_col)
        
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
            file_name=f"donnees_{echelle}_filtrees.csv",
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