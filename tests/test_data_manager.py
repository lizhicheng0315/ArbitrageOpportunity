import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pandas as pd

from utils.data_manager import DataManager


def test_latest_confirmed_lof_data_ignores_unconfirmed_latest_discount(tmp_path):
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    pd.DataFrame([
        {"price_dt": "2026-05-22", "discount_rt": 0.62, "price": 1.826},
        {"price_dt": "2026-05-25", "discount_rt": 0.65, "price": 1.840},
        {"price_dt": "2026-05-26", "discount_rt": None, "price": 1.841},
    ]).to_csv(data_dir / "lof_161126.csv", index=False)

    row = DataManager(data_dir=str(data_dir)).get_latest_confirmed_lof_data("161126")

    assert row is not None
    assert row["price_dt"] == pd.Timestamp("2026-05-25")
    assert row["discount_rt"] == 0.65


def test_latest_confirmed_lof_data_returns_none_when_no_confirmed_discount(tmp_path):
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    pd.DataFrame([
        {"price_dt": "2026-05-26", "discount_rt": None, "price": 1.841},
    ]).to_csv(data_dir / "lof_161126.csv", index=False)

    row = DataManager(data_dir=str(data_dir)).get_latest_confirmed_lof_data("161126")

    assert row is None
