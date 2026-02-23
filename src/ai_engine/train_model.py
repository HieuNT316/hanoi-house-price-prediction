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

# Đường dẫn lưu Model Champion
MODEL_PATH = MODEL_PATH

def load_data_from_db():
    print("🔄 Đang lấy dữ liệu từ PostgreSQL...")
    db = PostgresManager()
    # Chỉ lấy các cột cần thiết cho việc training
    query = """
        SELECT price_billion, area, ward, property_type, bedrooms, bathrooms 
        FROM listings 
        WHERE price_billion IS NOT NULL AND area IS NOT NULL
    """
    df = db.load_dataframe(query)
    print(f"✅ Đã tải {len(df)} bản ghi để huấn luyện.")
    return df

def preprocess_features(df):
    """Xử lý One-Hot Encoding cho các biến phân loại"""
    # Tách X, y
    y = df['price_billion']
    X = df.drop(columns=['price_billion'])
    
    # One-hot encoding cho Phường/Xã và Loại hình BĐS
    X_encoded = pd.get_dummies(X, columns=['ward', 'property_type'], drop_first=True)
    return X_encoded, y

def train_and_evaluate(X, y):
    print("🧠 Đang chia tập dữ liệu và thiết lập Cross-Validation...")
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

    # Khởi tạo mô hình
    rf = RandomForestRegressor(random_state=42)

    # Thiết lập Hyperparameter Tuning Grid
    param_grid = {
        'n_estimators': [100, 200],          # Số lượng cây quyết định
        'max_depth': [None, 10, 20],         # Độ sâu tối đa của cây
        'min_samples_split': [2, 5]          # Số mẫu tối thiểu để chia nhánh
    }

    # Áp dụng K-Fold Cross Validation (cv=3)
    grid_search = GridSearchCV(estimator=rf, param_grid=param_grid, 
                               cv=3, scoring='neg_mean_absolute_error', n_jobs=-1, verbose=1)
    
    print("⏳ Đang huấn luyện (Tìm kiếm siêu tham số tối ưu)...")
    grid_search.fit(X_train, y_train)
    
    # Lấy ra mô hình (Challenger) tốt nhất từ lưới tìm kiếm
    challenger_model = grid_search.best_estimator_
    print(f"✅ Tham số tối ưu: {grid_search.best_params_}")

    # Đánh giá MAE trên tập Test
    y_pred = challenger_model.predict(X_test)
    challenger_mae = mean_absolute_error(y_test, y_pred)
    
    print(f"📊 MAE của Challenger Model: {challenger_mae:.4f} Tỷ VNĐ")
    
    return challenger_model, challenger_mae, X.columns

def champion_challenger_evaluation(challenger_model, challenger_mae, feature_columns):
    """So sánh với model hiện tại (nếu có) và quyết định lưu đè"""
    os.makedirs(os.path.dirname(MODEL_PATH), exist_ok=True)
    
    if os.path.exists(MODEL_PATH):
        try:
            # Tải model cũ (Champion) và meta-data
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
    # Lưu cả model, MAE và danh sách cột (để đảm bảo input pipeline chuẩn xác lúc dự đoán)
    model_data = {
        'model': model,
        'mae': mae,
        'features': list(columns)
    }
    joblib.dump(model_data, MODEL_PATH)
    print(f"💾 Đã lưu tại: {MODEL_PATH}")

if __name__ == "__main__":
    df = load_data_from_db()
    if len(df) > 50: # Đảm bảo có đủ dữ liệu cơ bản
        X, y = preprocess_features(df)
        best_model, mae, features = train_and_evaluate(X, y)
        champion_challenger_evaluation(best_model, mae, features)
    else:
        print("⚠️ Dữ liệu trong DB quá ít để huấn luyện (Yêu cầu > 50 bản ghi).")