from __future__ import annotations

from pathlib import Path
from typing import Dict, Tuple
import pandas as pd     # type: ignore


BASE_DIR = Path(__file__).resolve().parents[1]
DATA_IN = BASE_DIR / "data" / "crime_reports_broken.csv"
DATA_OUT = BASE_DIR / "data" / "crime_reports_clean.csv"


VALID_NEIGHBORHOODS = {
    "Cambridgeport",
    "East Cambridge",
    "Mid-Cambridge",
    "North Cambridge",
    "Riverside",
    "Area 4",
    "West Cambridge",
    "Peabody",
    "Inman/Harrington",
    "Highlands",
    "Agassiz",
    "MIT",
    "Strawberry Hill",
}


DATE_OF_REPORT_FORMAT = "%m/%d/%Y %I:%M:%S %p"


def parse_date_of_report(s: pd.Series) -> pd.Series:
    """Convertit la date de signalement en date/heure.

    Les valeurs invalides deviennent NaT.
    """
    return pd.to_datetime(s, errors="coerce", format=DATE_OF_REPORT_FORMAT)


def extract_crime_start_datetime(crime_dt: pd.Series) -> pd.Series:
    """Extrait et convertit le début de la date/heure du crime.

    Format fréquent: "04/13/2016 20:00 - 04/14/2016 06:30".
    """
    start_txt = crime_dt.astype(str).str.split(" - ").str[0].replace("nan", pd.NA)
    return pd.to_datetime(start_txt, errors="coerce", format="%m/%d/%Y %H:%M")


def coerce_reporting_area_to_int(s: pd.Series) -> pd.Series:
    """Convertit la zone de signalement en entier nullable.

    Accepte 403, 403.0, "403.0", " 403 ".
    """
    num = pd.to_numeric(s, errors="coerce")
    num = num.where(num > 0)
    return num.round(0).astype("Int64")


def normalize_neighborhood(s: pd.Series) -> pd.Series:
    """Normalise le quartier avec un nettoyage léger des espaces.

    Ne force pas la casse titre pour préserver "Area 4" ou "MIT".
    """
    out = s.astype("string").str.strip()
    out = out.replace({"": pd.NA, "nan": pd.NA})
    return out


def pct(n: int, total: int) -> float:
    """Calcule un pourcentage sur 100 en évitant la division par zéro."""
    return 0.0 if total == 0 else (n / total) * 100.0


def completeness(df: pd.DataFrame, col: str) -> float:
    """Retourne le taux de complétude (valeurs non nulles) d'une colonne."""
    return pct(int(df[col].notna().sum()), len(df))


def uniqueness(df: pd.DataFrame, col: str) -> float:
    """Retourne le taux d'unicité sur les valeurs non nulles."""
    non_null = df[col].dropna()
    return pct(int(non_null.nunique(dropna=True)), len(non_null))


def exact_duplicates_rate(df: pd.DataFrame) -> float:
    """Retourne le taux de doublons exacts."""
    return pct(int(df.duplicated().sum()), len(df))


def invalid_date_of_report_rate(df: pd.DataFrame) -> float:
    """Retourne le taux de dates de signalement invalides."""
    return pct(int(df["Date of Report_parsed"].isna().sum()), len(df))


def deduplicate_file_number_keep_best(df: pd.DataFrame) -> Tuple[pd.DataFrame, int]:
    """Déduplique par numéro de dossier en gardant la ligne la plus complète.

    En cas d'égalité, la première ligne est conservée.
    """
    if "File Number" not in df.columns:
        return df, 0

    before = len(df)
    df = df.copy()
    df["_non_null_score"] = df.notna().sum(axis=1)

    df = (
        df.sort_values(by=["File Number", "_non_null_score"], ascending=[True, False])
        .drop_duplicates(subset=["File Number"], keep="first")
        .drop(columns=["_non_null_score"])
    )

    removed = before - len(df)
    return df, removed


def clean_dataset(df: pd.DataFrame) -> Tuple[pd.DataFrame, Dict[str, int]]:
    """Nettoie le jeu de données et retourne un journal d'actions.

    Étapes:
    - conversion des dates et normalisations de base
    - suppression des doublons exacts et par numéro de dossier
    - filtrage des crimes nuls et des dates invalides
    - correction des incohérences temporelles (signalement < début du crime)
    - normalisation de la zone de signalement et du quartier
    - création du groupe de zones de signalement et filtrage des valeurs aberrantes
    """
    log: Dict[str, int] = {}

    work = df.copy()

    work["Date of Report_parsed"] = parse_date_of_report(work["Date of Report"])
    work["Crime Start_parsed"] = extract_crime_start_datetime(work["Crime Date Time"])
    work["Reporting Area_int"] = coerce_reporting_area_to_int(work["Reporting Area"])
    work["Neighborhood_norm"] = normalize_neighborhood(work["Neighborhood"])

    before = len(work)
    work = work.drop_duplicates()
    log["Suppression des doublons exacts"] = before - len(work)

    work, removed_fn = deduplicate_file_number_keep_best(work)
    log["Suppression des doublons de numéro de dossier"] = removed_fn

    before = len(work)
    work = work[work["Crime"].notna()]
    log["Suppression des crimes nuls"] = before - len(work)

    before = len(work)
    work = work[work["Date of Report_parsed"].notna()]
    log["Suppression des dates de signalement invalides"] = before - len(work)

    mask_fixable = work["Crime Start_parsed"].notna() & (work["Date of Report_parsed"] < work["Crime Start_parsed"])
    log["Correction des incohérences temporelles (signalement < début du crime)"] = int(mask_fixable.sum())
    work.loc[mask_fixable, "Date of Report_parsed"] = work.loc[mask_fixable, "Crime Start_parsed"]

    invalid_ra = work["Reporting Area_int"].isna()
    log["Mise à NA de la zone de signalement"] = int(invalid_ra.sum())

    invalid_nb = work["Neighborhood_norm"].notna() & (~work["Neighborhood_norm"].isin(VALID_NEIGHBORHOODS))
    log["Mise à NA du quartier"] = int(invalid_nb.sum())
    work.loc[invalid_nb, "Neighborhood_norm"] = pd.NA

    work["reporting_area_group"] = (work["Reporting Area_int"] // 100).astype("Int64")

    aberr = work["reporting_area_group"].notna() & ((work["reporting_area_group"] < 0) | (work["reporting_area_group"] > 99))
    log["Mise à NA du groupe de zones de signalement (aberrant)"] = int(aberr.sum())
    work.loc[aberr, "reporting_area_group"] = pd.NA

    work = work.drop(columns=["Neighborhood"]).rename(columns={"Neighborhood_norm": "Neighborhood"})

    work = work.drop(columns=["Date of Report"]).rename(columns={"Date of Report_parsed": "Date of Report"})

    return work, log


def main() -> None:
    """Charge, nettoie et exporte les données."""
    if not DATA_IN.exists():
        raise FileNotFoundError(f"Fichier introuvable: {DATA_IN}")

    df = pd.read_csv(DATA_IN)

    print("\n=== PROFILAGE DU DATASET ===")

    # Nombre de lignes
    print(f"Nombre de lignes : {len(df)}")

    # Types des colonnes
    print("\nTypes des colonnes :")
    print(df.dtypes)

    # Valeurs manquantes par colonne
    print("\nNombre de valeurs manquantes par colonne :")
    print(df.isna().sum())

    print("\n=== PROBLÈMES DE QUALITÉ IDENTIFIÉS ===")

    print("    - Présence de doublons exacts dans le dataset.")
    print("    - Identifiants File Number non uniques.")
    print("    - Valeurs manquantes dans la colonne Crime.")
    print("    - Dates de signalement invalides ou non parsables.")
    print("    - Incohérences temporelles (Date of Report antérieure au début du crime).")
    print("    - Quartiers hors référentiel officiel.")
    print("    - Reporting Area non conforme.")

    print("\n=== AVANT NETTOYAGE (quelques indicateurs) ===")
    df_tmp = df.copy()
    df_tmp["Date of Report_parsed"] = parse_date_of_report(df_tmp["Date of Report"])
    print(f"Complétude des crimes (%): {completeness(df_tmp, 'Crime'):.3f}")
    print(f"Unicité des numéros de dossier (%): {uniqueness(df_tmp, 'File Number'):.3f}")
    print(f"Doublons exacts (%): {exact_duplicates_rate(df_tmp):.3f}")
    print(f"Dates de signalement invalides (%): {invalid_date_of_report_rate(df_tmp):.3f}")

    cleaned, log = clean_dataset(df)

    print("\n=== NETTOYAGE (journal des actions) ===")
    for k, v in log.items():
        print(f"- {k}: {v}")

    print("\n=== APRÈS NETTOYAGE (mêmes indicateurs) ===")
    cleaned_tmp = cleaned.copy()
    cleaned_tmp["Date of Report_parsed"] = pd.to_datetime(cleaned_tmp["Date of Report"], errors="coerce")
    print(f"Complétude des crimes (%): {completeness(cleaned_tmp, 'Crime'):.3f}")
    print(f"Unicité des numéros de dossier (%): {uniqueness(cleaned_tmp, 'File Number'):.3f}")
    print(f"Doublons exacts (%): {exact_duplicates_rate(cleaned_tmp):.3f}")
    print(f"Dates de signalement invalides (%): {pct(int(cleaned_tmp['Date of Report_parsed'].isna().sum()), len(cleaned_tmp)):.3f}")

    cleaned.to_csv(DATA_OUT, index=False)
    print(f"\nFichier exporté: {DATA_OUT} (lignes: {len(cleaned)})\n")


if __name__ == "__main__":
    main()
