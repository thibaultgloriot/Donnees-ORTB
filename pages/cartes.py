import streamlit as st
import pandas as pd
import json
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
import numpy as np
import re
from collections import defaultdict

# ============================================================================
# PARAMÈTRES DE CONFIGURATION
# ============================================================================

PRECISION_DECIMALES = 4
SEUIL_CENT = 0.01
MAX_TERRITOIRES_COMPARAISON = 70  # Nombre max de territoires à comparer

# ============================================================================
# CONFIGURATION DES ÉCHELLES
# ============================================================================

ECHELLES_CONFIG = {
    'communes': {
        'label': 'Commune',
        'code_col': 'code_commune',
        'libelle_col': 'libelle_commune',
        'geojson': 'data/communes_simple.geojson',
        'center': {"lat": 46.8, "lon": -2.3},
        'parent_col': 'code_departement',
        'parent_libelle_col': 'libelle_departement',
        'grandparent_col': 'code_region',
        'grandparent_libelle_col': 'libelle_region'
    },
    'epci': {
        'label': 'EPCI',
        'code_col': 'code_epci',
        'libelle_col': 'libelle_epci',
        'geojson': 'data/epci_simple.geojson',
        'center': {"lat": 46.8, "lon": -2.3},
        'parent_col': 'code_departement',
        'parent_libelle_col': 'libelle_departement',
        'grandparent_col': 'code_region',
        'grandparent_libelle_col': 'libelle_region'
    },
    'departements': {
        'label': 'Département',
        'code_col': 'code_departement',
        'libelle_col': 'libelle_departement',
        'geojson': 'data/departements-bretagne.geojson',
        'center': {"lat": 46.8, "lon": -2.3}
    },
    'regions': {
        'label': 'Région',
        'code_col': 'code_region',
        'libelle_col': 'libelle_region',
        'geojson': 'data/region-bretagne.geojson',
        'center': {"lat": 46.8, "lon": -2.3}
    }
}

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
            desc_df = sources_df[sources_df['Description'].notna() & (sources_df['Description'] != '')]
            descriptions_dict = dict(zip(desc_df[indicator_col], desc_df['Description']))
        
        # Groupes
        groups_dict = {}
        indicator_to_group = {}
        group_names = load_group_names()
        
        # Traitement des thématiques multiples
        thematiques_dict = {}
        if 'Thématique' in sources_df.columns:
            for _, row in sources_df.iterrows():
                if pd.notna(row['Thématique']) and row['Thématique'] != '':
                    themes = [t.strip() for t in str(row['Thématique']).split(';') if t.strip()]
                    if themes:
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
        
        menages_indicateurs = menages_df[menages_df['indicateur'].str.contains('ménages', case=False)]
        
        if menages_indicateurs.empty:
            return None, None
        
        menages_df_filtered = menages_indicateurs[['date', 'code_commune', 'valeur']].copy()
        menages_df_filtered['annee'] = menages_df_filtered['date'].dt.year
        
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
    annees_disponibles = [2012, 2017, 2023]
    
    annee_utilisee = None
    for a in sorted(annees_disponibles):
        if a <= annee:
            annee_utilisee = a
    
    if annee_utilisee is None:
        annee_utilisee = annees_disponibles[0]
    
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
        surface_data = df[df['indicateur'] == "Surface totale du territoire (ha)"].copy()
        if not surface_data.empty:
            code_col = ECHELLES_CONFIG[echelle]['code_col']
            surface_df = surface_data.sort_values('date').groupby([code_col]).last().reset_index()
        
        population_data = df[df['indicateur'] == "Nombre d'habitants du territoire"].copy()
        if not population_data.empty:
            population_dfs = []
            code_col = ECHELLES_CONFIG[echelle]['code_col']
            
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

def get_common_themes(all_data, thematiques_dict):
    """Récupère toutes les thématiques disponibles"""
    themes_communes = set()
    
    for df_temp in all_data.values():
        if df_temp is not None and 'indicateur' in df_temp.columns:
            for indicateur in df_temp['indicateur'].unique():
                if indicateur in thematiques_dict:
                    themes_communes.update(thematiques_dict[indicateur])
    
    return sorted(themes_communes) if themes_communes else []

# ============================================================================
# FONCTIONS DE GESTION DES GROUPES
# ============================================================================

def get_available_indicators_with_groups(df, groups_dict, indicator_to_group):
    """Récupère la liste des indicateurs disponibles"""
    all_indicators = df['indicateur'].unique().tolist()
    indicateurs_exclus = ["Surface totale du territoire (ha)", "Nombre d'habitants du territoire"]
    
    available_indicators = []
    
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
    
    for ind in groupe_info['indicateurs']:
        if ind in indicator_to_group:
            specific_value = indicator_to_group[ind].get('specific_value', '?')
            display_counts[specific_value] += 1
    
    for ind in groupe_info['indicateurs']:
        if ind in indicator_to_group:
            specific_value = indicator_to_group[ind].get('specific_value', '?')
            
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
    
    st.markdown(f"**{groupe_info['groupe_nom']}**")
    
    options_display = [opt['display'] for opt in indicator_options]
    
    selected_displays = st.multiselect(
        "Sélectionnez les valeurs à additionner",
        options=options_display,
        default=options_display if default_select_all else [],
        key=f"multiselect_{groupe_info['groupe_value']}"
    )
    
    selected_indicators = []
    for disp in selected_displays:
        if disp in display_to_indicator:
            selected_indicators.append(display_to_indicator[disp])
    
    st.caption(f"{len(selected_indicators)}/{len(indicator_options)} valeurs sélectionnées")
    
    return selected_indicators

def get_group_data(df, groupe_info, selected_indicators, code_col, selected_date, normalisation_option, surface_df, population_df):
    """Récupère et agrège les données pour les indicateurs sélectionnés du groupe"""
    if not selected_indicators:
        return None
    
    group_data = df[
        (df['indicateur'].isin(selected_indicators)) & 
        (df['date'] == selected_date)
    ].copy()
    
    if group_data.empty:
        return None
    
    pivot_data = group_data.pivot_table(
        index=[code_col],
        columns='indicateur',
        values='valeur',
        aggfunc='first'
    ).reset_index()
    
    pivot_data = pivot_data.fillna(0)
    pivot_data['valeur_somme'] = pivot_data[selected_indicators].sum(axis=1)
    
    if (pivot_data[selected_indicators].max().max() <= 105 and
        pivot_data[selected_indicators].min().min() >= -5):
        
        diff_avec_100 = (pivot_data['valeur_somme'] - 100).abs()
        pivot_data.loc[diff_avec_100 < SEUIL_CENT, 'valeur_somme'] = 100.0
    
    result_df = pivot_data[[code_col, 'valeur_somme']].copy()
    result_df['date'] = selected_date
    result_df['valeur'] = result_df['valeur_somme']
    
    libelle_col = ECHELLES_CONFIG.get('libelle_col', 'libelle')
    for config in ECHELLES_CONFIG.values():
        if config['code_col'] == code_col:
            libelle_col = config['libelle_col']
            break
    
    if libelle_col in group_data.columns:
        libelles = group_data.groupby(code_col)[libelle_col].first().reset_index()
        result_df = result_df.merge(libelles, on=code_col, how='left')
    else:
        libelle_df = df[df['date'] == selected_date][[code_col, libelle_col]].drop_duplicates()
        result_df = result_df.merge(libelle_df, on=code_col, how='left')
    
    if normalisation_option == "Par surface (ha)" and surface_df is not None:
        result_df = normalize_by_surface(result_df, code_col, surface_df)
    elif normalisation_option == "Par population (1000 hab.)" and population_df is not None:
        result_df = normalize_by_population(result_df, code_col, population_df)
    
    return result_df

# ============================================================================
# FONCTIONS D'AFFICHAGE DE LA DESCRIPTION
# ============================================================================

def show_description(descriptions_dict, indicator_name, indicator_type, selected_indicators=None, 
                    normalisation_type=None, menages_note=None):
    """Affiche la description de l'indicateur en préservant les sauts de ligne"""
    
    def format_description(text):
        if not text or pd.isna(text):
            return ""
        text = str(text)
        formatted = text.replace('\n', '  \n')
        return formatted
    
    description_a_afficher = False
    
    if indicator_type == 'individuel':
        description = descriptions_dict.get(indicator_name)
        if description and pd.notna(description) and description != '':
            description_a_afficher = True
            st.markdown("### 📝 Description de l'indicateur")
            formatted_desc = format_description(description)
            st.markdown(formatted_desc)
    
    elif indicator_type == 'groupe' and selected_indicators:
        has_description = False
        for ind in selected_indicators:
            if descriptions_dict.get(ind) and pd.notna(descriptions_dict.get(ind)) and descriptions_dict.get(ind) != '':
                has_description = True
                break
        
        if has_description:
            description_a_afficher = True
            st.markdown("### 📝 Descriptions des indicateurs sélectionnés")
            
            for ind in selected_indicators:
                description = descriptions_dict.get(ind)
                if description and pd.notna(description) and description != '':
                    with st.expander(f"**{ind}**"):
                        formatted_desc = format_description(description)
                        st.markdown(formatted_desc)
    
    # Message de normalisation par ménages (intégré dans le même bloc)
    if normalisation_type == "Par ménages" and menages_note:
        if not description_a_afficher:
            st.markdown("### 📝 Information sur la normalisation")
        else:
            st.markdown("")  # séparation
        st.warning(f"⚠️ {menages_note}")

# ============================================================================
# FONCTIONS D'AMÉLIORATION DU TITRE
# ============================================================================

def format_group_title(selected_indicators, indicator_to_group, groupe_nom):
    """Formate le titre pour les indicateurs groupés avec 'et' si nécessaire"""
    if not selected_indicators:
        return groupe_nom
    
    values = []
    for ind in selected_indicators:
        if ind in indicator_to_group:
            specific_value = indicator_to_group[ind].get('specific_value', '')
            if specific_value and specific_value != '?':
                values.append(specific_value)
    
    if not values:
        return groupe_nom
    
    if len(values) == 1:
        return f"{groupe_nom} ({values[0]})"
    
    if len(values) == 2:
        return f"{groupe_nom} ({values[0]} et {values[1]})"
    
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
        return "Min-Max"
    
    mean_val = np.mean(values)
    std_val = np.std(values)
    q1 = np.percentile(values, 25)
    q3 = np.percentile(values, 75)
    iqr = q3 - q1
    
    outliers_low = values[values < q1 - 1.5 * iqr]
    outliers_high = values[values > q3 + 1.5 * iqr]
    outlier_count = len(outliers_low) + len(outliers_high)
    outlier_ratio = outlier_count / len(values)
    
    skewness = (mean_val - np.median(values)) / std_val if std_val > 0 else 0
    
    if outlier_ratio > 0.05:
        return "Percentiles"
    
    if abs(skewness) > 0.5:
        return "Percentiles"
    
    cv = std_val / mean_val if mean_val != 0 else 0
    if cv > 0.5:
        return "Moyenne ± 2σ"
    
    if outlier_ratio < 0.01 and abs(skewness) < 0.2:
        return "Min-Max"
    
    if abs(skewness) < 0.5:
        return "Moyenne ± 2σ"
    
    return "Percentiles"

# ============================================================================
# FONCTION DE GÉNÉRATION DU GRAPHE D'ÉVOLUTION
# ============================================================================

def generate_evolution_graph(data, echelle, selected_indicator_info, selected_territory_code,
                             indicator_to_group, selected_indicators_for_group=None):
    """
    Génère le graphe d'évolution temporelle avec moyenne, médiane, département, région
    """
    # Récupérer le DataFrame et la configuration
    df = data.get(echelle)
    if df is None or df.empty:
        return None
    
    config = ECHELLES_CONFIG[echelle]
    code_col = config['code_col']
    libelle_col = config['libelle_col']
    date_col = 'date'
    
    # Déterminer l'indicateur à afficher
    if selected_indicator_info['type'] == 'individuel':
        indicator_name = selected_indicator_info['indicateur_nom']
        indicator_list = [indicator_name]
        is_group = False
    else:
        indicator_list = selected_indicators_for_group
        is_group = True
    
    # Récupérer toutes les données temporelles pour l'indicateur
    if is_group:
        all_data = df[df['indicateur'].isin(indicator_list)].copy()
    else:
        all_data = df[df['indicateur'] == indicator_name].copy()
    
    if all_data.empty:
        return None
    
    # Vérifier qu'il y a plus d'une date disponible
    dates_disponibles = all_data['date'].unique()
    if len(dates_disponibles) <= 1:
        st.info("ℹ️ Une seule date disponible pour cet indicateur. Pas de graphe d'évolution.")
        return None
    
    # Récupérer le libellé du territoire sélectionné
    territory_data = df[df[code_col] == selected_territory_code]
    if not territory_data.empty:
        territory_libelle = territory_data[libelle_col].iloc[0]
    else:
        territory_libelle = selected_territory_code
    
    # === 1. PRÉPARER LES DONNÉES POUR LE GRAPHE ===
    
    # 1.1 Données du territoire sélectionné (pour les stats)
    territory_series = all_data[all_data[code_col] == selected_territory_code].copy()
    territory_series = territory_series.groupby(date_col)['valeur'].mean().reset_index()
    
    # 1.2 Moyenne par date
    mean_series = all_data.groupby(date_col)['valeur'].mean().reset_index()
    
    # 1.3 Médiane par date
    median_series = all_data.groupby(date_col)['valeur'].median().reset_index()
    
    # === 2. RÉCUPÉRATION DES DONNÉES DÉPARTEMENTALES ET RÉGIONALES ===
    
    departement_series_dict = {}
    region_series_dict = {}
    
    dept_data = data.get('departements')
    if dept_data is not None and not dept_data.empty:
        if is_group:
            dept_filtered = dept_data[dept_data['indicateur'].isin(indicator_list)]
        else:
            dept_filtered = dept_data[dept_data['indicateur'] == indicator_name]
        
        if not dept_filtered.empty:
            for dept_code in dept_filtered['code_departement'].unique():
                dept_subset = dept_filtered[dept_filtered['code_departement'] == dept_code]
                dept_series = dept_subset.groupby(date_col)['valeur'].mean().reset_index()
                dept_libelle = dept_data[dept_data['code_departement'] == dept_code]['libelle_departement'].iloc[0]
                departement_series_dict[dept_code] = {
                    'data': dept_series,
                    'libelle': dept_libelle
                }
    
    region_data = data.get('regions')
    if region_data is not None and not region_data.empty:
        if is_group:
            region_filtered = region_data[region_data['indicateur'].isin(indicator_list)]
        else:
            region_filtered = region_data[region_data['indicateur'] == indicator_name]
        
        if not region_filtered.empty:
            for region_code in region_filtered['code_region'].unique():
                region_subset = region_filtered[region_filtered['code_region'] == region_code]
                region_series = region_subset.groupby(date_col)['valeur'].mean().reset_index()
                region_libelle = region_data[region_data['code_region'] == region_code]['libelle_region'].iloc[0]
                region_series_dict[region_code] = {
                    'data': region_series,
                    'libelle': region_libelle
                }
    
    # === 3. INTERFACE DE SÉLECTION ===
    
    st.markdown("### 📈 Évolution temporelle")
    
    echelle_label = ECHELLES_CONFIG[echelle]['label']
    if echelle == 'communes':
        echelle_label_plural = 'communes'
    elif echelle == 'epci':
        echelle_label_plural = 'EPCI'
    elif echelle == 'departements':
        echelle_label_plural = 'départements'
    else:
        echelle_label_plural = 'régions'
    
    col_controls1, col_controls2, col_controls3 = st.columns([1, 1, 1])
    
    show_mean = True
    show_median = True
    show_departements = False
    show_regions = False
    
    with col_controls1:
        st.markdown("**Afficher :**")
        show_mean = st.checkbox(f"📊 Moyenne ({echelle_label_plural})", value=True, key="show_mean")
        show_median = st.checkbox(f"📊 Médiane ({echelle_label_plural})", value=True, key="show_median")
    
    with col_controls2:
        st.markdown("**Comparer avec :**")
        if departement_series_dict:
            show_departements = st.checkbox("🏛️ Départements", value=False, key="show_departements")
        if region_series_dict:
            show_regions = st.checkbox("🌍 Région", value=False, key="show_regions")
    
    with col_controls3:
        st.markdown("**Ajouter/Retirer des territoires :**")
        all_territoires = all_data[[code_col, libelle_col]].drop_duplicates()
        territoire_options = sorted(all_territoires[libelle_col].tolist())
        
        # Sélection par défaut : le territoire sélectionné
        default_selection = [territory_libelle] if territory_libelle in territoire_options else []
        
        selected_territoires = st.multiselect(
            f"Sélectionnez les territoires à afficher (max {MAX_TERRITOIRES_COMPARAISON})",
            options=territoire_options,
            default=default_selection,
            key="territoires_select"
        )
        
        if len(selected_territoires) > MAX_TERRITOIRES_COMPARAISON:
            st.warning(f"⚠️ Maximum {MAX_TERRITOIRES_COMPARAISON} territoires")
            selected_territoires = selected_territoires[:MAX_TERRITOIRES_COMPARAISON]
    
    # === 4. GÉNÉRATION DU GRAPHE ===
    
    fig = go.Figure()
    territory_colors = px.colors.qualitative.Plotly
    dept_colors = px.colors.qualitative.Set2
    region_colors = px.colors.qualitative.Set1
    
    # 4.1 Territoire sélectionné (style bleu épais) et autres territoires
    selected_territory_libelle = territory_libelle
    other_territories = [t for t in selected_territoires if t != selected_territory_libelle]
    
    # Territoire sélectionné
    if selected_territory_libelle in selected_territoires:
        code = all_territoires[all_territoires[libelle_col] == selected_territory_libelle][code_col].iloc[0]
        territory_data_plot = all_data[all_data[code_col] == code].copy()
        if not territory_data_plot.empty:
            territory_series_plot = territory_data_plot.groupby(date_col)['valeur'].mean().reset_index()
            fig.add_trace(go.Scatter(
                x=territory_series_plot['date'],
                y=territory_series_plot['valeur'],
                mode='lines+markers',
                name=selected_territory_libelle,
                line=dict(color='#1f77b4', width=3),
                marker=dict(size=8)
            ))
    
    # Autres territoires
    for i, territoire_libelle in enumerate(other_territories):
        code = all_territoires[all_territoires[libelle_col] == territoire_libelle][code_col].iloc[0]
        extra_data = all_data[all_data[code_col] == code].copy()
        if not extra_data.empty:
            extra_series = extra_data.groupby(date_col)['valeur'].mean().reset_index()
            color_idx = i % len(territory_colors)
            fig.add_trace(go.Scatter(
                x=extra_series['date'],
                y=extra_series['valeur'],
                mode='lines+markers',
                name=territoire_libelle,
                line=dict(color=territory_colors[color_idx], width=2),
                marker=dict(size=7)
            ))
    
    # 4.2 Moyenne
    if show_mean and not mean_series.empty:
        fig.add_trace(go.Scatter(
            x=mean_series['date'],
            y=mean_series['valeur'],
            mode='lines+markers',
            name=f'Moyenne ({echelle_label_plural})',
            line=dict(color='#7f7f7f', width=2, dash='dash'),
            marker=dict(size=6)
        ))
    
    # 4.3 Médiane
    if show_median and not median_series.empty:
        fig.add_trace(go.Scatter(
            x=median_series['date'],
            y=median_series['valeur'],
            mode='lines+markers',
            name=f'Médiane ({echelle_label_plural})',
            line=dict(color='#b0b0b0', width=2, dash='dot'),
            marker=dict(size=6)
        ))
    
    # 4.4 Départements
    if show_departements and departement_series_dict:
        dept_idx = 0
        for dept_code, dept_info in departement_series_dict.items():
            if not dept_info['data'].empty:
                color_idx = dept_idx % len(dept_colors)
                fig.add_trace(go.Scatter(
                    x=dept_info['data']['date'],
                    y=dept_info['data']['valeur'],
                    mode='lines+markers',
                    name=f"Département {dept_info['libelle']}",
                    line=dict(color=dept_colors[color_idx], width=2, dash='dashdot'),
                    marker=dict(size=6)
                ))
                dept_idx += 1
    
    # 4.5 Régions
    if show_regions and region_series_dict:
        reg_idx = 0
        for region_code, region_info in region_series_dict.items():
            if not region_info['data'].empty:
                color_idx = reg_idx % len(region_colors)
                fig.add_trace(go.Scatter(
                    x=region_info['data']['date'],
                    y=region_info['data']['valeur'],
                    mode='lines+markers',
                    name=f"Région {region_info['libelle']}",
                    line=dict(color=region_colors[color_idx], width=2, dash='dot'),
                    marker=dict(size=7)
                ))
                reg_idx += 1
    
    # Mise en forme
    fig.update_layout(
        title=f"Évolution de {selected_indicator_info['groupe_nom'] if selected_indicator_info['type'] == 'groupe' else selected_indicator_info['indicateur_nom']}",
        xaxis_title="Date",
        yaxis_title="Valeur",
        hovermode='x unified',
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1
        ),
        height=400,
        margin=dict(l=50, r=50, t=80, b=50),
        xaxis=dict(
            tickformat="%d/%m/%Y",
            tickangle=45
        ),
        yaxis=dict(
            showgrid=True,
            gridwidth=1,
            gridcolor='lightgray'
        )
    )
    
    st.plotly_chart(fig, use_container_width=True)

# ============================================================================
# FONCTION PRINCIPALE D'AFFICHAGE
# ============================================================================

def show(data):
    # Charger les sources et les groupes
    indicator_sources, groups_dict, indicator_to_group, descriptions_dict, thematiques_dict = load_indicator_sources_and_groups()
    
    # Charger les données de ménages
    menages_data, _ = load_menages_data()
    
    st.title("📊 Visualisation Cartographique des indicateurs de l'ORTB")
    
    # Filtrer les échelles disponibles
    available_echelles = {}
    for key, config in ECHELLES_CONFIG.items():
        if data.get(key) is not None and not data[key].empty:
            available_echelles[key] = config
    
    if not available_echelles:
        st.error("Aucune donnée disponible")
        return
    
    common_themes = get_common_themes(data, thematiques_dict)
    
    # Contrôles principaux
    col1, col2, col3, col4 = st.columns([1, 0.7, 1.5, 0.6])
    
    with col1:
        echelle_keys = list(available_echelles.keys())
        echelle_labels = [config['label'] for config in available_echelles.values()]
        selected_echelle_label = st.radio("Échelle", options=echelle_labels, horizontal=True)
        
        # Trouver la clé correspondante
        echelle = None
        for key, config in available_echelles.items():
            if config['label'] == selected_echelle_label:
                echelle = key
                break
    
    # Récupérer le DataFrame correspondant
    df_to_use = data.get(echelle)
    config = ECHELLES_CONFIG[echelle]
    code_col = config['code_col']
    libelle_col = config['libelle_col']
    
    with col2:
        if common_themes:
            selected_thematique = st.selectbox("Thématique", ["Toutes"] + list(common_themes))
        else:
            selected_thematique = "Toutes"
    
    with col3:
        # Filtrer par thématique
        if selected_thematique != "Toutes":
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
    col_norm, col_palette, col_echelle = st.columns([0.5, 0.5, 0.7])

    with col_norm:
        normalisation_options = ["Aucune", "Par surface", "Par population", "Par ménages"]
        normalisation_option = st.selectbox("Normalisation", normalisation_options)

    with col_palette:
        palette_choices = ["Blues", "Greens", "Darkmint", "ice", "Reds"]
        selected_palette = st.selectbox("Palette", palette_choices)  # Renommer pour éviter confusion

    with col_echelle:
        col_scale, col_inv = st.columns([0.7, 0.3])
        with col_scale:
            stat_scale_choices = ["Auto", "Min-Max", "Percentiles", "Moyenne ± 2σ"]
            stat_scale = st.selectbox("Échelle", stat_scale_choices, index=0)
        with col_inv:
            st.write("")  # Pour aligner verticalement
            reverse_scale = st.checkbox("Inverser")
    # Données de normalisation
    surface_df, population_df = get_surface_population_data(df_to_use, echelle, selected_date)
    date_col = 'date'
    
    # Récupération des données
    menages_note = None
    
    if selected_indicator_info['type'] == 'individuel':
        filtered_df = df_to_use[
            (df_to_use['indicateur'] == selected_indicator_info['indicateur_nom']) & 
            (df_to_use['date'] == selected_date)
        ].copy()
        
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
                suffixe_titre = " (par ménages)"
                menages_note = "Attention: Du fait de la disponibilité de la donnée ménages uniquement pour 3 années (2012, 2017 et 2023), la division des données par le nombre de ménages se fait en utilisant la plus proche année antérieure. Exemple: Les données de 2020 seront divisées par les données de ménages de 2017"
            else:
                valeur_colonne = 'valeur'
                st.warning("Impossible de normaliser par ménages pour certains territoires")
        else:
            valeur_colonne = 'valeur'
            suffixe_titre = ""
        
        titre_indicateur = selected_indicator_info['indicateur_nom']
        source_key = selected_indicator_info['indicateur_nom']
        
    else:  # Groupe
        norm_option_for_group = "Aucune"
        if normalisation_option == "Par surface":
            norm_option_for_group = "Par surface (ha)"
        elif normalisation_option == "Par population":
            norm_option_for_group = "Par population (1000 hab.)"
        
        filtered_df = get_group_data(
            df_to_use,
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
        
        if normalisation_option == "Par ménages" and menages_data is not None:
            filtered_df, menages_notes = normalize_by_menages(filtered_df, code_col, date_col, menages_data)
            if 'valeur_normalisee' in filtered_df.columns:
                valeur_colonne = 'valeur_normalisee'
                suffixe_titre = " (par ménages)"
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
        
        titre_indicateur = format_group_title(
            selected_indicators_for_group, 
            indicator_to_group, 
            selected_indicator_info['groupe_nom']
        )
        source_key = None
    
    # === AFFICHAGE DE LA DESCRIPTION (AVANT LA CARTE) ===
    # Afficher la description avant la carte
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
    
    # Nettoyer les valeurs proches de 100
    if valeur_colonne in filtered_df.columns:
        mask_proche_100 = (filtered_df[valeur_colonne] - 100).abs() < SEUIL_CENT
        filtered_df.loc[mask_proche_100, valeur_colonne] = 100.0
    
    # Sélection automatique de l'échelle
    valeurs = filtered_df[valeur_colonne].dropna().values
    stat_scale_original = stat_scale
    if stat_scale == "Auto" and len(valeurs) > 0:
        suggested_scale = suggest_scale(valeurs)
        stat_scale = suggested_scale
    
    # Échelle de couleurs
    linear_scale, percentile_scale, std_scale = get_scale_options(filtered_df, valeur_colonne)
    format_str = f"{{:.{PRECISION_DECIMALES}f}}"
    
    if stat_scale == "Min-Max" and linear_scale:
        range_color = linear_scale
        scale_display_name = f"Min-Max (min={format_str.format(linear_scale[0])}, max={format_str.format(linear_scale[1])})"
    elif stat_scale == "Percentiles" and percentile_scale:
        range_color = percentile_scale
        scale_display_name = f"Percentiles (p5={format_str.format(percentile_scale[0])}, p95={format_str.format(percentile_scale[1])})"
    elif stat_scale == "Moyenne ± 2σ" and std_scale:
        range_color = std_scale
        scale_display_name = f"Moyenne ± 2σ (m-2σ={format_str.format(std_scale[0])}, m+2σ={format_str.format(std_scale[1])})"
    else:
        range_color = None
        scale_display_name = "Auto"
    
    if stat_scale_original == "Auto":
        scale_display_name = f"Auto → {scale_display_name}"
    
    color_scale = selected_palette + ("_r" if reverse_scale else "")
    
    # Création de la carte
    geojson = load_geojson(config['geojson'])
    center = config['center']
    
    source_text = ""
    if source_key and source_key in indicator_sources and pd.notna(indicator_sources[source_key]):
        source_text = f"<br><sub>Source : {indicator_sources[source_key]}</sub>"
    
    fig = px.choropleth(
        filtered_df,
        geojson=geojson,
        locations=code_col,
        featureidkey="properties.code",
        color=valeur_colonne,
        hover_name=libelle_col if libelle_col in filtered_df.columns else None,
        hover_data={valeur_colonne: f':.{PRECISION_DECIMALES}f'},
        color_continuous_scale=color_scale,
        range_color=range_color,
        scope="europe",
        center=center,
        title=f"{titre_indicateur}{suffixe_titre}<br><sub>Méthode : {scale_display_name}</sub>{source_text}")
    
    fig.update_geos(fitbounds="locations", visible=False)
    fig.update_layout(
        width=900, 
        height=700,
        margin=dict(l=0, r=0, t=30, b=10)
    )
    st.plotly_chart(fig, use_container_width=True)
    
    # === GRAPHE D'ÉVOLUTION TEMPORELLE ===
    # Récupérer le code du territoire sélectionné pour le graphe
    selected_territory_code = filtered_df[code_col].iloc[0] if not filtered_df.empty else None
    
    if selected_territory_code is not None:
        generate_evolution_graph(
            data=data,
            echelle=echelle,
            selected_indicator_info=selected_indicator_info,
            selected_territory_code=selected_territory_code,
            indicator_to_group=indicator_to_group,
            selected_indicators_for_group=selected_indicators_for_group
        )
    
    # Statistiques
    with st.expander("📈 Statistiques"):
        col_stat1, col_stat2, col_stat3 = st.columns(3)
        with col_stat1:
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
    
    # Données détaillées
    with st.expander("📋 Données détaillées"):
        date_str = selected_date.strftime('%d/%m/%Y')
        
        if selected_indicator_info['type'] == 'individuel':
            titre_detail = f"Données pour {selected_indicator_info['indicateur_nom']} - {date_str}"
        else:
            groupe_titre = format_group_title(
                selected_indicators_for_group, 
                indicator_to_group, 
                selected_indicator_info['groupe_nom']
            )
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
            st.caption(f"Indicateurs inclus : {liste_indicateurs}")
        
        st.markdown(f"**{titre_detail}**")
        
        display_cols = [libelle_col, code_col, valeur_colonne]
        display_cols = [col for col in display_cols if col in filtered_df.columns]
        display_df = filtered_df[display_cols].copy()
        
        display_df['Date'] = date_str
        
        if selected_indicator_info['type'] == 'individuel':
            display_df['Indicateur'] = selected_indicator_info['indicateur_nom']
        else:
            groupe_titre = format_group_title(
                selected_indicators_for_group, 
                indicator_to_group, 
                selected_indicator_info['groupe_nom']
            )
            display_df['Indicateur'] = groupe_titre
            
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
        
        if valeur_colonne in display_df.columns:
            mask_proche_100 = (display_df[valeur_colonne] - 100).abs() < SEUIL_CENT
            display_df.loc[mask_proche_100, valeur_colonne] = 100.0
            display_df[valeur_colonne] = display_df[valeur_colonne].round(PRECISION_DECIMALES)
        
        if valeur_colonne == 'valeur_normalisee':
            if normalisation_option == "Par surface":
                display_df.rename(columns={'valeur_normalisee': f'Valeur (par ha)'}, inplace=True)
            elif normalisation_option == "Par population":
                display_df.rename(columns={'valeur_normalisee': f'Valeur (pour 1000 hab.)'}, inplace=True)
            elif normalisation_option == "Par ménages":
                display_df.rename(columns={'valeur_normalisee': f'Valeur (par ménages)'}, inplace=True)
        elif valeur_colonne == 'valeur':
            display_df.rename(columns={'valeur': 'Valeur'}, inplace=True)
        
        st.dataframe(display_df, use_container_width=True, hide_index=True)
        
        if selected_indicator_info['type'] == 'groupe':
            selected_values = [indicator_to_group[ind].get('specific_value', '?') 
                             for ind in selected_indicators_for_group if ind in indicator_to_group]
            st.caption(f"Valeurs sélectionnées : {', '.join(selected_values)}")