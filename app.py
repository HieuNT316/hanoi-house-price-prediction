# app.py
import streamlit as st
import os
from streamlit_float import *
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# --- IMPORT MODULES CỦA BẠN ---
from src.ai_engine.chatbot import render_chatbot
from src.ui.dashboard import render_dashboard
from src.ui.prediction import render_prediction
from src.database.postgres_manager import PostgresManager # Import module kết nối DB mới

# --- CẤU HÌNH TRANG ---
st.set_page_config(page_title="Bất Động Sản Hà Đông", layout="wide", page_icon="🏠")
float_init() 

# --- HÀM LOAD DỮ LIỆU TỪ POSTGRESQL ---
@st.cache_data(ttl=3600) # Cache dữ liệu 1 tiếng để web chạy nhanh, không query DB liên tục
def load_data():
    try:
        db = PostgresManager()
        # Query toàn bộ bảng listings
        query = "SELECT * FROM listings"
        df = db.load_dataframe(query)
        
        # Nếu DB chưa có dữ liệu, trả về None
        if df is None or df.empty:
            return None
            
        return df
    except Exception as e:
        st.error(f"❌ Lỗi kết nối Database: {e}")
        return None

# GIAO DIỆN CHÍNH (MAIN APP)
st.title("🏡 Hệ Thống Phân Tích & Định Giá BĐS Hà Đông")

# 1. Load dữ liệu tổng từ DB
df = load_data()

if df is None:
    st.error("❌ Chưa có dữ liệu hoặc không thể kết nối PostgreSQL. Vui lòng kiểm tra Database và chạy luồng ETL (cleaner.py) trước!")
    st.stop()

# 2. Render Tabs
tab1, tab2 = st.tabs(["📊 Thống Kê Thị Trường", "🔮 AI Định Giá"])

with tab1:
    render_dashboard(df)

with tab2:
    render_prediction(df)

# CHATBOT (MODULE RIÊNG)
API_KEY = os.getenv("GEMINI_API_KEY")

if API_KEY:
    try:
        render_chatbot(df, API_KEY)
    except Exception as e:
        st.error(f"❌ Lỗi khi khởi tạo Chatbot: {e}")
else:
    # Cập nhật lại câu cảnh báo cho đúng với cơ chế file .env
    st.warning("⚠️ Chưa cấu hình GEMINI_API_KEY trong file `.env`. Chatbot hiện đang bị vô hiệu hóa.")