# src/config/paths.py
import os

# Xử lý đường dẫn tương đối (Lùi về đúng gốc project)
CONFIG_DIR = os.path.dirname(os.path.abspath(__file__)) # Thư mục src/config/
SRC_DIR = os.path.dirname(CONFIG_DIR)                   # Thư mục src/
ROOT_DIR = os.path.dirname(SRC_DIR)                     # Thư mục gốc project
DATA_DIR = os.path.join(ROOT_DIR, 'data')

# Các file paths
RAW_CSV_PATH = os.path.join(DATA_DIR, 'batdongsan_data.csv')
CLEANED_DATA_PATH = os.path.join(DATA_DIR, 'cleaned_data.csv')

# Đã cập nhật lại MODEL_PATH theo cấu trúc chuẩn lưu ở thư mục models/
MODEL_PATH = os.path.join(ROOT_DIR, 'models', 'house_price_model.pkl')
XGB_MODEL_PATH = os.path.join(ROOT_DIR, 'models', 'xgb_house_price_model.pkl')
CATBOOST_MODEL_PATH = os.path.join(ROOT_DIR, 'models', 'catboost_house_price_model.pkl')
ENSEMBLE_MODEL_PATH = os.path.join(ROOT_DIR, 'models', 'ensemble_champion.joblib')

# Đảm bảo thư mục lưu trữ luôn tồn tại
os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(os.path.dirname(MODEL_PATH), exist_ok=True)