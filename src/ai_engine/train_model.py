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

# Ép Python xuất dữ liệu text ra terminal hoặc file log bằng chuẩn UTF-8
sys.stdout.reconfigure(encoding='utf-8')

def load_data_from_db():
    print("🔄 Đang lấy dữ liệu từ PostgreSQL...")
    db = PostgresManager()
    query = """
        SELECT price_billion, area, ward, property_type, bedrooms, bathrooms 
        FROM listings 
        WHERE price_billion IS NOT NULL AND area IS NOT NULL
    """
    df = db.load_dataframe(query)
    print(f"✅ Đã tải {len(df)} bản ghi để huấn luyện.")
    return df

def preprocess_features(df):
    """Xử lý One-Hot Encoding và thiết lập biến mục tiêu Đơn Giá"""
    # 1. TẠO BIẾN MỤC TIÊU MỚI: Đơn giá (Tỷ / m2)
    df['unit_price'] = df['price_billion'] / df['area']
    
    # 2. Định nghĩa y: Giữ cả unit_price (để train) và price_billion (để test)
    y = df[['unit_price', 'price_billion']]
    
    # 3. Định nghĩa X: Bỏ các cột liên quan đến giá, giữ lại area
    X = df.drop(columns=['price_billion', 'unit_price'])
    
    # One-hot encoding cho Phường/Xã và Loại hình BĐS
    X_encoded = pd.get_dummies(X, columns=['ward', 'property_type'], drop_first=True)
    return X_encoded, y

def train_and_evaluate(X, y):
    print("🧠 Đang chia tập dữ liệu và thiết lập Cross-Validation...")
    # Chia test/train. Do truyền y (có 2 cột) nên y_train và y_test cũng sẽ giữ 2 cột này
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

    rf = RandomForestRegressor(random_state=42)

    param_grid = {
        'n_estimators': [200, 300],          # 200-300 cây là đủ, tập trung tối ưu cấu trúc cây
        'max_depth': [10, 15, 20],           # TUYỆT ĐỐI KHÔNG DÙNG None. Khống chế độ sâu để tăng tính tổng quát
        'min_samples_split': [5, 10],        # Số mẫu tối thiểu để chẻ nhánh
        'min_samples_leaf': [2, 4, 6],       # 🌟 QUAN TRỌNG: Bắt buộc mỗi node lá cuối cùng phải chứa ít nhất 2-6 căn nhà. Giúp loại bỏ các dự đoán dựa trên 1 căn duy nhất (outlier).
        'max_features': [1.0, 'sqrt']        # Thử nghiệm giới hạn số lượng feature khi chia nhánh để chống đa cộng tuyến
    }

    grid_search = GridSearchCV(estimator=rf, param_grid=param_grid, 
                               cv=3, scoring='neg_mean_absolute_error', n_jobs=-1, verbose=1)
    
    print("⏳ Đang huấn luyện (Học cách dự đoán ĐƠN GIÁ)...")
    # CHỈ TRUYỀN 'unit_price' VÀO ĐỂ HUẤN LUYỆN
    grid_search.fit(X_train, y_train['unit_price'])
    
    challenger_model = grid_search.best_estimator_
    print(f"✅ Tham số tối ưu: {grid_search.best_params_}")

    # --- ĐÁNH GIÁ (INFERENCE SIMULATION) ---
    # 1. Dự đoán ra Đơn giá cho tập Test
    y_pred_unit = challenger_model.predict(X_test)
    
    # 2. Quy đổi ra Tổng giá: Đơn giá dự đoán * Diện tích thực tế
    y_pred_total = y_pred_unit * X_test['area']
    
    # 3. Tính MAE so với Tổng giá thực tế ban đầu
    challenger_mae = mean_absolute_error(y_test['price_billion'], y_pred_total)
    
    print(f"📊 MAE của Challenger Model (Trên Tổng giá): {challenger_mae:.4f} Tỷ VNĐ")
    
    return challenger_model, challenger_mae, X.columns

def champion_challenger_evaluation(challenger_model, challenger_mae, feature_columns):
    """So sánh với model hiện tại (nếu có) và quyết định lưu đè"""
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
    model_data = {
        'model': model,
        'mae': mae,
        'features': list(columns)
    }
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