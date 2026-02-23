# src/data_loader/spider.py
import time
import random
import pandas as pd
from selenium.webdriver.common.by import By
import sys
import os

# Import modules từ project
# Thêm đường dẫn project vào sys.path để import được src
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from src.config.crawler import BASE_URL
from src.config.path import RAW_CSV_PATH
from src.data_loader.browser import init_driver

def extract_card_data(card_element):
    """Hàm helper để bóc tách thông tin từ 1 thẻ HTML"""
    data = {}
    try:
        data['title'] = card_element.find_element(By.CSS_SELECTOR, '.js__card-title').text
    except: data['title'] = ""
    
    try: data['price'] = card_element.find_element(By.CSS_SELECTOR, '.re__card-config-price').text
    except: data['price'] = ""
    
    try: data['area'] = card_element.find_element(By.CSS_SELECTOR, '.re__card-config-area').text
    except: data['area'] = ""
    
    try: data['location'] = card_element.find_element(By.CSS_SELECTOR, '.re__card-location').text
    except: data['location'] = ""

    try: data['scraped_date'] = time.strftime("%d/%m/%Y")
    except: data['scraped_date'] = ""
    
    try: data['published_date'] = card_element.find_element(By.CSS_SELECTOR, '.re__card-published-info-published-at').get_attribute('aria-label')
    except: data['published_date'] = ""
    
    try: data['description'] = card_element.find_element(By.CSS_SELECTOR, '.re__card-description').text
    except: data['description'] = ""
    
    try: data['bedrooms'] = card_element.find_element(By.CSS_SELECTOR, '.re__card-config-bedroom').get_attribute('aria-label')
    except: data['bedrooms'] = ""

    try: data['bathrooms'] = card_element.find_element(By.CSS_SELECTOR, '.re__card-config-bathroom').get_attribute('aria-label')
    except: data['bathrooms'] = ""

    return data

def run_crawler(pages=2):
    driver = init_driver()
    results = []
    
    try:
        for p in range(1, pages + 1):
            url = BASE_URL if p == 1 else f"{BASE_URL}/p{p}"
            print(f"[Spider] Đang cào trang {p}/{pages}: {url}")
            
            try:
                driver.get(url)
                time.sleep(random.uniform(5, 8))
                
                cards = driver.find_elements(By.CSS_SELECTOR, '.js__card')
                for card in cards:
                    # Logic bóc tách
                    try:
                        data = extract_card_data(card)
                        #print(f"[Spider] Bóc tách: {data['title']} | {data['price']} | {data['area']} | {data['location']} | {data['published_date']}")
                        if data['title']:  # Chỉ lấy tin có tiêu đề
                            results.append(data)
                    except: continue
                    
            except Exception as e:
                print(f"[Spider] Lỗi tại trang {p}: {e}")
                
    finally:
        try: driver.quit()
        except: pass
        
    return results

def save_data(data):
    if not data:
        print("[Spider] Không có dữ liệu mới.")
        return

    header = not os.path.exists(RAW_CSV_PATH)
    df = pd.DataFrame(data)
    df.to_csv(RAW_CSV_PATH, mode='a', index=False, header=header, encoding='utf-8-sig')
    print(f"[Spider] Đã lưu {len(df)} dòng vào: {RAW_CSV_PATH}")

if __name__ == "__main__":
    # Điểm chạy test
    data = run_crawler(pages=100)
    save_data(data)