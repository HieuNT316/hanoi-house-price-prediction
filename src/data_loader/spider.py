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

# Ép Python xuất dữ liệu text ra terminal hoặc file log bằng chuẩn UTF-8
sys.stdout.reconfigure(encoding='utf-8')

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

def run_crawler(pages=2, max_retries=3):
    """
    Hàm cào dữ liệu có tích hợp cơ chế Auto-Retry để vượt qua Cloudflare.
    - max_retries: Số lần thử tải lại trang tối đa nếu bị chặn.
    """
    driver = init_driver()
    results = []
    
    try:
        for p in range(1, pages + 1):
            url = BASE_URL if p == 1 else f"{BASE_URL}/p{p}"
            print(f"\n[Spider] Đang cào trang {p}/{pages}: {url}")
            
            for attempt in range(1, max_retries + 1):
                try:
                    if attempt == 1:
                        driver.get(url)
                    else:
                        print(f"[Spider] 🔄 Đang thử tải lại lần {attempt}/{max_retries} cho trang {p}...")
                        driver.refresh() # Tải lại trang sau khi Cloudflare cấp cookie
                    
                    # Chờ trang load hoàn toàn hoặc chờ Cloudflare duyệt JS
                    time.sleep(random.uniform(7, 10))
                    
                    cards = driver.find_elements(By.CSS_SELECTOR, '.js__card')
                    
                    if len(cards) > 0:
                        print(f"[Spider] ✅ Thành công: Tìm thấy {len(cards)} tin đăng ở trang {p}.")
                        for card in cards:
                            try:
                                data = extract_card_data(card)
                                if data['title']:  
                                    results.append(data)
                            except Exception: 
                                continue
                        break # Thoát vòng lặp retry vì đã lấy được dữ liệu thành công
                        
                    else:
                        print(f"[Spider] ⚠️ Không tìm thấy dữ liệu (Attempt {attempt}). Có thể đang bị Cloudflare chặn.")
                        
                        # Nếu đã thử hết số lần mà vẫn thất bại mới chụp ảnh debug
                        if attempt == max_retries:
                            debug_path = os.path.join(os.path.dirname(__file__), f"debug_page_{p}.png")
                            driver.save_screenshot(debug_path)
                            print(f"[Spider] 📸 Đã lưu ảnh màn hình lỗi cuối cùng tại: {debug_path}")
                        else:
                            # Nghỉ ngơi thêm 5 giây trước khi refresh để chắc chắn Cloudflare đã duyệt xong
                            time.sleep(5)
                            
                except Exception as e:
                    print(f"[Spider] Lỗi tại trang {p} (Attempt {attempt}): {e}")
                    if attempt == max_retries:
                        break
                    time.sleep(3) # Chờ 1 chút rồi thử lại
                    
    finally:
        try: 
            driver.quit()
        except Exception: 
            pass
        
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
    data = run_crawler(pages=10)
    save_data(data)