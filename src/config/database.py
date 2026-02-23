# src/config/database.py
import os
import toml

# 1. Định vị chính xác file secrets.toml dựa trên vị trí file code hiện tại
CONFIG_DIR = os.path.dirname(os.path.abspath(__file__)) # Đang ở src/config/
SRC_DIR = os.path.dirname(CONFIG_DIR)                   # Lùi ra src/
ROOT_DIR = os.path.dirname(SRC_DIR)                     # Lùi ra realtime_estimate_tracker/
SECRETS_PATH = os.path.join(ROOT_DIR, '.streamlit', 'secrets.toml')

try:
    # 2. Đọc file bằng thư viện toml chuẩn của Python (Bỏ qua Streamlit)
    with open(SECRETS_PATH, 'r', encoding='utf-8') as f:
        secrets = toml.load(f)

    # 3. Lấy thông tin
    DB_USER = secrets.get("DB_USER") 
    DB_PASS = secrets.get("DB_PASS")
    DB_HOST = secrets.get("DB_HOST", "localhost")
    DB_PORT = "5432"
    DB_NAME = "real_estate_db"

    if all([DB_USER, DB_PASS, DB_HOST]):
        POSTGRES_URI = f"postgresql://{DB_USER}:{DB_PASS}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
    else:
        raise ValueError("Thiếu thông tin DB trong file secrets.toml")

except FileNotFoundError:
    print(f"⚠️ Cảnh báo: Không tìm thấy file tại {SECRETS_PATH}")
    POSTGRES_URI = None
except Exception as e:
    print(f"⚠️ Lỗi đọc file cấu hình database: {e}")
    POSTGRES_URI = None