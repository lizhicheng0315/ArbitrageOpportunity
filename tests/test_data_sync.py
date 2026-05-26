import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pandas as pd
import pytest

from core.data_sync import DataSyncCore
from utils.data_manager import DataManager


class FakeResponse:
    status_code = 200

    def json(self):
        return {
            "rows": [
                {
                    "cell": {
                        "fund_id": "161126",
                        "price_dt": "2026-05-25",
                        "price": "1.840",
                        "net_value": "1.8281",
                        "discount_rt": "0.65",
                    }
                }
            ]
        }


def test_load_lof_codes_uses_project_root_when_cwd_is_elsewhere(tmp_path):
    previous_cwd = os.getcwd()
    os.chdir(tmp_path)
    try:
        codes = DataSyncCore().load_lof_codes()
    finally:
        os.chdir(previous_cwd)

    assert "161126" in codes


def test_data_manager_uses_configured_data_dir_when_cwd_is_elsewhere(tmp_path):
    data_dir = tmp_path / "project_data"
    data_dir.mkdir()
    pd.DataFrame([
        {"price_dt": "2026-05-25", "discount_rt": 0.65, "price": 1.84},
    ]).to_csv(data_dir / "lof_161126.csv", index=False)

    previous_cwd = os.getcwd()
    os.chdir(tmp_path)
    try:
        summary = DataManager(data_dir=str(data_dir)).get_data_summary()
    finally:
        os.chdir(previous_cwd)

    assert summary["total_lofs"] == 1
    assert summary["total_records"] == 1
    assert summary["latest_dates"]["161126"] == "2026-05-25"


def test_fetch_api_data_retries_after_timeout(monkeypatch):
    attempts = {"count": 0}

    def fake_get(*args, **kwargs):
        attempts["count"] += 1
        if attempts["count"] == 1:
            raise TimeoutError("temporary timeout")
        return FakeResponse()

    monkeypatch.setattr("core.data_sync.requests.get", fake_get)

    df = DataSyncCore(retry_delay=0).fetch_api_data("161126")

    assert attempts["count"] == 2
    assert len(df) == 1
    assert isinstance(df.loc[0, "price_dt"], pd.Timestamp)
    assert df.loc[0, "discount_rt"] == 0.65


def test_sync_single_lof_keeps_code_column_as_text_when_updating_existing_rows(tmp_path, monkeypatch):
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    pd.DataFrame([
        {
            "fund_id": 161126,
            "price_dt": "2026-05-25",
            "price": 1.83,
            "net_value": 1.82,
            "discount_rt": 0.0,
            "code": 161126,
        }
    ]).to_csv(data_dir / "lof_161126.csv", index=False)

    api_df = pd.DataFrame([
        {
            "fund_id": "161126",
            "price_dt": pd.Timestamp("2026-05-25"),
            "price": 1.84,
            "net_value": 1.8281,
            "discount_rt": 0.65,
            "code": "161126",
        }
    ])

    monkeypatch.setattr(DataSyncCore, "fetch_api_data", lambda self, code: api_df)

    result = DataSyncCore(data_dir=str(data_dir)).sync_single_lof("161126")

    assert result["status"] == "updated"
    saved = pd.read_csv(data_dir / "lof_161126.csv", dtype={"code": str, "fund_id": str})
    assert saved.loc[0, "code"] == "161126"
    assert saved.loc[0, "discount_rt"] == 0.65


def test_sync_single_lof_converts_numeric_api_strings_before_updating_existing_rows(tmp_path, monkeypatch):
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    pd.DataFrame([
        {
            "fund_id": "161126",
            "price_dt": "2026-05-25",
            "price": 1.83,
            "net_value": 1.82,
            "discount_rt": 0.0,
            "volume": 1.0,
            "amount": 1.0,
            "est_val": 1.0,
            "est_val2": 1.0,
            "est_val_increase_rt": 1.0,
            "est_error_rt": 1.0,
            "code": "161126",
        }
    ]).to_csv(data_dir / "lof_161126.csv", index=False)

    api_df = pd.DataFrame([
        {
            "fund_id": "161126",
            "price_dt": pd.Timestamp("2026-05-25"),
            "price": 1.84,
            "net_value": 1.8281,
            "discount_rt": 0.65,
            "volume": "27.65",
            "amount": "4926",
            "est_val": "1.1436",
            "est_val2": "1.1436",
            "est_val_increase_rt": "0.12",
            "est_error_rt": "-0.08",
            "code": "161126",
        }
    ])

    monkeypatch.setattr(DataSyncCore, "fetch_api_data", lambda self, code: api_df)

    result = DataSyncCore(data_dir=str(data_dir)).sync_single_lof("161126")

    assert result["status"] == "updated"
    saved = pd.read_csv(data_dir / "lof_161126.csv")
    assert saved.loc[0, "volume"] == 27.65
    assert saved.loc[0, "amount"] == 4926
    assert saved.loc[0, "est_val"] == 1.1436
    assert saved.loc[0, "est_val2"] == 1.1436
    assert saved.loc[0, "est_val_increase_rt"] == 0.12
    assert saved.loc[0, "est_error_rt"] == -0.08
