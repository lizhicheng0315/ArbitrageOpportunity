import subprocess
import sys
from pathlib import Path

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
