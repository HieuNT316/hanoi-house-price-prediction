import pandas as pd
import numpy as np
import os
import sys
import joblib
import optuna 

from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_absolute_error, r2_score
from sklearn.model_selection import RandomizedSearchCV
from xgboost import XGBRegressor

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from src.config.path import XGB_MODEL_PATH
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

    cat_cols = ['ward', 'property_type', 'direction', 'legal_status', 'furniture']
    for col in ['direction', 'legal_status', 'furniture']:
        df[col] = df[col].fillna("Không xác định")
    
    df['unit_price'] = df['price_billion'] / df['area'] 
    y = df[['unit_price', 'price_billion']]
    X = df.drop(columns=['unit_price', "price_billion"])

    X_encoded = pd.get_dummies(X, columns=cat_cols, drop_first=True)
    return X_encoded, y

def train_xgb_model(X, y):
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

    def objective(trial):
        params = {
            'objective': 'reg:absoluteerror',
            'random_state': 42,
            'n_jobs': -1,
            'n_estimators': trial.suggest_int('n_estimators', 300, 1500),
            'learning_rate': trial.suggest_float('learning_rate', 0.005, 0.1, log=True),
            'max_depth': trial.suggest_int('max_depth', 5, 15),
            'subsample': trial.suggest_float('subsample', 0.6, 1.0),
            'colsample_bytree': trial.suggest_float('colsample_bytree', 0.6, 1.0),
            'min_child_weight': trial.suggest_int('min_child_weight', 1, 10),
        }
        model = XGBRegressor(**params)
        model.fit(X_train, np.log1p(y_train['unit_price']))
        y_pred_unit = np.expm1(model.predict(X_test))
        y_pred_total = y_pred_unit * X_test['area']
        return mean_absolute_error(y_test['price_billion'], y_pred_total)
    
    study = optuna.create_study(direction='minimize')
    study.optimize(objective, n_trials=50, show_progress_bar=True) 

    print(f"✅ Tham số tối ưu nhất từ Optuna: {study.best_params}")

    best_model = XGBRegressor(
        objective='reg:absoluteerror',
        random_state=42,
        n_jobs=-1,
        task_type="GPU",
            devices='0',
        **study.best_params
    )
    best_model.fit(X_train, np.log1p(y_train['unit_price']))

    y_pred_unit = np.expm1(best_model.predict(X_test))
    y_pred_total = y_pred_unit * X_test['area']
    mae = mean_absolute_error(y_test['price_billion'], y_pred_total)
    r2 = r2_score(y_test['price_billion'], y_pred_total)
    print(f"MAE của mô hình XGBoost: {mae:.4f}")
    print(f"R² của mô hình XGBoost: {r2:.4f}")

    return best_model, mae, X.columns

if __name__ == "__main__":
    df = load_data_from_db()
    if len(df) > 50:
        X, y = preprocess_features(df)
        best_model, mae, features = train_xgb_model(X, y)
        champion_challenger_evaluation(best_model, mae, features, XGB_MODEL_PATH)
    else:
        print("⚠️ Dữ liệu trong DB quá ít để huấn luyện (Yêu cầu > 50 bản ghi).")
