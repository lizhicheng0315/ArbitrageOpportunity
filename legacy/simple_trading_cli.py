#!/usr/bin/env python3
"""
简单的交易决策CLI工具
基于历史溢价率提供交易建议
"""
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import json
import os
from typing import Dict, List

class SimpleTradingAnalyzer:
    """简单的交易分析器"""
    
    def __init__(self, data_dir: str = "data"):
        self.data_dir = data_dir
        self.lof_data = {}
        self.load_all_data()
    
    def load_all_data(self):
        """加载所有LOF数据"""
        csv_files = [f for f in os.listdir(self.data_dir) 
                    if f.startswith('lof_') and f.endswith('.csv')]
        
        for file in csv_files:
            code = file.replace('lof_', '').replace('.csv', '')
            file_path = os.path.join(self.data_dir, file)
            try:
                df = pd.read_csv(file_path)
                df['price_dt'] = pd.to_datetime(df['price_dt'])
                df['discount_rt'] = pd.to_numeric(df['discount_rt'], errors='coerce')
                df['price'] = pd.to_numeric(df['price'], errors='coerce')
                self.lof_data[code] = df.sort_values('price_dt')
            except Exception as e:
                print(f"加载 {code} 数据失败: {e}")
    
    def calculate_averages(self, code: str) -> Dict:
        """计算7/14/21日平均溢价率"""
        if code not in self.lof_data:
            return {}
        
        df = self.lof_data[code]
        
        results = {}
        for days in [7, 14, 21]:
            cutoff = datetime.now() - timedelta(days=days)
            recent = df[df['price_dt'] >= cutoff].copy()
            
            if not recent.empty:
                avg = recent['discount_rt'].mean()
                std = recent['discount_rt'].std()
                current = recent['discount_rt'].iloc[-1]
                results[f'{days}d'] = {
                    'avg': round(avg, 2),
                    'std': round(std, 2) if pd.notna(std) else 0,
                    'current': round(current, 2),
                    'count': len(recent)
                }
        
        return results
    
    def get_trading_advice(self, code: str) -> Dict:
        """获取交易建议"""
        if code not in self.lof_data:
            return {}
        
        df = self.lof_data[code]
        latest = df.iloc[-1]
        current_premium = latest['discount_rt']
        current_price = latest['price']
        
        averages = self.calculate_averages(code)
        if not averages:
            return {}
        
        # 核心交易逻辑
        advice = {
            'code': code,
            'current_premium': round(current_premium, 2),
            'current_price': round(current_price, 3),
            'averages': averages,
            'signals': {}
        }
        
        # 基于7日平均的交易信号
        if '7d' in averages:
            avg_7d = averages['7d']['avg']
            std_7d = averages['7d']['std']
            
            # Z-score计算
            z_score = (current_premium - avg_7d) / std_7d if std_7d > 0 else 0
            
            # 交易信号
            if z_score > 1.5:
                signal = "SELL"
                confidence = min(0.9, abs(z_score) * 0.2)
                reason = f"当前溢价率({current_premium}%)显著高于7日平均({avg_7d}%)"
            elif z_score < -1.5:
                signal = "BUY"
                confidence = min(0.9, abs(z_score) * 0.2)
                reason = f"当前折价率({current_premium}%)显著低于7日平均({avg_7d}%)"
            else:
                signal = "HOLD"
                confidence = 0.5
                reason = "当前溢价率处于正常区间"
            
            advice['signals']['7d'] = {
                'signal': signal,
                'confidence': round(confidence, 2),
                'z_score': round(z_score, 2),
                'reason': reason,
                'threshold': f"±1.5σ (±{round(std_7d * 1.5, 2)}%)"
            }
        
        # 基于14日平均的交易信号
        if '14d' in averages:
            avg_14d = averages['14d']['avg']
            advice['signals']['14d'] = {
                'vs_14d': round(current_premium - avg_14d, 2),
                'interpretation': "溢价" if current_premium > avg_14d else "折价"
            }
        
        # 基于21日平均的交易信号
        if '21d' in averages:
            avg_21d = averages['21d']['avg']
            advice['signals']['21d'] = {
                'vs_21d': round(current_premium - avg_21d, 2),
                'interpretation': "溢价" if current_premium > avg_21d else "折价"
            }
        
        return advice
    
    def analyze_all_lofs(self) -> List[Dict]:
        """分析所有LOF"""
        results = []
        for code in self.lof_data.keys():
            advice = self.get_trading_advice(code)
            if advice:
                results.append(advice)
        
        # 按当前溢价率排序
        return sorted(results, key=lambda x: abs(x['current_premium']), reverse=True)
    
    def get_filtered_signals(self, signal_type: str = None) -> List[Dict]:
        """获取过滤后的交易信号"""
        all_signals = self.analyze_all_lofs()
        
        if not signal_type:
            return all_signals
        
        filtered = []
        for item in all_signals:
            for period, signal_data in item['signals'].items():
                if isinstance(signal_data, dict) and 'signal' in signal_data:
                    if signal_data['signal'] == signal_type.upper():
                        filtered.append(item)
                        break
        
        return filtered
    
    def export_analysis(self, output_file: str = "trading_analysis.json"):
        """导出分析结果"""
        analysis = {
            "generated_at": datetime.now().isoformat(),
            "methodology": {
                "description": "基于历史溢价率的均值回归交易策略",
                "timeframes": ["7d", "14d", "21d"],
                "threshold": "±1.5σ (标准差)",
                "risk_management": "基于统计套利的低风险策略"
            },
            "signals": self.analyze_all_lofs()
        }
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(analysis, f, ensure_ascii=False, indent=2, default=str)
        
        return analysis

def display_trading_report():
    """显示交易报告"""
    analyzer = SimpleTradingAnalyzer()
    
    print("🎯 LOF溢价率交易分析报告")
    print("=" * 60)
    print(f"分析时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"数据来源: 集思录历史数据")
    print(f"分析LOF数量: {len(analyzer.lof_data)}")
    print()
    
    # 获取所有信号
    all_signals = analyzer.analyze_all_lofs()
    
    if not all_signals:
        print("❌ 暂无数据")
        return
    
    # 统计信号
    buy_signals = analyzer.get_filtered_signals("BUY")
    sell_signals = analyzer.get_filtered_signals("SELL")
    
    print(f"🔍 交易信号统计:")
    print(f"   买入信号: {len(buy_signals)}")
    print(f"   卖出信号: {len(sell_signals)}")
    print(f"   持有观望: {len(all_signals) - len(buy_signals) - len(sell_signals)}")
    print()
    
    # 显示买入信号
    if buy_signals:
        print("📈 买入信号 (折价机会):")
        print("-" * 40)
        for item in buy_signals[:5]:  # 显示前5个
            print(f"\n🏦 {item['code']}")
            print(f"   当前溢价率: {item['current_premium']}%")
            print(f"   当前价格: {item['current_price']}")
            print(f"   7日平均: {item['averages']['7d']['avg']}%")
            print(f"   置信度: {item['signals']['7d']['confidence']}")
            print(f"   理由: {item['signals']['7d']['reason']}")
    
    # 显示卖出信号
    if sell_signals:
        print("\n📉 卖出信号 (溢价机会):")
        print("-" * 40)
        for item in sell_signals[:5]:  # 显示前5个
            print(f"\n🏦 {item['code']}")
            print(f"   当前溢价率: {item['current_premium']}%")
            print(f"   当前价格: {item['current_price']}")
            print(f"   7日平均: {item['averages']['7d']['avg']}%")
            print(f"   置信度: {item['signals']['7d']['confidence']}")
            print(f"   理由: {item['signals']['7d']['reason']}")
    
    # 导出分析
    analysis = analyzer.export_analysis()
    print(f"\n✅ 详细分析已导出到: trading_analysis.json")
    
    return analyzer

if __name__ == "__main__":
    display_trading_report()