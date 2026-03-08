import numpy as np
import pandas as pd
import os
import sys
import joblib
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import src.ai_engine.train_xgb as xgb_trainer
import src.ai_engine.train_catboost as catboost_trainer
from src.database.postgres_manager import PostgresManager
from src.config.path import XGB_MODEL_PATH, CATBOOST_MODEL_PATH, ENSEMBLE_MODEL_PATH
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_absolute_error
class EnsembleModel:
    def __init__(self, xgb_model, catboost_model):
        self.xgb_model = xgb_model
        self.catboost_model = catboost_model
        self.weight = 0.5  # Trọng số mặc định, sẽ được tối ưu hóa sau
        self.mae = None  # MAE của mô hình Ensemble sẽ được tính sau khi tìm được trọng số tốt nhất

    def find_best_weights(self, X_xgb_test, X_catboost_test, y_test):
        
        xgb_pred_unit = np.expm1(self.xgb_model.predict(X_xgb_test))
        catboost_pred_unit = np.expm1(self.catboost_model.predict(X_catboost_test))

        best_mae = float('inf')
        best_weight = 0.5

        for weight in np.arange(0, 1.1, 0.1):
            ensemble_pred_unit = weight * xgb_pred_unit + (1 - weight) * catboost_pred_unit
            ensemble_pred_total = ensemble_pred_unit * X_xgb_test['area']  # Quy đổi về tổng giá
            mae = mean_absolute_error(y_test, ensemble_pred_total)
            if mae < best_mae:
                best_mae = mae
                best_weight = weight

        print(f"🔍 Tìm được trọng số tốt nhất: XGB={best_weight:.2f}, CatBoost={1 - best_weight:.2f} với MAE={best_mae:.4f}")
        return best_weight, best_mae

    def predict(self, X_xgb, X_catboost):
        xgb_pred_unit = np.expm1(self.xgb_model.predict(X_xgb))
        catboost_pred_unit = np.expm1(self.catboost_model.predict(X_catboost))
        # Cân bằng trọng số giữa hai mô hình (có thể điều chỉnh nếu cần)
        ensemble_pred_unit = self.weight * xgb_pred_unit + (1 - self.weight) * catboost_pred_unit
        return ensemble_pred_unit * X_xgb['area']  # Quy đổi về tổng giá
    
if __name__ == "__main__":
    # 1. Load dữ liệu (Đã có ORDER BY trong hàm)
    db = PostgresManager()
    query = """ 
        select price_billion, area, ward, property_type, bedrooms, bathrooms,
               frontage, road_width, direction, floors, legal_status, furniture
        from bds_hadong
        order by listing_id asc""" 
    df = db.load_dataframe(query)
    
    # 2. Xử lý riêng biệt với df.copy() để không dẫm chân lên nhau
    X_xgb, y_xgb = xgb_trainer.preprocess_features(df.copy())
    X_catboost, y_catboost = catboost_trainer.preprocess_features(df.copy())

    # 3. Chia tập train/test (Đảm bảo random_state=42 cho tất cả)
    X_xgb_train, X_xgb_test, y_xgb_train, y_xgb_test = train_test_split(X_xgb, y_xgb, test_size=0.2, random_state=42)
    X_catboost_train, X_catboost_test, y_catboost_train, y_catboost_test = train_test_split(X_catboost, y_catboost, test_size=0.2, random_state=42)
    
    # --- ĐỂ CHẮC CHẮN KHÔNG BỊ LỖI, IN THỬ MAE THỰC TẾ RA ---
    xgb_model_data = joblib.load(XGB_MODEL_PATH)
    catboost_model_data = joblib.load(CATBOOST_MODEL_PATH)
    xgb_model = xgb_model_data['model']
    catboost_model = catboost_model_data['model']

    print("--- KIỂM TRA ĐỘ TOÀN VẸN CỦA MODEL ---")
    xgb_test_pred = np.expm1(xgb_model.predict(X_xgb_test)) * X_xgb_test['area']
    cat_test_pred = np.expm1(catboost_model.predict(X_catboost_test)) * X_catboost_test['area']
    
    print(f"MAE thật của XGBoost trên tập Test này: {mean_absolute_error(y_xgb_test['price_billion'], xgb_test_pred):.4f}")
    print(f"MAE thật của CatBoost trên tập Test này: {mean_absolute_error(y_catboost_test['price_billion'], cat_test_pred):.4f}")
    
    # 4. Tìm trọng số và lưu model
    ensemble = EnsembleModel(xgb_model, catboost_model)
    best_weight, best_mae = ensemble.find_best_weights(X_xgb_test, X_catboost_test, y_xgb_test['price_billion'])
    ensemble.weight, ensemble.mae = best_weight, best_mae
    
    joblib.dump({
        'model': ensemble,
        'mae': ensemble.mae,
    }, ENSEMBLE_MODEL_PATH)