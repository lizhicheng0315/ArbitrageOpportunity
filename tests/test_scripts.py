import subprocess
import sys
from pathlib import Path

from scripts.dashboard import format_unknown, is_status_open, is_trade_operable

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def test_sync_daily_outputs_utf8_without_environment_override():
    result = subprocess.run(
        [sys.executable, str(PROJECT_ROOT / "scripts" / "sync_daily.py"), "--verify"],
        cwd=PROJECT_ROOT.parent,
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=True,
    )

    assert "验证数据完整性" in result.stdout
    assert "总LOF" in result.stdout


def test_format_unknown_normalizes_missing_values():
    assert format_unknown(None) == "未知"
    assert format_unknown("") == "未知"
    assert format_unknown("-") == "-"
    assert format_unknown("开放申购") == "开放申购"


def test_is_status_open_detects_open_status():
    assert is_status_open("开放申购") is True
    assert is_status_open("开放赎回") is True
    assert is_status_open("暂停申购") is False
    assert is_status_open("未知") is False
    assert is_status_open(None) is False


def test_is_trade_operable_uses_matching_subscription_status():
    info = {
        "apply_status": "开放申购",
        "redeem_status": "暂停赎回",
    }
    discount_info = {
        "apply_status": "暂停申购",
        "redeem_status": "开放赎回",
    }

    assert is_trade_operable("溢价套利", info) is True
    assert is_trade_operable("折价套利", info) is False
    assert is_trade_operable("折价套利", discount_info) is True
    assert is_trade_operable("溢价套利", discount_info) is False
    assert is_trade_operable("无", info) is False
    assert is_trade_operable("溢价套利", {}) is False
