# src/preprocessing/cleaner.py
import pandas as pd
import os
import numpy as np
import sys
import re
import hashlib
from datetime import datetime
from sklearn.impute import KNNImputer
from sqlalchemy import inspect

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from src.database.postgres_manager import PostgresManager
from src.config.path import RAW_CSV_PATH, CLEANED_DATA_PATH

# Ép chuẩn UTF-8
sys.stdout.reconfigure(encoding='utf-8')

# --- CÁC HÀM TIỀN XỬ LÝ CƠ BẢN ---
def extract_ward(location_str):
    if pd.isna(location_str): return "Khác"
    parts = location_str.split(',') 
    ward = parts[0].strip() if len(parts) > 1 else location_str.strip()
    return ward.replace('.', '').strip()

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

def determine_property_type(row):
    text = str(row.get('title', '')).lower() + " " + str(row.get('description', '')).lower()
    if any(kw in text for kw in ['đất nền', 'bán đất', 'thửa đất', 'lô đất', 'đất phân lô']): return 'Đất nền'
    if any(kw in text for kw in ['chung cư', 'căn hộ', 'apartment', 'tập thể']): return 'Chung cư'
    if any(kw in text for kw in ['nhà', 'biệt thự', 'villa', 'liền kề', 'shophouse']): return 'Nhà riêng'
    return 'Nhà riêng'

def extract_room_number(row, col_name, keywords):
    try:
        val = row.get(col_name)
        if pd.notna(val) and str(val).strip() != "":
            return float(re.search(r'(\d+)', str(val)).group(1))
    except: pass
    
    if row.get('property_type') == 'Đất nền': return 0.0
        
    text = str(row.get('title', '')).lower() + " " + str(row.get('description', '')).lower()
    pattern = rf'(\d+)\s*(?:{"|".join(keywords)})'
    match = re.search(pattern, text)
    if match: return float(match.group(1))
    
    return np.nan

# --- LUỒNG XỬ LÝ CHÍNH ---
def process_and_save():
    if not os.path.exists(RAW_CSV_PATH):
        print(f"Không tìm thấy file tại: {RAW_CSV_PATH}")
        return

    print("Đang đọc dữ liệu thô...")
    try:
        df = pd.read_csv(RAW_CSV_PATH, on_bad_lines='skip', engine='python')
        if 'title' in df.columns:
            df = df[df['title'] != 'title']
        print(f"Tổng số dòng thô: {len(df)}")
    except Exception as e:
        print(f"Lỗi đọc CSV: {e}")
        return

    # Khởi tạo các cột nếu thiếu
    for col in ['bedrooms', 'bathrooms', 'description', 'url']:
        if col not in df.columns:
            df[col] = np.nan

    # --- 1. LÀM SẠCH CƠ BẢN ---
    df['price_billion'] = df['price'].apply(clean_price)
    df['area'] = df['area'].astype(str).str.extract(r'(\d+\.?\d*)').astype(float)
    df['ward'] = df['location'].apply(extract_ward)
    df['description'] = df['description'].apply(clean_description)
    
    # --- 2. AI & NLP ---
    print("🧠 Đang áp dụng NLP trích xuất Đặc trưng...")
    df['property_type'] = df.apply(determine_property_type, axis=1)
    df['bedrooms'] = df.apply(lambda row: extract_room_number(row, 'bedrooms', ['pn', 'ngủ', 'phòng ngủ']), axis=1)
    df['bathrooms'] = df.apply(lambda row: extract_room_number(row, 'bathrooms', ['wc', 'vệ sinh', 'tắm']), axis=1)

    # --- 3. XỬ LÝ NGÀY THÁNG (Chuẩn YYYY-MM-DD từ spider mới) ---
    today_str = datetime.now().strftime("%Y-%m-%d")
    df['scraped_date'] = df.get('scraped_date', today_str).fillna(today_str)
    
    # --- 4. LỌC DỮ LIỆU ---
    required_features = ['title', 'price_billion', 'area', 'location', 'property_type']
    df_clean = df.dropna(subset=required_features, how='any').copy()

    # Lọc Bounding Box & Đơn giá (Tránh Outliers)
    df_clean = df_clean[
        df_clean['price_billion'].between(0.5, 50) & 
        df_clean['area'].between(15, 500)
    ].copy()
    df_clean['unit_price'] = (df_clean['price_billion'] * 1000) / df_clean['area']
    df_clean = df_clean[df_clean['unit_price'].between(15, 350)]
    df_clean = df_clean.drop(columns=['unit_price'])

    # --- 5. TẠO ID (MD5 CHỐNG CÒ MỒI SPAM) ---
    df_clean['listing_id'] = df_clean.apply(
        lambda row: hashlib.md5(
            f"{row['area']}_{row['ward']}_{row['property_type']}_{row['price_billion']}_{row['bedrooms']}_{row['bathrooms']}".encode('utf-8')
        ).hexdigest(), 
        axis=1
    )

    # Lọc trùng lặp ngay trong pandas trước khi đẩy vào DB
    df_clean = df_clean.drop_duplicates(subset=['listing_id'], keep='last')
    

    # --- 6. KNN IMPUTER ---
    print("🧠 Đang áp dụng KNN Imputer...")
    knn_features = ['area', 'price_billion', 'bedrooms', 'bathrooms']
    if df_clean[['bedrooms', 'bathrooms']].isna().any().any():
        imputer = KNNImputer(n_neighbors=5, weights='distance')
        df_clean[knn_features] = imputer.fit_transform(df_clean[knn_features])
        df_clean['bedrooms'] = df_clean['bedrooms'].round()
        df_clean['bathrooms'] = df_clean['bathrooms'].round()

    # Bổ sung 'url' vào list các cột cuối cùng
    final_columns = ['listing_id', 'url', 'title', 'price_billion', 'area', 'ward', 'property_type', 'bedrooms', 'bathrooms', 'scraped_date']
    df_final = df_clean[final_columns].copy()

    print(f"✅ Giữ lại {len(df_final)}/{len(df)} tin hợp lệ.")

# --- 7. ĐẨY VÀO POSTGRESQL ---
    if df_final.empty:
        print("⚠️ Không có dữ liệu hợp lệ để lưu vào DB.")
        return
    
    # 🌟 SỬA TẠI ĐÂY: KHAI BÁO CỘT TRƯỚC KHI TẠO BẢNG 🌟
    # 1. Bật cờ is_enriched cho data cũ (không có URL)
    df_final['is_enriched'] = df_final['url'].isna()
    
    # 2. Khởi tạo 6 cột trống để "giữ chỗ" trong PostgreSQL cho detail_spider update sau này
    advanced_features = ['frontage', 'road_width', 'direction', 'floors', 'legal_status', 'furniture']
    for col in advanced_features:
        df_final[col] = None
        
    # ==================================================

    db = PostgresManager()
    table_name = 'bds_hadong'
    
    # KIỂM TRA & TỰ ĐỘNG TẠO BẢNG
    
    inspector = inspect(db.engine)
    if not inspector.has_table(table_name):
        print(f"🏗️ Bảng '{table_name}' chưa tồn tại. Đang tự động build cấu trúc...")
        # Lúc này df_final đã có đủ 17 cột, Pandas sẽ tạo bảng chuẩn xác 100%
        df_final.head(0).to_sql(table_name, con=db.engine, if_exists='replace', index=False)

    # Kích hoạt Primary Key
    if hasattr(db, 'ensure_primary_key'):
        db.ensure_primary_key(table_name=table_name, column_name='listing_id')

    # DANH SÁCH BẢO VỆ: Không được ghi đè các cột này vì Luồng 2 sẽ/đã cào chúng
    protected_features = ['is_enriched', 'frontage', 'road_width', 'direction', 'floors', 'legal_status', 'furniture']
    
    print("Đang thực hiện Upsert dữ liệu vào PostgreSQL...")
    db.upsert_dataframe(
        df=df_final, 
        table_name=table_name, 
        unique_key='listing_id',
        exclude_cols=protected_features 
    )
    
    df_final.to_csv(CLEANED_DATA_PATH, index=False, encoding='utf-8-sig')
    print("✅ Hoàn tất Pipeline ETL.")

if __name__ == "__main__":
    process_and_save()