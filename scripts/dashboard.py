#!/usr/bin/env python3
"""
LOF溢价率交易仪表板
基于Streamlit的交互式分析界面
"""
import sys
import os

# 添加路径以便导入模块
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import json
import requests
from datetime import datetime, timedelta
from utils.data_manager import DataManager

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def load_fund_names():
    """加载基金名称映射"""
    names_file = os.path.join(PROJECT_ROOT, "data", "lof_names.json")
    if os.path.exists(names_file):
        with open(names_file, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


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


@st.cache_data(ttl=300)
def load_subscription_info():
    """从集思录加载LOF申购/赎回状态"""
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'Accept': 'application/json, text/javascript, */*; q=0.01',
        'X-Requested-With': 'XMLHttpRequest',
        'Referer': 'https://www.jisilu.cn/data/lof/',
    }
    # stock/index LOF 列表 + QDII 子分类（A/C/E 份额）
    lof_endpoints = [
        'https://www.jisilu.cn/data/lof/stock_lof_list/',
        'https://www.jisilu.cn/data/lof/index_lof_list/',
    ]
    qdii_endpoints = [
        'https://www.jisilu.cn/data/qdii/qdii_list/A',
        'https://www.jisilu.cn/data/qdii/qdii_list/E',
    ]

    subscription_info = {}
    for url in lof_endpoints + qdii_endpoints:
        try:
            req_headers = headers.copy()
            req_params = {}
            if 'qdii' in url:
                req_headers['Referer'] = 'https://www.jisilu.cn/data/qdii/'
                req_params = {'only_lof': 'y', 'rp': '50'}
            response = requests.get(url, params=req_params, headers=req_headers, timeout=15)
            if response.status_code != 200:
                continue
            data = response.json()
            for row in data.get('rows', []):
                cell = row.get('cell', {})
                code = str(cell.get('fund_id', '')).strip()
                if not code or code in subscription_info:
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


# ── 自定义 CSS ──────────────────────────────────────────────
def inject_custom_css():
    st.markdown("""
    <style>
    /* 顶部指标卡片阴影 */
    [data-testid="stMetricValue"] {
        font-size: 1.6rem;
        font-weight: 700;
    }

    /* 信号标签样式 */
    .signal-buy {
        background: #e6f9ed; color: #0d8532; padding: 2px 12px;
        border-radius: 12px; font-weight: 700; font-size: 0.85rem;
        display: inline-block;
    }
    .signal-sell {
        background: #fde8e8; color: #cf1322; padding: 2px 12px;
        border-radius: 12px; font-weight: 700; font-size: 0.85rem;
        display: inline-block;
    }
    .signal-hold {
        background: #f0f0f0; color: #666; padding: 2px 12px;
        border-radius: 12px; font-weight: 700; font-size: 0.85rem;
        display: inline-block;
    }

    /* 信号卡片 */
    .signal-card {
        border: 1px solid #e8e8e8; border-radius: 8px;
        padding: 12px 16px; margin-bottom: 8px;
        background: #fff; transition: box-shadow 0.2s;
    }
    .signal-card:hover { box-shadow: 0 2px 8px rgba(0,0,0,0.08); }
    .signal-card-buy { border-left: 4px solid #0d8532; }
    .signal-card-sell { border-left: 4px solid #cf1322; }
    .signal-card-hold { border-left: 4px solid #bbb; }

    /* 表格紧凑 */
    .stDataFrame { font-size: 0.9rem; }
    </style>
    """, unsafe_allow_html=True)


def signal_badge(signal):
    """生成信号标签 HTML"""
    cls = {"BUY": "signal-buy", "SELL": "signal-sell", "HOLD": "signal-hold"}[signal]
    return f'<span class="{cls}">{signal}</span>'


def signal_card_class(signal):
    """信号卡片 CSS 类"""
    return {"BUY": "signal-card-buy", "SELL": "signal-card-sell", "HOLD": "signal-card-hold"}[signal]


def main():
    st.set_page_config(
        page_title="LOF溢价率交易仪表板",
        page_icon="📈",
        layout="wide"
    )

    inject_custom_css()

    st.title("📈 LOF溢价率交易仪表板")
    st.markdown("### 基于T+1确认数据的交易信号分析")

    manager = DataManager()
    fund_names = load_fund_names()
    subscription_info = load_subscription_info()

    # ── 侧边栏 ─────────────────────────────────────────────
    with st.sidebar:
        st.header("🔧 设置")

        # 获取所有LOF代码
        summary = manager.get_data_summary()
        all_codes = list(summary['latest_dates'].keys())

        select_all = st.checkbox("全选", value=False)
        default_codes = all_codes if select_all else all_codes[:min(5, len(all_codes))] if all_codes else []

        # 带名称的选项：代码 - 名称
        code_labels = {code: f"{code} - {fund_names.get(code, '')}" for code in all_codes}
        default_labels = [code_labels[c] for c in default_codes]

        selected_labels = st.multiselect(
            "选择LOF代码",
            options=[code_labels[c] for c in all_codes],
            default=default_labels
        )
        selected_codes = [lbl.split(" - ")[0] for lbl in selected_labels]

        # 套利成本参数
        st.divider()
        st.header("💰 套利参数")
        st.caption("调整后实时计算套利利润")
        sub_fee = st.slider("申购费率(%)", 0.0, 2.0, 0.15, 0.01, help="场内申购费率，券商一折通常0.15%")
        sell_fee = st.slider("卖出佣金(%)", 0.0, 1.0, 0.10, 0.01, help="场内卖出佣金+印花税等")
        redeem_fee = st.slider("赎回费率(%)", 0.0, 2.0, 0.50, 0.01, help="持有<7天赎回费通常0.5%")
        buy_fee = st.slider("买入佣金(%)", 0.0, 1.0, 0.10, 0.01, help="场内买入佣金")

        premium_arb_cost = sub_fee + sell_fee    # 溢价套利总成本
        discount_arb_cost = buy_fee + redeem_fee  # 折价套利总成本
        only_operable_arb = st.checkbox("仅显示可操作套利", value=False)

        # 系统状态
        st.divider()
        st.header("📊 系统状态")
        st.metric("总LOF数量", summary['total_lofs'])
        st.metric("总记录数", f"{summary['total_records']:,}")
        st.info("""
        **套利逻辑**
        🔴 溢价套利：场内申购→场内卖出
        🟢 折价套利：场内买入→场内赎回
        ⏱ T+2日才能操作完成，存在风险

        ⚠️ 投资有风险，决策需谨慎
        """)

    # ── 数据预计算 ──────────────────────────────────────────
    lof_data = {}   # code -> {latest, signal, df_confirmed, ...}
    for code in selected_codes:
        df = manager.load_lof_data(code)
        if df.empty:
            continue
        confirmed_df = df.dropna(subset=['discount_rt'])
        recent_7d = confirmed_df.tail(7)
        latest = manager.get_latest_confirmed_lof_data(code)
        if latest is None:
            continue

        current = latest['discount_rt']
        mean_7d = recent_7d['discount_rt'].mean() if len(recent_7d) >= 1 else current
        std_7d = recent_7d['discount_rt'].std() if len(recent_7d) >= 2 else 0

        if current < mean_7d - std_7d:
            signal = "BUY"
        elif current > mean_7d + std_7d:
            signal = "SELL"
        else:
            signal = "HOLD"

        sub_info = subscription_info.get(code, {})
        arb_type = '溢价套利' if current > 0 else '折价套利' if current < 0 else '无'
        arb_operable = is_trade_operable(arb_type, sub_info)

        lof_data[code] = {
            'latest': latest,
            'signal': signal,
            'current': current,
            'mean_7d': mean_7d,
            'std_7d': std_7d,
            'confirmed_df': confirmed_df,
            'latest_date': latest['price_dt'].strftime('%Y-%m-%d'),
            # 套利分析
            'arb_type': arb_type,
            'arb_cost': premium_arb_cost if current > 0 else discount_arb_cost if current < 0 else 0,
            'arb_profit': abs(current) - (premium_arb_cost if current > 0 else discount_arb_cost if current < 0 else 0),
            'arb_viable': (current > premium_arb_cost) or (current < -discount_arb_cost),
            'arb_operable': arb_operable,
            'subscription_info': sub_info,
        }

    # ── 顶部概览指标 ────────────────────────────────────────
    if lof_data:
        all_premiums = [d['current'] for d in lof_data.values()]
        buy_count = sum(1 for d in lof_data.values() if d['signal'] == 'BUY')
        sell_count = sum(1 for d in lof_data.values() if d['signal'] == 'SELL')
        arb_viable_count = sum(1 for d in lof_data.values() if d['arb_viable'])
        max_profit = max((d['arb_profit'] for d in lof_data.values() if d['arb_viable']), default=0)
        max_premium = max(all_premiums)
        min_premium = min(all_premiums)

        m1, m2, m3, m4, m5 = st.columns(5)
        m1.metric("📊 监控LOF", f"{len(lof_data)} 只")
        m2.metric("🟢 买入信号", f"{buy_count} 只",
                   delta=f"卖出 {sell_count} 只" if sell_count else None)
        m3.metric("💰 可套利", f"{arb_viable_count} 只",
                   delta=f"最大利润 {max_profit:+.2f}%" if arb_viable_count else None)
        m4.metric("🔺 最大溢价", f"{max_premium:+.2f}%")
        m5.metric("🔻 最大折价", f"{min_premium:+.2f}%")
    else:
        st.warning("请在左侧选择LOF代码")

    # ── 套利机会 ──────────────────────────────────────────────
    if lof_data:
        arb_items = [
            (code, d) for code, d in lof_data.items()
            if d['arb_viable'] and (not only_operable_arb or d['arb_operable'])
        ]
        if arb_items:
            # 按套利利润排序
            arb_items.sort(key=lambda x: x[1]['arb_profit'], reverse=True)

            st.subheader("💰 套利机会")

            for code, d in arb_items:
                is_premium = d['current'] > 0
                arb_label = "溢价套利" if is_premium else "折价套利"
                arb_emoji = "🔴" if is_premium else "🟢"
                arb_desc = "场内申购→场内卖出" if is_premium else "场内买入→场内赎回"
                card_cls = "signal-card-sell" if is_premium else "signal-card-buy"
                premium_color = '#cf1322' if is_premium else '#0d8532'
                profit_color = '#0d8532' if d['arb_profit'] > 0 else '#999'
                name = fund_names.get(code, '')
                amount = d['latest'].get('amount', 0) or 0
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

                st.markdown(f"""
                <div class="signal-card {card_cls}" style="display:flex; justify-content:space-between; align-items:center;">
                    <div style="flex:1;">
                        <b style="font-size:1.05rem;">{code} {name}</b><br/>
                        <span style="color:#888; font-size:0.82rem;">{arb_emoji} {arb_label}：{arb_desc}</span><br/>
                        <span style="color:{operable_color}; font-size:0.82rem; font-weight:600;">{operable_text}｜状态：{status_text}</span>
                    </div>
                    <div style="text-align:center; min-width:100px;">
                        <div style="color:{premium_color}; font-size:1.3rem; font-weight:700;">{d['current']:+.2f}%</div>
                        <div style="color:#aaa; font-size:0.75rem;">溢价率</div>
                    </div>
                    <div style="text-align:center; min-width:80px; margin:0 16px;">
                        <div style="color:#888; font-size:0.95rem;">{d['arb_cost']:.2f}%</div>
                        <div style="color:#aaa; font-size:0.75rem;">成本</div>
                    </div>
                    <div style="text-align:center; min-width:100px;">
                        <div style="color:{profit_color}; font-size:1.3rem; font-weight:700;">{d['arb_profit']:+.2f}%</div>
                        <div style="color:#aaa; font-size:0.75rem;">预计利润</div>
                    </div>
                    <div style="text-align:center; min-width:80px; margin-left:12px;">
                        <div style="font-size:0.95rem;">{amount:.1f}亿</div>
                        <div style="color:#aaa; font-size:0.75rem;">规模</div>
                    </div>
                </div>
                """, unsafe_allow_html=True)
        else:
            st.subheader("💰 套利机会")
            st.info("当前没有溢价/折价超过手续费成本的套利机会。可尝试调低左侧手续费参数。")

    # ── 排序列表（全宽）──────────────────────────────────────
    if lof_data:
        st.subheader("📊 LOF溢价率排序列表")

        rows = []
        for code, d in lof_data.items():
            latest = d['latest']
            rows.append({
                '代码': code,
                '名称': fund_names.get(code, ''),
                '溢价率(%)': round(d['current'], 2),
                '套利方向': d['arb_type'],
                '成本(%)': round(d['arb_cost'], 2),
                '套利利润(%)': round(d['arb_profit'], 2) if d['arb_viable'] else None,
                '申购状态': d['subscription_info'].get('apply_status', '未知'),
                '最小申购': d['subscription_info'].get('min_amt', '-'),
                '申购费': d['subscription_info'].get('apply_fee', '-'),
                '赎回状态': d['subscription_info'].get('redeem_status', '未知'),
                '赎回费': d['subscription_info'].get('redeem_fee', '-'),
                '收盘价': round(latest['price'], 3),
                '净值': round(latest.get('net_value', 0) or 0, 4),
                '规模(亿)': round(latest.get('amount', 0) or 0, 2),
                '7日均值(%)': round(d['mean_7d'], 2),
                '信号': d['signal'],
            })

        df_table = pd.DataFrame(rows).sort_values('溢价率(%)', ascending=False).reset_index(drop=True)

        # 条件格式：溢价率正红负绿
        def color_premium(val):
            if pd.isna(val):
                return ''
            color = '#cf1322' if val > 0 else '#0d8532' if val < 0 else '#666'
            return f'color: {color}; font-weight: 600'

        def color_signal(val):
            colors = {'BUY': '#0d8532', 'SELL': '#cf1322', 'HOLD': '#999'}
            return f'color: {colors.get(val, "#666")}; font-weight: 700'

        def color_arb_profit(val):
            if pd.isna(val):
                return 'color: #ccc'
            return f'color: #0d8532; font-weight: 700'

        def color_arb_type(val):
            colors = {'溢价套利': '#cf1322', '折价套利': '#0d8532', '无': '#999'}
            return f'color: {colors.get(val, "#666")}; font-weight: 600'

        def color_open_status(val):
            if is_status_open(val):
                return 'color: #0d8532; font-weight: 600'
            if val == '未知':
                return 'color: #d48806; font-weight: 600'
            return 'color: #cf1322; font-weight: 600'

        styled = df_table.style.map(color_premium, subset=['溢价率(%)', '7日均值(%)']) \
                               .map(color_signal, subset=['信号']) \
                               .map(color_arb_profit, subset=['套利利润(%)']) \
                               .map(color_arb_type, subset=['套利方向']) \
                               .map(color_open_status, subset=['申购状态', '赎回状态'])

        st.dataframe(
            styled,
            use_container_width=True,
            height=min(600, 40 + 35 * len(df_table)),
            column_config={
                "溢价率(%)": st.column_config.ProgressColumn(
                    "溢价率",
                    help="溢价率进度条 (范围 -10% ~ +10%)",
                    format="%.2f%%",
                    min_value=-10,
                    max_value=10,
                ),
            },
            hide_index=True,
        )

    # ── 交易信号 + 趋势图 左右分栏 ────────────────────────────
    if lof_data:
        col_signal, col_chart = st.columns([1, 2])

        with col_signal:
            st.subheader("🎯 交易信号")

            # 按信号优先级排序：BUY > SELL > HOLD
            signal_order = {'BUY': 0, 'SELL': 1, 'HOLD': 2}
            sorted_items = sorted(lof_data.items(), key=lambda x: signal_order[x[1]['signal']])

            for code, d in sorted_items:
                card_cls = signal_card_class(d['signal'])
                badge = signal_badge(d['signal'])
                name = fund_names.get(code, '')
                premium_color = '#cf1322' if d['current'] > 0 else '#0d8532' if d['current'] < 0 else '#666'

                st.markdown(f"""
                <div class="signal-card {card_cls}">
                    <div style="display:flex; justify-content:space-between; align-items:center;">
                        <div>
                            <b>{code}</b> <span style="color:#888; font-size:0.85rem;">{name}</span><br/>
                            <span style="color:{premium_color}; font-size:1.2rem; font-weight:700;">{d['current']:+.2f}%</span>
                            <span style="color:#aaa; font-size:0.8rem; margin-left:8px;">7日均 {d['mean_7d']:+.2f}%</span>
                        </div>
                        <div>{badge}</div>
                    </div>
                </div>
                """, unsafe_allow_html=True)

        with col_chart:
            st.subheader("📈 溢价率趋势图")

            selected_code = st.selectbox(
                "选择代码", selected_codes,
                format_func=lambda c: f"{c} - {fund_names.get(c, '')}",
                key="chart_select"
            )

            if selected_code in lof_data:
                df = lof_data[selected_code]['confirmed_df']
                d = lof_data[selected_code]

                if not df.empty:
                    fig = go.Figure()

                    # 布林带：7日均值 ± 1倍标准差
                    df_sorted = df.sort_values('price_dt').copy()
                    df_sorted['ma7'] = df_sorted['discount_rt'].rolling(window=7, min_periods=1).mean()
                    df_sorted['std7'] = df_sorted['discount_rt'].rolling(window=7, min_periods=1).std().fillna(0)
                    df_sorted['upper'] = df_sorted['ma7'] + df_sorted['std7']
                    df_sorted['lower'] = df_sorted['ma7'] - df_sorted['std7']

                    # 布林带填充
                    fig.add_trace(go.Scatter(
                        x=pd.concat([df_sorted['price_dt'], df_sorted['price_dt'][::-1]]),
                        y=pd.concat([df_sorted['upper'], df_sorted['lower'][::-1]]),
                        fill='toself',
                        fillcolor='rgba(33,150,243,0.08)',
                        line=dict(color='rgba(33,150,243,0.2)', width=0.5),
                        hoverinfo='skip',
                        name='布林带 (±1σ)',
                        showlegend=True,
                    ))

                    # 7日均线
                    fig.add_trace(go.Scatter(
                        x=df_sorted['price_dt'],
                        y=df_sorted['ma7'],
                        mode='lines',
                        name='7日均线',
                        line=dict(color='#ff6b6b', width=1.5, dash='dash'),
                    ))

                    # 溢价率主曲线
                    fig.add_trace(go.Scatter(
                        x=df_sorted['price_dt'],
                        y=df_sorted['discount_rt'],
                        mode='lines+markers',
                        name='溢价率',
                        line=dict(color='#2196F3', width=2),
                        marker=dict(size=3),
                    ))

                    # 当前点高亮
                    last = df_sorted.iloc[-1]
                    fig.add_trace(go.Scatter(
                        x=[last['price_dt']],
                        y=[last['discount_rt']],
                        mode='markers',
                        name='当前',
                        marker=dict(size=10, color='#ff4444', symbol='circle',
                                    line=dict(width=2, color='white')),
                        showlegend=True,
                    ))

                    fig.update_layout(
                        title=dict(
                            text=f"{selected_code} {fund_names.get(selected_code, '')}",
                            font=dict(size=16, color='#333'),
                        ),
                        xaxis_title="日期",
                        yaxis_title="溢价率 (%)",
                        height=420,
                        plot_bgcolor='#fafafa',
                        paper_bgcolor='#fff',
                        font=dict(family="system-ui, sans-serif"),
                        legend=dict(orientation="h", yanchor="bottom", y=1.02,
                                    xanchor="right", x=1, font=dict(size=11)),
                        margin=dict(l=60, r=30, t=60, b=40),
                        xaxis=dict(
                            showgrid=True, gridcolor='#eee',
                            tickfont=dict(size=10),
                        ),
                        yaxis=dict(
                            showgrid=True, gridcolor='#eee',
                            tickfont=dict(size=10),
                            zeroline=True, zerolinecolor='#ccc', zerolinewidth=1,
                        ),
                        hovermode='x unified',
                    )

                    st.plotly_chart(fig, use_container_width=True)


if __name__ == "__main__":
    main()
