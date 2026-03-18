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

# Nombre de décimales pour l'affichage des valeurs
PRECISION_DECIMALES = 2  # Modifiez cette valeur (0, 1, 2, 3, etc.)

# Seuil pour considérer qu'une somme est égale à 100 (pour les pourcentages)
SEUIL_CENT = 0.01  # Si |somme - 100| < seuil, on considère que c'est 100

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
        # Créer un dictionnaire Groupe -> nom_groupe
        group_names = dict(zip(groups_df['Groupe'].astype(str), groups_df['nom_groupe']))
        return group_names
    except Exception as e:
        st.warning(f"Fichier denomination_groupes.csv non trouvé ou invalide: {e}")
        return {}

@st.cache_data
def load_indicator_sources_and_groups():
    """Charge les sources et les groupes des indicateurs depuis le fichier CSV"""
    try:
        sources_df = pd.read_csv("data/columns_indicateurs.csv", sep=",")
        
        # Déterminer le nom de la colonne indicateur
        if 'Nouveau_nom_indicateur' in sources_df.columns:
            indicator_col = 'Nouveau_nom_indicateur'
        else:
            indicator_col = 'Indicateur'
        
        # Charger les sources
        sources_dict = dict(zip(sources_df[indicator_col], sources_df.get('Source', '')))
        
        # Charger les groupes si la colonne existe
        groups_dict = {}
        indicator_to_group = {}
        
        # Charger les noms des groupes
        group_names = load_group_names()
        
        if 'Groupe' in sources_df.columns:
            # Filtrer les lignes avec un groupe défini (non nul et différent de 0)
            grouped_indicators = sources_df[sources_df['Groupe'].notna() & (sources_df['Groupe'] != 0)]
            
            for groupe_value in grouped_indicators['Groupe'].unique():
                # Convertir en string pour la cohérence
                groupe_value_str = str(groupe_value)
                
                # Récupérer tous les indicateurs de ce groupe
                group_indicators = grouped_indicators[grouped_indicators['Groupe'] == groupe_value][indicator_col].tolist()
                
                if len(group_indicators) >= 1:
                    # Utiliser le nom du groupe depuis le fichier de dénomination
                    display_name = group_names.get(groupe_value_str, f"Groupe {groupe_value}")
                    
                    # Nettoyer le nom d'affichage
                    display_name = re.sub(r'\s+', ' ', display_name).strip()
                    
                    groups_dict[groupe_value_str] = {
                        'indicateurs': group_indicators,
                        'display_name': display_name,
                        'original_value': groupe_value
                    }
                    
                    # Créer le mapping indicateur -> groupe
                    for ind in group_indicators:
                        # Extraire la valeur spécifique pour cet indicateur
                        specific_value = extract_specific_value(ind, display_name)
                        
                        indicator_to_group[ind] = {
                            'groupe': groupe_value_str,
                            'display_name': display_name,
                            'specific_value': specific_value,
                            'original_value': groupe_value
                        }
        
        return sources_dict, groups_dict, indicator_to_group
        
    except Exception as e:
        st.warning(f"Impossible de charger les sources et groupes des indicateurs: {e}")
        return {}, {}, {}

def extract_specific_value(indicator_name, group_name):
    """
    Extrait la valeur spécifique d'un indicateur en enlevant le nom du groupe.
    Gère correctement les parenthèses.
    """
    
    # 1. Nettoyer le nom du groupe pour la recherche
    # Enlever les parenthèses et leur contenu pour la comparaison
    group_for_search = re.sub(r'\([^)]*\)', '', group_name).strip()
    group_for_search = re.sub(r'\s+', ' ', group_for_search)
    
    # 2. Chercher le groupe dans l'indicateur
    if group_for_search in indicator_name:
        # Récupérer la partie après le groupe
        specific = indicator_name.split(group_for_search, 1)[-1].strip()
    else:
        # Essayer avec une version sans accents/casse
        indicator_lower = indicator_name.lower()
        group_lower = group_for_search.lower()
        
        if group_lower in indicator_lower:
            # Trouver la position dans la chaîne originale
            start_pos = indicator_lower.find(group_lower)
            specific = indicator_name[start_pos + len(group_for_search):].strip()
        else:
            # Prendre ce qui est entre parenthèses en priorité
            paren_match = re.search(r'\(([^)]+)\)', indicator_name)
            if paren_match:
                specific = paren_match.group(1).strip()
            else:
                # Prendre le dernier mot
                words = indicator_name.split()
                specific = words[-1] if words else "?"
    
    # 3. Nettoyer la valeur spécifique
    # Enlever les parenthèses superflues
    specific = re.sub(r'^[\(\s\)]+|[\(\s\)]+$', '', specific)
    # Enlever les parenthèses ouvrantes spécifiquement
    specific = re.sub(r'\(', '', specific)
    # Enlever les parenthèses fermantes
    specific = re.sub(r'\)', '', specific)
    # Enlever les %
    specific = re.sub(r'%', '', specific)
    # Normaliser les espaces
    specific = re.sub(r'\s+', ' ', specific)
    
    # 4. Si la valeur est trop longue, prendre une version courte
    if len(specific) > 30:
        # Chercher un pattern comme "E", "1", "Non classé" à la fin
        short_match = re.search(r'([A-Za-z0-9\s]+)$', specific)
        if short_match:
            specific = short_match.group(1).strip()
        else:
            specific = specific[:30] + "..."
    
    # 5. Valeur par défaut si vide
    if not specific or specific == '':
        # Chercher ce qui est entre parenthèses
        paren_match = re.search(r'\(([^)]+)\)', indicator_name)
        if paren_match:
            specific = paren_match.group(1).strip()
        else:
            specific = indicator_name.split()[-1] if indicator_name.split() else "?"
    
    return specific.strip()

# ============================================================================
# FONCTIONS DE NORMALISATION
# ============================================================================

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

def calculate_evolution(df_courant, df_reference, valeur_colonne):
    """Calcule l'évolution entre deux périodes"""
    if df_reference is None or df_reference.empty:
        return df_courant.copy()
    
    # Fusionner les deux DataFrames
    evolution_df = df_courant.merge(
        df_reference[['code_commune' if 'code_commune' in df_reference.columns else 'code_epci', 
                      valeur_colonne]].rename(columns={valeur_colonne: 'valeur_reference'}),
        on='code_commune' if 'code_commune' in df_courant.columns else 'code_epci',
        how='left'
    )
    
    # Calculer l'évolution (en pourcentage)
    evolution_df['valeur_evolution'] = (evolution_df[valeur_colonne] - evolution_df['valeur_reference']) 
    
    # Remplacer les valeurs infinies par NaN
    evolution_df['valeur_evolution'] = evolution_df['valeur_evolution'].replace([np.inf, -np.inf], np.nan)
    
    return evolution_df

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

def get_common_themes(df, epci_df):
    """Récupère les thématiques communes"""
    themes_communes = set(df['thematique'].dropna().unique()) if df is not None else set()
    themes_epci = set(epci_df['thematique'].dropna().unique()) if epci_df is not None else set()
    
    themes_communs = themes_communes.intersection(themes_epci)
    
    if not themes_communs:
        return sorted(themes_communes) if themes_communes else sorted(themes_epci)
    
    return sorted(themes_communs)

# ============================================================================
# FONCTIONS DE GESTION DES GROUPES
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
    
    # Récupérer les valeurs spécifiques pour chaque indicateur
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
                # Chercher un contexte dans le nom original
                context_match = re.search(r'\(([^)]+)\)', ind)
                if context_match:
                    context = context_match.group(1)
                    display = f"{specific_value} ({context})"
                else:
                    # Prendre le dernier mot comme contexte
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
    # Si toutes les valeurs sont entre 0 et 100 et que la somme est proche de 100
    if (pivot_data[selected_indicators].max().max() <= 105 and  # Max pas trop grand
        pivot_data[selected_indicators].min().min() >= -5):     # Min pas trop petit (tolérance pour arrondis)
        
        # Calculer la différence avec 100
        diff_avec_100 = (pivot_data['valeur_somme'] - 100).abs()
        
        # Si la différence est inférieure au seuil, on fixe à 100
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
# FONCTION PRINCIPALE D'AFFICHAGE
# ============================================================================

def show(df, epci_df):
    # Charger les sources et les groupes
    indicator_sources, groups_dict, indicator_to_group = load_indicator_sources_and_groups()
    
    st.title("📊 Visualisation Cartographique des indicateurs de l'ORTB")
    
    common_themes = get_common_themes(df, epci_df)
    
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
        
        if selected_thematique != "Toutes" and 'thematique' in df_to_use.columns:
            filtered_df_theme = df_to_use[df_to_use['thematique'] == selected_thematique]
            available_indicators = get_available_indicators_with_groups(filtered_df_theme, groups_dict, indicator_to_group)
        else:
            available_indicators = get_available_indicators_with_groups(df_to_use, groups_dict, indicator_to_group)
        
        if not available_indicators:
            st.error("Aucun indicateur disponible")
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
    
    # Normalisation, évolution et couleurs
    st.markdown("---")
    
    # Vérifier si plusieurs dates sont disponibles pour l'évolution
    plusieurs_dates = len(dates_disponibles) > 1
    
    col_norm, col_evo, col_scale1, col_scale2 = st.columns([0.5, 0.4, 0.5, 0.5])
    
    with col_norm:
        normalisation_option = st.selectbox("Normalisation", 
                                          ["Aucune", "Par surface", "Par population"])
    
    with col_evo:
        if plusieurs_dates:
            evolution_option = st.selectbox(
                "Évolution",
                ["Aucune", "Par rapport à l'année précédente", "Par rapport à une année spécifique"]
            )
            
            if evolution_option == "Par rapport à une année spécifique":
                # Filtrer les dates autres que la date sélectionnée
                autres_dates = [d for d in dates_disponibles if d != selected_date]
                date_reference_str = st.selectbox(
                    "Année de référence",
                    [d.strftime('%d/%m/%Y') for d in autres_dates],
                    index=len(autres_dates)-1 if autres_dates else 0,
                    key="date_reference"
                )
                date_reference = datetime.strptime(date_reference_str, '%d/%m/%Y')
            elif evolution_option == "Par rapport à l'année précédente":
                # Trouver l'année précédente (la plus proche avant la date sélectionnée)
                dates_anterieures = [d for d in dates_disponibles if d < selected_date]
                if dates_anterieures:
                    date_reference = max(dates_anterieures)
                else:
                    st.warning("Pas d'année précédente disponible")
                    evolution_option = "Aucune"
                    date_reference = None
            else:
                date_reference = None
        else:
            evolution_option = "Aucune"
            date_reference = None
            st.caption("Évolution non disponible (une seule date)")
    
    with col_scale1:
        scale_options = st.selectbox("Palette", ["Blues", "Greens", "Darkmint", "ice", "Reds"])
    
    with col_scale2:
        stat_scale = st.selectbox("Échelle", ["Min-Max", "Percentiles", "Moyenne ± 2σ"])
        reverse_scale = st.checkbox("Inverser")
    
    # Données de normalisation
    if echelle == "Commune":
        surface_df, population_df = get_surface_population_data(df, "Commune", selected_date)
        code_col = 'code_commune'
    else:
        surface_df, population_df = get_surface_population_data(epci_df, "EPCI", selected_date)
        code_col = 'code_epci'
    
    # Récupération des données pour la date courante
    if selected_indicator_info['type'] == 'individuel':
        if echelle == "Commune":
            filtered_df = df[(df['indicateur'] == selected_indicator_info['indicateur_nom']) & 
                           (df['date'] == selected_date)].copy()
        else:
            filtered_df = epci_df[(epci_df['indicateur'] == selected_indicator_info['indicateur_nom']) & 
                                 (epci_df['date'] == selected_date)].copy()
        
        if normalisation_option == "Par surface" and surface_df is not None:
            filtered_df = normalize_by_surface(filtered_df, code_col, surface_df)
            valeur_colonne = 'valeur_normalisee'
            suffixe_titre = " (par hectare)"
        elif normalisation_option == "Par population" and population_df is not None:
            filtered_df = normalize_by_population(filtered_df, code_col, population_df)
            valeur_colonne = 'valeur_normalisee'
            suffixe_titre = " (pour 1000 hab.)"
        else:
            valeur_colonne = 'valeur'
            suffixe_titre = ""
        
        titre_indicateur = selected_indicator_info['indicateur_nom']
        source_key = selected_indicator_info['indicateur_nom']
        
    else:
        # Convertir l'option de normalisation
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
        
        # Pour l'affichage, arrondir les valeurs proches de 100
        if 'valeur' in filtered_df.columns:
            # Si la valeur est très proche de 100 (à 0.01 près), on affiche 100
            mask_proche_100 = (filtered_df['valeur'] - 100).abs() < SEUIL_CENT
            filtered_df.loc[mask_proche_100, 'valeur'] = 100.0
        
        if 'valeur_normalisee' in filtered_df.columns:
            mask_proche_100_norm = (filtered_df['valeur_normalisee'] - 100).abs() < SEUIL_CENT
            filtered_df.loc[mask_proche_100_norm, 'valeur_normalisee'] = 100.0
        
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
        
        titre_indicateur = f"📊 {selected_indicator_info['groupe_nom']}"
        source_key = None
    
    # Récupération des données pour la date de référence (si évolution)
    if evolution_option != "Aucune" and date_reference is not None:
        if selected_indicator_info['type'] == 'individuel':
            if echelle == "Commune":
                reference_df = df[(df['indicateur'] == selected_indicator_info['indicateur_nom']) & 
                                 (df['date'] == date_reference)].copy()
            else:
                reference_df = epci_df[(epci_df['indicateur'] == selected_indicator_info['indicateur_nom']) & 
                                      (epci_df['date'] == date_reference)].copy()
        else:
            reference_df = get_group_data(
                df_to_use if echelle == "Commune" else epci_df,
                selected_indicator_info,
                selected_indicators_for_group,
                code_col,
                date_reference,
                norm_option_for_group,
                surface_df,
                population_df
            )
        
        # Calculer l'évolution
        if reference_df is not None and not reference_df.empty:
            evolution_df = calculate_evolution(filtered_df, reference_df, valeur_colonne)
            filtered_df = evolution_df
            valeur_colonne = 'valeur_evolution'
            suffixe_titre = " (%)"
            titre_indicateur = f"Évolution de {titre_indicateur}"
    
    # Échelle de couleurs - s'assurer que 100 est bien inclus
    if valeur_colonne in filtered_df.columns and valeur_colonne != 'valeur_evolution':
        # Si on a des valeurs très proches de 100, s'assurer que l'échelle va jusqu'à 100
        max_val = filtered_df[valeur_colonne].max()
        if abs(max_val - 100) < SEUIL_CENT:
            # Remplacer par 100 pour l'échelle
            filtered_df.loc[filtered_df[valeur_colonne] == max_val, valeur_colonne] = 100.0
    
    # Échelle de couleurs avec précision configurable
    linear_scale, percentile_scale, std_scale = get_scale_options(filtered_df, valeur_colonne)
    
    # Formater les notes avec la précision définie
    format_str = f"{{:.{PRECISION_DECIMALES}f}}"
    
    if stat_scale == "Min-Max" and linear_scale:
        range_color = linear_scale
        range_note = f"min={format_str.format(linear_scale[0])}, max={format_str.format(linear_scale[1])}"
    elif stat_scale == "Percentiles" and percentile_scale:
        range_color = percentile_scale
        range_note = f"p5={format_str.format(percentile_scale[0])}, p95={format_str.format(percentile_scale[1])}"
    elif stat_scale == "Moyenne ± 2σ" and std_scale:
        range_color = std_scale
        range_note = f"m±2σ=[{format_str.format(std_scale[0])}, {format_str.format(std_scale[1])}]"
    else:
        range_color = None
        range_note = "Auto"
    
    color_scale = scale_options + ("_r" if reverse_scale else "")
    
    # Création de la carte
    if echelle == "Commune":
        communes_geojson = load_geojson("data/communes_simple.geojson")
        
        source_text = ""
        if source_key and source_key in indicator_sources and pd.notna(indicator_sources[source_key]):
            source_text = f"<br><sub>Source : {indicator_sources[source_key]}</sub>"
        
        # Ajouter la date de référence dans le titre si évolution
        if evolution_option != "Aucune" and date_reference is not None:
            titre_complet = f"{titre_indicateur}{suffixe_titre} entre {date_reference.strftime('%d/%m/%Y')} et {selected_date_str}"
        else:
            titre_complet = f"{titre_indicateur}{suffixe_titre} au {selected_date_str}"
        
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
            title=f"{titre_complet}<br><sub>{range_note}</sub>{source_text}")
        
    else:
        epci_geojson = load_geojson("data/epci_simple.geojson")
        
        source_text = ""
        if source_key and source_key in indicator_sources and pd.notna(indicator_sources[source_key]):
            source_text = f"<br><sub>Source : {indicator_sources[source_key]}</sub>"
        
        # Ajouter la date de référence dans le titre si évolution
        if evolution_option != "Aucune" and date_reference is not None:
            titre_complet = f"{titre_indicateur}{suffixe_titre} entre {date_reference.strftime('%d/%m/%Y')} et {selected_date_str}"
        else:
            titre_complet = f"{titre_indicateur}{suffixe_titre} au {selected_date_str}"
        
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
            title=f"{titre_complet}<br><sub>{range_note}</sub>{source_text}")
    
    fig.update_geos(fitbounds="locations", visible=False)
    fig.update_layout(width=1000, height=1000, margin=dict(l=0, r=0, t=50, b=0))
    st.plotly_chart(fig, use_container_width=True)
    
    # Statistiques avec la précision configurée
    with st.expander("📈 Statistiques"):
        col_stat1, col_stat2, col_stat3 = st.columns(3)
        with col_stat1:
            # Pour la moyenne, on peut aussi arrondir les valeurs proches de 100
            mean_val = filtered_df[valeur_colonne].mean()
            if not np.isnan(mean_val):
                if abs(mean_val - 100) < SEUIL_CENT and valeur_colonne != 'valeur_evolution':
                    mean_val = 100.0
                st.metric("Moyenne", format_str.format(mean_val))
            else:
                st.metric("Moyenne", "N/A")
        with col_stat2:
            median_val = filtered_df[valeur_colonne].median()
            if not np.isnan(median_val):
                if abs(median_val - 100) < SEUIL_CENT and valeur_colonne != 'valeur_evolution':
                    median_val = 100.0
                st.metric("Médiane", format_str.format(median_val))
            else:
                st.metric("Médiane", "N/A")
        with col_stat3:
            std_val = filtered_df[valeur_colonne].std()
            if not np.isnan(std_val):
                st.metric("Écart-type", format_str.format(std_val))
            else:
                st.metric("Écart-type", "N/A")
    
    # Données détaillées avec la précision configurée
    with st.expander("📋 Données détaillées"):
        if echelle == "Commune":
            display_cols = ['libelle_commune', 'code_commune', valeur_colonne]
        else:
            display_cols = ['libelle_epci', 'code_epci', valeur_colonne]
        
        display_cols = [col for col in display_cols if col in filtered_df.columns]
        display_df = filtered_df[display_cols].copy()
        
        # Arrondir les valeurs et corriger celles proches de 100 (sauf pour l'évolution)
        if valeur_colonne in display_df.columns:
            if valeur_colonne != 'valeur_evolution':
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
        elif valeur_colonne == 'valeur':
            display_df.rename(columns={'valeur': 'Valeur'}, inplace=True)
        elif valeur_colonne == 'valeur_evolution':
            display_df.rename(columns={'valeur_evolution': f'Évolution (%)'}, inplace=True)
        
        st.dataframe(display_df, use_container_width=True, hide_index=True)
        
        if selected_indicator_info['type'] == 'groupe' and 'valeur_evolution' not in valeur_colonne:
            selected_values = [indicator_to_group[ind].get('specific_value', '?') 
                             for ind in selected_indicators_for_group if ind in indicator_to_group]
            st.caption(f"Valeurs sélectionnées : {', '.join(selected_values)}")
