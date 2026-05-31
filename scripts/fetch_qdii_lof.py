"""
从集思录 QDII 列表（A/E份额）爬取 LOF 的申购/赎回状态
"""
import requests
import json
import sys

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'application/json, text/javascript, */*; q=0.01',
    'X-Requested-With': 'XMLHttpRequest',
    'Referer': 'https://www.jisilu.cn/data/qdii/',
}

ENDPOINTS = [
    'https://www.jisilu.cn/data/qdii/qdii_list/A',
    'https://www.jisilu.cn/data/qdii/qdii_list/E',
]

PARAMS = {'only_lof': 'y', 'rp': '50'}

FIELDS = [
    'fund_id', 'fund_nm', 'lof_type',
    'apply_status', 'redeem_status',
    'apply_fee', 'redeem_fee', 'min_amt',
    'apply_fee_tips', 'redeem_fee_tips',
    'discount_rt', 'price', 'fund_nav',
]


def fetch_qdii_lof():
    """抓取 QDII 列表中的 LOF 基金，返回 {fund_id: {...}} 字典"""
    result = {}

    for url in ENDPOINTS:
        try:
            r = requests.get(url, params=PARAMS, headers=HEADERS, timeout=15)
            if r.status_code != 200:
                print(f"[WARN] {url} -> {r.status_code}", file=sys.stderr)
                continue
            data = r.json()
            for row in data.get('rows', []):
                cell = row.get('cell', {})
                fund_id = cell.get('fund_id', '')
                if not fund_id:
                    continue
                fund_id = cell.get('fund_id', '')
                if not fund_id or fund_id in result:
                    continue
                info = {}
                for f in FIELDS:
                    info[f] = cell.get(f, '')
                info['source'] = url.split('/')[-1]
                result[fund_id] = info
        except Exception as e:
            print(f"[ERR] {url}: {e}", file=sys.stderr)

    return result


def main():
    lof_data = fetch_qdii_lof()
    import sys
    sys.stdout.reconfigure(encoding='utf-8')
    print(json.dumps(lof_data, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
