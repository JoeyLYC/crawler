import pandas as pd
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright
import re

def retrieve_content():
    journals = []
    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=False)

        page = browser.new_page()

        search_url = "https://navi.cnki.net/knavi/"

        page.goto(search_url)
        search_box = page.locator('[name="txt_1_value1"]')
        search_query = "骨科"
        search_box.fill(search_query)

        search_button = page.locator('#btnSearch')
        search_button.click()

        # page 1
        result = page.locator('#searchResult')
        result.wait_for()
        journals.extend(get_journals(result.inner_html()))

        # go to page 2
        page.get_by_role("link", name="2", exact=True).click()
        # check the top pagination change to 2
        page.locator("#txtPageGoToBottom").filter(has_text="2").wait_for()
        # page.pause()
        result = page.locator('#searchResult')
        journals.extend(get_journals(result.inner_html()))

        browser.close()
        return journals

def clean_text(text):
    return ' '.join(text.replace('\n', '').split())

def extract_after(text, pattern):
    pos = text.find(pattern)
    return text[pos+len(pattern):].strip()

def extract_factors(data):
    factors = {}
    # sample data: '复合影响因子：0.969 综合影响因子：0.841 被引次数：16615 下载次数：428569'
    result = data.split(' ')
    for r in result:
        kv = r.split('：')
        if len(kv) == 2:
            factors[kv[0]] = kv[1]
    return factors

def get_journals(html_content):
    soup = BeautifulSoup(html_content, 'html.parser')
    dl_tags = soup.find_all('dl', class_='result')
    journals = []
    for dl_tag in dl_tags:
        div_tag = dl_tag.find("div", class_="re_tag fl")
        if div_tag:
            pub_type = div_tag.find("span").text
            if pub_type != "期刊":
                continue
        div_brief = dl_tag.find("div", class_="re_brief fl")
        if div_brief:
            title = clean_text(div_brief.find("h1").text)
            ul_tag = div_brief.find("ul")
            li_items = [clean_text(li.text) for li in ul_tag.find_all("li")]
            org_name = extract_after(li_items[0], '主办单位：')
            data = extract_factors(li_items[2])
            # print(li_items[2])

            journals.append({
                "期刊名": title, 
                "主办单位": org_name,
                **data
            })
    return journals

if __name__ == "__main__":
    journals = retrieve_content()
    df = pd.DataFrame(journals)
    df = df.sort_values(by="综合影响因子", ascending=False)
    df.to_excel("journals.xlsx", index=False)
