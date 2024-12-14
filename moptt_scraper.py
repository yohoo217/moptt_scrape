from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
import pandas as pd
import time
import random
from datetime import datetime

class MopttScraper:
    def __init__(self):
        self.base_url = "https://moptt.tw"
        self.options = webdriver.ChromeOptions()
        self.options.add_argument('--headless=new')
        self.options.add_argument('--no-sandbox')
        self.options.add_argument('--disable-dev-shm-usage')
        self.options.add_argument('--disable-gpu')
        self.options.add_argument("--window-size=1920,1080")
        self.driver = webdriver.Chrome(options=self.options)
        
    def get_article_links_and_titles(self, board_url, num_articles=5):
        try:
            self.driver.get(board_url)
            time.sleep(3)  # Wait for JavaScript to load
            
            # Find all article containers
            articles = self.driver.find_elements(By.CSS_SELECTOR, "div[class*='eQQBIg']")
            article_data = []
            
            for article in articles[:num_articles]:
                try:
                    # Find the link and title within the article container
                    link = article.find_element(By.CSS_SELECTOR, "a[href*='/p/']")
                    title = article.find_element(By.CSS_SELECTOR, "h3").text
                    article_data.append({
                        'url': link.get_attribute('href'),
                        'title': title
                    })
                except NoSuchElementException:
                    continue
            
            return article_data
        except Exception as e:
            print(f"Error getting article links: {str(e)}")
            return []

    def get_article_data(self, article):
        try:
            # 初始化變數
            post_time = ""
            likes = 0
            responses = []
            boos = 0
            
            # 訪問文章頁面
            self.driver.get(article['url'])
            time.sleep(2)
            
            try:
                # 取得發文時間
                time_element = self.driver.find_element(By.CSS_SELECTOR, "time")
                post_time = time_element.get_attribute('datetime')
            except NoSuchElementException:
                print(f"無法找到發文時間: {article['title']}")
            
            try:
                # 取得互動數
                interaction_elements = self.driver.find_elements(By.CSS_SELECTOR, "div.o_pqSZvuHj7qfwrPg7tI")
                for element in interaction_elements:
                    text = element.text.strip()
                    if '讚' in text:
                        likes = int(text.replace('讚', '').strip())
                    elif '噓' in text:
                        boos = int(text.replace('噓', '').strip())
            except Exception as e:
                print(f"取得互動數時發生錯誤: {str(e)}")
            
            try:
                # 點擊顯示全部回應按鈕
                show_all_button = self.driver.find_element(By.XPATH, "//button[contains(text(), '顯示全部回應')]")
                show_all_button.click()
                time.sleep(2)
            except NoSuchElementException:
                print("沒有找到顯示全部回應按鈕")
            except Exception as e:
                print(f"點擊顯示全部回應按鈕時發生錯誤: {str(e)}")
            
            try:
                # 取得回應內容
                response_elements = self.driver.find_elements(By.CSS_SELECTOR, "div.o_2OLTDP8GEkfxplQE7tN")
                for element in response_elements:
                    responses.append(element.text.strip())
            except Exception as e:
                print(f"取得回應內容時發生錯誤: {str(e)}")
            
            # 回傳結果
            return {
                'title': article['title'],
                'url': article['url'],
                'post_time': post_time,
                'likes': likes,
                'responses': len(responses),
                'responses_content': responses,
                'boos': boos
            }
            
        except Exception as e:
            print(f"處理文章時發生錯誤: {str(e)}")
            return None

    def scrape_and_save(self, board_url, output_file):
        try:
            # 獲取文章連結和標題
            articles_info = self.get_article_links_and_titles(board_url)
            print(f"Found {len(articles_info)} articles")
            
            if not articles_info:
                print("No articles found!")
                return pd.DataFrame()
            
            # 爬取每篇文章的資料
            all_data = []
            for i, article_info in enumerate(articles_info, 1):
                print(f"\nScraping article {i}/{len(articles_info)}: {article_info['title']}")
                article_data = self.get_article_data(article_info)
                if article_data is not None:
                    all_data.append(article_data)
                time.sleep(2)  # 避免請求過快
            
            # 將資料轉換為扁平結構
            flat_data = []
            for article in all_data:
                if not article['responses_content']:  
                    flat_data.append({
                        'url': article['url'],
                        'title': article['title'],
                        'post_time': article['post_time'],
                        'likes': article['likes'],
                        'responses': article['responses'],  
                        'boos': article['boos'],
                        'response_content': ''
                    })
                else:
                    for comment in article['responses_content']:
                        flat_data.append({
                            'url': article['url'],
                            'title': article['title'],
                            'post_time': article['post_time'],
                            'likes': article['likes'],
                            'responses': article['responses'],  
                            'boos': article['boos'],
                            'response_content': comment
                        })
            
            # 儲存為 CSV
            df = pd.DataFrame(flat_data)
            if not df.empty:
                df.to_csv(output_file, index=False, encoding='utf-8-sig')
                print(f"\n成功爬取 {len(articles_info)} 篇文章的資料")
            return df
        except Exception as e:
            print(f"Error during scraping: {str(e)}")
            return pd.DataFrame()
        finally:
            self.driver.quit()

if __name__ == "__main__":
    scraper = MopttScraper()
    board_url = "https://moptt.tw/b/movie"
    output_file = "moptt_movie_data.csv"
    
    try:
        print(f"\n開始爬取看板: {board_url}")
        articles = scraper.get_article_links_and_titles(board_url, num_articles=4)
        print(f"找到 {len(articles)} 篇文章\n")
        
        all_data = []
        for i, article in enumerate(articles, 1):
            print(f"\n正在處理第 {i}/{len(articles)} 篇文章: {article['title']}")
            article_data = scraper.get_article_data(article)
            if article_data:
                all_data.append(article_data)
            time.sleep(random.uniform(2, 4))  # 避免太快爬取
        
        # 將資料轉換為DataFrame
        df = pd.DataFrame(all_data)
        
        # 重新命名欄位
        df = df.rename(columns={
            'post_time': '發文時間',
            'responses': '回應數',
            'responses_content': '回應內容',
            'likes': '讚數',
            'boos': '噓數'
        })
        
        # 儲存資料
        df.to_csv(output_file, encoding='utf-8-sig', index=False)
        print(f"\n成功爬取 {len(df)} 篇文章的資料")
        print(f"資料已儲存至 {output_file}")
        
        # 顯示資料預覽
        print("\n資料預覽:")
        print(df.head())
        
    except Exception as e:
        print(f"執行過程中發生錯誤: {str(e)}")
    
    finally:
        scraper.driver.quit()
        print("\n瀏覽器已關閉")
