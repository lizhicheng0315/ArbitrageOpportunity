#!/usr/bin/env python3
"""
Complete sync script that saves ALL API data without filtering
"""
import requests
import pandas as pd
import json
import time
import os
import shutil

# Clean and create data directory
if os.path.exists('data'):
    shutil.rmtree('data')
os.makedirs('data', exist_ok=True)

# Read LOF codes
with open('all_LOF.txt', 'r', encoding='utf-8') as f:
    lof_codes = [line.strip() for line in f if line.strip()]

print(f"📋 Found {len(lof_codes)} LOF codes")

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
    'Accept': 'application/json, text/javascript, */*; q=0.01',
    'X-Requested-With': 'XMLHttpRequest',
}

params = {
    '___jsl': 'LST___t',
    'rp': '50',
    'page': '1'
}

def fetch_lof_data(code):
    """Fetch LOF data using synchronous requests - save all columns"""
    url = f"https://www.jisilu.cn/data/lof/hist_list/{code}"
    
    try:
        response = requests.get(url, params=params, headers=headers, timeout=30)
        
        if response.status_code == 200:
            data = response.json()
            
            # Extract rows
            rows = data.get('rows', [])
            
            if rows:
                # Convert to dataframe with all columns
                records = []
                for row in rows:
                    cell = row['cell']
                    # Save all data from cell as-is
                    record = dict(cell)  # Copy all fields
                    record['code'] = code  # Add code for reference
                    records.append(record)
                
                df = pd.DataFrame(records)
                
                # Save to CSV with all columns
                filename = f"data/lof_{code}.csv"
                df.to_csv(filename, index=False, encoding='utf-8-sig')
                print(f"✅ Saved {len(records)} records for {code}")
                return len(records)
            else:
                print(f"⚠️ No data for {code}")
                return 0
        else:
            print(f"❌ HTTP {response.status_code} for {code}")
            return 0
            
    except Exception as e:
        print(f"❌ Error for {code}: {e}")
        return 0

def main():
    print("🚀 Starting complete sync with ALL API data...")
    print("=" * 60)
    
    total_records = 0
    successful_codes = 0
    failed_codes = []
    
    for i, code in enumerate(lof_codes, 1):
        print(f"[{i:2d}/{len(lof_codes)}] Processing {code}...")
        
        count = fetch_lof_data(code)
        if count > 0:
            total_records += count
            successful_codes += 1
        else:
            failed_codes.append(code)
        
        # Add small delay to be respectful
        time.sleep(1)
    
    print("=" * 60)
    print(f"🎯 COMPLETE SYNC FINISHED")
    print(f"📊 Total records: {total_records}")
    print(f"✅ Successful codes: {successful_codes}")
    print(f"❌ Failed codes: {len(failed_codes)}")
    
    if failed_codes:
        print(f"Failed codes: {failed_codes}")
    
    # Show sample of saved data
    success_files = [f for f in os.listdir('data') if f.startswith('lof_') and f.endswith('.csv')]
    if success_files:
        sample_file = f"data/{success_files[0]}"
        df = pd.read_csv(sample_file)
        print(f"\n📈 Sample columns for {success_files[0]}:")
        print(list(df.columns))
        print(f"\n📋 First 3 rows:")
        print(df.head(3))

if __name__ == "__main__":
    main()