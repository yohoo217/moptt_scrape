from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException, WebDriverException
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service as ChromeService
from webdriver_manager.chrome import ChromeDriverManager
import pandas as pd
import time
from datetime import datetime
import json
import random
import os

def check_month(post_time_str):
    # 假設 post_time 為 ISO8601 格式字串，例如: "2024-01-15T12:34:56Z"
    # 根據需求，解析時間以取得 year、month。
    # 這裡僅示範，請依實務調整解析邏輯。
    # 回傳 (year, month) 的 tuple
    try:
        dt = datetime.fromisoformat(post_time_str.replace('Z','+00:00'))  # 若有Z為UTC標記
        return (dt.year, dt.month)
    except:
        return (None, None)


class MopttScraper:
    def __init__(self):
        self.base_url = "https://moptt.tw"
        self.init_driver()
        self.progress_file = 'scraping_progress.json'
        self.all_data = []
        self.load_progress()

    def load_progress(self):
        try:
            if os.path.exists(self.progress_file):
                with open(self.progress_file, 'r', encoding='utf-8') as f:
                    progress = json.load(f)
                    self.all_data = progress.get('data', [])
        except Exception as e:
            print(f"讀取進度檔案時發生錯誤: {str(e)}")
            self.all_data = []

    def save_progress(self, new_article):
        try:
            self.all_data.append(new_article)
            progress = {
                'data': self.all_data,
                'last_index': len(self.all_data),
                'timestamp': datetime.now().isoformat()
            }
            with open(self.progress_file, 'w', encoding='utf-8') as f:
                json.dump(progress, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"儲存進度時發生錯誤: {str(e)}")

    def init_driver(self):
        self.options = Options()
        self.options.add_argument('--headless')
        self.options.add_argument('--no-sandbox')
        self.options.add_argument('--disable-dev-shm-usage')
        self.options.add_argument('--disable-gpu')
        self.options.add_argument('--window-size=1920,1080')
        try:
            self.driver = webdriver.Chrome(service=ChromeService(ChromeDriverManager().install()), options=self.options)
            self.driver.set_page_load_timeout(30)
        except Exception as e:
            print(f"初始化瀏覽器時發生錯誤: {str(e)}")
            raise

    def restart_driver(self):
        try:
            self.driver.quit()
        except:
            pass
        time.sleep(5)  # 等待一下確保完全關閉
        self.init_driver()

    def get_with_retry(self, url, max_retries=3):
        for attempt in range(max_retries):
            try:
                self.driver.get(url)
                return True
            except WebDriverException as e:
                print(f"瀏覽器連線錯誤 (嘗試 {attempt + 1}/{max_retries}): {str(e)}")
                if attempt < max_retries - 1:
                    self.restart_driver()
                    time.sleep(5)
                else:
                    raise

    def get_article_links_and_titles(self):
        try:
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
        except WebDriverException:
            self.restart_driver()
            return []

    def get_article_data(self, article_info):
        try:
            self.get_with_retry(article_info['url'])
            
            # 取得發文時間
            post_time = ""
            try:
                time_element = WebDriverWait(self.driver, 5).until(
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

    def scrape_target_month(self, board_url, min_count=30):
        print(f"\n開始爬取 {board_url}")
        print(f"目標: 爬取至少 {min_count} 篇文章")
        
        visited_urls = set()
        consecutive_errors = 0
        max_consecutive_errors = 10
        article_number = len(self.all_data) + 1  # 從目前進度繼續編號

        try:
            self.get_with_retry(board_url)
            
            while True:  # 改為無限循環，直到達到目標文章數
                # 若已達成目標，則中斷
                if len(self.all_data) >= min_count:
                    break

                try:
                    # 取得文章連結和標題
                    new_articles = self.get_article_links_and_titles()
                    
                    if not new_articles:
                        consecutive_errors += 1
                        if consecutive_errors >= max_consecutive_errors:
                            print("連續多次無法取得文章，中止爬取")
                            break
                        continue
                    
                    consecutive_errors = 0  # 重設錯誤計數
                    
                    # 過濾已訪問的網址
                    new_articles = [a for a in new_articles if a['url'] not in visited_urls]
                    
                    for article in new_articles:
                        visited_urls.add(article['url'])
                        
                        # 最小延遲，避免被封鎖
                        time.sleep(0.5)
                        
                        article_data = self.get_article_data(article)
                        if article_data:
                            # 加入文章編號
                            article_data['article_number'] = article_number
                            article_number += 1
                            
                            # 立即儲存此篇文章
                            self.save_progress(article_data)
                            print(f"\r目前已爬取 {len(self.all_data)} 篇文章", end='', flush=True)
                            
                            if len(self.all_data) >= min_count:
                                break
                    
                    # 滾動頁面
                    if len(self.all_data) < min_count:
                        self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                        time.sleep(1)  # 等待頁面載入的最小時間
                        
                except WebDriverException as e:
                    print(f"\n瀏覽器錯誤，嘗試重新啟動: {str(e)}")
                    self.restart_driver()
                    self.get_with_retry(board_url)
                    time.sleep(2)  # 減少重啟後等待時間
                    continue
                    
        except Exception as e:
            print(f"\n爬取過程發生錯誤: {str(e)}")
        
        print(f"\n=== 爬取完成 ===")
        print(f"共爬取 {len(self.all_data)} 篇文章")

        return self.all_data

    def close(self):
        self.driver.quit()


if __name__ == "__main__":
    scraper = MopttScraper()
    board_url = "https://moptt.tw/b/Boy-Girl"
    min_count = 40  # 預設爬取30篇文章
    
    try:
        csv_file = 'moptt_Gossiping.csv'
        
        print(f"\n開始爬取 {board_url} 中至少 {min_count} 篇文章...")
        all_data = scraper.scrape_target_month(board_url, min_count=min_count)
        
        if len(all_data) > 0:
            # 轉換成 CSV
            df = pd.DataFrame(all_data)
            df = df.rename(columns={
                'article_number': '文章編號',
                'post_time': '發文時間',
                'responses': '回應數',
                'responses_content': '回應內容',
                'likes': '讚數',
                'boos': '噓數'
            })
            
            # 調整欄位順序，將文章編號放在最前面
            columns = ['文章編號'] + [col for col in df.columns if col != '文章編號']
            df = df[columns]
            
            df.to_csv(csv_file, encoding='utf-8-sig', index=False)
            print(f"資料已轉換並儲存至 {csv_file}")
            print(df.head())
        else:
            print("未找到任何文章。")
                
    except Exception as e:
        print(f"執行過程中發生錯誤: {str(e)}")
    finally:
        scraper.close()
        print("瀏覽器已關閉")
