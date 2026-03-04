# src/config/database.py
import streamlit as st
import urllib.parse
from dotenv import load_dotenv
from .get_config import get_config

# Tự động tìm và load các biến từ file .env ở thư mục gốc vào os.environ
load_dotenv()

# Lấy thông tin từ biến môi trường
DB_USER = get_config("DB_USER")
DB_PASS = get_config("DB_PASS")
DB_HOST = get_config("DB_HOST")
DB_PORT = get_config("DB_PORT")
DB_NAME = get_config("DB_NAME")

print(f"🔍 Đang cấu hình Database với: {DB_USER}@{DB_HOST}:{DB_PORT}/{DB_NAME}")

# Mã hóa Username và Password để tránh lỗi ký tự đặc biệt (@, ., :)
encoded_user = urllib.parse.quote_plus(DB_USER)
encoded_pass = urllib.parse.quote_plus(DB_PASS)

if all([DB_USER, DB_PASS, DB_HOST]):
    POSTGRES_URI = f"postgresql://{encoded_user}:{encoded_pass}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
else:
    print("⚠️ Cảnh báo: Thiếu thông tin DB trong file .env hoặc chưa load được biến môi trường")
    POSTGRES_URI = None