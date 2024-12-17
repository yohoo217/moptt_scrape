"""
MOPTT 文章列表爬蟲
專門用於爬取文章的基本資訊（編號、標題、URL）
"""

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.common.exceptions import NoSuchElementException
import json
import time

# ====== 設定區域開始 ======
# Chrome 瀏覽器驅動程式的路徑
chrome_driver_path = '/Users/aotter/chromedriver-mac-arm64/chromedriver'

# 要滾動的次數
MAX_SCROLLS = 5
# ====== 設定區域結束 ======


class MopttListScraper:
    """
    MOPTT 文章列表爬蟲類別
    負責爬取文章的基本資訊（編號、標題、URL）
    """
    
    def __init__(self):
        """初始化爬蟲設定"""
        self.base_url = "https://moptt.tw"
        self.options = Options()
        self.options.add_argument('--headless')
        self.options.add_argument('--no-sandbox')
        self.options.add_argument('--disable-dev-shm-usage')
        self.driver = webdriver.Chrome(service=Service(chrome_driver_path), options=self.options)

    def get_article_links_and_titles(self):
        """擷取當前頁面的所有文章連結和標題"""
        articles = self.driver.find_elements(By.CSS_SELECTOR, "div[class*='eQQBIg']")
        article_data = []
        for article in articles:
            try:
                link = article.find_element(By.CSS_SELECTOR, "a[href*='/p/']")
                title = article.find_element(By.CSS_SELECTOR, "h3").text
                article_data.append({
                    'url': link.get_attribute('href'),
                    'title': title
                })
            except NoSuchElementException:
                continue
        return article_data

    def scrape_board(self, board_url, max_scrolls=500, progress_file=None):
        """爬取指定看板的文章列表"""
        print(f"\r開始爬取看板列表：{board_url}", end='')
        
        # 載入進度檔案
        all_data = []
        visited_urls = set()
        last_article_url = None
        found_last_article = False

        if progress_file:
            try:
                with open(progress_file, 'r', encoding='utf-8') as f:
                    all_data = json.load(f)
                    visited_urls = {item.get('url') for item in all_data}
                    if all_data:
                        last_article_url = all_data[-1].get('url')
                print(f"\r已載入 {len(all_data)} 篇文章的進度", end='')
            except FileNotFoundError:
                print("\r找不到進度檔案，從頭開始爬取", end='')
            except Exception as e:
                print(f"\r載入進度檔案時發生錯誤: {str(e)}", end='')
        
        self.driver.get(board_url)
        
        # 滾動載入文章
        print("\r開始滾動載入文章", end='')
        last_height = self.driver.execute_script("return document.body.scrollHeight")
        scroll_count = 0
        
        while scroll_count < max_scrolls:
            scroll_count += 1
            print(f"\r滾動進度: {scroll_count}/{max_scrolls} | 已載入文章數: {len(all_data)}", end='')
            
            self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(0.5)
            
            current_articles = self.get_article_links_and_titles()
            
            # 檢查是否找到上次的最後一篇文章
            if last_article_url and not found_last_article:
                for article in current_articles:
                    if article['url'] == last_article_url:
                        found_last_article = True
                        print("\r找到上次爬取的最後一篇文章，將從此處繼續爬取", end='')
                        break
                if not found_last_article:
                    continue
            
            # 處理新文章
            for article in current_articles:
                if article['url'] not in visited_urls:
                    visited_urls.add(article['url'])
                    article_data = {
                        'url': article['url'],
                        'title': article['title'],
                        'article_number': len(all_data) + 1
                    }
                    all_data.append(article_data)
                    
                    # 儲存進度
                    if progress_file:
                        try:
                            with open(progress_file, 'w', encoding='utf-8') as f:
                                json.dump(all_data, f, ensure_ascii=False, indent=2)
                            print(f"\r已儲存文章 {len(all_data)}: {article['title'][:30]}{'...' if len(article['title']) > 30 else ''}", end='')
                        except Exception as e:
                            print(f"\r儲存進度時發生錯誤: {str(e)}", end='')
            
            # 檢查是否到達頁面底部
            new_height = self.driver.execute_script("return document.body.scrollHeight")
            if new_height == last_height:
                print("\r已到達頁面底部", end='')
                break
            last_height = new_height
        
        print(f"\r完成爬取，共 {len(all_data)} 篇文章", end='')
        return all_data

    def close(self):
        """關閉瀏覽器"""
        self.driver.quit()


if __name__ == "__main__":
    # 設定要爬取的看板
    board_names = ["Beauty", "marvel", "NBA"]
    
    scraper = MopttListScraper()
    
    for board_name in board_names:
        board_url = f"https://moptt.tw/b/{board_name}"
        json_file = f"moptt_{board_name}.json"
        
        try:
            print(f"\r開始爬取 {board_name} 看板，設定滾動 {MAX_SCROLLS} 次", end='')
            data = scraper.scrape_board(board_url, max_scrolls=MAX_SCROLLS, progress_file=json_file)
            
            if data:
                with open(json_file, 'w', encoding='utf-8') as f:
                    json.dump(data, f, ensure_ascii=False, indent=2)
                print(f"\r{board_name} 看板資料已儲存至 {json_file}", end='')
            else:
                print(f"\r{board_name} 看板未找到文章", end='')
            
        except Exception as e:
            print(f"\r爬取 {board_name} 看板時發生錯誤: {str(e)}", end='')
    
    scraper.close()
    print("\r爬蟲程式執行完成", end='')
    print()  # 最後換行
