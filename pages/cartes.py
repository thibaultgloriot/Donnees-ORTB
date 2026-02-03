import streamlit as st
import pandas as pd
import json
import requests
import plotly.express as px
from datetime import datetime
import numpy as np

@st.cache_data
def load_geojson(filepath):
    with open(filepath, 'r') as f:
        return json.load(f)

@st.cache_data
def load_indicator_sources():
    """Charge les sources des indicateurs depuis le fichier CSV"""
    try:
        sources_df = pd.read_csv("data/columns_indicateurs.csv", sep=";")
        # Créer un dictionnaire indicateur -> source
        # Utiliser 'Nouveau_nom_indicateur' si disponible, sinon 'Indicateur'
        if 'Nouveau_nom_indicateur' in sources_df.columns:
            sources_dict = dict(zip(sources_df['Nouveau_nom_indicateur'], sources_df.get('Source', '')))
        else:
            sources_dict = dict(zip(sources_df['Indicateur'], sources_df.get('Source', '')))
        return sources_dict
    except Exception as e:
        st.warning(f"Impossible de charger les sources des indicateurs: {e}")
        return {}

def get_scale_options(df, column):
    """Calcule les différentes échelles de représentation"""
    values = df[column].dropna()
    
    if len(values) == 0:
        return None, None, None
    
    # Option 1: Échelle linéaire (min à max)
    linear_scale = [values.min(), values.max()]
    
    # Option 2: Échelle avec percentiles (5ème à 95ème percentile)
    percentile_scale = [np.percentile(values, 5), np.percentile(values, 95)]
    
    # Option 3: Échelle avec écart-type (moyenne ± 2 écarts-types)
    mean_val = values.mean()
    std_val = values.std()
    std_scale = [max(values.min(), mean_val - 2*std_val), 
                 min(values.max(), mean_val + 2*std_val)]
    
    return linear_scale, percentile_scale, std_scale

def get_common_themes(df, epci_df):
    """Récupère les thématiques communes entre les deux échelles"""
    themes_communes = set()
    themes_epci = set()
    
    if df is not None and 'thematique' in df.columns:
        themes_communes = set(df['thematique'].dropna().unique())
    
    if epci_df is not None and 'thematique' in epci_df.columns:
        themes_epci = set(epci_df['thematique'].dropna().unique())
    
    # Retourne les thématiques communes et celles spécifiques à chaque échelle
    themes_communs = themes_communes.intersection(themes_epci)
    
    # Si pas de thématiques communes, on utilise celles de l'échelle sélectionnée
    if not themes_communs:
        return sorted(themes_communes) if themes_communes else sorted(themes_epci)
    
    return sorted(themes_communs)

def show(df, epci_df):
    # Charger les sources des indicateurs
    indicator_sources = load_indicator_sources()
    
    st.title("📊 Visualisation Cartographique des indicateurs de la Planification Ecologique")
    
    # Obtenir les thématiques communes
    common_themes = get_common_themes(df, epci_df)
    
    col1, col2, col3, col4 = st.columns([1, 0.7, 1.5, 0.6])
    
    with col1:
        echelle = st.radio(
            "Échelle géographique",
            options=["Commune", "EPCI"],
            horizontal=True,
            key="carte_radio_echelle"
        )
    
    with col2:
        if len(common_themes) > 0:
            selected_thematique = st.selectbox(
                "Thématique", 
                ["Toutes"] + list(common_themes),
                key="carte_select_thematique"
            )
        else:
            selected_thematique = "Toutes"
            st.info("Aucune thématique disponible")
    
    with col3:
        # Filtrer les indicateurs en fonction de l'échelle et de la thématique
        if echelle == "Commune":
            df_to_use = df
        else:
            df_to_use = epci_df if epci_df is not None else pd.DataFrame()
        
        # Filtrer par thématique si nécessaire
        if selected_thematique != "Toutes" and 'thematique' in df_to_use.columns:
            filtered_df = df_to_use[df_to_use['thematique'] == selected_thematique]
            indicateurs = filtered_df['indicateur'].unique()
        else:
            indicateurs = df_to_use['indicateur'].unique() if not df_to_use.empty else []
        
        selected_indicateur = st.selectbox(
            "Indicateur", 
            indicateurs if len(indicateurs) > 0 else ["Aucun indicateur disponible"],
            key="carte_select_indicateur"
        )
    
    with col4:
        # Gérer les dates disponibles
        if echelle == "Commune":
            df_to_use = df
        else:
            df_to_use = epci_df if epci_df is not None else df
        
        if not df_to_use.empty and selected_indicateur != "Aucun indicateur disponible":
            dates_disponibles = sorted(
                df_to_use[df_to_use['indicateur'] == selected_indicateur]['date'].unique()
            )
            
            if len(dates_disponibles) > 0:
                dates_options = [date.strftime('%d/%m/%Y') for date in dates_disponibles]
                selected_date_str = st.selectbox(
                    "Sélectionnez la date",
                    options=dates_options,
                    index=len(dates_options)-1,
                    key="carte_select_date"
                )
                selected_date = datetime.strptime(selected_date_str, '%d/%m/%Y')
            else:
                st.warning("Aucune date disponible pour cet indicateur")
                return
        else:
            st.warning("Veuillez sélectionner un indicateur")
            return
    
    # Nouvelle section pour les options d'échelle
    st.markdown("---")
    col_scale1, col_scale2, col_scale3 = st.columns(3)
    
    with col_scale1:
        scale_options = st.selectbox(
            "Échelle de couleur",
            options=["Blues", "Greens", "Darkmint", "ice", "Viridis", "Plasma"],
            key="carte_select_scale"
        )
    
    with col_scale2:
        stat_scale = st.selectbox(
            "Répartition statistique",
            options=[
                "Échelle complète (min-max)",
                "Percentiles (5-95%)", 
                "Moyenne ± 2 écarts-types"
            ],
            key="carte_select_stat_scale"
        )
    
    with col_scale3:
        reverse_scale = st.checkbox(
            "Inverser l'échelle de couleur",
            key="carte_checkbox_reverse"
        )
    
    # Filtrage des données selon l'échelle
    if echelle == "Commune":
        filtered_df = df[
            (df['indicateur'] == selected_indicateur) & 
            (df['date'] == selected_date)].copy()
        
        # Calcul des échelles statistiques
        if len(filtered_df) > 0:
            linear_scale, percentile_scale, std_scale = get_scale_options(filtered_df, 'valeur')
            
            # Appliquer l'échelle statistique sélectionnée
            if stat_scale == "Échelle complète (min-max)" and linear_scale:
                range_color = linear_scale
                range_note = f"min={linear_scale[0]:.2f}, max={linear_scale[1]:.2f}"
            elif stat_scale == "Percentiles (5-95%)" and percentile_scale:
                range_color = percentile_scale
                range_note = f"5e percentile={percentile_scale[0]:.2f}, 95e percentile={percentile_scale[1]:.2f}"
            elif stat_scale == "Moyenne ± 2 écarts-types" and std_scale:
                range_color = std_scale
                range_note = f"moyenne ± 2σ: [{std_scale[0]:.2f}, {std_scale[1]:.2f}]"
            else:
                range_color = None
                range_note = "Échelle automatique"
        else:
            range_color = None
            range_note = "Pas de données"
        
        # Inverser l'échelle si demandé
        color_scale = scale_options
        if reverse_scale:
            color_scale = color_scale + "_r"
        
        # Récupérer le GeoJSON
        communes_geojson = load_geojson("data/communes_simple.geojson")
        
        # Ajout de la source
        source_text = ""
        if selected_indicateur in indicator_sources:
            source_val = indicator_sources[selected_indicateur]
            if pd.notna(source_val) and str(source_val).strip():
                source_text = f"<br><sub>Source : {source_val}</sub>"
        
        # Créer la carte
        fig = px.choropleth(
            filtered_df,
            geojson=communes_geojson,
            locations='code_commune',
            featureidkey="properties.code",
            color='valeur',
            hover_name='libelle_commune',
            hover_data={'valeur': True, 'code_commune': False},
            color_continuous_scale=color_scale,
            range_color=range_color,
            scope="europe",
            center={"lat": 46.8, "lon": -2.3},
            title=f"{selected_indicateur} à l'échelle communale pour la date {selected_date_str}<br><sub>{range_note}</sub>{source_text}")
        
    else:  # EPCI
        filtered_df = epci_df[
            (epci_df['indicateur'] == selected_indicateur) & 
            (epci_df['date'] == selected_date)].copy()
        
        filtered_df['code'] = filtered_df['code_epci']
        
        # Calcul des échelles statistiques
        if len(filtered_df) > 0:
            linear_scale, percentile_scale, std_scale = get_scale_options(filtered_df, 'valeur')
            
            # Appliquer l'échelle statistique sélectionnée
            if stat_scale == "Échelle complète (min-max)" and linear_scale:
                range_color = linear_scale
                range_note = f"min={linear_scale[0]:.2f}, max={linear_scale[1]:.2f}"
            elif stat_scale == "Percentiles (5-95%)" and percentile_scale:
                range_color = percentile_scale
                range_note = f"5e percentile={percentile_scale[0]:.2f}, 95e percentile={percentile_scale[1]:.2f}"
            elif stat_scale == "Moyenne ± 2 écarts-types" and std_scale:
                range_color = std_scale
                range_note = f"moyenne ± 2σ: [{std_scale[0]:.2f}, {std_scale[1]:.2f}]"
            else:
                range_color = None
                range_note = "Échelle automatique"
        else:
            range_color = None
            range_note = "Pas de données"
        
        # Inverser l'échelle si demandé
        color_scale = scale_options
        if reverse_scale:
            color_scale = color_scale + "_r"
        
        # Récupérer le GeoJSON
        epci_geojson = load_geojson("data/epci_simple.geojson")
        
        # Ajout de la source
        source_text = ""
        if selected_indicateur in indicator_sources:
            source_val = indicator_sources[selected_indicateur]
            if pd.notna(source_val) and str(source_val).strip():
                source_text = f"<br><sub>Source : {source_val}</sub>"
        
        # Créer la carte
        fig = px.choropleth(
            filtered_df,
            geojson=epci_geojson,
            locations='code_epci',
            featureidkey="properties.code",
            color='valeur',
            hover_name='libelle_epci',
            hover_data={'valeur': True, 'code_epci': False},
            color_continuous_scale=color_scale,
            range_color=range_color,
            scope="europe",
            center={"lat": 46.8, "lon": -2.3},
            title=f"{selected_indicateur} à l'échelle EPCI pour la date {selected_date_str}<br><sub>{range_note}</sub>{source_text}")
    
    fig.update_geos(fitbounds="locations", visible=False)
    fig.update_layout(width=1000, height=1000)
    st.plotly_chart(fig, use_container_width=True)
    
    # Afficher un résumé des statistiques
    if len(filtered_df) > 0:
        with st.expander("📈 Statistiques descriptives"):
            col_stat1, col_stat2, col_stat3 = st.columns(3)
            with col_stat1:
                st.metric("Moyenne", f"{filtered_df['valeur'].mean():.2f}")
            with col_stat2:
                st.metric("Médiane", f"{filtered_df['valeur'].median():.2f}")
            with col_stat3:
                st.metric("Écart-type", f"{filtered_df['valeur'].std():.2f}")
    
    # Données sous la carte
    st.subheader("Données affichées")
    if echelle == "Commune":
        display_df = filtered_df[['libelle_commune', 'code_commune', 'valeur', 'date']].copy()
    else:
        display_df = filtered_df[['libelle_epci', 'code_epci', 'valeur', 'date']].copy()
    
    display_df['date'] = display_df['date'].dt.strftime('%d/%m/%Y')
    
    st.dataframe(display_df, use_container_width=True, key="carte_dataframe")
