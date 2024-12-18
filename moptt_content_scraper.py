"""
MOPTT 文章內容爬蟲
專門用於爬取文章的詳細內容（互動數據、回應等）
"""

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
import json
import time
from datetime import datetime

# ====== 設定區域開始 ======
# Chrome 瀏覽器驅動程式的路徑
chrome_driver_path = '/Users/aotter/chromedriver-mac-arm64/chromedriver'

# 等待時間設定（秒）
WAIT_TIME = 0.5
# ====== 設定區域結束 ======


class MopttContentScraper:
    """
    MOPTT 文章內容爬蟲類別
    負責爬取文章的詳細內容（互動數據、回應等）
    """
    
    def __init__(self):
        """初始化爬蟲設定"""
        self.options = Options()
        self.options.add_argument('--headless')
        self.options.add_argument('--no-sandbox')
        self.options.add_argument('--disable-dev-shm-usage')
        self.driver = webdriver.Chrome(service=Service(chrome_driver_path), options=self.options)
        self.wait = WebDriverWait(self.driver, WAIT_TIME)

    def get_article_content(self, article_info):
        """
        擷取單篇文章的詳細內容
        
        Args:
            article_info: 包含文章基本資訊的字典
            
        Returns:
            dict: 包含文章所有資訊的字典
        """
        try:
            self.driver.get(article_info['url'])
            time.sleep(WAIT_TIME)  # 等待頁面載入

            # 擷取發文時間
            post_time = ""
            try:
                time_element = self.driver.find_element(By.CSS_SELECTOR, "div.o_pqSZvuHj7qfwrPg7tI time")
                if time_element:
                    post_time = time_element.get_attribute('datetime')
            except NoSuchElementException:
                pass

            # 擷取互動數據
            likes = comments = boos = 0
            try:
                interaction_divs = self.driver.find_elements(By.CLASS_NAME, "T86VdSgcSk_wVSJ87Jd_")
                for div in interaction_divs:
                    try:
                        icon = div.find_element(By.TAG_NAME, "i")
                        count_text = div.text.strip()
                        count = int(count_text) if count_text.isdigit() else 0
                        icon_class = icon.get_attribute("class") or ""
                        
                        if "fa-thumbs-up" in icon_class:
                            likes = count
                        elif "fa-thumbs-down" in icon_class:
                            boos = count
                        elif "fa-comment-dots" in icon_class:
                            comments = count
                    except:
                        continue
            except:
                pass

            # 擷取回應內容
            comments_content = []
            try:
                # 嘗試點擊「顯示全部回應」按鈕
                try:
                    show_all_button = self.driver.find_element(By.CSS_SELECTOR, "div.FEfFxCwDtx6IcnHAFaMR")
                    if show_all_button:
                        show_all_button.click()
                        time.sleep(WAIT_TIME)
                except:
                    pass

                # 擷取回應
                comment_spans = self.driver.find_elements(By.CLASS_NAME, "qIm88EMEzWPkVVqwCol0")
                for span in comment_spans:
                    comment_text = span.text.strip()
                    if comment_text:
                        comments_content.append(comment_text)
            except:
                pass

            # 更新文章資訊
            article_info.update({
                'post_time': post_time,
                'likes': likes,
                'responses': comments,
                'boos': boos,
                'responses_content': comments_content,
                'content_fetched': True
            })
            
            return article_info
            
        except Exception as e:
            print(f"\r擷取文章內容時發生錯誤: {str(e)}", end='')
            return article_info

    def process_articles(self, json_file):
        """
        處理 JSON 檔案中的所有文章
        
        Args:
            json_file: JSON 檔案路徑
        """
        try:
            # 讀取文章列表
            with open(json_file, 'r', encoding='utf-8') as f:
                articles = json.load(f)
            
            total_articles = len(articles)
            print(f"\r開始處理 {total_articles} 篇文章的內容", end='')
            
            # 處理每篇文章
            for i, article in enumerate(articles):
                # 檢查是否已經爬取過內容
                if article.get('content_fetched'):
                    continue
                
                print(f"\r處理進度: {i+1}/{total_articles} | 當前: {article['title'][:30]}{'...' if len(article['title']) > 30 else ''}", end='')
                
                # 爬取文章內容
                updated_article = self.get_article_content(article)
                articles[i] = updated_article
                
                # 定期儲存進度
                if (i + 1) % 5 == 0 or i == len(articles) - 1:  # 改為每5篇儲存一次
                    with open(json_file, 'w', encoding='utf-8') as f:
                        json.dump(articles, f, ensure_ascii=False, indent=2)
                    print(f"\r已儲存進度，完成 {i+1}/{total_articles} 篇", end='')
                
                time.sleep(WAIT_TIME)  # 控制爬取間隔
            
            print(f"\r文章內容爬取完成，共處理 {total_articles} 篇文章", end='')
            
        except Exception as e:
            print(f"\r處理文章時發生錯誤: {str(e)}", end='')
        
    def close(self):
        """關閉瀏覽器"""
        self.driver.quit()


if __name__ == "__main__":
    # 設定要處理的看板
    board_names = ["Beauty", "marvel", "NBA"]
    
    for board_name in board_names:
        json_file_path = f'moptt_{board_name}.json'
        
        # 建立爬蟲實例並執行爬蟲
        scraper = MopttContentScraper()
        scraper.process_articles(json_file_path)
        scraper.close()
        print(f"\r{board_name} 看板文章內容處理完成")
