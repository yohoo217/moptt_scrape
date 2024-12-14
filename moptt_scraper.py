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

    def get_article_data(self, article_info):
        try:
            self.driver.get(article_info['url'])
            time.sleep(3)  # Wait for JavaScript to load
            
            # 等待互動容器載入
            try:
                WebDriverWait(self.driver, 10).until(
                    EC.presence_of_element_located((By.CLASS_NAME, "Zkj8rDosKwearzV1YjeL"))
                )
                
                # 取得發文時間
                try:
                    time_element = WebDriverWait(self.driver, 10).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, "div.o_pqSZvuHj7qfwrPg7tI time"))
                    )
                    post_time = time_element.get_attribute('datetime')
                except (TimeoutException, NoSuchElementException) as e:
                    print(f"無法取得發文時間: {str(e)}")
                    post_time = ""
                
                # 取得讚數、噓數和回應數
                likes = comments = boos = 0
                interaction_divs = self.driver.find_elements(By.CLASS_NAME, "T86VdSgcSk_wVSJ87Jd_")
                
                for div in interaction_divs:
                    icon = div.find_element(By.TAG_NAME, "i")
                    count = int(div.text.strip())
                    icon_class = icon.get_attribute("class") or ""
                    
                    if "fa-thumbs-up" in icon_class:
                        likes = count
                    elif "fa-thumbs-down" in icon_class:
                        boos = count
                    elif "fa-comment-dots" in icon_class:
                        comments = count
                
            except (TimeoutException, NoSuchElementException) as e:
                print(f"Error getting interaction counts: {str(e)}")
            
            # 取得回應內容
            comments_content = []
            try:
                # 尋找並點擊「顯示全部回應」按鈕
                try:
                    show_all_button = WebDriverWait(self.driver, 10).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, "div.FEfFxCwDtx6IcnHAFaMR"))
                    )
                    show_all_button.click()
                    time.sleep(2)  # 等待回應載入
                except (TimeoutException, NoSuchElementException) as e:
                    print(f"找不到「顯示全部回應」按鈕或點擊失敗: {str(e)}")
                
                # 等待回應載入
                WebDriverWait(self.driver, 10).until(
                    EC.presence_of_element_located((By.CLASS_NAME, "qIm88EMEzWPkVVqwCol0"))
                )
                
                # 找出所有回應
                comment_spans = self.driver.find_elements(By.CLASS_NAME, "qIm88EMEzWPkVVqwCol0")
                for span in comment_spans:
                    comment_text = span.text.strip()
                    if comment_text:
                        comments_content.append(comment_text)
                        
            except TimeoutException:
                print("等待回應載入超時")
            
            result = {
                'url': article_info['url'],
                'title': article_info['title'],
                'post_time': post_time,  # 加入發文時間
                'likes': likes,
                'responses': comments,
                'boos': boos,
                'responses_content': comments_content
            }
            
            print(f"成功擷取文章資料: {result}")
            return result
            
        except Exception as e:
            print(f"擷取文章資料時發生錯誤: {str(e)}")
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
