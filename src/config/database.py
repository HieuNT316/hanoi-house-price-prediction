# src/config/database.py
import os
from dotenv import load_dotenv

# Tự động tìm và load các biến từ file .env ở thư mục gốc vào os.environ
load_dotenv()

# Lấy thông tin từ biến môi trường
DB_USER = os.getenv("DB_USER")
DB_PASS = os.getenv("DB_PASS")
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", "5432")
DB_NAME = os.getenv("DB_NAME", "real_estate_db")

if all([DB_USER, DB_PASS, DB_HOST]):
    POSTGRES_URI = f"postgresql://{DB_USER}:{DB_PASS}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
else:
    print("⚠️ Cảnh báo: Thiếu thông tin DB trong file .env hoặc chưa load được biến môi trường")
    POSTGRES_URI = None