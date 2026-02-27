# src/data_loader/detail_spider.py
import time
import random
import os
import sys
from selenium.webdriver.common.by import By

# Import modules từ project
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from src.data_loader.browser import init_driver
from src.database.postgres_manager import PostgresManager # Import DB Manager

# Ép chuẩn UTF-8
sys.stdout.reconfigure(encoding='utf-8')

KEY_MAPPING = {
    'mặt tiền': 'frontage',
    'đường vào': 'road_width',
    'hướng nhà': 'direction',
    'số tầng': 'floors',
    'pháp lý': 'legal_status',
    'nội thất': 'furniture'
}

def extract_specifications(driver):
    """
    Thuật toán nội suy Key-Value từ trang chi tiết.
    """
    specs = {col: None for col in KEY_MAPPING.values()}
    
    try:
        spec_items = driver.find_elements(By.XPATH, "//*[contains(@class, 'specs-content-item') or contains(@class, 'pr-specs-item')]")
        
        for item in spec_items:
            text_lines = item.text.strip().split('\n')
            
            if len(text_lines) < 2:
                try:
                    title = item.find_element(By.XPATH, ".//*[contains(@class, 'title')]").text.strip().lower()
                    value = item.find_element(By.XPATH, ".//*[contains(@class, 'value')]").text.strip()
                except:
                    continue 
            else:
                title = text_lines[0].strip().lower()
                value = text_lines[1].strip()

            for vi_label, db_column in KEY_MAPPING.items():
                if vi_label in title:
                    specs[db_column] = value
                    break 
                    
    except Exception as e:
        print(f"[DetailSpider] ⚠️ Lỗi nội suy Key-Value: {e}")
        
    return specs

def run_detail_spider(table_name="bds_hadong", limit=50):
    """
    Hàm chạy chính cho Luồng 2.
    """
    print(f"\n[DetailSpider] Khởi động luồng làm giàu dữ liệu (Limit: {limit} bài/lượt)...")
    
    # Khởi tạo kết nối DB
    db = PostgresManager()
    if db.engine is None:
        print("[DetailSpider] ❌ Lỗi kết nối DB. Dừng luồng cào chi tiết.")
        return

    # BƯỚC 1: Lấy danh sách URL cần cào từ DB thông qua hàm đã viết
    listings_to_scrape = db.get_unenriched_listings(table_name=table_name, limit=limit) 
    
    if not listings_to_scrape:
        print("[DetailSpider] ✅ Không có listing nào cần làm giàu dữ liệu. Đi ngủ!")
        return

    # Khởi tạo Driver lần đầu
    driver = init_driver()
    success_count = 0
    
    try:
        for idx, listing in enumerate(listings_to_scrape, 1):
            raw_url = listing['url']
            listing_id = listing['listing_id']
            
            if raw_url.startswith('/'):
                url = f"https://batdongsan.com.vn{raw_url}"
            else:
                url = raw_url
                
            print(f"\n[DetailSpider] Đang cào ({idx}/{len(listings_to_scrape)}): {url}")
            
            try:
                driver.get(url)
                
                # Sleep chống bot
                time.sleep(random.uniform(8, 15)) 
                
                enriched_data = extract_specifications(driver)
                
                features_found = sum(1 for v in enriched_data.values() if v is not None)
                print(f"  -> Lấy được {features_found}/6 feature chi tiết.")
                
                # BƯỚC 2: Đẩy ngược lại vào DB
                enriched_data['listing_id'] = listing_id
                db.update_listing_details(table_name=table_name, enriched_data=enriched_data)
                
                success_count += 1
                
            except Exception as e:
                print(f"[DetailSpider] ❌ Lỗi khi xử lý {url}: {e}")
                
                # 🌟 KỸ THUẬT HỒI SINH TRÌNH DUYỆT TẠI ĐÂY 🌟
                error_msg = str(e).lower()
                if "target window already closed" in error_msg or "web view not found" in error_msg or "disconnected" in error_msg:
                    print("⚠️ Trình duyệt vừa bị Crash do trang quá nặng. Đang khởi động lại Browser...")
                    try:
                        driver.quit() # Dọn dẹp xác trình duyệt cũ
                    except:
                        pass
                    
                    time.sleep(3) # Nghỉ 3 giây cho RAM xả bớt
                    driver = init_driver() # Gọi lại browser.py của bạn để tạo trình duyệt mới
                    print("✅ Đã hồi sinh trình duyệt thành công. Sẽ tiếp tục với link tiếp theo.")
                
                continue # Bỏ qua bài lỗi này, đi tới vòng lặp tiếp theo
                
    finally:
        try:
            driver.quit()
        except:
            pass
        print(f"\n[DetailSpider] Hoàn thành. Cập nhật thành công {success_count}/{len(listings_to_scrape)} bài đăng.")

if __name__ == "__main__":
    # Test chạy thử 5 bài
    run_detail_spider(table_name="bds_hadong", limit=150)