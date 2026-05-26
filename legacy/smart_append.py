#!/usr/bin/env python3
"""
智能增量数据追加系统
解决API滚动窗口50条限制的数据同步问题
"""
import requests
import pandas as pd
import os
import json
import time
from datetime import datetime, timedelta
from typing import Dict, List, Tuple

class SmartDataSync:
    """智能数据同步器"""
    
    def __init__(self, data_dir: str = "data"):
        self.data_dir = data_dir
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'application/json, text/javascript, */*; q=0.01',
            'X-Requested-With': 'XMLHttpRequest',
        }
        self.params = {
            '___jsl': 'LST___t',
            'rp': '50',
            'page': '1'
        }
    
    def load_existing_data(self, code: str) -> pd.DataFrame:
        """加载本地现有数据"""
        filename = f"{self.data_dir}/lof_{code}.csv"
        if os.path.exists(filename):
            try:
                df = pd.read_csv(filename)
                df['price_dt'] = pd.to_datetime(df['price_dt'])
                return df
            except Exception as e:
                print(f"❌ 加载 {code} 数据失败: {e}")
        return pd.DataFrame()
    
    def fetch_api_data(self, code: str) -> pd.DataFrame:
        """从API获取最新50条数据"""
        url = f"https://www.jisilu.cn/data/lof/hist_list/{code}"
        
        try:
            response = requests.get(url, params=self.params, headers=self.headers, timeout=30)
            
            if response.status_code == 200:
                data = response.json()
                rows = data.get('rows', [])
                
                if rows:
                    records = []
                    for row in rows:
                        cell = row['cell']
                        record = dict(cell)
                        record['code'] = code
                        records.append(record)
                    
                    df = pd.DataFrame(records)
                    df['price_dt'] = pd.to_datetime(df['price_dt'])
                    
                    # 转换数值类型
                    numeric_cols = ['price', 'discount_rt', 'net_value']
                    for col in numeric_cols:
                        if col in df.columns:
                            df[col] = pd.to_numeric(df[col], errors='coerce')
                    
                    return df
            
            return pd.DataFrame()
            
        except Exception as e:
            print(f"❌ 获取 {code} API数据失败: {e}")
            return pd.DataFrame()
    
    def find_new_records(self, existing_df: pd.DataFrame, api_df: pd.DataFrame) -> pd.DataFrame:
        """找出API中的新增记录"""
        if existing_df.empty:
            return api_df
        
        if api_df.empty:
            return pd.DataFrame()
        
        # 基于日期进行精确匹配
        existing_dates = set(existing_df['price_dt'])
        api_dates = set(api_df['price_dt'])
        
        # 找出API中新增的日期
        new_dates = api_dates - existing_dates
        
        if new_dates:
            new_records = api_df[api_df['price_dt'].isin(new_dates)]
            return new_records
        
        return pd.DataFrame()
    
    def find_overlap_records(self, existing_df: pd.DataFrame, api_df: pd.DataFrame) -> Dict:
        """找出重叠记录进行验证"""
        if existing_df.empty or api_df.empty:
            return {}
        
        # 找出日期重叠的部分
        existing_dates = set(existing_df['price_dt'])
        api_dates = set(api_df['price_dt'])
        overlap_dates = existing_dates & api_dates
        
        if not overlap_dates:
            return {}
        
        # 验证重叠数据的准确性
        verification = {}
        for date in overlap_dates:
            existing_row = existing_df[existing_df['price_dt'] == date].iloc[0]
            api_row = api_df[api_df['price_dt'] == date].iloc[0]
            
            verification[str(date)[:10]] = {
                'price_match': abs(existing_row['price'] - api_row['price']) < 0.001,
                'discount_match': str(existing_row['discount_rt']) == str(api_row['discount_rt']),
                'price_diff': abs(existing_row['price'] - api_row['price']),
                'discount_diff': str(existing_row['discount_rt']) + " vs " + str(api_row['discount_rt'])
            }
        
        return verification
    
    def smart_append(self, code: str) -> Dict[str, any]:
        """智能追加数据到单个LOF"""
        print(f"🔄 处理 {code}...")
        
        # 加载现有数据
        existing_df = self.load_existing_data(code)
        
        # 获取API数据
        api_df = self.fetch_api_data(code)
        
        if api_df.empty:
            return {
                'code': code,
                'status': 'failed',
                'message': 'API数据获取失败',
                'existing_records': len(existing_df),
                'new_records': 0
            }
        
        # 找出新增记录
        new_records = self.find_new_records(existing_df, api_df)
        
        # 验证重叠数据
        overlap_verification = self.find_overlap_records(existing_df, api_df)
        
        if not new_records.empty:
            # 合并数据
            combined_df = pd.concat([existing_df, new_records])
            combined_df = combined_df.sort_values('price_dt').reset_index(drop=True)
            
            # 保存更新后的数据
            filename = f"{self.data_dir}/lof_{code}.csv"
            combined_df.to_csv(filename, index=False, encoding='utf-8-sig')
            
            return {
                'code': code,
                'status': 'updated',
                'existing_records': len(existing_df),
                'new_records': len(new_records),
                'total_records': len(combined_df),
                'latest_date': combined_df['price_dt'].max().strftime('%Y-%m-%d'),
                'overlap_verified': len(overlap_verification),
                'api_records': len(api_df)
            }
        else:
            return {
                'code': code,
                'status': 'no_change',
                'existing_records': len(existing_df),
                'new_records': 0,
                'total_records': len(existing_df),
                'latest_date': existing_df['price_dt'].max().strftime('%Y-%m-%d') if not existing_df.empty else '无数据',
                'overlap_verified': len(overlap_verification),
                'api_records': len(api_df)
            }
    
    def sync_all_lofs(self) -> Dict[str, List]:
        """同步所有LOF数据"""
        print("🚀 开始智能数据同步...")
        print("=" * 60)
        
        # 读取LOF代码
        try:
            with open('all_LOF.txt', 'r', encoding='utf-8') as f:
                lof_codes = [line.strip() for line in f if line.strip()]
        except FileNotFoundError:
            print("❌ all_LOF.txt 文件未找到")
            return {}
        
        results = {
            'updated': [],
            'no_change': [],
            'failed': [],
            'summary': {}
        }
        
        total_new = 0
        total_existing = 0
        
        for i, code in enumerate(lof_codes, 1):
            try:
                result = self.smart_append(code)
                
                if result['status'] == 'updated':
                    results['updated'].append(result)
                    total_new += result['new_records']
                    total_existing += result['existing_records']
                    print(f"[{i:2d}/{len(lof_codes)}] ✅ {code}: +{result['new_records']}条新数据 (共{result['total_records']}条)")
                elif result['status'] == 'no_change':
                    results['no_change'].append(result)
                    total_existing += result['existing_records']
                    print(f"[{i:2d}/{len(lof_codes)}] ℹ️ {code}: 无新数据 (现有{result['existing_records']}条)")
                else:
                    results['failed'].append(result)
                    print(f"[{i:2d}/{len(lof_codes)}] ❌ {code}: 失败 - {result['message']}")
                
                time.sleep(0.5)  # 避免请求过快
                
            except Exception as e:
                results['failed'].append({'code': code, 'status': 'error', 'message': str(e)})
                print(f"[{i:2d}/{len(lof_codes)}] ❌ {code}: 异常 - {e}")
        
        # 生成汇总
        results['summary'] = {
            'total_codes': len(lof_codes),
            'updated_codes': len(results['updated']),
            'no_change_codes': len(results['no_change']),
            'failed_codes': len(results['failed']),
            'total_new_records': total_new,
            'total_existing_records': total_existing,
            'total_records_after_sync': total_existing + total_new
        }
        
        return results
    
    def generate_sync_report(self, results: Dict):
        """生成同步报告"""
        summary = results['summary']
        
        print("\n" + "=" * 60)
        print("📊 智能同步完成报告")
        print("=" * 60)
        print(f"📈 总代码数: {summary['total_codes']}")
        print(f"✅ 更新代码: {summary['updated_codes']}")
        print(f"ℹ️  无变化代码: {summary['no_change_codes']}")
        print(f"❌ 失败代码: {summary['failed_codes']}")
        print(f"📋 新增记录: {summary['total_new_records']}")
        print(f"📊 总记录数: {summary['total_records_after_sync']}")
        
        if results['updated']:
            print(f"\n📈 更新详情:")
            for result in results['updated'][:5]:  # 显示前5个
                print(f"  {result['code']}: +{result['new_records']}条, 最新: {result['latest_date']}")
        
        return results

if __name__ == "__main__":
    syncer = SmartDataSync()
    results = syncer.sync_all_lofs()
    syncer.generate_sync_report(results)