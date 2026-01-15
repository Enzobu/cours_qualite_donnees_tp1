from __future__ import annotations

from pathlib import Path
import importlib
import sys
from types import ModuleType

import pandas as pd


SRC_DIR = Path(__file__).resolve().parents[1] / "src"
sys.path.insert(0, str(SRC_DIR))


def _install_dummy_modules(monkeypatch, gdf: pd.DataFrame) -> ModuleType:
    gpd = ModuleType("geopandas")

    def read_file(_path: Path) -> pd.DataFrame:
        return gdf.copy()

    gpd.read_file = read_file
    monkeypatch.setitem(sys.modules, "geopandas", gpd)

    folium = ModuleType("folium")
    folium._last_map = None

    class DummyMap:
        def __init__(self, *args, **kwargs) -> None:
            self._choropleth = None
            self._geojson = None
            self.saved_path = None
            folium._last_map = self

        def save(self, path: str) -> None:
            self.saved_path = path
            Path(path).write_text("map", encoding="utf-8")

    class DummyChoropleth:
        def __init__(self, **kwargs) -> None:
            self.data = kwargs.get("data")

        def add_to(self, m: DummyMap) -> "DummyChoropleth":
            m._choropleth = self
            return self

    class DummyGeoJson:
        def __init__(self, data, tooltip=None) -> None:
            self.data = data
            self.tooltip = tooltip

        def add_to(self, m: DummyMap) -> "DummyGeoJson":
            m._geojson = self
            return self

    class DummyGeoJsonTooltip:
        def __init__(self, *args, **kwargs) -> None:
            self.args = args
            self.kwargs = kwargs

    class DummyLayerControl:
        def add_to(self, m: DummyMap) -> "DummyLayerControl":
            return self

    folium.Map = DummyMap
    folium.Choropleth = DummyChoropleth
    folium.GeoJson = DummyGeoJson
    folium.GeoJsonTooltip = DummyGeoJsonTooltip
    folium.LayerControl = DummyLayerControl

    monkeypatch.setitem(sys.modules, "folium", folium)
    return folium


def _import_map(monkeypatch, gdf: pd.DataFrame):
    folium_mod = _install_dummy_modules(monkeypatch, gdf)
    if "map" in sys.modules:
        del sys.modules["map"]
    return importlib.import_module("map"), folium_mod


def test_main_prints_orphans_and_saves_map(tmp_path, monkeypatch, capsys) -> None:
    gdf = pd.DataFrame({"NAME": ["Area 2/MIT"]})
    map_mod, _folium_mod = _import_map(monkeypatch, gdf)

    data_path = tmp_path / "crime.csv"
    geo_path = tmp_path / "geo.json"
    out_path = tmp_path / "map.html"

    df = pd.DataFrame({"Neighborhood": ["MIT", "Unknown"]})
    df.to_csv(data_path, index=False)
    geo_path.write_text("{}", encoding="utf-8")

    map_mod.DATA_CLEAN = data_path
    map_mod.GEOJSON = geo_path
    map_mod.OUT_HTML = out_path

    map_mod.main()

    output = capsys.readouterr().out
    assert "Quartiers" in output
    assert "- Unknown" in output
    assert out_path.exists()


def test_main_fills_missing_crime_count_with_zero(tmp_path, monkeypatch) -> None:
    gdf = pd.DataFrame({"NAME": ["Area 2/MIT", "Baldwin"]})
    map_mod, folium_mod = _import_map(monkeypatch, gdf)

    data_path = tmp_path / "crime.csv"
    geo_path = tmp_path / "geo.json"
    out_path = tmp_path / "map.html"

    df = pd.DataFrame({"Neighborhood": ["MIT", "MIT"]})
    df.to_csv(data_path, index=False)
    geo_path.write_text("{}", encoding="utf-8")

    map_mod.DATA_CLEAN = data_path
    map_mod.GEOJSON = geo_path
    map_mod.OUT_HTML = out_path

    map_mod.main()

    merged = folium_mod._last_map._choropleth.data
    area_count = merged.loc[merged["NAME"] == "Area 2/MIT", "crime_count"].iloc[0]
    baldwin_count = merged.loc[merged["NAME"] == "Baldwin", "crime_count"].iloc[0]
    assert area_count == 2
    assert baldwin_count == 0
