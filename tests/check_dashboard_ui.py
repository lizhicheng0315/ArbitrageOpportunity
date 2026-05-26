from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page()
    page.goto('http://localhost:8503')
    page.wait_for_load_state('networkidle')
    page.wait_for_timeout(3000)
    page.get_by_text('160140 - SELL').click()
    page.wait_for_timeout(1000)
    text = page.locator('body').inner_text()
    print(text[:3000])
    assert '当前溢价率' in text or '当前溢价' in text
    assert 'nan%' not in text.lower()
    browser.close()
