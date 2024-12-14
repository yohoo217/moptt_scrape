import time
import csv
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# 設置和初始化部分保持不變
chrome_driver_path = '/Users/aotter/chromedriver-mac-arm64/chromedriver'
chrome_options = Options()
chrome_options.add_argument('--headless')
chrome_options.add_argument('--no-sandbox')
chrome_options.add_argument('--disable-dev-shm-usage')
service = Service(chrome_driver_path)
driver = webdriver.Chrome(service=service, options=chrome_options)

def login():
    # 登入函數保持不變
    url = 'https://trek.aotter.net/advertiser/list/campaign'
    driver.get(url)
    try:
        email_input = WebDriverWait(driver, 20).until(
            EC.presence_of_element_located((By.XPATH, "//input[@placeholder='Email 帳號']"))
        )
        email_input.send_keys("ian.chen@aotter.net")
        password_input = driver.find_element(By.XPATH, "//input[@placeholder='密碼']")
        password_input.send_keys("ean840217")
        login_button = driver.find_element(By.XPATH, "//button[@type='submit']")
        login_button.click()
        print("成功登入")
        
        user_span = WebDriverWait(driver, 20).until(
            EC.presence_of_element_located((By.XPATH, "//span[@class='team-label-name' and text()='ian.chen']"))
        )
        parent_element = user_span.find_element(By.XPATH, "..")
        parent_element.click()
        
        company_link = WebDriverWait(driver, 20).until(
            EC.presence_of_element_located((By.LINK_TEXT, "電豹股份有限公司"))
        )
        company_link.click()
    except Exception as e:
        print(f"登入時發生錯誤: {e}")
        driver.quit()
        exit()

# 1. 爬取 campaign URLs
def get_campaign_urls(page_count):
    campaign_urls = []
    base_url = "https://trek.aotter.net/advertiser/list/campaign?page="
    
    for page in range(1, page_count + 1):
        page_url = base_url + str(page)
        driver.get(page_url)
        try:
            WebDriverWait(driver, 20).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "tr.active.js-clickable"))
            )
            rows = driver.find_elements(By.CSS_SELECTOR, "tr.active.js-clickable")
            base_campaign_url = 'https://trek.aotter.net'
            for row in rows:
                relative_url = row.get_attribute('data-url')
                full_url = base_campaign_url + relative_url
                if full_url.startswith("https://trek.aotter.net/advertiser/show/campaign?campId="):
                    campaign_urls.append(full_url)
            print(f"第 {page} 頁找到 {len(rows)} 個 campaign URLs")
        except Exception as e:
            print(f"爬取第 {page} 頁時發生錯誤: {e}")
    
    return campaign_urls

# 2. 爬取每個 campaign 的 adset URLs、click rate 和 campaign 名稱
def get_campaign_data(campaign_urls):
    campaign_data = []
    for url in campaign_urls:
        try:
            driver.get(url)
            
            # 獲取 campaign 名稱
            campaign_name_element = WebDriverWait(driver, 20).until(
                EC.presence_of_element_located((By.XPATH, "//h3"))
            )
            campaign_name = campaign_name_element.text.strip()

            # 獲取 campaign click rate
            click_rate_element = WebDriverWait(driver, 20).until(
                EC.presence_of_element_located((By.XPATH, "//h4[text()='期間點擊率']/following-sibling::div//h2"))
            )
            campaign_click_rate = click_rate_element.text.strip()
            
            # 獲取 adset URLs
            adset_elements = driver.find_elements(By.XPATH, "//a[contains(@href, '/advertiser/show/adset?setId=')]")
            adset_urls = [element.get_attribute('href') for element in adset_elements]
            
            campaign_data.append({
                'campaign_url': url,
                'campaign_name': campaign_name,  # 新增 campaign 名稱
                'click_rate': campaign_click_rate,
                'adset_urls': adset_urls
            })
            print(f"處理 campaign: {url}, 名稱: {campaign_name}, 找到 {len(adset_urls)} 個 adset URLs")
        except Exception as e:
            print(f"處理 campaign {url} 時發生錯誤: {e}")
    return campaign_data


# 3. 爬取每個 adset 的 adunit URLs 和 click rate
def get_adset_data(campaign_data):
    for campaign in campaign_data:
        campaign['adsets'] = []
        for adset_url in campaign['adset_urls']:
            try:
                driver.get(adset_url)
                # 獲取 adset click rate
                adset_click_rate_element = WebDriverWait(driver, 20).until(
                    EC.presence_of_element_located((By.XPATH, "//h4[text()='期間點擊率']/following-sibling::div//h2"))
                )
                adset_click_rate = adset_click_rate_element.text.strip()
                
                # 獲取 adunit URLs
                adunit_elements = driver.find_elements(By.XPATH, "//a[contains(@href, '/advertiser/show/adunit?uuid=')]")
                adunit_urls = [element.get_attribute('href') for element in adunit_elements]
                
                campaign['adsets'].append({
                    'adset_url': adset_url,
                    'click_rate': adset_click_rate,
                    'adunit_urls': adunit_urls
                })
                print(f"處理 adset: {adset_url}, 找到 {len(adunit_urls)} 個 adunit URLs")
            except Exception as e:
                print(f"處理 adset {adset_url} 時發生錯誤: {e}")
    return campaign_data

# 4. 爬取每個 adunit 的 click rate
def get_adunit_data(campaign_data):
    for campaign in campaign_data:
        for adset in campaign['adsets']:
            adset['adunits'] = []
            for adunit_url in adset['adunit_urls']:
                try:
                    driver.get(adunit_url)
                    adunit_click_rate_element = WebDriverWait(driver, 20).until(
                        EC.presence_of_element_located((By.XPATH, "//h4[text()='期間點擊率']/following-sibling::div//h2"))
                    )
                    adunit_click_rate = adunit_click_rate_element.text.strip()
                    adset['adunits'].append({
                        'adunit_url': adunit_url,
                        'click_rate': adunit_click_rate
                    })
                    print(f"處理 adunit: {adunit_url}")
                except Exception as e:
                    print(f"處理 adunit {adunit_url} 時發生錯誤: {e}")
    return campaign_data

# 展開數據為扁平結構，整理成 CSV 的部分
def flatten_data(campaign_data):
    flattened_data = []
    for campaign in campaign_data:
        for adset in campaign['adsets']:
            for adunit in adset['adunits']:
                flattened_data.append({
                    'campaign_name': campaign['campaign_name'],
                    'campaign_url': campaign['campaign_url'],
                    'campaign_click_rate': campaign['click_rate'],
                    'adset_url': adset['adset_url'],
                    'adset_click_rate': adset['click_rate'],
                    'adunit_url': adunit['adunit_url'],
                    'adunit_click_rate': adunit['click_rate']
                })
    return flattened_data


# 主程序
def main(start_page, end_page):
    login()
    
    # 1. 獲取指定範圍頁碼的 campaign URLs
    campaign_urls = get_campaign_urls(end_page - start_page + 1)
    
    # 2. 獲取 campaign 數據和 adset URLs
    campaign_data = get_campaign_data(campaign_urls)
    
    # 3. 獲取 adset 數據和 adunit URLs
    campaign_data = get_adset_data(campaign_data)
    
    # 4. 獲取 adunit 數據
    campaign_data = get_adunit_data(campaign_data)
    
    # 展開數據
    flattened_data = flatten_data(campaign_data)
    
    # 存儲數據，文件名稱包含頁碼範圍
    if flattened_data:
        file_name = f'campaign_data_page_{start_page}_to_{end_page}.csv'
        with open(file_name, 'w', newline='', encoding='utf-8') as csvfile:
            fieldnames = ['campaign_url', 'campaign_name', 'campaign_click_rate', 'adset_url', 'adset_click_rate', 'adunit_url', 'adunit_click_rate']
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(flattened_data)
        print(f"數據已存儲到 {file_name} 文件")
    else:
        print("沒有找到任何數據。")
    
    driver.quit()

if __name__ == "__main__":
    # 設定起始頁和結束頁
    start_page = 12  # 起始頁
    end_page = 13  # 結束頁
    main(start_page, end_page)
