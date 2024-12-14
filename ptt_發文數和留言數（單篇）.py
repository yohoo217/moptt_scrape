import csv
import random
import time
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# 設置和初始化 Selenium
chrome_driver_path = '/Users/aotter/chromedriver-mac-arm64/chromedriver'
chrome_options = Options()
# chrome_options.add_argument('--headless')
chrome_options.add_argument('--no-sandbox')
chrome_options.add_argument('--disable-dev-shm-usage')
chrome_options.add_argument('--ignore-certificate-errors')  # 忽略 SSL 錯誤
chrome_options.add_argument('--ignore-ssl-errors')  # 忽略 SSL 錯誤
chrome_options.add_argument('user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36')
service = Service(chrome_driver_path)
driver = webdriver.Chrome(service=service, options=chrome_options)

def get_ptt_data(start_url):
    driver.get(start_url)
    
    # 檢查是否有滿 18 歲的確認頁面
    try:
        agree_button = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.XPATH, "//button[contains(text(), '我同意')]"))
        )
        agree_button.click()
        print("已點擊 '我同意' 進入看板")
    except Exception as e:
        print("沒有滿 18 歲的確認頁面，或已成功跳過。")
    
    post_data = []
    cutoff_date = datetime.strptime("09/07", "%m/%d")
    post_number = 1  # 貼文編號從1開始

    while True:
        try:
            # 等待頁面加載完成，找到所有 <div class="r-ent">
            r_ent_elements = WebDriverWait(driver, 20).until(
                EC.presence_of_all_elements_located((By.CSS_SELECTOR, "div.r-ent"))
            )
            
            print(f"找到 {len(r_ent_elements)} 個 r-ent 元素")
            
            # 遍歷每個 r-ent 元素
            all_posts_before_cutoff = True
            for r_ent in r_ent_elements:
                # 提取 nrec 的內容
                try:
                    nrec = r_ent.find_element(By.CSS_SELECTOR, "div.nrec span").text
                except Exception:
                    nrec = '0'  # 沒有數字時默認為 0
                
                # 提取 title 和作者
                try:
                    title_element = r_ent.find_element(By.CSS_SELECTOR, "div.title a")
                    title = title_element.text
                    link = title_element.get_attribute('href')
                except Exception as e:
                    print(f"無法找到標題或鏈接，跳過此文章：{e}")
                    continue

                author = r_ent.find_element(By.CSS_SELECTOR, "div.meta div.author").text

                # 提取發文日期
                try:
                    date_element = r_ent.find_element(By.CSS_SELECTOR, "div.meta div.date").text.strip()
                    post_date = datetime.strptime(date_element, "%m/%d")
                except Exception as e:
                    print(f"無法提取發文日期，跳過此文章：{e}")
                    continue
                
                # 如果發文日期在 9/7 之前，跳過並記錄標記
                if post_date < cutoff_date:
                    print(f"跳過文章，因為發文日期為 {date_element}")
                    continue

                all_posts_before_cutoff = False
                
                # 將數據加入列表，並加上編號
                post_data.append({
                    'number': post_number,
                    'title': title,
                    'link': f'https://www.ptt.cc{link}',  # 確保完整 URL
                    'author': author,
                    'date': date_element,
                    'nrec': nrec
                })
                post_number += 1
                print(f"處理文章: {title}, 發文日期: {date_element}, 編號: {post_number - 1}")
            
            # 如果該頁的所有文章都是 9/7 以前，停止爬取
            if all_posts_before_cutoff:
                print("所有文章發文時間都小於 9/7，停止爬取。")
                break

            # 查找「上頁」按鈕並跳轉到上一頁
            try:
                previous_page_element = driver.find_element(By.CSS_SELECTOR, "div.btn-group-paging a:nth-child(2)")
                previous_page_url = previous_page_element.get_attribute('href')
                # 確保只有相對 URL 時才拼接
                if not previous_page_url.startswith("http"):
                    previous_page_url = f'https://www.ptt.cc{previous_page_url}'
                
                print(f"前往上一頁: {previous_page_url}")
                
                # 隨機等待時間，模擬人類行為
                time.sleep(random.uniform(1, 3))
                
                driver.get(previous_page_url)
            except Exception as e:
                print(f"無法找到上頁按鈕，停止爬取: {e}")
                break

        except Exception as e:
            print(f"抓取時發生錯誤: {e}")
            break
    
    # 儲存數據為 CSV 檔案
    if post_data:
        file_name = 'ptt_C_Chat_posts_after_0907.csv'
        with open(file_name, 'w', newline='', encoding='utf-8') as csvfile:
            fieldnames = ['number', 'title', 'link', 'author', 'date', 'nrec']
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(post_data)
        print(f"數據已儲存到 {file_name} 文件")
    else:
        print("沒有找到符合條件的數據。")

    driver.quit()

if __name__ == "__main__":
    # 從第一頁開始爬取
    start_url = 'https://www.ptt.cc/bbs/C_Chat/index.html'
    get_ptt_data(start_url)
