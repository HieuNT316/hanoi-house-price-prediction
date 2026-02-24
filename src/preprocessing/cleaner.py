# src/preprocessing/cleaner.py
import pandas as pd
import os
import numpy as np
import sys
import re
import hashlib
from datetime import datetime
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from src.database.postgres_manager import PostgresManager
from src.config.path import RAW_CSV_PATH, CLEANED_DATA_PATH

# Ép Python xuất dữ liệu text ra terminal hoặc file log bằng chuẩn UTF-8
sys.stdout.reconfigure(encoding='utf-8')

# --- CÁC HÀM TIỀN XỬ LÝ CƠ BẢN ---
def extract_ward(location_str):
    if pd.isna(location_str): return "Khác"
    parts = location_str.split(',') 
    if len(parts) > 1: return parts[0].strip()
    return location_str.strip()

def clean_price(price_str):
    if pd.isna(price_str): return None
    price_str = str(price_str).lower().replace(',', '.') 
    if "tỷ" in price_str: return float(price_str.replace("tỷ", "").strip())
    elif "triệu" in price_str: return float(price_str.replace("triệu", "").strip()) / 1000
    return None

def clean_description(text):
    if pd.isna(text): return ""
    text = str(text).strip()
    if re.match(r'^\d{2}/\d{2}/\d{4}$', text): return ""
    return text

# --- CÁC HÀM AI & NLP MỚI ---
def determine_property_type(row):
    """Phân loại Bất động sản dựa vào từ khóa trong Tiêu đề và Mô tả"""
    text = str(row.get('title', '')).lower() + " " + str(row.get('description', '')).lower()
    
    if any(kw in text for kw in ['đất nền', 'bán đất', 'thửa đất', 'lô đất', 'đất phân lô']):
        return 'Đất nền'
    if any(kw in text for kw in ['chung cư', 'căn hộ', 'apartment', 'tập thể']):
        return 'Chung cư'
    if any(kw in text for kw in ['nhà', 'biệt thự', 'villa', 'liền kề', 'shophouse']):
        return 'Nhà riêng'
    
    return 'Nhà riêng' # Giá trị mặc định an toàn

def extract_room_number(row, col_name, keywords):
    """Trích xuất số phòng từ văn bản nếu cào bị thiếu"""
    # 1. Nếu đã cào được số liệu hợp lệ -> Làm sạch và trả về
    try:
        val = row.get(col_name)
        if pd.notna(val) and str(val).strip() != "":
            return float(re.search(r'(\d+)', str(val)).group(1))
    except: pass
    
    # 2. Nếu là Đất nền -> Chắc chắn bằng 0
    if row.get('property_type') == 'Đất nền':
        return 0.0
        
    # 3. Dùng NLP Regex để bới trong text
    text = str(row.get('title', '')).lower() + " " + str(row.get('description', '')).lower()
    pattern = rf'(\d+)\s*(?:{"|".join(keywords)})'
    match = re.search(pattern, text)
    if match:
        return float(match.group(1))
    
    # 4. Fallback (Trung vị) nếu không thể tìm thấy
    if col_name == 'bedrooms':
        return 2.0 if row.get('property_type') == 'Chung cư' else 3.0
    else: # bathrooms
        return 2.0 if row.get('property_type') == 'Chung cư' else 3.0

# --- LUỒNG XỬ LÝ CHÍNH ---
def process_and_save():
    if not os.path.exists(RAW_CSV_PATH):
        print(f"Không tìm thấy file tại: {RAW_CSV_PATH}")
        return

    print("Đang đọc dữ liệu thô...")
    try:
        # Xóa khai báo column_names cứng, để Pandas tự nhận diện header
        df = pd.read_csv(RAW_CSV_PATH, on_bad_lines='skip', engine='python')
        
        # Sửa lỗi dòng Header bị lặp lại trong thân file (do crawler chạy nhiều lần)
        if 'title' in df.columns:
            df = df[df['title'] != 'title']
        print(f"Tổng số dòng thô: {len(df)}")
    except Exception as e:
        print(f"Lỗi đọc CSV: {e}")
        return

    # Khởi tạo các cột mới nếu dữ liệu cũ chưa có (tránh lỗi KeyError)
    for col in ['bedrooms', 'bathrooms', 'description']:
        if col not in df.columns:
            df[col] = np.nan

    # --- 1. LÀM SẠCH CƠ BẢN ---
    df['price_billion'] = df['price'].apply(clean_price)
    df['area'] = df['area'].astype(str).str.extract(r'(\d+\.?\d*)').astype(float)
    df['ward'] = df['location'].apply(extract_ward)
    df['description'] = df['description'].apply(clean_description)
    
    # --- 2. XÁC ĐỊNH PROPERTY_TYPE & ĐIỀN KHUYẾT PHÒNG ---
    print("🧠 Đang áp dụng NLP trích xuất Đặc trưng & Phân loại...")
    df['property_type'] = df.apply(determine_property_type, axis=1)
    
    # Trích xuất số phòng ngủ (từ khóa: pn, ngủ, phòng ngủ)
    df['bedrooms'] = df.apply(lambda row: extract_room_number(row, 'bedrooms', ['pn', 'ngủ', 'phòng ngủ']), axis=1)
    
    # Trích xuất số phòng tắm (từ khóa: wc, vệ sinh, phòng tắm)
    df['bathrooms'] = df.apply(lambda row: extract_room_number(row, 'bathrooms', ['wc', 'vệ sinh', 'tắm']), axis=1)

    # --- 3. XỬ LÝ NGÀY THÁNG LỘN XỘN ---
    today_str = datetime.now().strftime("%d/%m/%Y")
    df['scraped_date'] = df.get('scraped_date', today_str).fillna(today_str)
    df['published_date'] = df.get('published_date', df['scraped_date']).fillna(df['scraped_date'])

    # Đồng bộ ngày đăng vô lý
    df['pub_dt'] = pd.to_datetime(df['published_date'], format='%d/%m/%Y', errors='coerce')
    df['scrape_dt'] = pd.to_datetime(df['scraped_date'], format='%d/%m/%Y', errors='coerce')
    mask_future = df['pub_dt'] > df['scrape_dt']
    if mask_future.sum() > 0:
        df.loc[mask_future, 'published_date'] = df.loc[mask_future, 'scraped_date']
    
    # --- 4. LỌC DỮ LIỆU & LƯU TRỮ ---
    required_features = ['title', 'price_billion', 'area', 'location', 'property_type', 'bedrooms']
    df_clean = df.dropna(subset=required_features, how='any')
    
    df_clean = df_clean.drop_duplicates(subset=['title', 'area', 'published_date'], keep='last')

    # Nhà 999 tỷ, 0.001m2 vẫn lọt vào DB
    df_clean = df_clean[
        df_clean['price_billion'].between(0.1, 200) &
        df_clean['area'].between(5, 10000)
    ]

    # 🌟 MỚI: Tạo Unique ID (listing_id) dựa trên các trường quan trọng
    df_clean['listing_id'] = df_clean.apply(
        lambda row: hashlib.md5(f"{row['title']}_{row['area']}_{row['published_date']}".encode('utf-8')).hexdigest(), 
        axis=1
    )
    
    print(f"✅ Giữ lại {len(df_clean)}/{len(df)} tin hợp lệ.")

    # Thêm 'listing_id' vào danh sách cột cuối cùng
    final_columns = ['listing_id', 'title', 'price_billion', 'area', 'ward', 'property_type', 'bedrooms', 'bathrooms', 'published_date']
    df_final = df_clean[final_columns]

    # Khởi tạo DB Manager
    db = PostgresManager()
    
    # 🌟 MỚI: Gọi phương thức Upsert thay vì dùng if_exists='replace'
    print("Đang thực hiện Upsert dữ liệu vào PostgreSQL...")
    db.upsert_dataframe(df=df_final, table_name='listings', unique_key='listing_id')
    
    # Lưu backup ra CSV (Tùy chọn)
    df_final.to_csv(CLEANED_DATA_PATH, index=False, encoding='utf-8-sig')
    print("✅ Hoàn tất Pipeline ETL.")

if __name__ == "__main__":
    process_and_save()