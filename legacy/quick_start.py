#!/usr/bin/env python3
"""
快速启动脚本
整合所有核心功能，提供简洁的CLI接口
"""
import os
import sys
import subprocess
from utils.data_manager import DataManager
from core.data_sync import DataSyncCore

def check_environment():
    """检查环境"""
    print("🔍 检查环境...")
    
    # 检查data目录
    if not os.path.exists('data'):
        os.makedirs('data', exist_ok=True)
        print("✅ 创建data目录")
    
    # 检查all_LOF.txt
    if not os.path.exists('all_LOF.txt'):
        print("❌ 缺少all_LOF.txt文件")
        return False
    
    # 检查Python环境
    try:
        import pandas
        import streamlit
        import plotly
        print("✅ 依赖检查通过")
    except ImportError as e:
        print(f"❌ 缺少依赖: {e}")
        return False
    
    return True

def show_status():
    """显示系统状态"""
    manager = DataManager()
    summary = manager.get_data_summary()
    
    print("\n📊 系统状态")
    print("=" * 30)
    print(f"📈 LOF数量: {summary['total_lofs']}")
    print(f"📋 总记录: {summary['total_records']}")
    
    if summary['latest_dates']:
        latest = list(summary['latest_dates'].items())[-1]
        print(f"🗓️  最新数据: {latest[0]} ({latest[1]})")
    
    return summary['total_lofs'] > 0

def main():
    print("🚀 LOF溢价率交易系统 - 快速启动")
    print("=" * 50)
    
    if not check_environment():
        print("❌ 环境检查未通过")
        return
    
    has_data = show_status()
    
    print("\n🎯 可用操作:")
    print("1. 数据同步")
    print("2. 启动Web仪表板")
    print("3. 查看帮助")
    
    if not has_data:
        print("\n⚠️  首次运行，建议先同步数据")
        choice = input("是否同步数据? (y/n): ").lower()
        if choice == 'y':
            syncer = DataSyncCore()
            results = syncer.sync_all()
            print(f"✅ 同步完成: {len(results['updated'])}个LOF已更新")
    
    print("\n🎉 启动仪表板...")
    os.system("streamlit run scripts/dashboard.py")

if __name__ == "__main__":
    main()