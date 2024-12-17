"""
Mobile PTT (MOPTT) 網站爬蟲工具
此程式用於自動化爬取 MOPTT 網站上的文章內容、互動數據及回應
使用 Selenium 進行網頁操作和資料擷取
"""

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
import pandas as pd
import time
from datetime import datetime
import json

# ====== 設定區域開始 ======
# Chrome 瀏覽器驅動程式的路徑
chrome_driver_path = '/Users/aotter/chromedriver-mac-arm64/chromedriver'

# 要滾動的次數
MAX_SCROLLS = 500

# ====== 設定區域結束 ======


class MopttScraper:
    """
    MOPTT 爬蟲類別
    負責初始化瀏覽器設定、爬取文章列表、擷取文章內容及相關資訊
    """
    
    def __init__(self):
        """
        初始化爬蟲設定
        - 設定基礎URL
        - 配置Chrome瀏覽器選項（無頭模式、安全設定）
        - 初始化瀏覽器驅動
        """
        self.base_url = "https://moptt.tw"
        self.options = Options()
        self.options.add_argument('--headless')  # 啟用無頭模式（背景執行）
        self.options.add_argument('--no-sandbox')  # 停用沙箱模式以提高穩定性
        self.options.add_argument('--disable-dev-shm-usage')  # 避免記憶體問題
        self.driver = webdriver.Chrome(service=Service(chrome_driver_path), options=self.options)

    def get_article_links_and_titles(self):
        """
        從當前頁面擷取所有文章的連結和標題
        
        Returns:
            list: 包含文章URL和標題的字典列表
        """
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

    def get_article_data(self, article_info):
        """
        擷取單篇文章的詳細資訊
        
        Args:
            article_info (dict): 包含文章URL和標題的字典
            
        Returns:
            dict: 包含文章所有相關資訊的字典，若擷取失敗則返回None
        """
        try:
            self.driver.get(article_info['url'])

            # 擷取發文時間
            post_time = ""
            try:
                time_element = WebDriverWait(self.driver, 3).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "div.o_pqSZvuHj7qfwrPg7tI time"))
                )
                post_time = time_element.get_attribute('datetime')  # 取得ISO8601格式的時間
            except (TimeoutException, NoSuchElementException):
                return None

            # 擷取文章互動數據（讚數、噓數、回應數）
            likes = comments = boos = 0
            try:
                interaction_divs = self.driver.find_elements(By.CLASS_NAME, "T86VdSgcSk_wVSJ87Jd_")
                for div in interaction_divs:
                    icon = div.find_element(By.TAG_NAME, "i")
                    count_text = div.text.strip()
                    count = int(count_text) if count_text.isdigit() else 0
                    icon_class = icon.get_attribute("class") or ""
                    
                    # 根據圖示類別判斷互動類型
                    if "fa-thumbs-up" in icon_class:
                        likes = count
                    elif "fa-thumbs-down" in icon_class:
                        boos = count
                    elif "fa-comment-dots" in icon_class:
                        comments = count
            except Exception:
                pass

            # 擷取文章回應內容
            comments_content = []
            try:
                # 嘗試點擊「顯示全部回應」按鈕
                try:
                    show_all_button = WebDriverWait(self.driver, 2).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, "div.FEfFxCwDtx6IcnHAFaMR"))
                    )
                    show_all_button.click()
                    # 等待回應載入完成
                    WebDriverWait(self.driver, 2).until(
                        EC.presence_of_element_located((By.CLASS_NAME, "qIm88EMEzWPkVVqwCol0"))
                    )
                except:
                    pass  # 若無「顯示全部」按鈕則略過
                
                # 擷取所有回應內容
                comment_spans = self.driver.find_elements(By.CLASS_NAME, "qIm88EMEzWPkVVqwCol0")
                for span in comment_spans:
                    comment_text = span.text.strip()
                    if comment_text:
                        comments_content.append(comment_text)
            except:
                pass

            # 整理所有擷取到的資訊
            result = {
                'url': article_info['url'],
                'title': article_info['title'],
                'post_time': post_time,
                'likes': likes,
                'responses': comments,
                'boos': boos,
                'responses_content': comments_content
            }
            
            return result
        except Exception as e:
            print(f"擷取文章資料時發生錯誤: {str(e)}")
            return None

    def scrape_board(self, board_url, max_scrolls=500, progress_file=None):
        """
        爬取指定看板的文章
        
        Args:
            board_url (str): 看板URL
            max_scrolls (int): 最大滾動次數
            progress_file (str): 進度檔案路徑，用於儲存爬取進度
            
        Returns:
            list: 包含所有爬取到的文章資料的列表
        """
        print(f"\r開始爬取 {board_url}", end='')
        print(f"\r設定滾動次數: {max_scrolls} 次", end='')
        
        # 載入之前的爬取進度（如果有的話）
        all_data = []
        visited_urls = set()
        last_article_url = None
        found_last_article = False

        if progress_file:
            try:
                with open(progress_file, 'r', encoding='utf-8') as f:
                    all_data = json.load(f)
                    visited_urls = {item.get('url') for item in all_data}
                    # 取得上次爬取的最後一篇文章URL
                    if all_data:
                        last_article_url = all_data[-1].get('url')
                print(f"\r已載入 {len(all_data)} 篇文章的進度", end='')
            except FileNotFoundError:
                print("\r找不到進度檔案，從頭開始爬取", end='')
            except Exception as e:
                print(f"\r載入進度檔案時發生錯誤: {str(e)}", end='')
        
        self.driver.get(board_url)
        
        # 透過滾動載入更多文章
        print("\r=== 開始預載文章 ===", end='')
        last_height = self.driver.execute_script("return document.body.scrollHeight")
        scroll_count = 0
        
        while scroll_count < max_scrolls:
            scroll_count += 1
            print(f"\r預載進度: {scroll_count}/{max_scrolls} | 已載入文章數: {len(all_data)}", end='')
            
            # 滾動頁面
            self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(0.5)  # 等待新內容載入
            
            # 取得目前頁面上的所有文章
            current_articles = self.get_article_links_and_titles()
            
            # 檢查是否找到上次的最後一篇文章
            if last_article_url and not found_last_article:
                for article in current_articles:
                    if article['url'] == last_article_url:
                        found_last_article = True
                        print("\r找到上次爬取的最後一篇文章，將從此處繼續爬取", end='')
                        break
                if not found_last_article:
                    continue  # 如果還沒找到上次的文章，就繼續滾動
            
            # 處理新的文章
            for i, article in enumerate(current_articles):
                if article['url'] not in visited_urls:
                    visited_urls.add(article['url'])
                    # 將基本資訊加入all_data
                    article_basic = {
                        'url': article['url'],
                        'title': article['title'],
                        'article_number': len(all_data) + 1,
                        'preloaded': True  # 標記為預載狀態
                    }
                    all_data.append(article_basic)
                    
                    # 儲存進度
                    if progress_file:
                        try:
                            with open(progress_file, 'w', encoding='utf-8') as f:
                                json.dump(all_data, f, ensure_ascii=False, indent=2)
                            print(f"\r預載文章 {len(all_data)}: {article['title'][:30]}{'...' if len(article['title']) > 30 else ''}", end='')
                        except Exception as e:
                            print(f"\r儲存進度時發生錯誤: {str(e)}", end='')
            
            # 檢查頁面高度是否有變化
            new_height = self.driver.execute_script("return document.body.scrollHeight")
            if new_height == last_height:
                print("\r頁面已到底部，停止滾動", end='')
                break
            last_height = new_height
        
        print("\r完成預載，開始處理文章內容", end='')
        
        # 開始處理已載入的文章
        total_articles = len(all_data)
        
        # 逐一處理文章
        for i, article_info in enumerate(all_data):
            if article_info.get('preloaded', False):  # 只處理標記為預載的文章
                print(f"\r處理進度: {i+1}/{total_articles} | 當前: {article_info['title'][:30]}{'...' if len(article_info['title']) > 30 else ''}", end='')
                
                article_data = self.get_article_data(article_info)
                
                if article_data:
                    # 更新文章資料
                    article_data['article_number'] = article_info['article_number']
                    all_data[i] = article_data
                    
                    # 儲存進度
                    if progress_file:
                        try:
                            with open(progress_file, 'w', encoding='utf-8') as f:
                                json.dump(all_data, f, ensure_ascii=False, indent=2)
                        except Exception as e:
                            print(f"\r儲存進度時發生錯誤: {str(e)}", end='')
        
        print(f"\r爬取完成，共處理 {len(all_data)} 篇文章", end='')
        return all_data

    def close(self):
        """關閉瀏覽器驅動程式"""
        self.driver.quit()


if __name__ == "__main__":
    # 您可以在此設定要爬取的看板名稱清單
    board_names = ["Beauty", "marvel", "NBA"]
    
    # 初始化爬蟲物件
    scraper = MopttScraper()
    
    # 迴圈爬取多個看板
    for board_name in board_names:
        board_url = f"https://moptt.tw/b/{board_name}"
        json_file = f"moptt_{board_name}.json"  # JSON格式輸出檔案
        csv_file = f"moptt_{board_name}.csv"    # CSV格式輸出檔案
        
        try:
            print(f"\r開始爬取看板：{board_name} 並滾動 {MAX_SCROLLS} 次", end='')
            data = scraper.scrape_board(board_url, max_scrolls=MAX_SCROLLS, progress_file=json_file)
            
            if data:
                # 將資料儲存為JSON格式
                with open(json_file, 'w', encoding='utf-8') as f:
                    json.dump(data, f, ensure_ascii=False, indent=2)
                print(f"\r資料已儲存至 {json_file}", end='')
                
                # 將資料轉換為CSV格式並儲存
                df = pd.DataFrame(data)
                df = df.rename(columns={
                    'article_number': '文章序號',
                    'post_time': '發文時間',
                    'responses': '回應數',
                    'responses_content': '回應內容',
                    'likes': '讚數',
                    'boos': '噓數'
                })
                
                df.to_csv(csv_file, encoding='utf-8-sig', index=False)
                print(f"\r資料已轉換並儲存至 {csv_file}", end='')
            else:
                print("\r未找到文章", end='')
            
        except Exception as e:
            print(f"\r執行過程中發生錯誤: {str(e)}", end='')
    
    # 爬取結束後關閉瀏覽器
    scraper.close()
    print("\r瀏覽器已關閉，程式結束", end='')
    print()  # 最後加入一個換行
