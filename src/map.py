from __future__ import annotations

"""Génère une carte choroplèthe des crimes par quartier."""

from pathlib import Path

import pandas as pd         #type: ignore
import geopandas as gpd     #type: ignore
import folium               #type: ignore


BASE_DIR = Path(__file__).resolve().parents[1]
DATA_CLEAN = BASE_DIR / "data" / "crime_reports_clean.csv"
GEOJSON = BASE_DIR / "data" / "BOUNDARY_CDDNeighborhoods.geojson"
OUT_HTML = BASE_DIR / "data" / "map.html"


NEIGHBORHOOD_TO_GEO = {
    "MIT": "Area 2/MIT",
    "Area 4": "The Port",
    "Inman/Harrington": "Wellington-Harrington",
    "Highlands": "Cambridge Highlands",
    "Peabody": "Neighborhood Nine",
    "Agassiz": "Baldwin",
    # Ceux déjà identiques (pas besoin) :
    # "Cambridgeport": "Cambridgeport", etc.
}


def main() -> None:
    """Construit la carte et exporte un HTML."""
    if not DATA_CLEAN.exists():
        raise FileNotFoundError(f"Missing: {DATA_CLEAN}")
    if not GEOJSON.exists():
        raise FileNotFoundError(f"Missing: {GEOJSON}")

    df = pd.read_csv(DATA_CLEAN)

    df["Neighborhood"] = df["Neighborhood"].astype("string")
    df["Neighborhood_geo"] = df["Neighborhood"].map(NEIGHBORHOOD_TO_GEO).fillna(df["Neighborhood"])

    crimes_by_nb = (
        df.dropna(subset=["Neighborhood_geo"])
        .groupby("Neighborhood_geo", as_index=False)
        .size()
        .rename(columns={"size": "crime_count"})
    )

    expected = int(df["Neighborhood_geo"].notna().sum())
    got = int(crimes_by_nb["crime_count"].sum())
    if got != expected:
        raise ValueError(f"Aggregation check failed: got={got} expected={expected}")

    gdf = gpd.read_file(GEOJSON)

    GEO_NAME_COL = "NAME"
    merged = gdf.merge(crimes_by_nb, left_on=GEO_NAME_COL, right_on="Neighborhood_geo", how="left")
    merged["crime_count"] = merged["crime_count"].fillna(0).astype(int)

    geo_names = set(gdf[GEO_NAME_COL].dropna().astype(str))
    orphans = crimes_by_nb.loc[~crimes_by_nb["Neighborhood_geo"].isin(geo_names), "Neighborhood_geo"]
    if not orphans.empty:
        print("\nQuartiers présents dans le CSV (après mapping) mais absents du GeoJSON :")
        for n in sorted(orphans.unique()):
            print(f"- {n}")

    m = folium.Map(location=[42.3736, -71.1097], zoom_start=13)

    folium.Choropleth(
        geo_data=merged.to_json(),
        name="Crimes par quartier",
        data=merged,
        columns=[GEO_NAME_COL, "crime_count"],
        key_on=f"feature.properties.{GEO_NAME_COL}",
        fill_color="RdYlGn_r",
        fill_opacity=0.75,
        line_opacity=0.25,
        legend_name="Nombre de crimes",
    ).add_to(m)

    folium.GeoJson(
        merged,
        tooltip=folium.GeoJsonTooltip(
            fields=[GEO_NAME_COL, "crime_count"],
            aliases=["Quartier", "Crimes"],
        ),
    ).add_to(m)

    folium.LayerControl().add_to(m)

    m.save(str(OUT_HTML))
    print(f"\nCarte exportée: {OUT_HTML}\n")


if __name__ == "__main__":
    main()
