# LOF 申购状态与额度展示设计

## 背景

当前仪表板已经能展示 LOF 溢价率、套利方向和理论套利利润，但用户无法判断这些套利机会是否真的可操作。溢价套利需要对应基金开放申购；折价套利需要开放赎回。用户还希望看到申购相关额度信息，以便判断下单门槛。

本次设计采用集思录 LOF 列表接口中的可靠字段，不解析基金公告，不尝试推断未披露的单日限额。

## 目标

1. 在仪表板中展示每只 LOF 的申购/赎回状态。
2. 展示最小申购金额、申购费率、赎回费率。
3. 在套利机会判断中加入申赎状态过滤。
4. 当实时申赎接口失败时，不影响原有仪表板可用性。

## 非目标

1. 不抓取基金公告。
2. 不自动解析单日申购上限。
3. 不对申购额度做投资建议或保证。
4. 不更改现有历史数据同步 CSV 结构。

## 数据来源

新增一个加载函数，从以下集思录接口读取实时申赎信息：

- `https://www.jisilu.cn/data/lof/stock_lof_list/`
- `https://www.jisilu.cn/data/lof/index_lof_list/`

从每条记录的 `cell` 中读取：

| 字段 | 用途 |
|---|---|
| `fund_id` | LOF 代码 |
| `apply_status` | 申购状态 |
| `redeem_status` | 赎回状态 |
| `min_amt` | 最小申购金额 |
| `apply_fee` | 申购费率 |
| `redeem_fee` | 赎回费率 |
| `apply_fee_tips` | 申购费率说明 |
| `redeem_fee_tips` | 赎回费率说明 |

函数返回 `dict[str, dict]`，键为基金代码。若接口失败，返回空字典。

## UI 设计

### 侧边栏

在“套利参数”附近新增开关：

- `仅显示可操作套利`

开启后，套利机会区域只显示：

- 套利利润为正；
- 溢价套利时申购状态包含“开放”；
- 折价套利时赎回状态包含“开放”。

### 排序列表

在现有排序列表中新增列：

- `申购状态`
- `最小申购`
- `申购费`
- `赎回状态`
- `赎回费`

字段缺失时显示 `未知` 或 `-`。

### 套利机会卡片

每张套利卡片增加操作状态：

- 溢价套利：检查 `apply_status` 是否开放。
- 折价套利：检查 `redeem_status` 是否开放。

显示文案：

- 状态满足：`可操作`
- 状态不满足：`理论有利润，当前不可操作`
- 状态未知：`申赎状态未知，请手动确认`

## 套利可操作判断

新增辅助函数：

```python
def is_trade_operable(arb_type, subscription_info):
    if arb_type == "溢价套利":
        return "开放" in subscription_info.get("apply_status", "")
    if arb_type == "折价套利":
        return "开放" in subscription_info.get("redeem_status", "")
    return False
```

实际实现需要处理 `subscription_info` 为空的情况。

## 错误处理

1. 接口异常、超时、返回非 JSON：捕获异常并返回空字典。
2. 字段缺失：UI 显示 `未知` 或 `-`。
3. 不因申赎信息缺失阻断现有溢价率、套利利润和趋势图展示。

## 修改范围

主要修改：

- `scripts/dashboard.py`

不修改：

- `core/data_sync.py`
- `utils/data_manager.py`
- 现有 `data/lof_*.csv`

## 验证

1. 运行 Python 语法检查：
   - `python -c "import py_compile; py_compile.compile('scripts/dashboard.py', doraise=True)"`
2. 启动 Streamlit：
   - `streamlit run scripts/dashboard.py --server.port 8501`
3. 浏览器验证：
   - 排序列表显示申购状态、最小申购、申购费、赎回状态、赎回费。
   - 套利机会卡片显示可操作状态。
   - 开启“仅显示可操作套利”后，不可操作套利被过滤。
   - 网络接口失败时，页面仍能正常展示历史数据。
