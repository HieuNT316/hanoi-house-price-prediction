# src/ai_engine/train_model.py
import pandas as pd
import numpy as np
import os
import sys
import joblib
from sklearn.model_selection import train_test_split, GridSearchCV
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error

from src.config.path import MODEL_PATH
from src.database.postgres_manager import PostgresManager

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
sys.stdout.reconfigure(encoding='utf-8')

def load_data_from_db():
    print("🔄 Đang lấy dữ liệu từ PostgreSQL...")
    db = PostgresManager()
    # THÊM 6 FEATURE MỚI VÀO CÂU TRUY VẤN
    query = """
        SELECT price_billion, area, ward, property_type, bedrooms, bathrooms,
               frontage, road_width, direction, floors, legal_status, furniture
        FROM bds_hadong 
        WHERE price_billion IS NOT NULL AND area IS NOT NULL
    """
    df = db.load_dataframe(query)
    print(f"✅ Đã tải {len(df)} bản ghi để huấn luyện.")
    return df

def preprocess_features(df):
    """Xử lý One-Hot Encoding và thiết lập biến mục tiêu Đơn Giá"""
    print("🧠 Đang tiền xử lý dữ liệu và làm sạch Features mới...")
    
    # --- XỬ LÝ FEATURE SỐ (NUMERICAL) ---
    # Dùng Regex bóc tách con số từ chuỗi text cào được (VD: "5 m" -> 5.0)
    df['frontage'] = df['frontage'].astype(str).str.extract(r'(\d+\.?\d*)').astype(float)
    df['road_width'] = df['road_width'].astype(str).str.extract(r'(\d+\.?\d*)').astype(float)
    df['floors'] = df['floors'].astype(str).str.extract(r'(\d+)').astype(float)

    # Điền giá trị khuyết thiếu (Missing Data) bằng giá trị trung vị (Median)
    df['frontage'] = df['frontage'].fillna(df['frontage'].median() if pd.notna(df['frontage'].median()) else 4.0)
    df['road_width'] = df['road_width'].fillna(df['road_width'].median() if pd.notna(df['road_width'].median()) else 3.0)
    df['floors'] = df['floors'].fillna(df['floors'].median() if pd.notna(df['floors'].median()) else 3.0)

    # --- XỬ LÝ FEATURE PHÂN LOẠI (CATEGORICAL) ---
    cat_cols = ['ward', 'property_type', 'direction', 'legal_status', 'furniture']
    for col in ['direction', 'legal_status', 'furniture']:
        df[col] = df[col].fillna('Không xác định') # Nếu trống thì quy về Không xác định

    # --- TẠO BIẾN MỤC TIÊU ---
    df['unit_price'] = df['price_billion'] / df['area']
    y = df[['unit_price', 'price_billion']]
    
    # Bỏ cột giá khỏi tập Features
    X = df.drop(columns=['price_billion', 'unit_price'])
    
    # One-hot encoding toàn bộ biến phân loại
    X_encoded = pd.get_dummies(X, columns=cat_cols, drop_first=True)
    return X_encoded, y

def train_and_evaluate(X, y):
    print("🧠 Đang chia tập dữ liệu và thiết lập Cross-Validation...")
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

    rf = RandomForestRegressor(random_state=42)

    param_grid = {
        'n_estimators': [200, 300],          
        'max_depth': [10, 15, 20],           
        'min_samples_split': [5, 10],        
        'min_samples_leaf': [2, 4, 6],       
        'max_features': [1.0, 'sqrt']        
    }

    grid_search = GridSearchCV(estimator=rf, param_grid=param_grid, 
                               cv=3, scoring='neg_mean_absolute_error', n_jobs=-1, verbose=1)
    
    print("⏳ Đang huấn luyện (Học cách dự đoán ĐƠN GIÁ)...")
    grid_search.fit(X_train, y_train['unit_price'])
    
    challenger_model = grid_search.best_estimator_
    print(f"✅ Tham số tối ưu: {grid_search.best_params_}")

    # ĐÁNH GIÁ TRÊN TỔNG GIÁ
    y_pred_unit = challenger_model.predict(X_test)
    y_pred_total = y_pred_unit * X_test['area']
    challenger_mae = mean_absolute_error(y_test['price_billion'], y_pred_total)
    
    print(f"📊 MAE của Challenger Model (Trên Tổng giá): {challenger_mae:.4f} Tỷ VNĐ")
    
    return challenger_model, challenger_mae, X.columns

def champion_challenger_evaluation(challenger_model, challenger_mae, feature_columns):
    os.makedirs(os.path.dirname(MODEL_PATH), exist_ok=True)
    
    if os.path.exists(MODEL_PATH):
        try:
            saved_data = joblib.load(MODEL_PATH)
            champion_mae = saved_data.get('mae', float('inf'))
            
            print(f"🥊 Đang so sánh... Champion MAE: {champion_mae:.4f} vs Challenger MAE: {challenger_mae:.4f}")
            
            if challenger_mae < champion_mae:
                print("🏆 Challenger chiến thắng! Cập nhật mô hình mới vào hệ thống.")
                save_model(challenger_model, challenger_mae, feature_columns)
            else:
                print("🛡️ Champion bảo vệ ngôi vương. Giữ nguyên mô hình cũ.")
        except Exception as e:
            print(f"⚠️ Lỗi đọc model cũ ({e}). Đang ghi đè model mới...")
            save_model(challenger_model, challenger_mae, feature_columns)
    else:
        print("🌟 Chưa có model trong hệ thống. Đang lưu Challenger làm Champion đầu tiên!")
        save_model(challenger_model, challenger_mae, feature_columns)

def save_model(model, mae, columns):
    model_data = {'model': model, 'mae': mae, 'features': list(columns)}
    joblib.dump(model_data, MODEL_PATH)
    print(f"💾 Đã lưu tại: {MODEL_PATH}")

if __name__ == "__main__":
    df = load_data_from_db()
    if len(df) > 50:
        X, y = preprocess_features(df)
        best_model, mae, features = train_and_evaluate(X, y)
        champion_challenger_evaluation(best_model, mae, features)
    else:
        print("⚠️ Dữ liệu trong DB quá ít để huấn luyện (Yêu cầu > 50 bản ghi).")