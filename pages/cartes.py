import streamlit as st
import pandas as pd
import json
import plotly.express as px
from datetime import datetime
import numpy as np
import re
from collections import defaultdict

# ============================================================================
# PARAMÈTRES DE CONFIGURATION
# ============================================================================

PRECISION_DECIMALES = 1
SEUIL_CENT = 0.01

# ============================================================================
# FONCTIONS DE CHARGEMENT DES DONNÉES
# ============================================================================

@st.cache_data
def load_geojson(filepath):
    """Charge un fichier GeoJSON"""
    with open(filepath, 'r') as f:
        return json.load(f)

@st.cache_data
def load_group_names():
    """Charge les noms des groupes depuis le fichier CSV"""
    try:
        groups_df = pd.read_csv("data/denomination_groupes.csv", sep=",")
        group_names = dict(zip(groups_df['Groupe'].astype(str), groups_df['nom_groupe']))
        return group_names
    except Exception as e:
        st.warning(f"Fichier denomination_groupes.csv non trouvé ou invalide: {e}")
        return {}

@st.cache_data
def load_indicator_sources_and_groups():
    """Charge les sources, descriptions et groupes des indicateurs depuis le fichier CSV"""
    try:
        sources_df = pd.read_csv("data/columns_indicateurs.csv", sep=",")
        
        if 'Nouveau_nom_indicateur' in sources_df.columns:
            indicator_col = 'Nouveau_nom_indicateur'
        else:
            indicator_col = 'Indicateur'
        
        # Sources
        sources_dict = dict(zip(sources_df[indicator_col], sources_df.get('Source', '')))
        
        # Descriptions
        descriptions_dict = {}
        if 'Description' in sources_df.columns:
            # Ne garder que les descriptions non nulles et non vides
            desc_df = sources_df[sources_df['Description'].notna() & (sources_df['Description'] != '')]
            descriptions_dict = dict(zip(desc_df[indicator_col], desc_df['Description']))
        
        # Groupes
        groups_dict = {}
        indicator_to_group = {}
        group_names = load_group_names()
        
        # Traitement des thématiques multiples - OPTIMISÉ
        thematiques_dict = {}
        if 'Thématique' in sources_df.columns:
            for _, row in sources_df.iterrows():
                if pd.notna(row['Thématique']) and row['Thématique'] != '':
                    # Split par ; et nettoyer
                    themes = [t.strip() for t in str(row['Thématique']).split(';') if t.strip()]
                    if themes:  # Ne garder que si la liste n'est pas vide
                        thematiques_dict[row[indicator_col]] = themes
        
        if 'Groupe' in sources_df.columns:
            grouped_indicators = sources_df[sources_df['Groupe'].notna() & (sources_df['Groupe'] != 0)]
            
            for groupe_value in grouped_indicators['Groupe'].unique():
                groupe_value_str = str(groupe_value)
                group_indicators = grouped_indicators[grouped_indicators['Groupe'] == groupe_value][indicator_col].tolist()
                
                if len(group_indicators) >= 1:
                    display_name = group_names.get(groupe_value_str, f"Groupe {groupe_value}")
                    display_name = re.sub(r'\s+', ' ', display_name).strip()
                    
                    groups_dict[groupe_value_str] = {
                        'indicateurs': group_indicators,
                        'display_name': display_name,
                        'original_value': groupe_value
                    }
                    
                    for ind in group_indicators:
                        specific_value = extract_specific_value(ind, display_name)
                        indicator_to_group[ind] = {
                            'groupe': groupe_value_str,
                            'display_name': display_name,
                            'specific_value': specific_value,
                            'original_value': groupe_value
                        }
        
        return sources_dict, groups_dict, indicator_to_group, descriptions_dict, thematiques_dict
        
    except Exception as e:
        st.warning(f"Impossible de charger les sources et groupes des indicateurs: {e}")
        return {}, {}, {}, {}, {}

def extract_specific_value(indicator_name, group_name):
    """Extrait la valeur spécifique d'un indicateur en enlevant le nom du groupe"""
    group_for_search = re.sub(r'\([^)]*\)', '', group_name).strip()
    group_for_search = re.sub(r'\s+', ' ', group_for_search)
    
    if group_for_search in indicator_name:
        specific = indicator_name.split(group_for_search, 1)[-1].strip()
    else:
        indicator_lower = indicator_name.lower()
        group_lower = group_for_search.lower()
        
        if group_lower in indicator_lower:
            start_pos = indicator_lower.find(group_lower)
            specific = indicator_name[start_pos + len(group_for_search):].strip()
        else:
            paren_match = re.search(r'\(([^)]+)\)', indicator_name)
            if paren_match:
                specific = paren_match.group(1).strip()
            else:
                words = indicator_name.split()
                specific = words[-1] if words else "?"
    
    specific = re.sub(r'^[\(\s\)]+|[\(\s\)]+$', '', specific)
    specific = re.sub(r'\(', '', specific)
    specific = re.sub(r'\)', '', specific)
    specific = re.sub(r'%', '', specific)
    specific = re.sub(r'\s+', ' ', specific)
    
    if len(specific) > 30:
        short_match = re.search(r'([A-Za-z0-9\s]+)$', specific)
        if short_match:
            specific = short_match.group(1).strip()
        else:
            specific = specific[:30] + "..."
    
    if not specific or specific == '':
        paren_match = re.search(r'\(([^)]+)\)', indicator_name)
        if paren_match:
            specific = paren_match.group(1).strip()
        else:
            specific = indicator_name.split()[-1] if indicator_name.split() else "?"
    
    return specific.strip()

# ============================================================================
# FONCTIONS DE NORMALISATION
# ============================================================================

@st.cache_data
def load_menages_data():
    """Charge les données de ménages pour les années disponibles"""
    try:
        menages_df = pd.read_csv("data/final_df_communes.csv")
        menages_df['date'] = pd.to_datetime(menages_df['date'], format='%d/%m/%Y', errors='coerce')
        menages_df['code_commune'] = menages_df['code_commune'].astype(str)
        
        # Filtrer les indicateurs de ménages
        menages_indicateurs = menages_df[menages_df['indicateur'].str.contains('ménages', case=False)]
        
        if menages_indicateurs.empty:
            return None, None
        
        # Créer un mapping année -> date
        menages_df_filtered = menages_indicateurs[['date', 'code_commune', 'valeur']].copy()
        menages_df_filtered['annee'] = menages_df_filtered['date'].dt.year
        
        # Garder une valeur par année pour chaque commune
        menages_by_year = menages_df_filtered.groupby(['code_commune', 'annee'])['valeur'].mean().reset_index()
        
        return menages_by_year, menages_df_filtered
    
    except Exception as e:
        st.warning(f"Impossible de charger les données de ménages: {e}")
        return None, None

def get_menages_for_date(menages_data, code, date_reference):
    """Récupère le nombre de ménages pour une date donnée (valeur précédente)"""
    if menages_data is None:
        return None, None
    
    annee = date_reference.year
    
    # Années disponibles
    annees_disponibles = [2012, 2017, 2023]
    
    # Trouver l'année la plus proche (précédente)
    annee_utilisee = None
    for a in sorted(annees_disponibles):
        if a <= annee:
            annee_utilisee = a
    
    if annee_utilisee is None:
        annee_utilisee = annees_disponibles[0]
    
    # Filtrer les données
    menage_row = menages_data[(menages_data['code_commune'] == code) & 
                              (menages_data['annee'] == annee_utilisee)]
    
    if not menage_row.empty:
        return menage_row['valeur'].values[0], annee_utilisee
    
    return None, None

def normalize_by_menages(df, code_col, date_col, menages_data):
    """Normalise les valeurs par nombre de ménages"""
    if menages_data is None:
        return df, None
    
    df_normalized = df.copy()
    menages_notes = []
    
    # Récupérer les ménages pour chaque ligne
    menages_values = []
    for idx, row in df_normalized.iterrows():
        code = str(row[code_col])
        date = row[date_col]
        
        menage_val, annee_utilisee = get_menages_for_date(menages_data, code, date)
        
        if menage_val is not None and menage_val > 0:
            menages_values.append(menage_val)
            menages_notes.append(f"{annee_utilisee}")
        else:
            menages_values.append(np.nan)
            menages_notes.append("N/A")
    
    df_normalized['menages'] = menages_values
    df_normalized['annee_menages'] = menages_notes
    df_normalized['valeur_normalisee'] = df_normalized['valeur'] / df_normalized['menages']
    
    return df_normalized, menages_notes

def get_surface_population_data(df, echelle, date_reference):
    """Récupère les données de surface et population"""
    surface_df = None
    population_df = None
    
    if df is not None and not df.empty:
        # Surface (valeur unique - la plus récente)
        surface_data = df[df['indicateur'] == "Surface totale du territoire (ha)"].copy()
        if not surface_data.empty:
            surface_df = surface_data.sort_values('date').groupby(
                ['code_commune'] if echelle == "Commune" else ['code_epci']
            ).last().reset_index()
        
        # Population (valeur la plus proche de la date de référence)
        population_data = df[df['indicateur'] == "Nombre d'habitants du territoire"].copy()
        if not population_data.empty:
            population_dfs = []
            code_col = 'code_commune' if echelle == "Commune" else 'code_epci'
            
            for code, group in population_data.groupby(code_col):
                dates = group['date'].values
                mask = dates <= np.datetime64(date_reference)
                
                if mask.any():
                    idx = np.where(mask)[0][-1]
                else:
                    idx = 0
                
                population_dfs.append(group.iloc[[idx]])
            
            if population_dfs:
                population_df = pd.concat(population_dfs, ignore_index=True)
                population_df['valeur'] = population_df['valeur'] / 1000
    
    return surface_df, population_df

def normalize_by_surface(df, code_col, surface_df):
    """Normalise les valeurs par surface"""
    df_normalized = df.copy()
    df_normalized = df_normalized.merge(
        surface_df[[code_col, 'valeur']].rename(columns={'valeur': 'surface_ha'}),
        on=code_col, how='left'
    )
    df_normalized['valeur_normalisee'] = df_normalized['valeur'] / df_normalized['surface_ha']
    return df_normalized

def normalize_by_population(df, code_col, population_df):
    """Normalise les valeurs par population"""
    df_normalized = df.copy()
    df_normalized = df_normalized.merge(
        population_df[[code_col, 'valeur']].rename(columns={'valeur': 'population_milliers'}),
        on=code_col, how='left'
    )
    df_normalized['valeur_normalisee'] = df_normalized['valeur'] / df_normalized['population_milliers']
    return df_normalized

def get_scale_options(df, column):
    """Calcule les différentes échelles de représentation"""
    values = df[column].dropna()
    
    if len(values) == 0:
        return None, None, None
    
    linear_scale = [values.min(), values.max()]
    percentile_scale = [np.percentile(values, 5), np.percentile(values, 95)]
    
    mean_val = values.mean()
    std_val = values.std()
    std_scale = [max(values.min(), mean_val - 2*std_val), 
                 min(values.max(), mean_val + 2*std_val)]
    
    return linear_scale, percentile_scale, std_scale

def get_common_themes(df, epci_df, thematiques_dict):
    """Récupère les thématiques communes en gérant les multiples thématiques"""
    themes_communes = set()
    
    # Pour chaque DataFrame, récupérer les thématiques
    for df_temp in [df, epci_df]:
        if df_temp is not None and 'indicateur' in df_temp.columns:
            for indicateur in df_temp['indicateur'].unique():
                if indicateur in thematiques_dict:
                    themes_communes.update(thematiques_dict[indicateur])
    
    return sorted(themes_communes) if themes_communes else []

# ============================================================================
# FONCTIONS DE GESTION DES GROUPES - OPTIMISÉES
# ============================================================================

def get_available_indicators_with_groups(df, groups_dict, indicator_to_group):
    """Récupère la liste des indicateurs disponibles"""
    all_indicators = df['indicateur'].unique().tolist()
    indicateurs_exclus = ["Surface totale du territoire (ha)", "Nombre d'habitants du territoire"]
    
    available_indicators = []
    
    # Ajouter les groupes
    for groupe_value, groupe_info in groups_dict.items():
        indicateurs_presents = [ind for ind in groupe_info['indicateurs'] if ind in all_indicators]
        
        if len(indicateurs_presents) >= 1:
            available_indicators.append({
                'nom': f"📊 {groupe_info['display_name']} ({len(indicateurs_presents)} indicateurs)",
                'type': 'groupe',
                'groupe_value': groupe_value,
                'groupe_nom': groupe_info['display_name'],
                'indicateurs': indicateurs_presents
            })
    
    # Ajouter les indicateurs individuels
    for indicator in all_indicators:
        if indicator in indicateurs_exclus:
            continue
            
        if indicator not in indicator_to_group:
            available_indicators.append({
                'nom': f"📈 {indicator}",
                'type': 'individuel',
                'indicateur_nom': indicator
            })
    
    available_indicators.sort(key=lambda x: x['nom'])
    return available_indicators

def get_group_selection_interface(groupe_info, indicator_to_group, default_select_all=True):
    """Interface avec multiselect pour sélectionner les indicateurs du groupe"""
    indicator_options = []
    display_to_indicator = {}
    display_counts = defaultdict(int)
    
    # Premier passage pour compter les doublons
    for ind in groupe_info['indicateurs']:
        if ind in indicator_to_group:
            specific_value = indicator_to_group[ind].get('specific_value', '?')
            display_counts[specific_value] += 1
    
    # Deuxième passage pour créer les options
    for ind in groupe_info['indicateurs']:
        if ind in indicator_to_group:
            specific_value = indicator_to_group[ind].get('specific_value', '?')
            
            # Si la valeur est un doublon, ajouter un contexte
            if display_counts[specific_value] > 1:
                context_match = re.search(r'\(([^)]+)\)', ind)
                if context_match:
                    context = context_match.group(1)
                    display = f"{specific_value} ({context})"
                else:
                    words = ind.split()
                    context = words[-1] if words else ""
                    display = f"{specific_value} ({context})" if context != specific_value else specific_value
            else:
                display = specific_value
            
            indicator_options.append({
                'indicateur': ind,
                'display': display
            })
            display_to_indicator[display] = ind
    
    # Afficher le titre du groupe
    st.markdown(f"**{groupe_info['groupe_nom']}**")
    
    # Options d'affichage
    options_display = [opt['display'] for opt in indicator_options]
    
    # Multiselect avec tous les éléments sélectionnés par défaut
    selected_displays = st.multiselect(
        "Sélectionnez les valeurs à additionner",
        options=options_display,
        default=options_display if default_select_all else [],
        key=f"multiselect_{groupe_info['groupe_value']}"
    )
    
    # Convertir les displays sélectionnés en noms d'indicateurs
    selected_indicators = []
    for disp in selected_displays:
        if disp in display_to_indicator:
            selected_indicators.append(display_to_indicator[disp])
    
    # Afficher le compteur
    st.caption(f"{len(selected_indicators)}/{len(indicator_options)} valeurs sélectionnées")
    
    return selected_indicators

def get_group_data(df, groupe_info, selected_indicators, code_col, selected_date, normalisation_option, surface_df, population_df):
    """Récupère et agrège les données pour les indicateurs sélectionnés du groupe"""
    if not selected_indicators:
        return None
    
    # Filtrer les données
    group_data = df[
        (df['indicateur'].isin(selected_indicators)) & 
        (df['date'] == selected_date)
    ].copy()
    
    if group_data.empty:
        return None
    
    # Pivoter et sommer
    pivot_data = group_data.pivot_table(
        index=[code_col],
        columns='indicateur',
        values='valeur',
        aggfunc='first'
    ).reset_index()
    
    pivot_data = pivot_data.fillna(0)
    
    # Calculer la somme
    pivot_data['valeur_somme'] = pivot_data[selected_indicators].sum(axis=1)
    
    # Vérifier si ce sont probablement des pourcentages qui devraient totaliser 100
    if (pivot_data[selected_indicators].max().max() <= 105 and
        pivot_data[selected_indicators].min().min() >= -5):
        
        diff_avec_100 = (pivot_data['valeur_somme'] - 100).abs()
        pivot_data.loc[diff_avec_100 < SEUIL_CENT, 'valeur_somme'] = 100.0
    
    # Créer le résultat
    result_df = pivot_data[[code_col, 'valeur_somme']].copy()
    result_df['date'] = selected_date
    result_df['valeur'] = result_df['valeur_somme']
    
    # Ajouter les libellés
    libelle_col = 'libelle_commune' if 'commune' in code_col else 'libelle_epci'
    if libelle_col in group_data.columns:
        libelles = group_data.groupby(code_col)[libelle_col].first().reset_index()
        result_df = result_df.merge(libelles, on=code_col, how='left')
    else:
        libelle_df = df[df['date'] == selected_date][[code_col, libelle_col]].drop_duplicates()
        result_df = result_df.merge(libelle_df, on=code_col, how='left')
    
    # Normalisation
    if normalisation_option == "Par surface (ha)" and surface_df is not None:
        result_df = normalize_by_surface(result_df, code_col, surface_df)
    elif normalisation_option == "Par population (1000 hab.)" and population_df is not None:
        result_df = normalize_by_population(result_df, code_col, population_df)
    
    return result_df

# ============================================================================
# FONCTION D'AFFICHAGE DE LA DESCRIPTION
# ============================================================================

def show_description(descriptions_dict, indicator_name, indicator_type, selected_indicators=None, 
                    normalisation_type=None, menages_note=None):
    """Affiche la description de l'indicateur en préservant les sauts de ligne"""
    
    def format_description(text):
        """Formate la description pour préserver les sauts de ligne"""
        if not text or pd.isna(text):
            return ""
        text = str(text)
        # Remplacer les sauts de ligne par deux espaces + saut de ligne (format markdown)
        formatted = text.replace('\n', '  \n')
        return formatted
    
    if indicator_type == 'individuel':
        description = descriptions_dict.get(indicator_name)
        if description and pd.notna(description) and description != '':
            st.markdown("---")
            st.markdown("### 📝 Description de l'indicateur")
            formatted_desc = format_description(description)
            st.markdown(formatted_desc)
            
            # Ajouter la note de normalisation si présente
            if normalisation_type == "Par ménages" and menages_note:
                st.markdown("---")
                st.warning(f"⚠️ {menages_note}")
    
    elif indicator_type == 'groupe' and selected_indicators:
        st.markdown("---")
        st.markdown("### 📝 Descriptions des indicateurs sélectionnés")
        
        for ind in selected_indicators:
            description = descriptions_dict.get(ind)
            if description and pd.notna(description) and description != '':
                with st.expander(f"**{ind}**"):
                    formatted_desc = format_description(description)
                    st.markdown(formatted_desc)
        
        # Ajouter la note de normalisation si présente
        if normalisation_type == "Par ménages" and menages_note:
            st.markdown("---")
            st.warning(f"⚠️ {menages_note}")

# ============================================================================
# FONCTIONS D'AMÉLIORATION DU TITRE ET DE L'AFFICHAGE
# ============================================================================

def format_group_title(selected_indicators, indicator_to_group, groupe_nom):
    """Formate le titre pour les indicateurs groupés avec 'et' si nécessaire"""
    if not selected_indicators:
        return groupe_nom
    
    # Récupérer les valeurs spécifiques pour chaque indicateur sélectionné
    values = []
    for ind in selected_indicators:
        if ind in indicator_to_group:
            specific_value = indicator_to_group[ind].get('specific_value', '')
            if specific_value and specific_value != '?':
                values.append(specific_value)
    
    if not values:
        return groupe_nom
    
    # Si une seule valeur, retourner le nom complet
    if len(values) == 1:
        return f"{groupe_nom} ({values[0]})"
    
    # Si plusieurs valeurs, les lier avec "et"
    if len(values) == 2:
        return f"{groupe_nom} ({values[0]} et {values[1]})"
    
    # Si plus de 2 valeurs, lier les dernières avec "et"
    if len(values) > 2:
        last_value = values[-1]
        first_values = values[:-1]
        return f"{groupe_nom} ({', '.join(first_values)} et {last_value})"
    
    return groupe_nom

# ============================================================================
# FONCTION DE SÉLECTION AUTOMATIQUE DE L'ÉCHELLE
# ============================================================================

def suggest_scale(values):
    """
    Suggère automatiquement la meilleure échelle de représentation
    basée sur la distribution des données.
    """
    if len(values) < 5:
        return "Min-Max"  # Peu de données -> Min-Max
    
    # Calculer les métriques
    mean_val = np.mean(values)
    std_val = np.std(values)
    min_val = np.min(values)
    max_val = np.max(values)
    q1 = np.percentile(values, 25)
    q3 = np.percentile(values, 75)
    iqr = q3 - q1
    
    # Détecter les outliers (valeurs aberrantes)
    # Utiliser la règle de l'IQR: valeur < Q1 - 1.5*IQR ou > Q3 + 1.5*IQR
    outliers_low = values[values < q1 - 1.5 * iqr]
    outliers_high = values[values > q3 + 1.5 * iqr]
    outlier_count = len(outliers_low) + len(outliers_high)
    outlier_ratio = outlier_count / len(values)
    
    # Détecter si les données sont fortement asymétriques
    skewness = (mean_val - np.median(values)) / std_val if std_val > 0 else 0
    
    # Décision
    # 1. Si beaucoup d'outliers > 5% des données -> utiliser Percentiles
    if outlier_ratio > 0.05:
        return "Percentiles"
    
    # 2. Si asymétrie forte > 0.5 ou < -0.5
    if abs(skewness) > 0.5:
        return "Percentiles"
    
    # 3. Si l'écart-type est très grand par rapport à la moyenne (CV > 0.5)
    cv = std_val / mean_val if mean_val != 0 else 0
    if cv > 0.5:
        return "Moyenne ± 2σ"
    
    # 4. Si les données sont bien distribuées (pas d'outliers, pas d'asymétrie)
    if outlier_ratio < 0.01 and abs(skewness) < 0.2:
        return "Min-Max"
    
    # 5. Par défaut, si les données sont modérément asymétriques
    if abs(skewness) < 0.5:
        return "Moyenne ± 2σ"
    
    # 6. En dernier recours
    return "Percentiles"

def get_scale_label(stat_scale, linear_scale, percentile_scale, std_scale, format_str):
    """Retourne le libellé de l'échelle avec ses valeurs"""
    if stat_scale == "Min-Max" and linear_scale:
        return f"Min-Max (min={format_str.format(linear_scale[0])}, max={format_str.format(linear_scale[1])})"
    elif stat_scale == "Percentiles" and percentile_scale:
        return f"Percentiles (p5={format_str.format(percentile_scale[0])}, p95={format_str.format(percentile_scale[1])})"
    elif stat_scale == "Moyenne ± 2σ" and std_scale:
        return f"Moyenne ± 2σ (m-2σ={format_str.format(std_scale[0])}, m+2σ={format_str.format(std_scale[1])})"
    else:
        return "Auto"

# ============================================================================
# FONCTION PRINCIPALE D'AFFICHAGE - OPTIMISÉE
# ============================================================================

def show(df, epci_df):
    # Charger les sources et les groupes
    indicator_sources, groups_dict, indicator_to_group, descriptions_dict, thematiques_dict = load_indicator_sources_and_groups()
    
    # Charger les données de ménages
    menages_data, _ = load_menages_data()
    
    st.title("📊 Visualisation Cartographique des indicateurs de l'ORTB")
    
    common_themes = get_common_themes(df, epci_df, thematiques_dict)
    
    # Contrôles principaux
    col1, col2, col3, col4 = st.columns([1, 0.7, 1.5, 0.6])
    
    with col1:
        echelle = st.radio("Échelle", options=["Commune", "EPCI"], horizontal=True)
    
    with col2:
        if common_themes:
            selected_thematique = st.selectbox("Thématique", ["Toutes"] + list(common_themes))
        else:
            selected_thematique = "Toutes"
    
    with col3:
        df_to_use = df if echelle == "Commune" else epci_df
        
        # OPTIMISATION: Filtrer par thématique de manière vectorisée
        if selected_thematique != "Toutes":
            # Créer un masque pour filtrer les indicateurs de la thématique
            mask = df_to_use['indicateur'].apply(
                lambda x: x in thematiques_dict and selected_thematique in thematiques_dict[x]
            )
            filtered_df_theme = df_to_use[mask].copy()
            
            if filtered_df_theme is not None and not filtered_df_theme.empty:
                available_indicators = get_available_indicators_with_groups(
                    filtered_df_theme, groups_dict, indicator_to_group
                )
            else:
                available_indicators = []
        else:
            available_indicators = get_available_indicators_with_groups(
                df_to_use, groups_dict, indicator_to_group
            )
        
        if not available_indicators:
            st.error("Aucun indicateur disponible pour cette thématique")
            return
            
        indicator_names = [ind['nom'] for ind in available_indicators]
        selected_indicator_name = st.selectbox("Indicateur", indicator_names)
        
        selected_indicator_info = next(
            (ind for ind in available_indicators if ind['nom'] == selected_indicator_name),
            None
        )
    
    with col4:
        if selected_indicator_info['type'] == 'individuel':
            dates_disponibles = sorted(df_to_use[df_to_use['indicateur'] == selected_indicator_info['indicateur_nom']]['date'].unique())
        else:
            dates_par_indicateur = []
            for ind in selected_indicator_info['indicateurs']:
                dates = set(df_to_use[df_to_use['indicateur'] == ind]['date'].unique())
                dates_par_indicateur.append(dates)
            
            if dates_par_indicateur:
                dates_communes = set.intersection(*dates_par_indicateur)
                dates_disponibles = sorted(list(dates_communes))
            else:
                dates_disponibles = []
        
        if dates_disponibles:
            selected_date_str = st.selectbox("Date", [d.strftime('%d/%m/%Y') for d in dates_disponibles], 
                                           index=len(dates_disponibles)-1)
            selected_date = datetime.strptime(selected_date_str, '%d/%m/%Y')
        else:
            st.error("Aucune date disponible")
            return
    
    # Interface de sélection pour les groupes
    selected_indicators_for_group = None
    if selected_indicator_info['type'] == 'groupe':
        st.markdown("---")
        with st.container():
            selected_indicators_for_group = get_group_selection_interface(
                selected_indicator_info, 
                indicator_to_group,
                default_select_all=True
            )
            
            if not selected_indicators_for_group:
                st.warning("⚠️ Veuillez sélectionner au moins une valeur")
                return
    
    # Normalisation et couleurs
    st.markdown("---")
    col_norm, col_scale1, col_scale2 = st.columns([0.7, 0.5, 0.5])
    
    with col_norm:
        normalisation_options = ["Aucune", "Par surface", "Par population", "Par ménages"]
        normalisation_option = st.selectbox("Normalisation", normalisation_options)
    
    with col_scale1:
        scale_options = st.selectbox("Palette", ["Blues", "Greens", "Darkmint", "ice", "Reds"])
    
    with col_scale2:
        stat_scale_options = ["Auto", "Min-Max", "Percentiles", "Moyenne ± 2σ"]
        # Sélection avec l'option "Auto"
        stat_scale = st.selectbox("Échelle", stat_scale_options, index=0)
        reverse_scale = st.checkbox("Inverser")
    
    # Données de normalisation
    if echelle == "Commune":
        surface_df, population_df = get_surface_population_data(df, "Commune", selected_date)
        code_col = 'code_commune'
        date_col = 'date'
    else:
        surface_df, population_df = get_surface_population_data(epci_df, "EPCI", selected_date)
        code_col = 'code_epci'
        date_col = 'date'
    
    # Récupération des données
    # Initialiser menages_note à None avant les conditions
    menages_note = None
    
    if selected_indicator_info['type'] == 'individuel':
        if echelle == "Commune":
            filtered_df = df[(df['indicateur'] == selected_indicator_info['indicateur_nom']) & 
                           (df['date'] == selected_date)].copy()
        else:
            filtered_df = epci_df[(epci_df['indicateur'] == selected_indicator_info['indicateur_nom']) & 
                                 (epci_df['date'] == selected_date)].copy()
        
        # Normalisation
        suffixe_titre = ""
        
        if normalisation_option == "Par surface" and surface_df is not None:
            filtered_df = normalize_by_surface(filtered_df, code_col, surface_df)
            valeur_colonne = 'valeur_normalisee'
            suffixe_titre = " (par hectare)"
        elif normalisation_option == "Par population" and population_df is not None:
            filtered_df = normalize_by_population(filtered_df, code_col, population_df)
            valeur_colonne = 'valeur_normalisee'
            suffixe_titre = " (pour 1000 hab.)"
        elif normalisation_option == "Par ménages" and menages_data is not None:
            filtered_df, menages_notes = normalize_by_menages(filtered_df, code_col, date_col, menages_data)
            if 'valeur_normalisee' in filtered_df.columns:
                valeur_colonne = 'valeur_normalisee'
                suffixe_titre = " (par ménage)"
                menages_note = "Attention: Du fait de la disponibilité de la donnée ménages uniquement pour 3 années (2012, 2017 et 2023), la division des données par le nombre de ménages se fait en utilisant l'année précédente. Exemple: Les données de 2020 seront divisées par les données de ménages de 2017"
            else:
                valeur_colonne = 'valeur'
                st.warning("Impossible de normaliser par ménages pour certains territoires")
        else:
            valeur_colonne = 'valeur'
            suffixe_titre = ""
        
        titre_indicateur = selected_indicator_info['indicateur_nom']
        source_key = selected_indicator_info['indicateur_nom']
        
    else:  # Groupe
        # Conversion de la normalisation pour les groupes
        norm_option_for_group = "Aucune"
        if normalisation_option == "Par surface":
            norm_option_for_group = "Par surface (ha)"
        elif normalisation_option == "Par population":
            norm_option_for_group = "Par population (1000 hab.)"
        
        filtered_df = get_group_data(
            df_to_use if echelle == "Commune" else epci_df,
            selected_indicator_info,
            selected_indicators_for_group,
            code_col,
            selected_date,
            norm_option_for_group,
            surface_df,
            population_df
        )
        
        if filtered_df is None or filtered_df.empty:
            st.error("Aucune donnée disponible")
            return
        
        # Normalisation par ménages pour les groupes
        if normalisation_option == "Par ménages" and menages_data is not None:
            filtered_df, menages_notes = normalize_by_menages(filtered_df, code_col, date_col, menages_data)
            if 'valeur_normalisee' in filtered_df.columns:
                valeur_colonne = 'valeur_normalisee'
                suffixe_titre = " (par ménage)"
                menages_note = "Attention: Du fait de la disponibilité de la donnée ménages uniquement pour 3 années (2012, 2017 et 2023), la division des données par le nombre de ménages se fait en utilisant l'année précédente. Exemple: Les données de 2020 seront divisées par les données de ménages de 2017"
            else:
                valeur_colonne = 'valeur'
                suffixe_titre = ""
                st.warning("Impossible de normaliser par ménages pour certains territoires")
        else:
            if 'valeur_normalisee' in filtered_df.columns:
                valeur_colonne = 'valeur_normalisee'
                if normalisation_option == "Par surface":
                    suffixe_titre = " (par hectare)"
                elif normalisation_option == "Par population":
                    suffixe_titre = " (pour 1000 hab.)"
                else:
                    suffixe_titre = ""
            else:
                valeur_colonne = 'valeur'
                suffixe_titre = ""
        
        # Formater le titre du groupe avec les valeurs sélectionnées
        titre_indicateur = format_group_title(
            selected_indicators_for_group, 
            indicator_to_group, 
            selected_indicator_info['groupe_nom']
        )
        source_key = None
    
    # Nettoyer les valeurs proches de 100
    if valeur_colonne in filtered_df.columns:
        mask_proche_100 = (filtered_df[valeur_colonne] - 100).abs() < SEUIL_CENT
        filtered_df.loc[mask_proche_100, valeur_colonne] = 100.0
    
    # === SÉLECTION AUTOMATIQUE DE L'ÉCHELLE ===
    # Récupérer les valeurs pour l'analyse
    valeurs = filtered_df[valeur_colonne].dropna().values
    
    # Si "Auto" est sélectionné, choisir automatiquement la meilleure échelle
    stat_scale_original = stat_scale  # Garder la valeur originale pour l'affichage
    if stat_scale == "Auto" and len(valeurs) > 0:
        suggested_scale = suggest_scale(valeurs)
        # Utiliser l'échelle suggérée
        stat_scale = suggested_scale
    
    # Échelle de couleurs
    linear_scale, percentile_scale, std_scale = get_scale_options(filtered_df, valeur_colonne)
    format_str = f"{{:.{PRECISION_DECIMALES}f}}"
    
    if stat_scale == "Min-Max" and linear_scale:
        range_color = linear_scale
        range_note = f"min={format_str.format(linear_scale[0])}, max={format_str.format(linear_scale[1])}"
        scale_display_name = f"Min-Max (min={format_str.format(linear_scale[0])}, max={format_str.format(linear_scale[1])})"
    elif stat_scale == "Percentiles" and percentile_scale:
        range_color = percentile_scale
        range_note = f"p5={format_str.format(percentile_scale[0])}, p95={format_str.format(percentile_scale[1])}"
        scale_display_name = f"Percentiles (p5={format_str.format(percentile_scale[0])}, p95={format_str.format(percentile_scale[1])})"
    elif stat_scale == "Moyenne ± 2σ" and std_scale:
        range_color = std_scale
        range_note = f"m±2σ=[{format_str.format(std_scale[0])}, {format_str.format(std_scale[1])}]"
        scale_display_name = f"Moyenne ± 2σ (m-2σ={format_str.format(std_scale[0])}, m+2σ={format_str.format(std_scale[1])})"
    else:
        range_color = None
        range_note = "Auto"
        scale_display_name = "Auto"
    
    # Si "Auto" a été sélectionné, ajouter une indication
    if stat_scale_original == "Auto":
        scale_display_name = f"Auto → {scale_display_name}"
    
    color_scale = scale_options + ("_r" if reverse_scale else "")
    
    # Création de la carte
    if echelle == "Commune":
        communes_geojson = load_geojson("data/communes_simple.geojson")
        
        source_text = ""
        if source_key and source_key in indicator_sources and pd.notna(indicator_sources[source_key]):
            source_text = f"<br><sub>Source : {indicator_sources[source_key]}</sub>"
        
        fig = px.choropleth(
            filtered_df,
            geojson=communes_geojson,
            locations='code_commune',
            featureidkey="properties.code",
            color=valeur_colonne,
            hover_name='libelle_commune' if 'libelle_commune' in filtered_df.columns else None,
            hover_data={valeur_colonne: f':.{PRECISION_DECIMALES}f'},
            color_continuous_scale=color_scale,
            range_color=range_color,
            scope="europe",
            center={"lat": 46.8, "lon": -2.3},
            title=f"{titre_indicateur}{suffixe_titre}<br><sub>Méthode : {scale_display_name}</sub>{source_text}")
        
    else:
        epci_geojson = load_geojson("data/epci_simple.geojson")
        
        source_text = ""
        if source_key and source_key in indicator_sources and pd.notna(indicator_sources[source_key]):
            source_text = f"<br><sub>Source : {indicator_sources[source_key]}</sub>"
        
        fig = px.choropleth(
            filtered_df,
            geojson=epci_geojson,
            locations='code_epci',
            featureidkey="properties.code",
            color=valeur_colonne,
            hover_name='libelle_epci' if 'libelle_epci' in filtered_df.columns else None,
            hover_data={valeur_colonne: f':.{PRECISION_DECIMALES}f'},
            color_continuous_scale=color_scale,
            range_color=range_color,
            scope="europe",
            center={"lat": 46.8, "lon": -2.3},
            title=f"{titre_indicateur}{suffixe_titre}<br><sub>Méthode : {scale_display_name} </sub>{source_text}")
    
    fig.update_geos(fitbounds="locations", visible=False)
    # RÉDUCTION DE L'ESPACE VIDE APRÈS LA CARTE
    fig.update_layout(
        width=1000, 
        height=900,  # Réduit de 1000 à 900
        margin=dict(l=0, r=0, t=50, b=10)  # Réduit la marge du bas
    )
    st.plotly_chart(fig, use_container_width=True)
    
    # --- AFFICHAGE DE LA DESCRIPTION ---
    # menages_note est déjà défini plus haut dans la fonction
    if selected_indicator_info['type'] == 'individuel':
        show_description(
            descriptions_dict,
            selected_indicator_info['indicateur_nom'],
            'individuel',
            normalisation_type=normalisation_option,
            menages_note=menages_note
        )
    else:
        show_description(
            descriptions_dict,
            selected_indicator_info['groupe_nom'],
            'groupe',
            selected_indicators=selected_indicators_for_group,
            normalisation_type=normalisation_option,
            menages_note=menages_note
        )
    
    # Statistiques avec la précision configurée
    with st.expander("📈 Statistiques"):
        col_stat1, col_stat2, col_stat3 = st.columns(3)
        with col_stat1:
            # Pour la moyenne, on peut aussi arrondir les valeurs proches de 100
            mean_val = filtered_df[valeur_colonne].mean()
            if abs(mean_val - 100) < SEUIL_CENT:
                mean_val = 100.0
            st.metric("Moyenne", format_str.format(mean_val))
        with col_stat2:
            median_val = filtered_df[valeur_colonne].median()
            if abs(median_val - 100) < SEUIL_CENT:
                median_val = 100.0
            st.metric("Médiane", format_str.format(median_val))
        with col_stat3:
            st.metric("Écart-type", format_str.format(filtered_df[valeur_colonne].std()))
    
    # Données détaillées avec la précision configurée
    with st.expander("📋 Données détaillées"):
        # Créer le titre avec la date et les indicateurs
        date_str = selected_date.strftime('%d/%m/%Y')
        
        if selected_indicator_info['type'] == 'individuel':
            titre_detail = f"Données pour {selected_indicator_info['indicateur_nom']} - {date_str}"
        else:
            # Formater le nom du groupe avec les valeurs sélectionnées
            groupe_titre = format_group_title(
                selected_indicators_for_group, 
                indicator_to_group, 
                selected_indicator_info['groupe_nom']
            )
            # Récupérer les noms des indicateurs sélectionnés
            indicateurs_noms = []
            for ind in selected_indicators_for_group:
                if ind in indicator_to_group:
                    specific_value = indicator_to_group[ind].get('specific_value', '')
                    if specific_value and specific_value != '?':
                        indicateurs_noms.append(specific_value)
                    else:
                        indicateurs_noms.append(ind)
                else:
                    indicateurs_noms.append(ind)
            
            if len(indicateurs_noms) == 1:
                liste_indicateurs = indicateurs_noms[0]
            elif len(indicateurs_noms) == 2:
                liste_indicateurs = f"{indicateurs_noms[0]} et {indicateurs_noms[1]}"
            else:
                last_ind = indicateurs_noms[-1]
                first_inds = indicateurs_noms[:-1]
                liste_indicateurs = f"{', '.join(first_inds)} et {last_ind}"
            
            titre_detail = f"Données pour {groupe_titre} - {date_str}"
            # Ajouter les indicateurs détaillés en sous-titre
            st.caption(f"Indicateurs inclus : {liste_indicateurs}")
        
        st.markdown(f"**{titre_detail}**")
        
        if echelle == "Commune":
            display_cols = ['libelle_commune', 'code_commune', valeur_colonne]
        else:
            display_cols = ['libelle_epci', 'code_epci', valeur_colonne]
        
        # Ajouter une colonne avec le nom de l'indicateur et la date pour l'export
        # Créer une colonne 'indicateur_date' qui sera incluse dans le DataFrame exporté
        display_df = filtered_df[display_cols].copy()
        
        # Ajouter des colonnes d'information pour l'export
        display_df['Date'] = date_str
        
        if selected_indicator_info['type'] == 'individuel':
            display_df['Indicateur'] = selected_indicator_info['indicateur_nom']
        else:
            # Pour les groupes, mettre le nom du groupe et les indicateurs inclus
            groupe_titre = format_group_title(
                selected_indicators_for_group, 
                indicator_to_group, 
                selected_indicator_info['groupe_nom']
            )
            display_df['Indicateur'] = groupe_titre
            
            # Ajouter une colonne avec la liste détaillée des indicateurs
            indicateurs_noms = []
            for ind in selected_indicators_for_group:
                if ind in indicator_to_group:
                    specific_value = indicator_to_group[ind].get('specific_value', '')
                    if specific_value and specific_value != '?':
                        indicateurs_noms.append(specific_value)
                    else:
                        indicateurs_noms.append(ind)
                else:
                    indicateurs_noms.append(ind)
            display_df['Indicateurs inclus'] = ', '.join(indicateurs_noms)
        
        # Arrondir les valeurs et corriger celles proches de 100
        if valeur_colonne in display_df.columns:
            # Corriger les valeurs proches de 100
            mask_proche_100 = (display_df[valeur_colonne] - 100).abs() < SEUIL_CENT
            display_df.loc[mask_proche_100, valeur_colonne] = 100.0
            # Arrondir
            display_df[valeur_colonne] = display_df[valeur_colonne].round(PRECISION_DECIMALES)
        
        if valeur_colonne == 'valeur_normalisee':
            if normalisation_option == "Par surface":
                display_df.rename(columns={'valeur_normalisee': f'Valeur (par ha)'}, inplace=True)
            elif normalisation_option == "Par population":
                display_df.rename(columns={'valeur_normalisee': f'Valeur (pour 1000 hab.)'}, inplace=True)
            elif normalisation_option == "Par ménages":
                display_df.rename(columns={'valeur_normalisee': f'Valeur (par ménage)'}, inplace=True)
        elif valeur_colonne == 'valeur':
            display_df.rename(columns={'valeur': 'Valeur'}, inplace=True)
        
        st.dataframe(display_df, use_container_width=True, hide_index=True)
        
        if selected_indicator_info['type'] == 'groupe':
            selected_values = [indicator_to_group[ind].get('specific_value', '?') 
                             for ind in selected_indicators_for_group if ind in indicator_to_group]
            st.caption(f"Valeurs sélectionnées : {', '.join(selected_values)}")