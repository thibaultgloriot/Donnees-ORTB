import streamlit as st
import pandas as pd

def show(df):
    st.title("📁 Données Brutes")
    
    # Filtres
    col1, col2 = st.columns(2)
    
    with col1:
        indicateurs = st.multiselect(
            "Filtrer par indicateur",
            options=df['indicateur'].unique(),
            default=df['indicateur'].unique()
        )
    
    with col2:
        dates = st.multiselect(
            "Filtrer par date",
            options=df['date'].dt.strftime('%Y-%m-%d').unique(),
            default=df['date'].dt.strftime('%Y-%m-%d').unique()
        )
    
    # Application des filtres
    filtered_df = df[
        (df['indicateur'].isin(indicateurs)) &
        (df['date'].astype(str).isin(dates))
    ]
    
    # Affichage des données
    st.dataframe(
        filtered_df,
        use_container_width=True,
        height=400
    )
    
    # Téléchargement
    csv = filtered_df.to_csv(index=False)
    st.download_button(
        label="📥 Télécharger les données filtrées (CSV)",
        data=csv,
        file_name="donnees_communes_filtrees.csv",
        mime="text/csv"
    )