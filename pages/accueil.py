import streamlit as st
import pandas as pd

def show(df, epci_df):
    st.title("🏠 Tableau de bord - Observatoire Régional")
    
    # KPI globaux
    col1, col2, col3,col4 = st.columns(4)
    
    with col1:
        st.metric("Nombre d'indicateurs à l'échelle commune", df['indicateur'].nunique())
    with col2:
        st.metric("Nombre d'indicateurs à l'échelle EPCI", df_epci['indicateur'].nunique())
    
    with col3:
        st.metric("Nombre de communes", df['code_commune'].nunique())
    
    with col4:
        if epci_df is not None:
            st.metric("Nombre d'EPCI", 61)
        else:
            st.metric("Période couverte", f"{df['date'].min().year}-{df['date'].max().year}")
    
    # Liste des indicateurs disponibles
    st.subheader("📋 Indicateurs disponibles")
    
    if 'thematique' in epci_df.columns:
        for thematique in epci_df['thematique'].unique():
            with st.expander(f"{thematique}"):
                indicateurs = epci_df[epci_df['thematique'] == thematique]['indicateur'].unique()
                for ind in indicateurs:
                    st.write(f"• {ind}")
    else:
        for ind in sorted(epci_df['indicateur'].unique()):

            st.write(f"• {ind}")


