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

chrome_driver_path = '/Users/aotter/chromedriver-mac-arm64/chromedriver'

class MopttScraper:
    def __init__(self):
        self.base_url = "https://moptt.tw"
        self.options = Options()
        self.options.add_argument('--headless')
        self.options.add_argument('--no-sandbox')
        self.options.add_argument('--disable-dev-shm-usage')
        self.driver = webdriver.Chrome(service=Service(chrome_driver_path), options=self.options)

    def get_article_links_and_titles(self):
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
        try:
            self.driver.get(article_info['url'])

            # 取得發文時間
            post_time = ""
            try:
                time_element = WebDriverWait(self.driver, 3).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "div.o_pqSZvuHj7qfwrPg7tI time"))
                )
                post_time = time_element.get_attribute('datetime')  # ISO8601格式
            except (TimeoutException, NoSuchElementException):
                return None

            # 取得讚數、噓數、回應數
            likes = comments = boos = 0
            try:
                interaction_divs = self.driver.find_elements(By.CLASS_NAME, "T86VdSgcSk_wVSJ87Jd_")
                for div in interaction_divs:
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
            except Exception:
                pass

            # 顯示全部回應並取得回應內容
            comments_content = []
            try:
                # 點擊顯示全部回應 (若有的話)
                try:
                    show_all_button = WebDriverWait(self.driver, 2).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, "div.FEfFxCwDtx6IcnHAFaMR"))
                    )
                    show_all_button.click()
                    # 等待回應載入
                    WebDriverWait(self.driver, 2).until(
                        EC.presence_of_element_located((By.CLASS_NAME, "qIm88EMEzWPkVVqwCol0"))
                    )
                except:
                    # 沒有顯示全部回應按鈕就直接略過
                    pass
                
                comment_spans = self.driver.find_elements(By.CLASS_NAME, "qIm88EMEzWPkVVqwCol0")
                for span in comment_spans:
                    comment_text = span.text.strip()
                    if comment_text:
                        comments_content.append(comment_text)
            except:
                pass

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

    def scrape_board(self, board_url, min_count=30000, max_scrolls=1500, progress_file=None):
        print(f"\n開始爬取 {board_url}")
        print(f"目標: 至少{min_count}篇文章")
        
        # 載入進度檔案
        all_data = []
        visited_urls = set()
        if progress_file:
            try:
                with open(progress_file, 'r', encoding='utf-8') as f:
                    all_data = json.load(f)
                    visited_urls = {item['url'] for item in all_data}
                print(f"已載入 {len(all_data)} 篇文章的進度")
            except FileNotFoundError:
                print("找不到進度檔案，從頭開始爬取")
            except Exception as e:
                print(f"載入進度檔案時發生錯誤: {str(e)}")
        
        self.driver.get(board_url)
        
        # 先進行多次滾動載入更多文章
        print("\n=== 開始預載文章 ===")
        last_height = self.driver.execute_script("return document.body.scrollHeight")
        
        # 先滾動指定次數，載入更多文章
        for scroll_count in range(1, max_scrolls + 1):
            print(f"\r預載進度: {scroll_count}/{max_scrolls}", end='')
            self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(0.5)  # 等待頁面載入
            
            # 強制執行所有滾動次數，不檢查是否到達底部
            if scroll_count % 10 == 0:  # 每10次滾動重新整理一次頁面高度
                new_height = self.driver.execute_script("return document.body.scrollHeight")
                if new_height > last_height:  # 只在頁面確實變高時更新高度
                    last_height = new_height
        
        print("\n完成預載")
        
        print("\n=== 開始處理文章 ===")
        # 取得所有已載入的文章
        articles = self.get_article_links_and_titles()
        total_articles = len(articles)
        print(f"總共載入 {total_articles} 篇文章")
        
        # 處理所有已載入的文章
        for i, article_info in enumerate(articles, 1):
            url = article_info['url']
            if url in visited_urls:
                continue
            
            # 使用 \r 來更新同一行
            print(f"\r進度: {i}/{total_articles} 篇 | 已成功爬取: {len(all_data)} 篇 | 當前文章: {article_info['title'][:30]}{'...' if len(article_info['title']) > 30 else ''}", end='')
            
            visited_urls.add(url)
            article_data = self.get_article_data(article_info)
            
            if article_data:
                # 加入文章序號
                article_data['article_number'] = len(all_data) + 1
                all_data.append(article_data)
                
                # 儲存進度
                if progress_file:
                    try:
                        with open(progress_file, 'w', encoding='utf-8') as f:
                            json.dump(all_data, f, ensure_ascii=False, indent=2)
                    except Exception as e:
                        print(f"\n儲存進度時發生錯誤: {str(e)}")
                
                # 如果已經達到目標數量，就提前結束
                if len(all_data) >= min_count:
                    print(f"\n已達到目標數量 {min_count} 篇！")
                    break
        
        print(f"\n=== 爬取完成 ===")
        print(f"共爬取 {len(all_data)} 篇文章")
        
        return all_data

    def close(self):
        self.driver.quit()


if __name__ == "__main__":
    scraper = MopttScraper()
    board_url = "https://moptt.tw/b/Gossiping"
    json_file = "moptt_Gossiping.json"
    csv_file = "moptt_Gossiping.csv"
    
    try:
        print(f"開始爬取 {board_url} 中至少 30000 篇文章...")
        data = scraper.scrape_board(board_url, min_count=30000, max_scrolls=1500, progress_file=json_file)
        
        if data:
            # 儲存為 JSON 格式 (最終版本)
            with open(json_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            print(f"資料已儲存至 {json_file}")
            
            # 轉換為 CSV 格式
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
            print(f"資料已轉換並儲存至 {csv_file}")
            print(df.head())
        else:
            print("未找到足夠文章。")
        
    except Exception as e:
        print(f"執行過程中發生錯誤: {str(e)}")
    finally:
        scraper.close()
        print("瀏覽器已關閉")
