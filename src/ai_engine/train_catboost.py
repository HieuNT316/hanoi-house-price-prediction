import pandas as pd
import numpy as np
import os
import sys
import joblib
import optuna 

from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_absolute_error, r2_score
from catboost import CatBoostRegressor, Pool

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from src.config.path import CATBOOST_MODEL_PATH
from src.database.postgres_manager import PostgresManager
from src.ai_engine.evaluate import champion_challenger_evaluation

def load_data_from_db():
    db = PostgresManager()
    query = """ 
        select price_billion, area, ward, property_type, bedrooms, bathrooms,
               frontage, road_width, direction, floors, legal_status, furniture
        from bds_hadong
        order by listing_id asc"""  # Đảm bảo lấy dữ liệu mới nhất
    return db.load_dataframe(query)

def preprocess_features(df):
    df['frontage'] = df['frontage'].astype(str).str.extract(r'(\d+\.?\d*)').astype(float)
    df['road_width'] = df['road_width'].astype(str).str.extract(r'(\d+\.?\d*)').astype(float)
    df['floors'] = df['floors'].astype(str).str.extract(r'(\d+)').astype(float)

    df.loc[df['frontage'].isna() & df['property_type'] != 'Chung cư', 'frontage'] = df['frontage'].median()
    df['road_width'] = df['road_width'].fillna(df['road_width'].median()) 
    df.loc[df['floors'].isna() & df['property_type'] == 'Nhà riêng', 'floors'] = df['floors'].median()
    df.loc[df['floors'].isna() & df['property_type'] != 'Nhà riêng', 'floors'] = 0
    df['floors'] = df['floors'].astype(str)
    for col in ['direction', 'legal_status', 'furniture']:
        df[col] = df[col].fillna("Không xác định")
    
    df['unit_price'] = df['price_billion'] / df['area'] 
    y = df[['unit_price', 'price_billion']]
    X = df.drop(columns=['unit_price', "price_billion"])

    return X, y

def train_catboost_model(X, y):
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
    cat_features = ['ward', 'property_type', 'floors', 'direction', 'legal_status', 'furniture']
    train_pool = Pool(X_train, np.log1p(y_train['unit_price']), cat_features=cat_features)
    test_pool = Pool(X_test, np.log1p(y_test['unit_price']), cat_features=cat_features)

    def objective(trial):
        params = {
            'iterations': 2000, 
            'depth': trial.suggest_int('depth', 6, 12), # Thu hẹp độ sâu
            'learning_rate': trial.suggest_float('learning_rate', 0.01, 0.08, log=True),
            'l2_leaf_reg': trial.suggest_float('l2_leaf_reg', 2.0, 15.0), # Tăng phạt để chống overfitting
            'random_strength': trial.suggest_float('random_strength', 1.0, 5.0), # Tăng tính ngẫu nhiên
            'bagging_temperature': trial.suggest_float('bagging_temperature', 0.2, 1.0),
            'grow_policy': 'Lossguide', # Cây sẽ mọc theo nút có lợi nhuận giảm lỗi cao nhất (giống LightGBM/XGBoost)
            'max_leaves': trial.suggest_int('max_leaves', 31, 128), #Giới hạn số lá thay vì depth 
            'od_type': 'Iter',
            'od_wait': 50,
            'loss_function': 'RMSE',
            'verbose': False,
            'allow_writing_files': False,
            # Thêm tham số xử lý nhiễu
            'min_data_in_leaf': trial.suggest_int('min_data_in_leaf', 10, 50), #Chống học vẹt khi depth cao 
        }
        model = CatBoostRegressor(
            task_type="GPU",
            devices='0',
            **params)
        model.fit(train_pool, eval_set=test_pool, early_stopping_rounds=50, verbose=False)
        y_pred_unit = np.expm1(model.predict(test_pool))
        y_pred_total = y_pred_unit * X_test['area']
        return mean_absolute_error(y_test['price_billion'], y_pred_total)
    
    study = optuna.create_study(direction='minimize')
    study.optimize(objective, n_trials=100, show_progress_bar=True) 

    print(f"✅ Tham số tối ưu nhất từ Optuna: {study.best_params}")

    best_model = CatBoostRegressor(
        random_state=42,
        grow_policy='Lossguide',  # Thêm dòng này để cho phép dùng max_leaves
        eval_metric='MAE',
        task_type='GPU', # Nhớ tận dụng GPU Colab nhé
        verbose=100,
        **study.best_params
    )
    best_model.fit(train_pool, eval_set=test_pool, early_stopping_rounds=50, verbose=False)

    y_pred_unit = np.expm1(best_model.predict(test_pool))
    y_pred_total = y_pred_unit * X_test['area']
    mae = mean_absolute_error(y_test['price_billion'], y_pred_total)
    r2 = r2_score(y_test['price_billion'], y_pred_total)
    print(f"MAE của mô hình CatBoost: {mae:.4f}")
    print(f"R² của mô hình CatBoost: {r2:.4f}")

    return best_model, mae, X.columns

if __name__ == "__main__":
    df = load_data_from_db()
    if len(df) > 50:
        X, y = preprocess_features(df)
        best_model, mae, features = train_catboost_model(X, y)
        champion_challenger_evaluation(best_model, mae, features, CATBOOST_MODEL_PATH)
    else:
        print("⚠️ Dữ liệu trong DB quá ít để huấn luyện (Yêu cầu > 50 bản ghi).")
