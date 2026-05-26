#!/usr/bin/env python3
"""
修复T+1数据延迟问题的脚本
清理"-"占位符，确保只保留T+1确认的完整数据
"""
import pandas as pd
import os
import glob
from datetime import datetime

def fix_t1_data_for_lof(code):
    """修复单个LOF的T+1数据"""
    filename = f"data/lof_{code}.csv"
    if not os.path.exists(filename):
        return False
    
    try:
        df = pd.read_csv(filename)
        df['price_dt'] = pd.to_datetime(df['price_dt'])
        
        # 检查是否有"-"占位符
        mask_missing = df['discount_rt'] == "-"
        missing_count = mask_missing.sum()
        
        if missing_count == 0:
            print(f"{code}: 无缺失数据")
            return False
        
        # 删除含有"-"的记录（T日未确认数据）
        clean_df = df[df['discount_rt'] != "-"].copy()
        
        # 转换数据类型
        clean_df['discount_rt'] = pd.to_numeric(clean_df['discount_rt'], errors='coerce')
        clean_df = clean_df.dropna(subset=['discount_rt'])
        
        # 按日期排序并保存
        clean_df = clean_df.sort_values('price_dt').reset_index(drop=True)
        clean_df.to_csv(filename, index=False, encoding='utf-8-sig')
        
        print(f"{code}: 删除{missing_count}条T日未确认数据，保留{clean_df.shape[0]}条T+1确认数据")
        return True
        
    except Exception as e:
        print(f"{code}: 处理错误 - {e}")
        return False

def check_t1_status():
    """检查所有LOF的T+1状态"""
    csv_files = glob.glob('data/lof_*.csv')
    
    total_missing = 0
    fixed_count = 0
    
    print("🔍 检查T+1数据状态...")
    print("=" * 60)
    
    for file in csv_files:
        code = file.replace('data/lof_', '').replace('.csv', '')
        
        try:
            df = pd.read_csv(file)
            missing_count = (df['discount_rt'] == "-").sum()
            
            if missing_count > 0:
                print(f"{code}: {missing_count} 条T日未确认数据")
                total_missing += missing_count
                
                # 同时修复
                if fix_t1_data_for_lof(code):
                    fixed_count += 1
            
        except Exception as e:
            print(f"{code}: 读取错误 - {e}")
    
    print("=" * 60)
    print(f"📊 总计发现 {total_missing} 条T日未确认数据")
    print(f"✅ 成功修复 {fixed_count} 个LOF文件")
    
    return total_missing, fixed_count

def verify_fix():
    """验证修复结果"""
    csv_files = glob.glob('data/lof_*.csv')
    
    print("\n✅ 验证修复结果...")
    print("=" * 40)
    
    clean_count = 0
    total_records = 0
    
    for file in csv_files:
        code = file.replace('data/lof_', '').replace('.csv', '')
        
        try:
            df = pd.read_csv(file)
            missing_count = (df['discount_rt'] == "-").sum()
            
            if missing_count == 0:
                clean_count += 1
                
            latest_date = df['price_dt'].max()
            record_count = len(df)
            total_records += record_count
            
            print(f"{code}: {latest_date} ({record_count}条记录)")
            
        except Exception as e:
            print(f"{code}: 验证错误 - {e}")
    
    print(f"\n📊 验证结果:")
    print(f"✅ 干净数据文件: {clean_count}/{len(csv_files)}")
    print(f"📈 总记录数: {total_records}")

if __name__ == "__main__":
    print("🚀 开始修复T+1数据延迟问题")
    print("=" * 50)
    
    # 检查并修复
    total_missing, fixed_count = check_t1_status()
    
    # 验证结果
    verify_fix()
    
    print("\n🎯 T+1数据修复完成！")
    print("所有LOF现在只包含T+1确认的完整数据")