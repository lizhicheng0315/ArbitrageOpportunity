#!/usr/bin/env python3
"""
每日数据同步脚本
核心功能的简洁调用接口
"""
import sys
import os
import argparse

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")

# 添加路径以便导入模块
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.data_sync import DataSyncCore
from utils.data_manager import DataManager

def main():
    parser = argparse.ArgumentParser(description="LOF每日数据同步")
    parser.add_argument("--init", action="store_true", help="首次初始化数据")
    parser.add_argument("--code", type=str, help="指定单个LOF代码")
    parser.add_argument("--verify", action="store_true", help="验证数据完整性")
    
    args = parser.parse_args()
    
    syncer = DataSyncCore()
    manager = DataManager()
    
    if args.init:
        print("首次数据初始化...")
        results = syncer.sync_all()
        
        updated = len(results['updated'])
        total = len(results['updated']) + len(results['no_change']) + len(results['failed'])
        
        print(f"初始化完成: {updated}/{total} 个LOF已更新")
        return
    
    if args.code:
        print(f"同步单个LOF: {args.code}")
        result = syncer.sync_single_lof(args.code)
        print(f"{result['code']}: {result['status']} - {result['existing']}→{result['total']}条")
        return
    
    if args.verify:
        print("验证数据完整性...")
        summary = manager.get_data_summary()
        print(f"总LOF: {summary['total_lofs']}, 总记录: {summary['total_records']}")
        
        # 显示最近5个LOF的数据状态
        latest = list(summary['latest_dates'].items())[-5:]
        for code, date in latest:
            print(f"  {code}: {date}")
        return
    
    # 默认：执行增量同步
    print("执行增量数据同步...")
    results = syncer.sync_all()
    
    updated = len(results['updated'])
    total = len(results['updated']) + len(results['no_change']) + len(results['failed'])
    new_records = sum(r['new'] for r in results['updated'])
    
    print(f"同步完成: {updated}/{total} 个LOF更新, 新增{new_records}条记录")

if __name__ == "__main__":
    main()