import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import json
import numpy as np
import os

# Ne pas utiliser st.set_page_config ici car il est déjà configuré dans app.py

def load_carburant_data(filepath, code_col, libelle_col):
    """Charge un fichier de données de carburants avec les colonnes standardisées"""
    try:
        df = pd.read_csv(filepath)
        # Essayer plusieurs formats de date
        try:
            df['date'] = pd.to_datetime(df['date'], format='%Y-%m-%d', errors='coerce')
        except:
            try:
                df['date'] = pd.to_datetime(df['date'], format='%d/%m/%Y', errors='coerce')
            except:
                df['date'] = pd.to_datetime(df['date'], errors='coerce')
        
        df[code_col] = df[code_col].astype(str)
        df = df.dropna(subset=['date'])
        if 'valeur' in df.columns:
            df['valeur'] = pd.to_numeric(df['valeur'], errors='coerce')
            df = df.dropna(subset=['valeur'])
        return df
    except Exception as e:
        st.warning(f"Impossible de charger {filepath}: {e}")
        return None

@st.cache_data
def load_carburant_data_all():
    """Charge toutes les données carburant (EPCI, départements, régions)"""
    data = {}
    
    # Charger les EPCI
    data['epci'] = load_carburant_data('data/prix_carburants_epci_2013_2026.csv', 'code_epci', 'libelle_epci')
    
    # Charger les départements
    data['departements'] = load_carburant_data('data/prix_carburants_departement_2013_2026.csv', 'code_departement', 'libelle_departement')
    
    # Charger les régions
    data['regions'] = load_carburant_data('data/prix_carburants_region_2013_2026.csv', 'code_region', 'libelle_region')
    
    # Nettoyer les libellés
    for key in data:
        if data[key] is not None:
            if key == 'departements':
                libelle_col = 'libelle_departement'
            elif key == 'epci':
                libelle_col = 'libelle_epci'
            else:
                libelle_col = f"libelle_{key[:-1]}"
            
            if libelle_col in data[key].columns:
                data[key][libelle_col] = data[key][libelle_col].str.strip()
    
    return data

@st.cache_data
def load_energy_prices():
    """Charge les données des prix du pétrole et du gaz naturel"""
    energy_data = {}
    
    # Charger le pétrole Brent ($)
    try:
        brent = pd.read_csv('data/Prix_moyen_petrole_brent.csv')
        try:
            brent['date'] = pd.to_datetime(brent['date'], format='%d/%m/%Y', errors='coerce')
        except:
            brent['date'] = pd.to_datetime(brent['date'], errors='coerce')
        brent = brent.dropna(subset=['date'])
        if 'valeur' in brent.columns:
            brent['valeur'] = pd.to_numeric(brent['valeur'], errors='coerce')
        energy_data['brent'] = brent
    except Exception as e:
        st.warning(f"Impossible de charger les données du pétrole Brent ($): {e}")
    
    # Charger le pétrole Brent (EURO)
    try:
        brent_euro = pd.read_csv('data/Prix_moyen_petrole_brent_euro.csv')
        try:
            brent_euro['date'] = pd.to_datetime(brent_euro['date'], format='%d/%m/%Y', errors='coerce')
        except:
            brent_euro['date'] = pd.to_datetime(brent_euro['date'], errors='coerce')
        brent_euro = brent_euro.dropna(subset=['date'])
        if 'valeur' in brent_euro.columns:
            brent_euro['valeur'] = pd.to_numeric(brent_euro['valeur'], errors='coerce')
        energy_data['brent_euro'] = brent_euro
    except Exception as e:
        st.warning(f"Impossible de charger les données du pétrole Brent (Euro): {e}")
    
    # Charger le gaz naturel
    try:
        gaz = pd.read_csv('data/Prix_moyen_gaz_naturel.csv')
        try:
            gaz['date'] = pd.to_datetime(gaz['date'], format='%d/%m/%Y', errors='coerce')
        except:
            gaz['date'] = pd.to_datetime(gaz['date'], errors='coerce')
        gaz = gaz.dropna(subset=['date'])
        if 'valeur' in gaz.columns:
            gaz['valeur'] = pd.to_numeric(gaz['valeur'], errors='coerce')
        energy_data['gaz'] = gaz
    except Exception as e:
        st.warning(f"Impossible de charger les données du gaz naturel: {e}")
    
    return energy_data if energy_data else None

@st.cache_data
def load_motorisation_data():
    """Charge les données de motorisation des voitures neuves"""
    try:
        df = pd.read_csv('data/final_df_region.csv')
        df['date'] = pd.to_datetime(df['date'], format='%d/%m/%Y', errors='coerce')
        
        # Filtrer les indicateurs de motorisation
        motorisation_indicators = [
            'pourcentage_des_voitures_neuves_de_motorisation_Gaz',
            'pourcentage_des_voitures_neuves_de_motorisation_Hybride rechargeable',
            'pourcentage_des_voitures_neuves_de_motorisation_Essence',
            'pourcentage_des_voitures_neuves_de_motorisation_Electrique et hydrogène',
            'pourcentage_des_voitures_neuves_de_motorisation_Diesel'
        ]
        
        # Garder uniquement les lignes correspondant aux indicateurs de motorisation
        motorisation_df = df[df['indicateur'].isin(motorisation_indicators)].copy()
        
        # Extraire le type de motorisation du nom de l'indicateur
        motorisation_df['motorisation'] = motorisation_df['indicateur'].str.replace(
            'pourcentage_des_voitures_neuves_de_motorisation_', ''
        )
        
        return motorisation_df
    except Exception as e:
        st.warning(f"Impossible de charger les données de motorisation: {e}")
        return None

@st.cache_data
def load_geojson_for_echelle(echelle):
    """Charge le fichier GeoJSON approprié selon l'échelle"""
    geojson_files = {
        'regions': 'data/region-bretagne.geojson',
        'departements': 'data/departements-bretagne.geojson',
        'epci': 'data/epci_simple.geojson'
    }
    
    try:
        filepath = geojson_files.get(echelle)
        if filepath and os.path.exists(filepath):
            with open(filepath, 'r', encoding='utf-8') as f:
                geojson = json.load(f)
            return geojson
        else:
            return None
    except Exception as e:
        st.warning(f"Impossible de charger le GeoJSON pour {echelle}: {e}")
        return None

def prepare_map_data(df, echelle_code, libelle_col, carburant_type, date_choice):
    """Prépare les données pour la carte"""
    if df is None or df.empty:
        return None
    
    # Filtrer par carburant
    filtered = df[df['indicateur'].str.contains(carburant_type, case=False, na=False)]
    
    if filtered.empty:
        return None
    
    # Filtrer par date
    date_choice = pd.Timestamp(date_choice)
    filtered['date'] = pd.to_datetime(filtered['date'])
    date_mask = (filtered['date'].dt.date == date_choice.date())
    filtered = filtered[date_mask]
    
    if filtered.empty:
        return None
    
    # Grouper par entité pour avoir une valeur par entité
    result = filtered.groupby([echelle_code, libelle_col])['valeur'].mean().reset_index()
    
    return result

def show():
    st.title("⛽ Évolution du prix des carburants")
    
    # Charger les données
    carburant_data = load_carburant_data_all()
    energy_data = load_energy_prices()
    motorisation_data = load_motorisation_data()
    
    if not carburant_data or all(df is None for df in carburant_data.values()):
        st.error("Impossible de charger les données des carburants.")
        return
    
    # --- SECTION 1: Carte des prix ---
    st.header("🗺️ Carte des prix des carburants")
    st.markdown("Visualisez le prix d'un carburant à une date donnée sur une carte interactive.<br>Les prix affichés correspondent à la moyenne des prix des stations services du territoire, à la date considérée", unsafe_allow_html=True)
    
    # Sélecteurs pour la carte
    col1, col2, col3 = st.columns(3)
    
    with col1:
        echelle_options = {
            'epci': 'EPCI',
            'departements': 'Départements',
            'regions': 'Régions'
        }
        echelle_choice = st.selectbox(
            "Échelle géographique",
            options=list(echelle_options.keys()),
            format_func=lambda x: echelle_options[x],
            key="map_echelle"
        )
    
    with col2:
        carburants = ['SP95', 'SP98', 'Gazole' ,'E10', 'E85', 'GPLc']
        carburant_choice = st.selectbox(
            "Type de carburant",
            options=carburants,
            key="map_carburant"
        )
    
    with col3:
        df_carb = carburant_data.get(echelle_choice)
        if df_carb is not None and not df_carb.empty:
            carb_filter = df_carb[df_carb['indicateur'].str.contains(carburant_choice, case=False, na=False)]
            if not carb_filter.empty:
                available_dates = sorted(carb_filter['date'].unique())
            else:
                available_dates = sorted(df_carb['date'].unique())
            
            if len(available_dates) > 0:
                default_date = available_dates[-1]
                date_choice = st.date_input(
                    "Date",
                    value=default_date,
                    min_value=available_dates[0],
                    max_value=available_dates[-1],
                    key="map_date"
                )
                date_choice = pd.Timestamp(date_choice)
            else:
                st.warning("Aucune date disponible")
                date_choice = pd.Timestamp(datetime.now().date())
        else:
            st.warning("Aucune donnée disponible")
            date_choice = pd.Timestamp(datetime.now().date())
    
    # Afficher la carte
    if carburant_data.get(echelle_choice) is not None:
        # Déterminer les noms de colonnes
        if echelle_choice == 'departements':
            code_col = 'code_departement'
            libelle_col = 'libelle_departement'
        elif echelle_choice == 'epci':
            code_col = 'code_epci'
            libelle_col = 'libelle_epci'
        else:  # regions
            code_col = 'code_region'
            libelle_col = 'libelle_region'
        
        map_data = prepare_map_data(
            carburant_data[echelle_choice], 
            code_col, 
            libelle_col, 
            carburant_choice, 
            date_choice
        )
        
        if map_data is not None and not map_data.empty:
            geojson = load_geojson_for_echelle(echelle_choice)
            
            if geojson:
                try:
                    fig = px.choropleth(
                        map_data,
                        geojson=geojson,
                        locations=code_col,
                        featureidkey="properties.code",
                        color='valeur',
                        color_continuous_scale="Greens",
                        range_color=(map_data['valeur'].min(), map_data['valeur'].max()),
                        scope="europe",
                        center={"lat": 48.1, "lon": -3.0},
                        labels={'valeur': f'Prix {carburant_choice} (€/L)'},
                        hover_data={code_col: False, libelle_col: True, 'valeur': ':.3f'},
                        title=f'Prix du {carburant_choice} - {date_choice.strftime("%d/%m/%Y")}'
                    )
                    
                    fig.update_geos(fitbounds="locations", visible=False)
                    fig.update_layout(
                        width=500,
                        height=500,
                        margin=dict(l=0, r=0, t=0, b=10)
                    )
                    st.plotly_chart(fig, use_container_width=True)
                    
                    with st.expander("📊 Données détaillées"):
                        st.dataframe(map_data.sort_values('valeur', ascending=False), use_container_width=True)
                        
                        csv = map_data.to_csv(index=False)
                        st.download_button(
                            label="Télécharger les données (CSV)",
                            data=csv,
                            file_name=f"prix_{carburant_choice}_{date_choice.strftime('%Y-%m-%d')}_{echelle_choice}.csv",
                            mime="text/csv"
                        )
                        
                except Exception as e:
                    st.error(f"Erreur lors de la création de la carte: {e}")
                    
                    # Essayer avec featureidkey différent si "code" ne fonctionne pas
                    try:
                        first_feature = geojson['features'][0]
                        properties = first_feature.get('properties', {})
                        
                        possible_keys = ['code', 'CODE', 'code_epci', 'code_departement', 'code_region', 'id', 'ID', 'SIREN']
                        code_key = None
                        for key in possible_keys:
                            if key in properties:
                                code_key = key
                                break
                        
                        if code_key is None and properties:
                            code_key = list(properties.keys())[0]
                        
                        if code_key:
                            fig = px.choropleth(
                                map_data,
                                geojson=geojson,
                                locations=code_col,
                                featureidkey=f"properties.{code_key}",
                                color='valeur',
                                color_continuous_scale="Viridis",
                                range_color=(map_data['valeur'].min(), map_data['valeur'].max()),
                                scope="europe",
                                center={"lat": 48.1, "lon": -3.0},
                                labels={'valeur': f'Prix {carburant_choice} (€/L)'},
                                hover_data={code_col: False, libelle_col: True, 'valeur': ':.3f'},
                                title=f'Prix du {carburant_choice} - {date_choice.strftime("%d/%m/%Y")}'
                            )
                            fig.update_geos(fitbounds="locations", visible=False)
                            fig.update_layout(
                                width=900,
                                height=700,
                                margin=dict(l=0, r=0, t=30, b=10)
                            )
                            st.plotly_chart(fig, use_container_width=True)
                        else:
                            st.subheader("Affichage alternatif - Données en tableau")
                            st.dataframe(map_data.sort_values('valeur', ascending=False), use_container_width=True)
                    except Exception as e2:
                        st.error(f"Erreur lors de la tentative alternative: {e2}")
                        st.subheader("Affichage alternatif - Données en tableau")
                        st.dataframe(map_data.sort_values('valeur', ascending=False), use_container_width=True)
            else:
                st.info("GeoJSON non disponible. Affichage des prix sous forme de graphique à barres.")
                
                fig = px.bar(
                    map_data.sort_values('valeur', ascending=False).head(20),
                    x=libelle_col,
                    y='valeur',
                    title=f'Prix moyen du {carburant_choice} par {echelle_options[echelle_choice].lower()} le {date_choice.strftime("%d/%m/%Y")}',
                    labels={libelle_col: echelle_options[echelle_choice], 'valeur': f'Prix {carburant_choice} (€/L)'},
                    color='valeur',
                    color_continuous_scale="Viridis",
                    text='valeur'
                )
                
                fig.update_traces(texttemplate='%{text:.3f}', textposition='outside')
                fig.update_layout(height=500)
                st.plotly_chart(fig, use_container_width=True)
                
                st.dataframe(map_data.sort_values('valeur', ascending=False), use_container_width=True)
                
                csv = map_data.to_csv(index=False)
                st.download_button(
                    label="Télécharger les données (CSV)",
                    data=csv,
                    file_name=f"prix_{carburant_choice}_{date_choice.strftime('%Y-%m-%d')}_{echelle_choice}.csv",
                    mime="text/csv"
                )
        else:
            df_carb = carburant_data.get(echelle_choice)
            if df_carb is not None:
                carb_filter = df_carb[df_carb['indicateur'].str.contains(carburant_choice, case=False, na=False)]
                if not carb_filter.empty:
                    available_dates = sorted(carb_filter['date'].unique())
                    if len(available_dates) > 0:
                        st.warning(
                            f"Aucune donnée disponible pour {carburant_choice} à la date {date_choice.strftime('%Y-%m-%d')}.\n"
                            f"Dates disponibles (les 5 plus récentes) : {', '.join([d.strftime('%Y-%m-%d') for d in available_dates[-5:]])}"
                        )
                    else:
                        st.warning(f"Aucune date disponible pour {carburant_choice}")
                else:
                    st.warning(f"Aucune donnée disponible pour {carburant_choice} dans la base.")
            else:
                st.warning(f"Aucune donnée disponible pour l'échelle sélectionnée.")
    
    st.divider()
    
    # --- SECTION 2: Évolution temporelle des prix ---
    st.header("📈 Évolution temporelle des prix")
    st.markdown("Visualisez l'évolution des prix des carburants au niveau régional sur une période donnée.")
    
    # Sélecteurs pour le graphique temporel
    col1, col2 = st.columns([1, 1])
    
    with col1:
        if carburant_data.get('regions') is not None:
            df_regions = carburant_data['regions']
            regions = df_regions['libelle_region'].unique()
            regions = sorted([r for r in regions if pd.notna(r)])
            region_choice = st.selectbox(
                "Région",
                options=regions,
                key="time_region"
            )
        else:
            st.warning("Données régionales non disponibles")
            region_choice = None
    
    with col2:
        carburants_all = ['SP95', 'SP98', 'Gazole' ,'E10', 'E85', 'GPLc']
        carburants_selected = st.multiselect(
            "Carburants à afficher",
            options=carburants_all,
            default=carburants_all,
            key="time_carburants"
        )
    
    # Sélection de la plage de dates
    if carburant_data.get('regions') is not None and region_choice:
        df_regions = carburant_data['regions']
        region_data = df_regions[df_regions['libelle_region'] == region_choice]
        if not region_data.empty:
            min_date = region_data['date'].min()
            max_date = region_data['date'].max()
            
            start_default = max(min_date, max_date - pd.Timedelta(days=365))
            end_default = max_date
            
            date_range = st.date_input(
                "Plage de dates",
                value=[start_default, end_default],
                min_value=min_date,
                max_value=max_date,
                key="time_date_range"
            )
            
            if len(date_range) == 2:
                start_date, end_date = date_range
            else:
                start_date, end_date = start_default, end_default
        else:
            st.warning("Aucune donnée pour la région sélectionnée")
            start_date, end_date = None, None
    else:
        start_date, end_date = None, None
    
    # Ajouter les options pour les données énergétiques
    st.subheader("📊 Données de référence")
    col1, col2, col3 = st.columns(3)
    
    with col1:
        show_brent = st.checkbox("🛢️ Pétrole Brent ($/Baril)", value=True, key="show_brent")
    
    with col2:
        show_brent_euro = st.checkbox("🛢️ Pétrole Brent (€/Baril)", value=False, key="show_brent_euro")
    
    with col3:
        show_gaz = st.checkbox("🔥 Gaz naturel ($/MMBtu)", value=False, key="show_gaz")
    
    # Créer le graphique temporel
    if region_choice and carburant_data.get('regions') is not None and carburants_selected and start_date is not None:
        df_regions = carburant_data['regions']
        
        mask = (df_regions['libelle_region'] == region_choice)
        mask &= (df_regions['date'] >= pd.Timestamp(start_date))
        mask &= (df_regions['date'] <= pd.Timestamp(end_date))
        
        carb_mask = False
        for c in carburants_selected:
            carb_mask |= df_regions['indicateur'].str.contains(c, case=False, na=False)
        mask &= carb_mask
        
        filtered_data = df_regions[mask].copy()
        
        if not filtered_data.empty:
            fig = go.Figure()
            
            # Ajouter les courbes des carburants
            for carb in carburants_selected:
                carb_data = filtered_data[filtered_data['indicateur'].str.contains(carb, case=False, na=False)]
                if not carb_data.empty:
                    daily_avg = carb_data.groupby('date')['valeur'].mean().reset_index()
                    fig.add_trace(
                        go.Scatter(
                            x=daily_avg['date'],
                            y=daily_avg['valeur'],
                            mode='lines',
                            name=carb,
                            line=dict(width=2)
                        )
                    )
            
            # Ajouter les données énergétiques si demandé
            if energy_data:
                if show_brent:
                    brent_data = energy_data.get('brent')
                    if brent_data is not None and not brent_data.empty:
                        brent_filtered = brent_data[
                            (brent_data['date'] >= pd.Timestamp(start_date)) & 
                            (brent_data['date'] <= pd.Timestamp(end_date))
                        ]
                        if not brent_filtered.empty:
                            fig.add_trace(
                                go.Scatter(
                                    x=brent_filtered['date'],
                                    y=brent_filtered['valeur'],
                                    mode='lines',
                                    name='Pétrole Brent ($/baril)',
                                    line=dict(dash='dot', width=2),
                                    yaxis='y2'
                                )
                            )
                
                if show_brent_euro:
                    brent_euro_data = energy_data.get('brent_euro')
                    if brent_euro_data is not None and not brent_euro_data.empty:
                        brent_euro_filtered = brent_euro_data[
                            (brent_euro_data['date'] >= pd.Timestamp(start_date)) & 
                            (brent_euro_data['date'] <= pd.Timestamp(end_date))
                        ]
                        if not brent_euro_filtered.empty:
                            yaxis_name = 'y3' if show_brent else 'y2'
                            fig.add_trace(
                                go.Scatter(
                                    x=brent_euro_filtered['date'],
                                    y=brent_euro_filtered['valeur'],
                                    mode='lines',
                                    name='Pétrole Brent (€/baril)',
                                    line=dict(dash='dot', width=2),
                                    yaxis=yaxis_name
                                )
                            )
                
                if show_gaz:
                    gaz_data = energy_data.get('gaz')
                    if gaz_data is not None and not gaz_data.empty:
                        gaz_filtered = gaz_data[
                            (gaz_data['date'] >= pd.Timestamp(start_date)) & 
                            (gaz_data['date'] <= pd.Timestamp(end_date))
                        ]
                        if not gaz_filtered.empty:
                            if show_brent and show_brent_euro:
                                yaxis_name = 'y4'
                            elif show_brent or show_brent_euro:
                                yaxis_name = 'y3'
                            else:
                                yaxis_name = 'y2'
                            
                            fig.add_trace(
                                go.Scatter(
                                    x=gaz_filtered['date'],
                                    y=gaz_filtered['valeur'],
                                    mode='lines',
                                    name='Gaz naturel ($/MMBtu)',
                                    line=dict(dash='dash', width=2),
                                    yaxis=yaxis_name
                                )
                            )
            
            # Configuration du layout
            fig.update_layout(
                title=f'Évolution des prix des carburants en {region_choice}',
                height=600,
                hovermode='x unified',
                legend=dict(
                    orientation='h',
                    yanchor='bottom',
                    y=1.02,
                    xanchor='right',
                    x=1
                ),
                yaxis=dict(
                    title='Prix carburants (€/L)',
                    side='left'
                )
            )
            
            # Ajouter des axes secondaires
            axis_counter = 2
            axis_configs = {}
            
            if show_brent:
                axis_configs['yaxis2'] = dict(
                    title='Pétrole Brent ($/baril)',
                    overlaying='y',
                    side='right',
                    showgrid=False
                )
                axis_counter += 1
            
            if show_brent_euro:
                axis_configs[f'yaxis{axis_counter}'] = dict(
                    title='Pétrole Brent (€/baril)',
                    overlaying='y',
                    side='right',
                    position=0.85 if axis_counter == 3 else 0.85 + (axis_counter - 3) * 0.05,
                    showgrid=False
                )
                axis_counter += 1
            
            if show_gaz:
                axis_configs[f'yaxis{axis_counter}'] = dict(
                    title='Gaz naturel ($/MMBtu)',
                    overlaying='y',
                    side='right',
                    position=0.85 + (axis_counter - 3) * 0.05 if axis_counter > 3 else 0.85,
                    showgrid=False
                )
            
            fig.update_layout(**axis_configs)
            
            st.plotly_chart(fig, use_container_width=True)
            
            # Résumé statistique
            st.subheader("📊 Résumé statistique")
            summary = filtered_data.groupby('indicateur')['valeur'].agg(['min', 'max', 'mean', 'median']).round(3)
            summary.columns = ['Minimum', 'Maximum', 'Moyenne', 'Médiane']
            st.dataframe(summary, use_container_width=True)
            
            # Téléchargement des données
            csv_data = filtered_data[['date', 'indicateur', 'valeur']].copy()
            csv_data['date'] = csv_data['date'].dt.strftime('%Y-%m-%d')
            csv = csv_data.to_csv(index=False)
            st.download_button(
                label="📥 Télécharger les données (CSV)",
                data=csv,
                file_name=f"prix_carburants_{region_choice}_{start_date.strftime('%Y%m%d')}_{end_date.strftime('%Y%m%d')}.csv",
                mime="text/csv"
            )
            
        else:
            st.warning("Aucune donnée disponible pour les critères sélectionnés")
    
    st.divider()
    
    # --- SECTION 3: Évolution des motorisations des voitures neuves ---
    st.header("🚗 Évolution des motorisations des voitures neuves")
    st.markdown("Visualisez l'évolution de la part des différentes motorisations dans les ventes de voitures neuves.")
    
    if motorisation_data is not None and not motorisation_data.empty:
        # Sélecteurs pour le graphique des motorisations
        col1, col2 = st.columns([1, 1])
        
        with col1:
            # Récupérer les régions disponibles
            regions_disponibles = sorted(motorisation_data['libelle_region'].unique())
            if len(regions_disponibles) > 0:
                region_motorisation = st.selectbox(
                    "Sélectionnez une région",
                    options=regions_disponibles,
                    key="motorisation_region"
                )
            else:
                st.warning("Aucune région disponible dans les données de motorisation")
                region_motorisation = None
        
        with col2:
            # Types de motorisation disponibles
            motorisation_types = sorted(motorisation_data['motorisation'].unique())
            # Par défaut, sélectionner toutes les motorisations
            selected_motorisations = st.multiselect(
                "Motorisations à afficher",
                options=motorisation_types,
                default=motorisation_types,
                key="motorisation_types"
            )
        
        if region_motorisation and selected_motorisations:
            # Filtrer les données
            mask = (motorisation_data['libelle_region'] == region_motorisation)
            mask &= (motorisation_data['motorisation'].isin(selected_motorisations))
            filtered_motorisation = motorisation_data[mask].copy()
            
            if not filtered_motorisation.empty:
                # Créer le graphique
                fig_motorisation = go.Figure()
                
                # Palette de couleurs pour les motorisations
                colors = {
                    'Electrique et hydrogène': '#2ECC71',
                    'Hybride rechargeable': '#3498DB',
                    'Essence': '#F1C40F',
                    'Diesel': '#E74C3C',
                    'Gaz': '#9B59B6'
                }
                
                # Ajouter les traces pour chaque motorisation
                for motorisation in selected_motorisations:
                    motor_data = filtered_motorisation[filtered_motorisation['motorisation'] == motorisation]
                    if not motor_data.empty:
                        # Agréger par année (prendre la moyenne par année)
                        motor_data['annee'] = motor_data['date'].dt.year
                        annual_data = motor_data.groupby('annee')['valeur'].mean().reset_index()
                        
                        color = colors.get(motorisation, None)
                        fig_motorisation.add_trace(
                            go.Scatter(
                                x=annual_data['annee'],
                                y=annual_data['valeur'],
                                mode='lines+markers',
                                name=motorisation,
                                line=dict(width=3, color=color),
                                marker=dict(size=8, color=color)
                            )
                        )
                
                # Mise en forme du graphique
                fig_motorisation.update_layout(
                    title=f'Évolution de la part des motorisations des voitures neuves - {region_motorisation}',
                    xaxis_title='Année',
                    yaxis_title='Part des ventes (%)',
                    height=500,
                    hovermode='x unified',
                    legend=dict(
                        orientation='h',
                        yanchor='bottom',
                        y=1.02,
                        xanchor='right',
                        x=1
                    ),
                    yaxis=dict(
                        range=[0, 105],
                        tickformat='.0f',
                        gridcolor='lightgray'
                    ),
                    xaxis=dict(
                        tickformat='d',
                        gridcolor='lightgray'
                    )
                )
                
                st.plotly_chart(fig_motorisation, use_container_width=True)
                
                # Téléchargement des données
                with st.expander("📊 Données détaillées des motorisations"):
                    display_data = filtered_motorisation[['date', 'motorisation', 'valeur']].copy()
                    display_data['date'] = display_data['date'].dt.strftime('%Y-%m-%d')
                    display_data = display_data.pivot_table(
                        index='date',
                        columns='motorisation',
                        values='valeur'
                    ).reset_index()
                    
                    st.dataframe(display_data, use_container_width=True)
                    
                    csv_motorisation = display_data.to_csv(index=False)
                    st.download_button(
                        label="📥 Télécharger les données (CSV)",
                        data=csv_motorisation,
                        file_name=f"motorisations_{region_motorisation}.csv",
                        mime="text/csv"
                    )
            else:
                st.warning("Aucune donnée disponible pour les critères sélectionnés")
        else:
            if not selected_motorisations:
                st.info("Veuillez sélectionner au moins un type de motorisation")
    
    st.divider()
    
    # --- SECTION 4: Description ---
    st.header("ℹ️ À propos de cet outil")
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.markdown("""
        ### Pourquoi cet outil ?
        
        Cet outil vous permet de visualiser et d'analyser l'évolution des prix des carburants en Bretagne.
        Il a été construit dans l'optique de donner des éléments de suivi de la motorisation (et donc de la décarbonation) des véhicules bretons en lien avec les hausses du prix de l'énergie
        
        **Une mise à jour mensuelle des données est prévue**. Si vous avez besoin d'une actualisation plus récente, n'hésitez pas à nous contacter (rubrique à propos)
        
        ### Fonctionnalités
        
        1. **Carte interactive** : Visualisez les prix par région, département ou EPCI à une date donnée.
        2. **Évolution temporelle des prix** : Suivez les tendances des prix des carburants sur une période personnalisée.
        3. **Évolution des motorisations** : Visualisez l'évolution de la part des différentes motorisations dans les ventes de voitures neuves.
        4. **Données de référence** : Comparez avec les prix du pétrole Brent et du gaz naturel.
        
        ### Sources des données
        
        - **Prix des carburants** : Plateforme www.prix-carburants.gouv.fr
        - **Motorisations des voitures neuves** : Données régionales
        - **Pétrole Brent** : https://www.kaggle.com/datasets/lakshmi2305/crude-oil-brent-prices/data?select=crude_oil_brent.csv
        - **Gaz naturel** : https://github.com/datasets/natural-gas/blob/main/data/daily.csv
        - **Prix d'échange Euro/dollar** : https://data.ecb.europa.eu/data/datasets/EXR/EXR.D.$.EUR.SP00.A
        """)
    
    with col2:
        if carburant_data.get('regions') is not None:
            df_regions = carburant_data['regions']
            last_update = df_regions['date'].max()
            if pd.notna(last_update):
                st.metric("📅 Dernière mise à jour", last_update.strftime('%d/%m/%Y'))
            st.metric("📊 Enregistrements", f"{len(df_regions):,}")
        
        if energy_data:
            if 'brent' in energy_data and energy_data['brent'] is not None and not energy_data['brent'].empty:
                brent_latest = energy_data['brent'].sort_values('date').iloc[-1]
                st.metric("🛢️ Pétrole Brent (USD)", f"{brent_latest['valeur']:.2f} USD/baril")
            
            if 'brent_euro' in energy_data and energy_data['brent_euro'] is not None and not energy_data['brent_euro'].empty:
                brent_euro_latest = energy_data['brent_euro'].sort_values('date').iloc[-1]
                st.metric("🛢️ Pétrole Brent (€)", f"{brent_euro_latest['valeur']:.2f} €/baril")
            
            if 'gaz' in energy_data and energy_data['gaz'] is not None and not energy_data['gaz'].empty:
                gaz_latest = energy_data['gaz'].sort_values('date').iloc[-1]
                st.metric("🔥 Gaz naturel", f"{gaz_latest['valeur']:.2f} $/MMBtu")
        
        if motorisation_data is not None and not motorisation_data.empty:
            st.metric("🚗 Motorisations", f"{len(motorisation_data['motorisation'].unique())} types")