# LOF Subscription Status Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add LOF purchase/redemption status, minimum purchase amount, and operability filtering to the Streamlit arbitrage dashboard.

**Architecture:** Keep the change focused in `scripts/dashboard.py`, matching the existing single-file dashboard style. Add pure helper functions for fetching Jisilu subscription metadata and computing arbitrage operability, then wire those helpers into the existing data precomputation, sidebar controls, arbitrage cards, and ranking table.

**Tech Stack:** Python, Streamlit, pandas, requests, Plotly, pytest/py_compile for verification.

---

## File Structure

- Modify: `scripts/dashboard.py`
  - Add `requests` import.
  - Add helper functions:
    - `load_subscription_info()` — fetches stock/index LOF list metadata from Jisilu.
    - `is_status_open(status)` — checks if a Chinese status string contains `开放`.
    - `is_trade_operable(arb_type, subscription_info)` — determines whether an arbitrage direction can currently be operated.
    - `format_unknown(value, default="未知")` — normalizes missing UI values.
  - Add sidebar filter `仅显示可操作套利`.
  - Add subscription fields to `lof_data`.
  - Add operability display to arbitrage opportunity cards.
  - Add subscription columns to ranking table.
- Modify: `tests/test_scripts.py`
  - Add lightweight unit tests for helper behavior by importing `scripts.dashboard`.

No new production files are required. Do not change `core/data_sync.py`, `utils/data_manager.py`, or historical CSV format.

---

### Task 1: Add Pure Helper Tests

**Files:**
- Modify: `tests/test_scripts.py`
- Test target: `scripts/dashboard.py`

- [ ] **Step 1: Add dashboard helper imports and tests**

Append this code to `tests/test_scripts.py`:

```python
from scripts.dashboard import format_unknown, is_status_open, is_trade_operable


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

    assert is_trade_operable("溢价套利", info) is True
    assert is_trade_operable("折价套利", info) is False
    assert is_trade_operable("无", info) is False
    assert is_trade_operable("溢价套利", {}) is False
```

- [ ] **Step 2: Run tests to verify they fail before implementation**

Run:

```bash
cd "e:/project/ArbitrageOpportunity/ArbitrageOpportunity" && pytest tests/test_scripts.py -v
```

Expected: FAIL with an import error similar to:

```text
ImportError: cannot import name 'format_unknown' from 'scripts.dashboard'
```

---

### Task 2: Add Subscription Helper Functions

**Files:**
- Modify: `scripts/dashboard.py`
- Test: `tests/test_scripts.py`

- [ ] **Step 1: Add `requests` import**

In `scripts/dashboard.py`, change the imports near the top from:

```python
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import json
```

to:

```python
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import json
import requests
```

- [ ] **Step 2: Add pure helper functions after `load_fund_names()`**

Insert this code after `load_fund_names()`:

```python
def format_unknown(value, default="未知"):
    """格式化缺失字段"""
    if value is None or value == "":
        return default
    return value


def is_status_open(status):
    """判断申购/赎回状态是否开放"""
    return isinstance(status, str) and "开放" in status


def is_trade_operable(arb_type, subscription_info):
    """判断套利方向当前是否可操作"""
    if not subscription_info:
        return False
    if arb_type == "溢价套利":
        return is_status_open(subscription_info.get("apply_status"))
    if arb_type == "折价套利":
        return is_status_open(subscription_info.get("redeem_status"))
    return False
```

- [ ] **Step 3: Run helper tests**

Run:

```bash
cd "e:/project/ArbitrageOpportunity/ArbitrageOpportunity" && pytest tests/test_scripts.py -v
```

Expected: PASS for the new helper tests and existing UTF-8 test.

---

### Task 3: Add Jisilu Subscription Metadata Loader

**Files:**
- Modify: `scripts/dashboard.py`

- [ ] **Step 1: Add `load_subscription_info()` after `is_trade_operable()`**

Insert this code:

```python
@st.cache_data(ttl=300)
def load_subscription_info():
    """从集思录加载LOF申购/赎回状态"""
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'Accept': 'application/json, text/javascript, */*; q=0.01',
        'X-Requested-With': 'XMLHttpRequest',
        'Referer': 'https://www.jisilu.cn/data/lof/',
    }
    endpoints = [
        'https://www.jisilu.cn/data/lof/stock_lof_list/',
        'https://www.jisilu.cn/data/lof/index_lof_list/',
    ]

    subscription_info = {}
    for url in endpoints:
        try:
            response = requests.get(url, headers=headers, timeout=15)
            if response.status_code != 200:
                continue
            data = response.json()
            for row in data.get('rows', []):
                cell = row.get('cell', {})
                code = str(cell.get('fund_id', '')).strip()
                if not code:
                    continue
                subscription_info[code] = {
                    'apply_status': format_unknown(cell.get('apply_status')),
                    'redeem_status': format_unknown(cell.get('redeem_status')),
                    'min_amt': format_unknown(cell.get('min_amt'), '-'),
                    'apply_fee': format_unknown(cell.get('apply_fee'), '-'),
                    'redeem_fee': format_unknown(cell.get('redeem_fee'), '-'),
                    'apply_fee_tips': format_unknown(cell.get('apply_fee_tips'), '-'),
                    'redeem_fee_tips': format_unknown(cell.get('redeem_fee_tips'), '-'),
                }
        except Exception:
            continue

    return subscription_info
```

- [ ] **Step 2: Run syntax check**

Run:

```bash
cd "e:/project/ArbitrageOpportunity/ArbitrageOpportunity" && python -c "import py_compile; py_compile.compile('scripts/dashboard.py', doraise=True); print('Syntax OK')"
```

Expected:

```text
Syntax OK
```

---

### Task 4: Wire Subscription Data Into Dashboard State

**Files:**
- Modify: `scripts/dashboard.py`

- [ ] **Step 1: Load subscription info near existing fund names**

In `main()`, change:

```python
    manager = DataManager()
    fund_names = load_fund_names()
```

to:

```python
    manager = DataManager()
    fund_names = load_fund_names()
    subscription_info = load_subscription_info()
```

- [ ] **Step 2: Add operability filter to sidebar**

In the sidebar, after the four fee sliders and cost calculations:

```python
        premium_arb_cost = sub_fee + sell_fee    # 溢价套利总成本
        discount_arb_cost = buy_fee + redeem_fee  # 折价套利总成本
```

insert:

```python
        only_operable_arb = st.checkbox("仅显示可操作套利", value=False)
```

- [ ] **Step 3: Add subscription fields to each `lof_data` record**

Before constructing `lof_data[code]`, add:

```python
        sub_info = subscription_info.get(code, {})
        arb_type = '溢价套利' if current > 0 else '折价套利' if current < 0 else '无'
        arb_operable = is_trade_operable(arb_type, sub_info)
```

Then replace the existing arbitrage fields inside `lof_data[code]`:

```python
            'arb_type': '溢价套利' if current > 0 else '折价套利' if current < 0 else '无',
            'arb_cost': premium_arb_cost if current > 0 else discount_arb_cost if current < 0 else 0,
            'arb_profit': abs(current) - (premium_arb_cost if current > 0 else discount_arb_cost if current < 0 else 0),
            'arb_viable': (current > premium_arb_cost) or (current < -discount_arb_cost),
```

with:

```python
            'arb_type': arb_type,
            'arb_cost': premium_arb_cost if current > 0 else discount_arb_cost if current < 0 else 0,
            'arb_profit': abs(current) - (premium_arb_cost if current > 0 else discount_arb_cost if current < 0 else 0),
            'arb_viable': (current > premium_arb_cost) or (current < -discount_arb_cost),
            'arb_operable': arb_operable,
            'subscription_info': sub_info,
```

- [ ] **Step 4: Run syntax check**

Run:

```bash
cd "e:/project/ArbitrageOpportunity/ArbitrageOpportunity" && python -c "import py_compile; py_compile.compile('scripts/dashboard.py', doraise=True); print('Syntax OK')"
```

Expected:

```text
Syntax OK
```

---

### Task 5: Update Arbitrage Opportunity Cards

**Files:**
- Modify: `scripts/dashboard.py`

- [ ] **Step 1: Filter arbitrage items with the sidebar switch**

Find:

```python
        arb_items = [(code, d) for code, d in lof_data.items() if d['arb_viable']]
```

Replace it with:

```python
        arb_items = [
            (code, d) for code, d in lof_data.items()
            if d['arb_viable'] and (not only_operable_arb or d['arb_operable'])
        ]
```

- [ ] **Step 2: Add status text to the card loop**

Inside the `for code, d in arb_items:` loop, after:

```python
                amount = d['latest'].get('amount', 0) or 0
```

insert:

```python
                sub_info = d.get('subscription_info', {})
                if d['arb_operable']:
                    operable_text = "可操作"
                    operable_color = "#0d8532"
                elif sub_info:
                    operable_text = "理论有利润，当前不可操作"
                    operable_color = "#cf1322"
                else:
                    operable_text = "申赎状态未知，请手动确认"
                    operable_color = "#d48806"
                status_text = sub_info.get('apply_status') if is_premium else sub_info.get('redeem_status')
                status_text = format_unknown(status_text)
```

- [ ] **Step 3: Update card HTML to show status**

In the card HTML, replace:

```html
<span style="color:#888; font-size:0.82rem;">{arb_emoji} {arb_label}：{arb_desc}</span>
```

with:

```html
<span style="color:#888; font-size:0.82rem;">{arb_emoji} {arb_label}：{arb_desc}</span><br/>
<span style="color:{operable_color}; font-size:0.82rem; font-weight:600;">{operable_text}｜状态：{status_text}</span>
```

- [ ] **Step 4: Run syntax check**

Run:

```bash
cd "e:/project/ArbitrageOpportunity/ArbitrageOpportunity" && python -c "import py_compile; py_compile.compile('scripts/dashboard.py', doraise=True); print('Syntax OK')"
```

Expected:

```text
Syntax OK
```

---

### Task 6: Add Subscription Columns to Ranking Table

**Files:**
- Modify: `scripts/dashboard.py`

- [ ] **Step 1: Add subscription columns to `rows.append()`**

In the ranking table `rows.append({...})`, add these fields after `套利利润(%)`:

```python
                '申购状态': d['subscription_info'].get('apply_status', '未知'),
                '最小申购': d['subscription_info'].get('min_amt', '-'),
                '申购费': d['subscription_info'].get('apply_fee', '-'),
                '赎回状态': d['subscription_info'].get('redeem_status', '未知'),
                '赎回费': d['subscription_info'].get('redeem_fee', '-'),
```

The final block should include both existing price/value fields and the new subscription fields.

- [ ] **Step 2: Add status coloring helper**

After `color_arb_type`, add:

```python
        def color_open_status(val):
            if is_status_open(val):
                return 'color: #0d8532; font-weight: 600'
            if val == '未知':
                return 'color: #d48806; font-weight: 600'
            return 'color: #cf1322; font-weight: 600'
```

- [ ] **Step 3: Apply status coloring**

Change the `styled = ...` chain from:

```python
        styled = df_table.style.map(color_premium, subset=['溢价率(%)', '7日均值(%)']) \
                               .map(color_signal, subset=['信号']) \
                               .map(color_arb_profit, subset=['套利利润(%)']) \
                               .map(color_arb_type, subset=['套利方向'])
```

to:

```python
        styled = df_table.style.map(color_premium, subset=['溢价率(%)', '7日均值(%)']) \
                               .map(color_signal, subset=['信号']) \
                               .map(color_arb_profit, subset=['套利利润(%)']) \
                               .map(color_arb_type, subset=['套利方向']) \
                               .map(color_open_status, subset=['申购状态', '赎回状态'])
```

- [ ] **Step 4: Run syntax check**

Run:

```bash
cd "e:/project/ArbitrageOpportunity/ArbitrageOpportunity" && python -c "import py_compile; py_compile.compile('scripts/dashboard.py', doraise=True); print('Syntax OK')"
```

Expected:

```text
Syntax OK
```

---

### Task 7: End-to-End Verification

**Files:**
- Verify: `scripts/dashboard.py`
- Verify: `tests/test_scripts.py`

- [ ] **Step 1: Run focused tests**

Run:

```bash
cd "e:/project/ArbitrageOpportunity/ArbitrageOpportunity" && pytest tests/test_scripts.py -v
```

Expected:

```text
4 passed
```

If existing environment has additional warnings, tests still pass.

- [ ] **Step 2: Run syntax check**

Run:

```bash
cd "e:/project/ArbitrageOpportunity/ArbitrageOpportunity" && python -c "import py_compile; py_compile.compile('scripts/dashboard.py', doraise=True); print('Syntax OK')"
```

Expected:

```text
Syntax OK
```

- [ ] **Step 3: Launch Streamlit**

Run:

```bash
cd "e:/project/ArbitrageOpportunity/ArbitrageOpportunity" && streamlit run scripts/dashboard.py --server.port 8501
```

Expected output includes:

```text
Local URL: http://localhost:8501
```

- [ ] **Step 4: Manual browser checks**

Open `http://localhost:8501` and verify:

1. Sidebar shows `仅显示可操作套利`.
2. Ranking table has columns `申购状态`, `最小申购`, `申购费`, `赎回状态`, `赎回费`.
3. Arbitrage cards show one of:
   - `可操作`
   - `理论有利润，当前不可操作`
   - `申赎状态未知，请手动确认`
4. Turning on `仅显示可操作套利` removes non-operable arbitrage cards.
5. If Jisilu metadata cannot load, dashboard still renders with `未知`/`-` fields.

---

## Self-Review

- Spec coverage: Data loader, UI columns, operability filtering, card status display, and failure fallback are covered by Tasks 2-7.
- Placeholder scan: No TBD/TODO/fill-in placeholders remain.
- Type consistency: Helper names and dictionary keys are consistent across tests, implementation, and UI wiring.
