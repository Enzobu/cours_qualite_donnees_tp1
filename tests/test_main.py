from pathlib import Path
import sys

import pandas as pd


SRC_DIR = Path(__file__).resolve().parents[1] / "src"
sys.path.insert(0, str(SRC_DIR))

import main


def test_parse_date_of_report_valid_and_invalid() -> None:
    s = pd.Series(["04/13/2016 01:23:45 PM", "invalid"])
    result = main.parse_date_of_report(s)
    assert result.iloc[0] == pd.Timestamp("2016-04-13 13:23:45")
    assert pd.isna(result.iloc[1])


def test_extract_crime_start_datetime() -> None:
    s = pd.Series(
        [
            "04/13/2016 20:00 - 04/14/2016 06:30",
            None,
            "bad",
        ]
    )
    result = main.extract_crime_start_datetime(s)
    assert result.iloc[0] == pd.Timestamp("2016-04-13 20:00:00")
    assert pd.isna(result.iloc[1])
    assert pd.isna(result.iloc[2])


def test_coerce_reporting_area_to_int() -> None:
    s = pd.Series(["403", "403.0", 403.0, " 403 ", "-1", "abc", None])
    result = main.coerce_reporting_area_to_int(s)
    assert result.iloc[0] == 403
    assert result.iloc[1] == 403
    assert result.iloc[2] == 403
    assert result.iloc[3] == 403
    assert pd.isna(result.iloc[4])
    assert pd.isna(result.iloc[5])
    assert pd.isna(result.iloc[6])


def test_normalize_neighborhood() -> None:
    s = pd.Series(["  MIT ", "", "nan", None, "Area 4"])
    result = main.normalize_neighborhood(s)
    assert result.iloc[0] == "MIT"
    assert pd.isna(result.iloc[1])
    assert pd.isna(result.iloc[2])
    assert pd.isna(result.iloc[3])
    assert result.iloc[4] == "Area 4"


def test_deduplicate_file_number_keep_best() -> None:
    df = pd.DataFrame(
        {
            "File Number": ["A", "A", "B"],
            "Crime": ["X", "X", "Y"],
            "Extra": [None, 2, None],
        }
    )
    cleaned, removed = main.deduplicate_file_number_keep_best(df)
    assert removed == 1
    kept = cleaned.loc[cleaned["File Number"] == "A"].iloc[0]
    assert kept["Extra"] == 2


def test_clean_dataset_logs_and_outputs() -> None:
    df = pd.DataFrame(
        [
            {
                "File Number": "A",
                "Crime": "Theft",
                "Date of Report": "01/01/2020 01:00:00 AM",
                "Crime Date Time": "01/01/2020 00:30 - 01/01/2020 02:00",
                "Reporting Area": "100",
                "Neighborhood": "MIT",
            },
            {
                "File Number": "A",
                "Crime": "Theft",
                "Date of Report": "01/01/2020 01:00:00 AM",
                "Crime Date Time": "01/01/2020 00:30 - 01/01/2020 02:00",
                "Reporting Area": "100",
                "Neighborhood": "MIT",
            },
            {
                "File Number": "B",
                "Crime": None,
                "Date of Report": "01/01/2020 01:00:00 AM",
                "Crime Date Time": "01/01/2020 00:30 - 01/01/2020 02:00",
                "Reporting Area": "200",
                "Neighborhood": "MIT",
            },
            {
                "File Number": "C",
                "Crime": "Assault",
                "Date of Report": "bad",
                "Crime Date Time": "01/02/2020 01:00 - 01/02/2020 02:00",
                "Reporting Area": "300",
                "Neighborhood": "MIT",
            },
            {
                "File Number": "D",
                "Crime": "Theft",
                "Date of Report": "01/01/2020 01:00:00 AM",
                "Crime Date Time": "01/02/2020 02:00 - 01/02/2020 04:00",
                "Reporting Area": "400",
                "Neighborhood": "MIT",
            },
            {
                "File Number": "E",
                "Crime": "Theft",
                "Date of Report": "01/01/2020 01:00:00 AM",
                "Crime Date Time": "01/01/2020 00:30 - 01/01/2020 02:00",
                "Reporting Area": "abc",
                "Neighborhood": "MIT",
            },
            {
                "File Number": "F",
                "Crime": "Theft",
                "Date of Report": "01/01/2020 01:00:00 AM",
                "Crime Date Time": "01/01/2020 00:30 - 01/01/2020 02:00",
                "Reporting Area": "500",
                "Neighborhood": "Unknown",
            },
            {
                "File Number": "G",
                "Crime": "Theft",
                "Date of Report": "01/01/2020 01:00:00 AM",
                "Crime Date Time": "01/01/2020 00:30 - 01/01/2020 02:00",
                "Reporting Area": "10000",
                "Neighborhood": "MIT",
            },
        ]
    )

    cleaned, log = main.clean_dataset(df)

    assert log["Suppression des doublons exacts"] == 1
    log_key_dossier = next(k for k in log if "dossier" in k)
    assert log[log_key_dossier] == 0
    assert log["Suppression des crimes nuls"] == 1
    assert log["Suppression des dates de signalement invalides"] == 1
    log_key_incoh = next(k for k in log if k.startswith("Correction des incoh"))
    assert log[log_key_incoh] == 1
    log_key_zone = next(k for k in log if "zone de signalement" in k)
    assert log[log_key_zone] == 1
    log_key_quartier = next(k for k in log if "du quartier" in k)
    assert log[log_key_quartier] == 1
    log_key_groupe = next(k for k in log if "groupe de zones" in k)
    assert log[log_key_groupe] == 1

    assert "Neighborhood_norm" not in cleaned.columns
    assert "Date of Report_parsed" not in cleaned.columns
    assert pd.api.types.is_datetime64_any_dtype(cleaned["Date of Report"])

    row_d = cleaned.loc[cleaned["File Number"] == "D"].iloc[0]
    assert row_d["Date of Report"] == pd.Timestamp("2020-01-02 02:00:00")

    row_f = cleaned.loc[cleaned["File Number"] == "F"].iloc[0]
    assert pd.isna(row_f["Neighborhood"])

    row_g = cleaned.loc[cleaned["File Number"] == "G"].iloc[0]
    assert pd.isna(row_g["reporting_area_group"])
