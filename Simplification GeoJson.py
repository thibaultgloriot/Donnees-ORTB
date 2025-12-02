import geopandas as gpd

def simplify_geometries(tolerance):
    """Simplifie les géométries pour réduire la taille"""
    # Communes
    gdf_com = gpd.read_file("data/communes.geojson")
    gdf_com['geometry'] = gdf_com['geometry'].simplify(tolerance)
    gdf_com.to_file("data/communes_simple.geojson", driver='GeoJSON')
    
    # EPCI
    gdf_epci = gpd.read_file("data/epci.geojson")
    gdf_epci['geometry'] = gdf_epci['geometry'].simplify(tolerance)
    gdf_epci.to_file("data/epci_simple.geojson", driver='GeoJSON')
    
simplify_geometries(0.0008)